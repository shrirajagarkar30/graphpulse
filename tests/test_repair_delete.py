"""Tests for Milestone 3.4: Incremental repair for edge deletions.

Covers T3.4-01 through T3.4-09:
- T3.4-01: Chain repair (positive)
- T3.4-02: Disconnection (edge case)
- T3.4-03: Adversarial comb (integration)
- T3.4-04: Non-affected child re-parented (edge case)
- T3.4-05: Small repair beats rebuild (validation)
- T3.4-06: Differential run (regression, 25,000 total deletions across 5 seeds)
- T3.4-07: Earlier behavior (regression)
- T3.4-08: Deleting to empty (edge case)
- T3.4-09: Nested diamonds (edge case)
"""

from __future__ import annotations

import pytest

from graphpulse.dijkstra import INF, dijkstra
from graphpulse.generators import (
    Update,
    comb_adversarial,
    grid,
    hub_spoke,
    random_sparse,
    random_updates,
)
from graphpulse.graph import DiGraph
from graphpulse.maintainer import RecomputeMaintainer
from graphpulse.opcount import OpCounter
from graphpulse.repair import RepairMaintainer
from graphpulse.verify import check_state


# ---------------------------------------------------------------------------
# T3.4-01: Chain repair (positive)
# ---------------------------------------------------------------------------

def test_t34_01_chain_repair_positive():
    """T3.4-01: g2 with a detour edge 0->3; delete 1->2.

    Distances match a fresh Dijkstra; check_state passes.
    """
    g = DiGraph(4)
    g.add_edge(0, 1, 2)
    g.add_edge(1, 2, 3)
    g.add_edge(2, 3, 4)
    # Add detour edge 0 -> 3 with weight 10
    g.add_edge(0, 3, 10)

    maintainer = RepairMaintainer(g, src=0)
    assert maintainer.dist() == [0, 2, 5, 9]
    assert maintainer.state.tight[3] == 1

    # Delete 1 -> 2
    stats = maintainer.apply(Update(kind="delete", u=1, v=2))

    assert stats.strategy == "repair"
    # Vertex 2 has become unreachable; vertex 3 routed via detour 0->3 (w=10)
    assert maintainer.dist() == [0, 2, INF, 10]
    assert maintainer.state.parent == [-1, 0, -1, 0]
    assert maintainer.state.tight == [0, 1, 0, 1]

    ref_dist, _ = dijkstra(maintainer.graph, 0, OpCounter())
    assert maintainer.dist() == ref_dist
    check_state(maintainer.graph, maintainer.state)


# ---------------------------------------------------------------------------
# T3.4-02: Disconnection (edge case)
# ---------------------------------------------------------------------------

def test_t34_02_disconnection():
    """T3.4-02: Chain graph, delete 0->1.

    All affected vertices {1, 2, 3} become dist=INF, parent=-1, tight=0.
    """
    g = DiGraph(4)
    g.add_edge(0, 1, 2)
    g.add_edge(1, 2, 3)
    g.add_edge(2, 3, 4)

    maintainer = RepairMaintainer(g, src=0)
    stats = maintainer.apply(Update(kind="delete", u=0, v=1))

    assert stats.strategy == "repair"
    assert maintainer.last_affected == {1, 2, 3}
    assert maintainer.dist() == [0, INF, INF, INF]
    assert maintainer.state.parent == [-1, -1, -1, -1]
    assert maintainer.state.tight == [0, 0, 0, 0]
    for c in maintainer.state.children:
        assert len(c) == 0

    ref_dist, _ = dijkstra(maintainer.graph, 0, OpCounter())
    assert maintainer.dist() == ref_dist
    check_state(maintainer.graph, maintainer.state)


# ---------------------------------------------------------------------------
# T3.4-03: Adversarial comb (integration)
# ---------------------------------------------------------------------------

def test_t34_03_adversarial_comb():
    """T3.4-03: comb_adversarial(200), delete (0, 1).

    Repair recomputes distances correctly and work is of the same order as a full Dijkstra.
    """
    n = 200
    g = comb_adversarial(n=n, seed=42)
    maintainer = RepairMaintainer(g, src=0)
    f_ops = maintainer.state.F_ops

    stats = maintainer.apply(Update(kind="delete", u=0, v=1))

    assert stats.strategy == "repair"
    assert maintainer.last_affected == set(range(1, n))

    ref_dist, _ = dijkstra(maintainer.graph, 0, OpCounter())
    assert maintainer.dist() == ref_dist
    check_state(maintainer.graph, maintainer.state)

    # Work is of the same order as a full Dijkstra (within a small constant factor of F_ops)
    assert stats.work > 0
    assert stats.work <= 5 * f_ops


# ---------------------------------------------------------------------------
# T3.4-04: Non-affected child re-parented (edge case)
# ---------------------------------------------------------------------------

def test_t34_04_non_affected_child_reparented():
    """T3.4-04: Vertex whose parent enters A but keeps another tight edge.

    New parent chosen from a non-affected tight in-neighbor.
    """
    g = DiGraph(5)
    g.add_edge(0, 1, 2)
    g.add_edge(1, 2, 2)  # dist[2] = 4
    g.add_edge(0, 4, 4)  # dist[4] = 4
    g.add_edge(2, 3, 2)  # dist[3] = 6 via 2
    g.add_edge(4, 3, 2)  # dist[3] = 6 via 4

    maintainer = RepairMaintainer(g, src=0)
    assert maintainer.dist()[3] == 6
    assert maintainer.state.tight[3] == 2
    # Deterministic parent selection picks min(tight_preds) = min(2, 4) = 2
    assert maintainer.state.parent[3] == 2

    # Delete 1 -> 2: 2 loses sole tight edge from 1, so 2 enters A
    stats = maintainer.apply(Update(kind="delete", u=1, v=2))

    assert stats.strategy == "repair"
    assert maintainer.last_affected == {2}
    # Vertex 3 keeps distance 6 via 4 -> 3
    assert maintainer.dist()[3] == 6
    assert maintainer.state.tight[3] == 1
    assert maintainer.state.parent[3] == 4  # re-parented to 4
    assert 3 in maintainer.state.children[4]
    assert 3 not in maintainer.state.children[2]

    ref_dist, _ = dijkstra(maintainer.graph, 0, OpCounter())
    assert maintainer.dist() == ref_dist
    check_state(maintainer.graph, maintainer.state)


# ---------------------------------------------------------------------------
# T3.4-05: Small repair beats rebuild (validation)
# ---------------------------------------------------------------------------

def test_t34_05_small_repair_beats_rebuild():
    """T3.4-05: Grid 30x30, delete a leaf-adjacent tight edge.

    Repair work is strictly less than F (in fact an order of magnitude smaller).
    """
    g = grid(rows=30, cols=30, seed=42, wmin=1, wmax=10)
    maintainer = RepairMaintainer(g, src=0)
    f_ops = maintainer.state.F_ops

    # Find a leaf vertex v in the SPT with tight[v] == 1 and no children
    leaf_v = None
    for v in range(1, g.n):
        if maintainer.state.tight[v] == 1 and len(maintainer.state.children[v]) == 0:
            leaf_v = v
            break
    assert leaf_v is not None, "Could not find leaf vertex in SPT"

    parent_v = maintainer.state.parent[leaf_v]
    stats = maintainer.apply(Update(kind="delete", u=parent_v, v=leaf_v))

    assert stats.strategy == "repair"
    # Repair only explores the neighborhood of {leaf_v}
    assert stats.work < f_ops
    assert stats.work < f_ops // 10, f"Work {stats.work} not < {f_ops // 10}"

    ref_dist, _ = dijkstra(maintainer.graph, 0, OpCounter())
    assert maintainer.dist() == ref_dist
    check_state(maintainer.graph, maintainer.state)


# ---------------------------------------------------------------------------
# T3.4-06: Differential run across seeds (25,000 total deletions)
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("seed", [0, 1, 2, 3, 4])
def test_t34_06_differential_run(seed: int):
    """T3.4-06: 5000 deletions across 3 graph families for each seed (25,000 total).

    Zero mismatches against RecomputeMaintainer; check_state passes after every step.
    """
    # 2000 grid deletions, 2000 random_sparse deletions, 1000 hub_spoke deletions = 5000 per seed
    families = [
        ("grid", grid(rows=30, cols=30, seed=seed, wmin=1, wmax=10), 2000),
        ("random_sparse", random_sparse(n=300, m=2500, seed=seed, wmin=1, wmax=10), 2000),
        ("hub_spoke", hub_spoke(hubs=10, spokes_per_hub=150, seed=seed), 1000),
    ]

    total_deletions = 0

    for fam_name, g, count in families:
        updates = random_updates(g, count=count, seed=seed, mode="uniform", p_delete=1.0)
        assert len(updates) == count, f"Failed to generate {count} deletions for {fam_name}"

        cand = RepairMaintainer(g, src=0)
        ref = RecomputeMaintainer(g, src=0)

        for i, upd in enumerate(updates):
            ref.apply(upd)
            cand.apply(upd)

            assert cand.dist() == ref.dist(), (
                f"[{fam_name} seed={seed}] Mismatch at update {i}: {upd}"
            )
            check_state(cand.graph, cand.state)
            total_deletions += 1

    assert total_deletions == 5000


# ---------------------------------------------------------------------------
# T3.4-07: Earlier behavior (regression)
# ---------------------------------------------------------------------------

def test_t34_07_earlier_behavior_regression():
    """T3.4-07: Verify tests T3.2-01 to T3.2-09 remain valid with repair maintainer."""
    from tests.test_cert import (
        test_t32_01_non_tight_deletion,
        test_t32_02_unreachable_tail,
        test_t32_03_alternative_support,
        test_t32_04_alternative_not_parent,
        test_t32_05_increase_with_alternative,
        test_t32_06_sole_tight_edge_falls_back,
        test_t32_07_edge_into_source,
    )

    test_t32_01_non_tight_deletion()
    test_t32_02_unreachable_tail()
    test_t32_03_alternative_support()
    test_t32_04_alternative_not_parent()
    test_t32_05_increase_with_alternative()
    test_t32_06_sole_tight_edge_falls_back()
    test_t32_07_edge_into_source()


# ---------------------------------------------------------------------------
# T3.4-08: Deleting to empty (edge case)
# ---------------------------------------------------------------------------

def test_t34_08_deleting_to_empty():
    """T3.4-08: Repeatedly delete edges until the graph is empty.

    State remains valid at every step; all unreachable vertices have dist=INF, tight=0, parent=-1.
    """
    g = grid(rows=4, cols=4, seed=123, wmin=1, wmax=5)
    src = 0
    maintainer = RepairMaintainer(g, src=src)
    ref = RecomputeMaintainer(g, src=src)

    while maintainer.graph.m > 0:
        # Pick the first available edge to delete
        u, v = None, None
        for cand_u in range(maintainer.graph.n):
            for cand_v, _ in maintainer.graph.out_edges(cand_u):
                u, v = cand_u, cand_v
                break
            if u is not None:
                break

        upd = Update(kind="delete", u=u, v=v)
        ref.apply(upd)
        maintainer.apply(upd)

        assert maintainer.dist() == ref.dist()
        check_state(maintainer.graph, maintainer.state)

    assert maintainer.graph.m == 0
    # Final state: only source has finite distance
    for v in range(maintainer.graph.n):
        if v == src:
            assert maintainer.state.dist[v] == 0
            assert maintainer.state.parent[v] == -1
            assert maintainer.state.tight[v] == 0
        else:
            assert maintainer.state.dist[v] == INF
            assert maintainer.state.parent[v] == -1
            assert maintainer.state.tight[v] == 0
        assert len(maintainer.state.children[v]) == 0


# ---------------------------------------------------------------------------
# T3.4-09: Nested diamonds (edge case)
# ---------------------------------------------------------------------------

def test_t34_09_nested_diamonds():
    """T3.4-09: Chained diamond graph; delete early edges and check propagation."""
    # Build 3 chained diamonds:
    # Diamond 1: 0 -> (1, 2) -> 3
    # Diamond 2: 3 -> (4, 5) -> 6
    # Diamond 3: 6 -> (7, 8) -> 9
    g = DiGraph(10)
    # Diamond 1
    g.add_edge(0, 1, 2)
    g.add_edge(0, 2, 3)
    g.add_edge(1, 3, 2)  # dist[3] = 4 via 1
    g.add_edge(2, 3, 1)  # dist[3] = 4 via 2
    # Diamond 2
    g.add_edge(3, 4, 2)
    g.add_edge(3, 5, 3)
    g.add_edge(4, 6, 2)  # dist[6] = 8 via 4
    g.add_edge(5, 6, 1)  # dist[6] = 8 via 5
    # Diamond 3
    g.add_edge(6, 7, 2)
    g.add_edge(6, 8, 3)
    g.add_edge(7, 9, 2)  # dist[9] = 12 via 7
    g.add_edge(8, 9, 1)  # dist[9] = 12 via 8

    cand = RepairMaintainer(g, src=0)
    ref = RecomputeMaintainer(g, src=0)

    assert cand.dist() == ref.dist()
    check_state(cand.graph, cand.state)

    # Initial check: 3 has tight support from both 1 and 2
    assert cand.state.tight[3] == 2
    assert cand.state.parent[3] == 1  # min(1, 2)

    # Step 1: Delete 0 -> 1
    # 1 loses its sole tight edge from 0 (A = {1}).
    # 3 loses tight edge 1->3, but still has 2->3 (scratch_tight[3] = 1).
    # 3 is re-parented to 2. Subsequent diamonds are unaffected.
    upd1 = Update(kind="delete", u=0, v=1)
    stats1 = cand.apply(upd1)
    ref.apply(upd1)

    assert stats1.strategy == "repair"
    assert cand.last_affected == {1}
    assert cand.dist()[3] == 4
    assert cand.state.parent[3] == 2
    assert cand.state.tight[3] == 1
    assert cand.dist() == ref.dist()
    check_state(cand.graph, cand.state)

    # Step 2: Delete 0 -> 2
    # 2 is affected. Now 3 loses its remaining tight edge 2->3.
    # The entire downstream chain of diamonds becomes disconnected.
    upd2 = Update(kind="delete", u=0, v=2)
    stats2 = cand.apply(upd2)
    ref.apply(upd2)

    assert stats2.strategy == "repair"
    assert cand.dist() == ref.dist()
    # All nodes 1..9 are now unreachable
    for v in range(1, 10):
        assert cand.state.dist[v] == INF
        assert cand.state.parent[v] == -1
        assert cand.state.tight[v] == 0
    check_state(cand.graph, cand.state)
