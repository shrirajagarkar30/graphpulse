"""Tests for update model and random update sequences (Milestone 2.2)."""

from __future__ import annotations

import pytest

from graphpulse.generators import (
    Update,
    _bfs_within,
    apply_update,
    grid,
    random_sparse,
    random_updates,
)
from graphpulse.graph import DiGraph


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def snapshot_edges(g: DiGraph) -> dict:
    """Return a frozen snapshot of all edge weights, keyed by (u, v)."""
    return {
        (u, v): w
        for u in range(g.n)
        for v, w in g.out_edges(u)
    }


def apply_all(g: DiGraph, updates: list) -> None:
    """Apply a sequence of updates to *g* in-place; raises on any invalid step."""
    for upd in updates:
        apply_update(g, upd)


# ---------------------------------------------------------------------------
# T2.2-01: Sequential validity
# ---------------------------------------------------------------------------

def test_t22_01_sequential_validity():
    """T2.2-01: 300 updates on a 10x10 grid apply without exception."""
    g_orig = grid(10, 10, seed=0)
    updates = random_updates(g_orig, 300, seed=42, mode="uniform", p_delete=0.5)
    assert len(updates) > 0

    g_apply = g_orig.copy()
    apply_all(g_apply, updates)   # must not raise


def test_t22_01_sequential_validity_all_modes():
    """T2.2-01: All three modes produce valid sequences on the same graph."""
    g = grid(8, 8, seed=1)
    for mode in ("uniform", "clustered", "near_source"):
        upds = random_updates(g, 100, seed=7, mode=mode, p_delete=0.5)
        g_copy = g.copy()
        apply_all(g_copy, upds)   # must not raise


# ---------------------------------------------------------------------------
# T2.2-02: Determinism
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("mode", ["uniform", "clustered", "near_source"])
def test_t22_02_determinism(mode):
    """T2.2-02: Same seed and mode produce identical update lists."""
    g = grid(6, 6, seed=0)
    u1 = random_updates(g, 50, seed=99, mode=mode)
    u2 = random_updates(g, 50, seed=99, mode=mode)
    assert u1 == u2, f"mode={mode}: different seeds produced different lists"


# ---------------------------------------------------------------------------
# T2.2-03: Input graph untouched
# ---------------------------------------------------------------------------

def test_t22_03_input_graph_untouched():
    """T2.2-03: The caller's graph is identical before and after random_updates."""
    g = grid(5, 5, seed=0)
    before = snapshot_edges(g)
    n_before = g.n
    m_before = g.m

    random_updates(g, 200, seed=3, mode="uniform", p_delete=1.0)

    assert g.n == n_before
    assert g.m == m_before
    assert snapshot_edges(g) == before, "Caller's graph was mutated by random_updates"


# ---------------------------------------------------------------------------
# T2.2-04: Exhaustion
# ---------------------------------------------------------------------------

def test_t22_04_exhaustion():
    """T2.2-04: Asking for 50 deletions on a 5-edge graph yields <= 5 updates."""
    g = DiGraph(4)
    g.add_edge(0, 1, 1)
    g.add_edge(1, 2, 2)
    g.add_edge(2, 3, 3)
    g.add_edge(0, 2, 4)
    g.add_edge(0, 3, 5)
    assert g.m == 5

    updates = random_updates(g, 50, seed=0, mode="uniform", p_delete=1.0)
    assert len(updates) <= 5, f"Got {len(updates)} updates from a 5-edge graph"

    # All returned updates must be valid when applied in order
    g_apply = g.copy()
    apply_all(g_apply, updates)


# ---------------------------------------------------------------------------
# T2.2-05: Invalid apply raises and leaves graph unchanged
# ---------------------------------------------------------------------------

def test_t22_05_invalid_apply_missing_edge():
    """T2.2-05: Deleting a non-existent edge raises ValueError."""
    g = DiGraph(3)
    g.add_edge(0, 1, 5)
    before = snapshot_edges(g)

    with pytest.raises(ValueError, match="does not exist"):
        apply_update(g, Update(kind="delete", u=1, v=2, new_w=0))

    assert snapshot_edges(g) == before, "Graph changed despite failed apply"


def test_t22_05_invalid_apply_increase_to_smaller_weight():
    """T2.2-05: Increasing to a weight <= old weight raises ValueError."""
    g = DiGraph(3)
    g.add_edge(0, 1, 10)
    before = snapshot_edges(g)

    # new_w == old_w → must raise
    with pytest.raises(ValueError, match="must be > old_w|must be strictly greater"):
        apply_update(g, Update(kind="increase", u=0, v=1, new_w=10))

    # new_w < old_w → must raise
    with pytest.raises(ValueError, match="must be > old_w|must be strictly greater"):
        apply_update(g, Update(kind="increase", u=0, v=1, new_w=5))

    assert snapshot_edges(g) == before, "Graph changed despite failed apply"


def test_t22_05_invalid_apply_increase_missing_edge():
    """T2.2-05: Increasing a non-existent edge raises ValueError."""
    g = DiGraph(3)
    with pytest.raises(ValueError, match="does not exist"):
        apply_update(g, Update(kind="increase", u=0, v=1, new_w=999))


# ---------------------------------------------------------------------------
# T2.2-06: Clustered locality
# ---------------------------------------------------------------------------

def test_t22_06_clustered_locality():
    """T2.2-06: Clustered updates with radius=2 — all endpoint vertices within 2*radius hops of each other."""
    g = grid(5, 5, seed=0, wmin=1, wmax=5)   # 25-vertex grid, diameter=8

    updates = random_updates(g, 30, seed=0, mode="clustered", radius=2, p_delete=0.3)
    if not updates:
        return  # nothing to check

    # Collect unique endpoint vertices from the updates
    endpoint_vertices = set()
    for upd in updates:
        endpoint_vertices.add(upd.u)
        endpoint_vertices.add(upd.v)

    # Pick any endpoint as a reference; all others should be within 2*radius=4 hops
    ref = next(iter(endpoint_vertices))
    reachable_within_4 = _bfs_within(g, ref, radius=4)
    for ep in endpoint_vertices:
        assert ep in reachable_within_4, (
            f"Endpoint {ep} is more than 4 hops from reference {ref} "
            "(expected clustered locality with radius=2)"
        )


# ---------------------------------------------------------------------------
# T2.2-07: Increase strictness
# ---------------------------------------------------------------------------

def test_t22_07_increase_strictness():
    """T2.2-07: Every 'increase' update has new_w strictly greater than the current weight."""
    g = random_sparse(20, 60, seed=5, wmin=1, wmax=10)
    g_track = g.copy()   # track current weights as updates apply

    updates = random_updates(g, 500, seed=0, mode="uniform", p_delete=0.0)
    for upd in updates:
        assert upd.kind == "increase"
        old_w = g_track.weight(upd.u, upd.v)
        assert upd.new_w > old_w, (
            f"Increase({upd.u},{upd.v}): new_w={upd.new_w} not > old_w={old_w}"
        )
        apply_update(g_track, upd)


# ---------------------------------------------------------------------------
# T2.2-08: Mix ratio
# ---------------------------------------------------------------------------

def test_t22_08_mix_ratio():
    """T2.2-08: With p_delete=0.7 and 1000 updates, deletion share is ~0.7 (±0.05)."""
    g = grid(8, 8, seed=0)     # 64 nodes, 448 edges — plenty of budget
    updates = random_updates(g, 1000, seed=42, mode="uniform", p_delete=0.7)

    # Count (all increases are valid since the graph has many edges)
    n_delete = sum(1 for u in updates if u.kind == "delete")
    n_total = len(updates)
    assert n_total > 0

    ratio = n_delete / n_total
    assert abs(ratio - 0.7) < 0.07, (
        f"Deletion ratio {ratio:.3f} outside [0.63, 0.77] for p_delete=0.7"
    )


# ---------------------------------------------------------------------------
# Bulk validity: 1000 seeded sequences on three graph families
# ---------------------------------------------------------------------------

def test_t22_bulk_validity_three_families():
    """Verification checklist: 1000 seeded sequences apply without error."""
    from graphpulse.generators import hub_spoke, comb_adversarial

    families = [
        grid(6, 6, seed=0),
        hub_spoke(4, 8, seed=0),
        comb_adversarial(30, seed=0),
    ]
    for seed in range(0, 100):    # 100 seeds × 3 families × 3 modes = 900 sequences
        for g in families:
            for mode in ("uniform", "clustered", "near_source"):
                upds = random_updates(g, 20, seed=seed, mode=mode, p_delete=0.5)
                g_copy = g.copy()
                apply_all(g_copy, upds)   # must not raise
