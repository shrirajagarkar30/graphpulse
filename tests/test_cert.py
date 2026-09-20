"""Tests for Free-Update Certificate and Fallback Maintainer (Milestone 3.2).

Covers test cases T3.2-01 through T3.2-09 per PLAYBOOK.md §Milestone 3.2.
"""

from __future__ import annotations

import json
from pathlib import Path
import pytest

from graphpulse.dijkstra import INF, dijkstra
from graphpulse.generators import (
    Update,
    grid,
    hub_spoke,
    random_sparse,
    random_updates,
)
from graphpulse.graph import DiGraph
from graphpulse.harness import run_differential
from graphpulse.maintainer import Maintainer, RecomputeMaintainer, UpdateStats
from graphpulse.opcount import OpCounter
from graphpulse.repair import RepairMaintainer
from graphpulse.verify import check_state

GOLDEN_DIR = Path(__file__).parent / "golden"


def load_golden(name: str) -> dict:
    with open(GOLDEN_DIR / name, encoding="utf-8") as f:
        return json.load(f)


def graph_from_golden(data: dict) -> DiGraph:
    g = DiGraph(data["n"])
    for u, v, w in data["edges"]:
        g.add_edge(u, v, w)
    return g


# ---------------------------------------------------------------------------
# T3.2-01: Non-tight deletion (positive)
# ---------------------------------------------------------------------------

def test_t32_01_non_tight_deletion():
    """T3.2-01: Deleting a non-tight edge triggers 'cert', work==1, state invariant."""
    data = load_golden("g1_diamond.json")
    g = graph_from_golden(data)
    # Add a heavy non-tight edge 0 -> 3 with weight 10
    g.add_edge(0, 3, 10)

    maintainer = RepairMaintainer(g, src=0)
    init_dist = maintainer.dist()
    init_parent = maintainer.parent()
    init_tight = list(maintainer.state.tight)

    # Delete non-tight edge 0 -> 3
    stats = maintainer.apply(Update(kind="delete", u=0, v=3))

    assert stats.strategy == "cert"
    assert stats.work == 1
    assert stats.scan == 1
    assert stats.push == 0
    assert stats.pop == 0
    assert stats.queue == 0

    assert maintainer.dist() == init_dist
    assert maintainer.parent() == init_parent
    assert maintainer.state.tight == init_tight
    check_state(maintainer.graph, maintainer.state)


# ---------------------------------------------------------------------------
# T3.2-02: Unreachable tail (edge case)
# ---------------------------------------------------------------------------

def test_t32_02_unreachable_tail():
    """T3.2-02: Edge with unreachable tail (dist[u] == INF) is a certificate hit."""
    # g3 has unreachable vertex 4. Add edge from 4 to 1 (w=3)
    data = load_golden("g3_unreachable.json")
    g = graph_from_golden(data)
    g.add_edge(4, 1, 3)

    maintainer = RepairMaintainer(g, src=0)
    assert maintainer.dist()[4] == INF

    stats = maintainer.apply(Update(kind="delete", u=4, v=1))

    assert stats.strategy == "cert"
    assert stats.work == 1
    assert stats.scan == 1
    check_state(maintainer.graph, maintainer.state)


# ---------------------------------------------------------------------------
# T3.2-03: Alternative support (positive)
# ---------------------------------------------------------------------------

def test_t32_03_alternative_support():
    """T3.2-03: Delete tight edge when tight[v]>1 updates parent and decrements tight."""
    data = load_golden("g1_diamond.json")
    g = graph_from_golden(data)
    maintainer = RepairMaintainer(g, src=0)

    # In g1, tight[3] == 2 (in-edges from 1 and 2, both tight).
    # Initial parent[3] == min(1, 2) == 1.
    assert maintainer.state.tight[3] == 2
    assert maintainer.parent()[3] == 1
    assert 3 in maintainer.state.children[1]

    # Delete 1 -> 3
    stats = maintainer.apply(Update(kind="delete", u=1, v=3))

    assert stats.strategy == "alt"
    assert maintainer.dist() == [0, 1, 1, 2]
    assert maintainer.state.tight[3] == 1
    # Smallest remaining tight in-neighbor is 2
    assert maintainer.parent()[3] == 2
    assert 3 not in maintainer.state.children[1]
    assert 3 in maintainer.state.children[2]

    # Work: 1 initial cert check + 1 scan of remaining in-edge (2 -> 3)
    assert stats.work == 2
    assert stats.scan == 2

    check_state(maintainer.graph, maintainer.state)


# ---------------------------------------------------------------------------
# T3.2-04: Alternative, edge was not the parent (edge case)
# ---------------------------------------------------------------------------

def test_t32_04_alternative_not_parent():
    """T3.2-04: When deleted tight edge is not parent[v], parent stays unchanged."""
    data = load_golden("g1_diamond.json")
    g = graph_from_golden(data)
    maintainer = RepairMaintainer(g, src=0)

    # Initial parent[3] == 1. Delete 2 -> 3 (which was tight, but not the parent).
    assert maintainer.parent()[3] == 1
    assert maintainer.state.tight[3] == 2

    stats = maintainer.apply(Update(kind="delete", u=2, v=3))

    assert stats.strategy == "alt"
    assert stats.work == 1  # 1 scan only; no in-edge scan required
    assert stats.scan == 1
    assert maintainer.parent()[3] == 1
    assert maintainer.state.tight[3] == 1
    assert maintainer.dist() == [0, 1, 1, 2]

    check_state(maintainer.graph, maintainer.state)


# ---------------------------------------------------------------------------
# T3.2-05: Increase with alternative (positive)
# ---------------------------------------------------------------------------

def test_t32_05_increase_with_alternative():
    """T3.2-05: Weight increase on tight edge invalidates tightness, handled like delete."""
    data = load_golden("g1_diamond.json")
    g = graph_from_golden(data)
    maintainer = RepairMaintainer(g, src=0)

    assert maintainer.state.tight[3] == 2
    assert maintainer.parent()[3] == 1

    # Increase weight of 1 -> 3 from 1 to 5 (no longer tight)
    stats = maintainer.apply(Update(kind="increase", u=1, v=3, new_w=5))

    assert stats.strategy == "alt"
    assert maintainer.dist() == [0, 1, 1, 2]
    assert maintainer.state.tight[3] == 1
    assert maintainer.parent()[3] == 2
    assert 3 not in maintainer.state.children[1]
    assert 3 in maintainer.state.children[2]

    check_state(maintainer.graph, maintainer.state)


# ---------------------------------------------------------------------------
# T3.2-06: Sole tight edge falls back (integration)
# ---------------------------------------------------------------------------

def test_t32_06_sole_tight_edge_falls_back():
    """T3.2-06: Losing the sole tight in-edge triggers 'rebuild' strategy."""
    data = load_golden("g2_chain.json")
    g = graph_from_golden(data)
    maintainer = RepairMaintainer(g, src=0)

    # g2: 0 -> 1 (w=2), 1 -> 2 (w=3), 2 -> 3 (w=4).
    # tight[2] == 1, parent[2] == 1.
    assert maintainer.state.tight[2] == 1

    # Delete 1 -> 2
    stats = maintainer.apply(Update(kind="delete", u=1, v=2))

    assert stats.strategy in ("rebuild", "repair")
    assert stats.work > 1
    if stats.strategy == "rebuild":
        assert stats.push > 0
        assert stats.pop > 0

    # Distances after cutting 1 -> 2: vertices 2 and 3 are now unreachable
    assert maintainer.dist() == [0, 2, INF, INF]
    assert maintainer.parent() == [-1, 0, -1, -1]

    check_state(maintainer.graph, maintainer.state)


# ---------------------------------------------------------------------------
# T3.2-07: Edge into source (edge case)
# ---------------------------------------------------------------------------

def test_t32_07_edge_into_source():
    """T3.2-07: Deleting or increasing an edge into source is always a certificate hit."""
    g = DiGraph(3)
    g.add_edge(0, 1, 2)
    g.add_edge(1, 2, 3)
    g.add_edge(2, 0, 4)  # cycle back to source

    maintainer = RepairMaintainer(g, src=0)
    init_dist = maintainer.dist()

    # Deleting edge into source
    stats_del = maintainer.apply(Update(kind="delete", u=2, v=0))
    assert stats_del.strategy == "cert"
    assert stats_del.work == 1
    assert maintainer.dist() == init_dist
    check_state(maintainer.graph, maintainer.state)

    # Re-add and test increase into source
    maintainer.graph.add_edge(2, 0, 4)
    # Rebuild maintainer on updated graph
    maintainer = RepairMaintainer(maintainer.graph, src=0)
    stats_inc = maintainer.apply(Update(kind="increase", u=2, v=0, new_w=10))
    assert stats_inc.strategy == "cert"
    assert stats_inc.work == 1
    assert maintainer.dist() == init_dist
    check_state(maintainer.graph, maintainer.state)


# ---------------------------------------------------------------------------
# T3.2-08 & T3.2-09: Differential run & Stats consistency across 3 families
# ---------------------------------------------------------------------------

@pytest.mark.parametrize(
    "family_name,make_graph_fn,expect_alt",
    [
        ("grid", lambda: grid(rows=15, cols=15, seed=42, wmin=1, wmax=10), True),
        ("random_sparse", lambda: random_sparse(n=80, m=400, seed=42, wmin=1, wmax=10), True),
        ("hub_spoke", lambda: hub_spoke(hubs=10, spokes_per_hub=30, seed=42), False),
    ],
)
def test_t32_08_and_09_differential_and_stats(family_name, make_graph_fn, expect_alt):
    """T3.2-08 & T3.2-09: 2000 mixed updates on 3 graph families with zero mismatches,
    check_state verified after every step, and stats consistency checked.
    """
    g = make_graph_fn()
    src = 0
    num_updates = 2000
    updates = random_updates(g, count=num_updates, seed=42, mode="uniform", p_delete=0.1)

    ref = RecomputeMaintainer(make_graph_fn(), src)
    cand = RepairMaintainer(make_graph_fn(), src)

    # Initial state agreement
    assert cand.dist() == ref.dist()
    check_state(cand.graph, cand.state)

    strategy_counts = {"cert": 0, "alt": 0, "rebuild": 0, "repair": 0}

    for i, upd in enumerate(updates):
        ref.apply(upd)
        cand_stats = cand.apply(upd)

        # T3.2-08: Distances match trusted Dijkstra baseline after every update
        ref_dist = ref.dist()
        cand_dist = cand.dist()
        assert cand_dist == ref_dist, (
            f"[{family_name}] Step {i}: distance mismatch after update {upd}"
        )

        # check_state passes after every update
        check_state(cand.graph, cand.state)

        # Accumulate strategy stats
        assert cand_stats.strategy in strategy_counts
        strategy_counts[cand_stats.strategy] += 1

    # T3.2-09: Sum of strategy counts equals total number of updates
    total_strategies = sum(strategy_counts.values())
    assert total_strategies == len(updates) == num_updates, (
        f"Strategy sum {total_strategies} != total updates {num_updates}"
    )

    # Strategy coverage
    assert strategy_counts["cert"] > 0
    assert (strategy_counts["rebuild"] > 0 or strategy_counts["repair"] > 0)
    if expect_alt:
        assert strategy_counts["alt"] > 0


# ---------------------------------------------------------------------------
# Informational: Certificate hit rate on 30x30 grid (Verification Checklist)
# ---------------------------------------------------------------------------

def test_t32_cert_hit_rate_30x30_grid(capsys):
    """Verification checklist: Certificate hit rate on 30x30 grid with 1000 uniform deletions."""
    g = grid(rows=30, cols=30, seed=999, wmin=1, wmax=10)
    updates = random_updates(g, count=1000, seed=999, mode="uniform", p_delete=1.0)
    maintainer = RepairMaintainer(g, src=0)

    cert_hits = 0
    for upd in updates:
        stats = maintainer.apply(upd)
        if stats.strategy == "cert":
            cert_hits += 1

    hit_rate = (cert_hits / 1000.0) * 100.0
    # Informational output (captured by capsys or pytest -s)
    print(f"\n[30x30 Grid] Certificate hit rate: {hit_rate:.2f}% ({cert_hits}/1000 deletions)")
    assert 0.0 <= hit_rate <= 100.0
    assert cert_hits > 500  # Majority of edges in 2D grid are non-tight
