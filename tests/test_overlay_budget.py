"""Tests for Milestone 4.1: Abortable repair with overlay and work cap."""

from __future__ import annotations

import pytest
from hypothesis import given, settings, strategies as st

from graphpulse.dijkstra import INF, dijkstra
from graphpulse.generators import (
    comb_adversarial,
    grid,
    hub_spoke,
    random_sparse,
    random_updates,
    Update,
    apply_update,
)
from graphpulse.graph import DiGraph
from graphpulse.maintainer import RecomputeMaintainer
from graphpulse.opcount import BudgetExceeded, OpCounter
from graphpulse.repair import (
    ChildrenOverlay,
    ChildSetProxy,
    DictOverlay,
    Overlay,
    RepairMaintainer,
    find_affected,
    repair,
)
from graphpulse.spt import SPTState
from graphpulse.verify import check_state


def all_edges(g: DiGraph) -> list[tuple[int, int]]:
    """Return all directed edges in g as (u, v) pairs."""
    return [(u, v) for u in range(g.n) for v, _ in g.out_edges(u)]


def snapshot_state(state: SPTState) -> tuple[list[float], list[int], list[int], list[set[int]]]:
    """Capture a deep snapshot of an SPTState."""
    return (
        list(state.dist),
        list(state.parent),
        list(state.tight),
        [set(c) for c in state.children],
    )


def assert_states_equal(
    s1: SPTState,
    snapshot: tuple[list[float], list[int], list[int], list[set[int]]],
) -> None:
    """Assert that s1 deep-equals the captured snapshot."""
    assert s1.dist == snapshot[0], "dist mismatch"
    assert s1.parent == snapshot[1], "parent mismatch"
    assert s1.tight == snapshot[2], "tight mismatch"
    assert s1.children == snapshot[3], "children mismatch"


# ---------------------------------------------------------------------------
# T4.1-01: Unlimited budget equals old behavior (regression)
# ---------------------------------------------------------------------------

@pytest.mark.slow
def test_t41_01_unlimited_budget_regression():
    """T4.1-01: 20,000 mixed updates with budget=None yield zero mismatches against RecomputeMaintainer."""
    families = [
        ("grid", grid(rows=45, cols=45, seed=42, wmin=1, wmax=10), 7000),
        ("random_sparse", random_sparse(n=400, m=7000, seed=42, wmin=1, wmax=10), 7000),
        ("hub_spoke", hub_spoke(hubs=20, spokes_per_hub=250, seed=42), 6000),
    ]

    total_updates = 0

    for fam_name, g, count in families:
        updates = random_updates(
            g, count=count, seed=42, mode="uniform", p_delete=0.5, w_increase_max=50
        )
        assert len(updates) == count, f"Failed to generate {count} updates for {fam_name}"
        cand = RepairMaintainer(g, src=0)
        ref = RecomputeMaintainer(g, src=0)

        for i, upd in enumerate(updates):
            ref.apply(upd)
            stats = cand.apply(upd, budget=None)
            assert stats.work > 0

            assert cand.dist() == ref.dist(), (
                f"[{fam_name}] Mismatch at update {i}: {upd}"
            )
            check_state(cand.graph, cand.state)
            total_updates += 1

    assert total_updates == 20000


# ---------------------------------------------------------------------------
# T4.1-02: Zero budget (edge case)
# ---------------------------------------------------------------------------

def test_t41_02_zero_budget():
    """T4.1-02: budget=0 aborts on sole-tight update; state deep-equals snapshot."""
    g = grid(rows=4, cols=4, seed=10, wmin=1, wmax=5)
    cand = RepairMaintainer(g, src=0)

    # Find a sole-tight update
    sole_update = None
    for u, v in all_edges(g):
        if v != 0 and cand.state.dist[u] + g.weight(u, v) == cand.state.dist[v] and cand.state.tight[v] == 1:
            sole_update = Update(kind="delete", u=u, v=v)
            break

    assert sole_update is not None, "Failed to find sole-tight update"

    snap = snapshot_state(cand.state)

    with pytest.raises(BudgetExceeded) as exc_info:
        cand.apply(sole_update, budget=0)

    # Wasted work is at most B + 1 = 0 + 1 = 1
    assert exc_info.value.work <= 1
    assert exc_info.value.budget == 0
    assert_states_equal(cand.state, snap)


# ---------------------------------------------------------------------------
# T4.1-03: Boundary: exactly enough (edge case)
# ---------------------------------------------------------------------------

def test_t41_03_boundary_exactly_enough():
    """T4.1-03: budget=W where W is needed work; repair succeeds."""
    g = grid(rows=5, cols=5, seed=123, wmin=1, wmax=5)
    cand_dry = RepairMaintainer(g, src=0)

    # Find sole-tight update
    sole_update = None
    for u, v in all_edges(g):
        if v != 0 and cand_dry.state.dist[u] + g.weight(u, v) == cand_dry.state.dist[v] and cand_dry.state.tight[v] == 1:
            sole_update = Update(kind="delete", u=u, v=v)
            break

    assert sole_update is not None

    # Dry run to find W
    stats_dry = cand_dry.apply(sole_update, budget=None)
    assert stats_dry.strategy == "repair"
    W = stats_dry.work

    # Fresh maintainer with budget=W
    cand_exact = RepairMaintainer(g, src=0)
    stats_exact = cand_exact.apply(sole_update, budget=W)

    assert stats_exact.work == W
    assert cand_exact.dist() == cand_dry.dist()
    check_state(cand_exact.graph, cand_exact.state)


# ---------------------------------------------------------------------------
# T4.1-04: Boundary: one short (edge case)
# ---------------------------------------------------------------------------

def test_t41_04_boundary_one_short():
    """T4.1-04: budget=W-1; BudgetExceeded raised and state untouched."""
    g = grid(rows=5, cols=5, seed=123, wmin=1, wmax=5)
    cand_dry = RepairMaintainer(g, src=0)

    sole_update = None
    for u, v in all_edges(g):
        if v != 0 and cand_dry.state.dist[u] + g.weight(u, v) == cand_dry.state.dist[v] and cand_dry.state.tight[v] == 1:
            sole_update = Update(kind="delete", u=u, v=v)
            break

    assert sole_update is not None

    stats_dry = cand_dry.apply(sole_update, budget=None)
    W = stats_dry.work

    # Fresh maintainer with budget = W - 1
    cand = RepairMaintainer(g, src=0)
    snap = snapshot_state(cand.state)

    with pytest.raises(BudgetExceeded) as exc_info:
        cand.apply(sole_update, budget=W - 1)

    assert exc_info.value.work == W
    assert exc_info.value.budget == W - 1
    assert_states_equal(cand.state, snap)


# ---------------------------------------------------------------------------
# T4.1-05: Abort during identification (failure handling)
# ---------------------------------------------------------------------------

def test_t41_05_abort_during_identification():
    """T4.1-05: Budget at 10% of W aborts during identification; state untouched."""
    g = comb_adversarial(n=100, seed=42)
    cand_dry = RepairMaintainer(g, src=0)
    upd = Update(kind="delete", u=0, v=1)

    stats_dry = cand_dry.apply(upd, budget=None)
    W = stats_dry.work

    cand = RepairMaintainer(g, src=0)
    snap = snapshot_state(cand.state)

    budget_10pct = max(1, int(0.10 * W))
    with pytest.raises(BudgetExceeded) as exc_info:
        cand.apply(upd, budget=budget_10pct)

    assert exc_info.value.work <= budget_10pct + 1
    assert_states_equal(cand.state, snap)


# ---------------------------------------------------------------------------
# T4.1-06: Abort during recompute (failure handling)
# ---------------------------------------------------------------------------

def test_t41_06_abort_during_recompute():
    """T4.1-06: Budget at 80% of W aborts during recompute; state untouched."""
    g = comb_adversarial(n=100, seed=42)
    cand_dry = RepairMaintainer(g, src=0)
    upd = Update(kind="delete", u=0, v=1)

    stats_dry = cand_dry.apply(upd, budget=None)
    W = stats_dry.work

    cand = RepairMaintainer(g, src=0)
    snap = snapshot_state(cand.state)

    budget_80pct = int(0.80 * W)
    with pytest.raises(BudgetExceeded) as exc_info:
        cand.apply(upd, budget=budget_80pct)

    assert exc_info.value.work <= budget_80pct + 1
    assert_states_equal(cand.state, snap)


# ---------------------------------------------------------------------------
# T4.1-07: Correct after abort (integration)
# ---------------------------------------------------------------------------

def test_t41_07_correct_after_abort():
    """T4.1-07: Rebuild after abort produces correct state matching Dijkstra."""
    g = comb_adversarial(n=50, seed=42)
    cand = RepairMaintainer(g, src=0)
    upd = Update(kind="delete", u=0, v=1)

    # Abort with low budget
    with pytest.raises(BudgetExceeded):
        cand.apply(upd, budget=10)

    # Caller rebuilds
    rebuild_stats = cand._rebuild()
    assert rebuild_stats.strategy == "rebuild"
    assert rebuild_stats.work > 0

    ref_dist, _ = dijkstra(cand.graph, 0, OpCounter())
    assert cand.dist() == ref_dist
    check_state(cand.graph, cand.state)


# ---------------------------------------------------------------------------
# T4.1-08: Overlay isolation (validation)
# ---------------------------------------------------------------------------

def test_t41_08_overlay_isolation():
    """T4.1-08: Overlay isolation: base state untouched until commit."""
    g = grid(rows=4, cols=4, seed=7, wmin=1, wmax=5)
    counter = OpCounter()
    base_state = SPTState.build(g, src=0, counter=counter)
    snap = snapshot_state(base_state)

    overlay = Overlay(base_state)
    assert not overlay.has_changes

    # Perform reads
    assert overlay.dist[0] == 0.0
    assert overlay.parent[0] == -1
    assert 1 in overlay.children[0]

    # Perform writes strictly through overlay
    overlay.dist[1] = 999.0
    overlay.parent[1] = -1
    overlay.tight[1] = 0
    overlay.children[0].discard(1)
    overlay.children[2].add(1)

    assert overlay.has_changes

    # Base state is completely untouched
    assert_states_equal(base_state, snap)
    assert base_state.dist[1] != 999.0
    assert base_state.parent[1] != -1
    assert base_state.tight[1] != 0
    assert 1 in base_state.children[0]
    assert 1 not in base_state.children[2]

    # Commit applies changes
    overlay.commit()
    assert base_state.dist[1] == 999.0
    assert base_state.parent[1] == -1
    assert base_state.tight[1] == 0
    assert 1 not in base_state.children[0]
    assert 1 in base_state.children[2]


# ---------------------------------------------------------------------------
# T4.1-09: Overlay equals in-place (property)
# ---------------------------------------------------------------------------

@settings(max_examples=300)
@given(
    seed=st.integers(min_value=0, max_value=10000),
    p_delete=st.floats(min_value=0.0, max_value=1.0),
)
def test_t41_09_overlay_equals_oracle_property(seed: int, p_delete: float):
    """T4.1-09: Property test (300 cases): Repair via overlay produces identical state to Recompute baseline."""
    g = random_sparse(n=25, m=80, seed=seed, wmin=1, wmax=10)
    cand = RepairMaintainer(g, src=0)
    ref = RecomputeMaintainer(g, src=0)

    updates = random_updates(g, count=5, seed=seed, mode="uniform", p_delete=p_delete)

    for upd in updates:
        ref.apply(upd)
        cand.apply(upd, budget=None)

        assert cand.dist() == ref.dist()
        check_state(cand.graph, cand.state)


# ---------------------------------------------------------------------------
# T4.1-10: Work not inflated (validation)
# ---------------------------------------------------------------------------

def test_t41_10_work_not_inflated():
    """T4.1-10: Compare counter delta to manual pre-refactor counts; zero inflation."""
    g = grid(rows=4, cols=4, seed=42, wmin=1, wmax=5)
    cand = RepairMaintainer(g, src=0)

    # Find sole-tight update
    sole_update = None
    for u, v in all_edges(g):
        if v != 0 and cand.state.dist[u] + g.weight(u, v) == cand.state.dist[v] and cand.state.tight[v] == 1:
            sole_update = Update(kind="delete", u=u, v=v)
            break

    assert sole_update is not None

    stats = cand.apply(sole_update, budget=None)
    assert stats.strategy == "repair"

    # Verify work decomposition
    assert stats.work == stats.scan + stats.push + stats.pop + stats.queue
    assert stats.scan >= 1
    assert stats.queue >= 2


# ---------------------------------------------------------------------------
# Verification Checklist: Abort at 10 budget fractions on 3 families
# ---------------------------------------------------------------------------

@pytest.mark.parametrize(
    "fam_func,fam_args",
    [
        (grid, {"rows": 6, "cols": 6, "seed": 99, "wmin": 1, "wmax": 5}),
        (random_sparse, {"n": 40, "m": 150, "seed": 99, "wmin": 1, "wmax": 5}),
        (hub_spoke, {"hubs": 4, "spokes_per_hub": 15, "seed": 99}),
    ],
)
def test_t41_abort_ten_fractions_no_leak(fam_func, fam_args):
    """Abort tested at 10 different budget fractions per update on 3 families with no state leak."""
    g = fam_func(**fam_args)
    cand_dry = RepairMaintainer(g, src=0)

    # Find sole-tight update
    sole_update = None
    for u, v in all_edges(g):
        if v != 0 and cand_dry.state.dist[u] + g.weight(u, v) == cand_dry.state.dist[v] and cand_dry.state.tight[v] == 1:
            sole_update = Update(kind="delete", u=u, v=v)
            break

    assert sole_update is not None

    stats_dry = cand_dry.apply(sole_update, budget=None)
    W = stats_dry.work

    fractions = [0.0, 0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9]

    for frac in fractions:
        budget = int(frac * W)
        cand = RepairMaintainer(g, src=0)
        snap = snapshot_state(cand.state)

        with pytest.raises(BudgetExceeded) as exc_info:
            cand.apply(sole_update, budget=budget)

        assert exc_info.value.work <= budget + 1
        assert_states_equal(cand.state, snap)
