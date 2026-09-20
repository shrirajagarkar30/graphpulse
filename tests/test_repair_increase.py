"""Tests for Milestone 3.5: Incremental repair for edge weight increases.

Covers T3.5-01 through T3.5-09:
- T3.5-01: Increase, edge stays best (positive)
- T3.5-02: Increase, alternative wins (positive)
- T3.5-03: Non-tight increase (edge case)
- T3.5-04: Tight with alternative (edge case)
- T3.5-05: Edge becomes tight again (edge case)
- T3.5-06: Invalid increase (negative)
- T3.5-07: Mixed differential run (regression, 100,000 total mixed updates across 5 seeds)
- T3.5-08: Deletion tests (regression)
- T3.5-09: Huge increase (edge case)
"""

from __future__ import annotations

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
from graphpulse.maintainer import RecomputeMaintainer
from graphpulse.opcount import OpCounter
from graphpulse.repair import RepairMaintainer
from graphpulse.verify import check_state


# ---------------------------------------------------------------------------
# T3.5-01: Increase, edge stays best (positive)
# ---------------------------------------------------------------------------

def test_t35_01_increase_edge_stays_best():
    """T3.5-01: Chain graph, increase middle edge by 5; downstream distances rise by exactly 5."""
    g = DiGraph(4)
    g.add_edge(0, 1, 2)
    g.add_edge(1, 2, 3)
    g.add_edge(2, 3, 4)

    maintainer = RepairMaintainer(g, src=0)
    old_dist = maintainer.dist()
    assert old_dist == [0, 2, 5, 9]

    # Increase 1 -> 2 from w=3 to w=8 (+5)
    stats = maintainer.apply(Update(kind="increase", u=1, v=2, new_w=8))

    assert stats.strategy == "repair"
    new_dist = maintainer.dist()
    # Unaffected: vertices 0 and 1
    assert new_dist[0] == old_dist[0]
    assert new_dist[1] == old_dist[1]
    # Downstream vertices 2 and 3 rise by exactly 5
    assert new_dist[2] == old_dist[2] + 5 == 10
    assert new_dist[3] == old_dist[3] + 5 == 14

    ref_dist, _ = dijkstra(maintainer.graph, 0, OpCounter())
    assert maintainer.dist() == ref_dist
    check_state(maintainer.graph, maintainer.state)


# ---------------------------------------------------------------------------
# T3.5-02: Increase, alternative wins (positive)
# ---------------------------------------------------------------------------

def test_t35_02_increase_alternative_wins():
    """T3.5-02: Chain with detour; increase past the detour, distances use the detour."""
    g = DiGraph(4)
    g.add_edge(0, 1, 2)
    g.add_edge(1, 2, 3)  # dist[2] = 5
    g.add_edge(2, 3, 4)  # dist[3] = 9
    # Detour: 0 -> 2 with weight 10 (heavier than 5 initially)
    g.add_edge(0, 2, 10)

    maintainer = RepairMaintainer(g, src=0)
    assert maintainer.dist()[2] == 5
    assert maintainer.state.parent[2] == 1

    # Increase 1 -> 2 to 20 (> 10 detour)
    stats = maintainer.apply(Update(kind="increase", u=1, v=2, new_w=20))

    assert stats.strategy == "repair"
    assert maintainer.dist() == [0, 2, 10, 14]
    # Detour 0 -> 2 is now the parent of 2
    assert maintainer.state.parent[2] == 0
    assert maintainer.state.parent[3] == 2
    assert maintainer.state.tight[2] == 1

    ref_dist, _ = dijkstra(maintainer.graph, 0, OpCounter())
    assert maintainer.dist() == ref_dist
    check_state(maintainer.graph, maintainer.state)


# ---------------------------------------------------------------------------
# T3.5-03: Non-tight increase (edge case)
# ---------------------------------------------------------------------------

def test_t35_03_non_tight_increase():
    """T3.5-03: Increasing a non-tight edge triggers certificate hit with work == 1."""
    g = DiGraph(4)
    g.add_edge(0, 1, 2)
    g.add_edge(1, 2, 3)  # dist[2] = 5
    g.add_edge(2, 3, 4)
    g.add_edge(0, 2, 10)  # non-tight: 0 + 10 > 5

    maintainer = RepairMaintainer(g, src=0)
    old_dist = maintainer.dist()

    # Increase non-tight edge 0 -> 2 from 10 to 15
    stats = maintainer.apply(Update(kind="increase", u=0, v=2, new_w=15))

    assert stats.strategy == "cert"
    assert stats.work == 1
    assert stats.scan == 1
    assert maintainer.dist() == old_dist
    check_state(maintainer.graph, maintainer.state)


# ---------------------------------------------------------------------------
# T3.5-04: Tight with alternative (edge case)
# ---------------------------------------------------------------------------

def test_t35_04_tight_with_alternative():
    """T3.5-04: Diamond where vertex 3 has 2 tight predecessors; increase one branch."""
    g = DiGraph(4)
    g.add_edge(0, 1, 2)
    g.add_edge(0, 2, 2)
    g.add_edge(1, 3, 2)  # dist[3] = 4 via 1
    g.add_edge(2, 3, 2)  # dist[3] = 4 via 2

    maintainer = RepairMaintainer(g, src=0)
    assert maintainer.dist()[3] == 4
    assert maintainer.state.tight[3] == 2
    assert maintainer.state.parent[3] == 1  # min(1, 2)

    # Increase 1 -> 3 from 2 to 5: loses tightness, but 2 -> 3 remains tight
    stats = maintainer.apply(Update(kind="increase", u=1, v=3, new_w=5))

    assert stats.strategy == "alt"
    assert maintainer.dist()[3] == 4  # distance unchanged!
    assert maintainer.state.tight[3] == 1  # decremented to 1
    assert maintainer.state.parent[3] == 2  # re-parented to 2
    assert 3 in maintainer.state.children[2]
    assert 3 not in maintainer.state.children[1]

    ref_dist, _ = dijkstra(maintainer.graph, 0, OpCounter())
    assert maintainer.dist() == ref_dist
    check_state(maintainer.graph, maintainer.state)


# ---------------------------------------------------------------------------
# T3.5-05: Edge becomes tight again (edge case)
# ---------------------------------------------------------------------------

def test_t35_05_edge_becomes_tight_again():
    """T3.5-05: After an increase where the edge stays best, it is counted as tight for v."""
    g = DiGraph(4)
    g.add_edge(0, 1, 2)
    g.add_edge(1, 2, 3)
    g.add_edge(2, 3, 4)

    maintainer = RepairMaintainer(g, src=0)
    # Increase 1 -> 2 from 3 to 7
    maintainer.apply(Update(kind="increase", u=1, v=2, new_w=7))

    # In-edge 1 -> 2 has new weight 7: dist[1] + 7 = 2 + 7 = 9 == dist[2]
    assert maintainer.state.tight[2] == 1
    assert maintainer.state.parent[2] == 1
    assert 2 in maintainer.state.children[1]
    check_state(maintainer.graph, maintainer.state)


# ---------------------------------------------------------------------------
# T3.5-06: Invalid increase (negative)
# ---------------------------------------------------------------------------

def test_t35_06_invalid_increase():
    """T3.5-06: Increase with new_w <= old_w is rejected; maintainer state is unchanged."""
    g = DiGraph(3)
    g.add_edge(0, 1, 2)
    g.add_edge(1, 2, 5)

    maintainer = RepairMaintainer(g, src=0)
    old_dist = maintainer.dist()
    old_parent = maintainer.parent()

    # Attempt increase with equal weight 5
    with pytest.raises(ValueError, match="new_w=5 must be > old_w=5"):
        maintainer.apply(Update(kind="increase", u=1, v=2, new_w=5))

    # Attempt increase with smaller weight 4
    with pytest.raises(ValueError, match="new_w=4 must be > old_w=5"):
        maintainer.apply(Update(kind="increase", u=1, v=2, new_w=4))

    # Maintainer state is completely unchanged
    assert maintainer.dist() == old_dist
    assert maintainer.parent() == old_parent
    assert maintainer.graph.weight(1, 2) == 5
    check_state(maintainer.graph, maintainer.state)


# ---------------------------------------------------------------------------
# T3.5-07: Mixed differential run across seeds (100,000 total mixed updates)
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("seed", [0, 1, 2, 3, 4])
def test_t35_07_mixed_differential_run(seed: int):
    """T3.5-07: 20,000 mixed updates (p_delete=0.5) across 3 families per seed (100,000 total).

    Zero mismatches against RecomputeMaintainer; check_state passes after every step.
    """
    # 7,000 grid updates, 7,000 random_sparse updates, 6,000 hub_spoke updates = 20,000 per seed
    families = [
        ("grid", grid(rows=45, cols=45, seed=seed, wmin=1, wmax=10), 7000),
        ("random_sparse", random_sparse(n=400, m=7000, seed=seed, wmin=1, wmax=10), 7000),
        ("hub_spoke", hub_spoke(hubs=20, spokes_per_hub=250, seed=seed), 6000),
    ]

    total_updates = 0

    for fam_name, g, count in families:
        updates = random_updates(
            g, count=count, seed=seed, mode="uniform", p_delete=0.5, w_increase_max=50
        )
        assert len(updates) == count, f"Failed to generate {count} updates for {fam_name}"

        cand = RepairMaintainer(g, src=0)
        ref = RecomputeMaintainer(g, src=0)

        for i, upd in enumerate(updates):
            ref.apply(upd)
            cand.apply(upd)

            assert cand.dist() == ref.dist(), (
                f"[{fam_name} seed={seed}] Mismatch at update {i}: {upd}"
            )
            check_state(cand.graph, cand.state)
            total_updates += 1

    assert total_updates == 20000


# ---------------------------------------------------------------------------
# T3.5-08: Deletion tests (regression)
# ---------------------------------------------------------------------------

def test_t35_08_deletion_tests_regression():
    """T3.5-08: Re-run all Milestone 3.4 deletion tests to ensure no regression."""
    from tests.test_repair_delete import (
        test_t34_01_chain_repair_positive,
        test_t34_02_disconnection,
        test_t34_03_adversarial_comb,
        test_t34_04_non_affected_child_reparented,
        test_t34_05_small_repair_beats_rebuild,
        test_t34_07_earlier_behavior_regression,
        test_t34_08_deleting_to_empty,
        test_t34_09_nested_diamonds,
    )

    test_t34_01_chain_repair_positive()
    test_t34_02_disconnection()
    test_t34_03_adversarial_comb()
    test_t34_04_non_affected_child_reparented()
    test_t34_05_small_repair_beats_rebuild()
    test_t34_07_earlier_behavior_regression()
    test_t34_08_deleting_to_empty()
    test_t34_09_nested_diamonds()


# ---------------------------------------------------------------------------
# T3.5-09: Huge increase (edge case)
# ---------------------------------------------------------------------------

def test_t35_09_huge_increase():
    """T3.5-09: Huge weight increase (10^12); behaves like deletion, no overflow."""
    g = DiGraph(4)
    g.add_edge(0, 1, 2)
    g.add_edge(1, 2, 3)
    g.add_edge(2, 3, 4)
    # Detour edge 0 -> 2 with weight 100
    g.add_edge(0, 2, 100)

    maintainer = RepairMaintainer(g, src=0)
    huge_w = 10**12

    stats = maintainer.apply(Update(kind="increase", u=1, v=2, new_w=huge_w))

    assert stats.strategy == "repair"
    # Vertex 2 takes the detour (0 -> 2, w=100)
    assert maintainer.dist() == [0, 2, 100, 104]
    assert maintainer.state.parent == [-1, 0, 0, 2]
    assert maintainer.state.tight == [0, 1, 1, 1]

    ref_dist, _ = dijkstra(maintainer.graph, 0, OpCounter())
    assert maintainer.dist() == ref_dist
    check_state(maintainer.graph, maintainer.state)
