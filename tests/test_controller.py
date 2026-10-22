"""Tests for Milestone 4.2: Budgeted repair controller."""

from __future__ import annotations

import math
import pytest

from graphpulse.controller import BudgetedMaintainer
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
from graphpulse.opcount import OpCounter
from graphpulse.repair import RepairMaintainer
from graphpulse.spt import SPTState
from graphpulse.verify import check_state


def all_edges(g: DiGraph) -> list[tuple[int, int]]:
    """Return all directed edges in g as (u, v) pairs."""
    return [(u, v) for u in range(g.n) for v, _ in g.out_edges(u)]


# ---------------------------------------------------------------------------
# T4.2-01: Correctness across budgets (regression)
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("c", [0.25, 1.0, 4.0])
def test_t42_01_correctness_across_budgets(c: float):
    """T4.2-01: 5000 mixed updates across 3 families with c in {0.25, 1, 4}; zero mismatches."""
    # ~1700 updates per value of c across 3 families = ~5100 total
    families = [
        ("grid", grid(rows=20, cols=20, seed=int(c * 100), wmin=1, wmax=10), 600),
        ("random_sparse", random_sparse(n=150, m=1000, seed=int(c * 100), wmin=1, wmax=10), 600),
        ("hub_spoke", hub_spoke(hubs=6, spokes_per_hub=80, seed=int(c * 100)), 500),
    ]

    for fam_name, g, count in families:
        updates = random_updates(g, count=count, seed=int(c * 100), mode="uniform", p_delete=0.5)
        cand = BudgetedMaintainer(g, src=0, c=c)
        ref = RecomputeMaintainer(g, src=0)

        for i, upd in enumerate(updates):
            ref.apply(upd)
            stats = cand.apply(upd)
            assert stats.work > 0

            assert cand.dist() == ref.dist(), (
                f"[{fam_name} c={c}] Mismatch at update {i}: {upd}"
            )


# ---------------------------------------------------------------------------
# T4.2-02: c = 0 (edge case)
# ---------------------------------------------------------------------------

def test_t42_02_c_zero_edge_case():
    """T4.2-02: c=0 forces every sole-tight repair to fallback; cert & alt succeed."""
    g = grid(rows=5, cols=5, seed=42, wmin=1, wmax=5)
    cand = BudgetedMaintainer(g, src=0, c=0.0)

    # Find non-tight, alt, and sole-tight updates
    updates = random_updates(g, count=100, seed=42, mode="uniform", p_delete=0.4)
    ref = RecomputeMaintainer(g, src=0)

    strategy_seen: set[str] = set()
    for upd in updates:
        ref.apply(upd)
        stats = cand.apply(upd)
        strategy_seen.add(stats.strategy)
        assert stats.strategy != "repair", "c=0 should never succeed at repair"
        assert cand.dist() == ref.dist()

    # Must have seen fallback and cert
    assert "fallback" in strategy_seen
    assert "cert" in strategy_seen


# ---------------------------------------------------------------------------
# T4.2-03: c = inf (edge case)
# ---------------------------------------------------------------------------

def test_t42_03_c_inf_edge_case():
    """T4.2-03: c=inf on adversarial comb never falls back; equals repair-always."""
    g = comb_adversarial(n=50, seed=42)
    cand = BudgetedMaintainer(g, src=0, c=float("inf"))
    ref_repair = RepairMaintainer(g, src=0)

    upd = Update(kind="delete", u=0, v=1)
    stats = cand.apply(upd)
    stats_ref = ref_repair.apply(upd, budget=None)

    assert stats.strategy == "repair"
    assert stats.fallback_work == 0
    assert stats.work == stats_ref.work
    assert cand.dist() == ref_repair.dist()


# ---------------------------------------------------------------------------
# T4.2-04: Per-update work bound (validation)
# ---------------------------------------------------------------------------

def test_t42_04_per_update_work_bound_adversarial():
    """T4.2-04: In oracle mode with c=1 on adversarial comb, repair_work + fallback_work <= (1+c)*F_true + 1."""
    g = comb_adversarial(n=40, seed=42)
    cand = BudgetedMaintainer(g, src=0, c=1.0, f_mode="oracle")

    upd = Update(kind="delete", u=0, v=1)

    # Compute F_true on updated graph
    scratch_g = g.copy()
    apply_update(scratch_g, upd)
    scratch_counter = OpCounter()
    SPTState.build(scratch_g, 0, scratch_counter)
    F_true = scratch_counter.work

    stats = cand.apply(upd)

    # Deleting (0, 1) on adversarial comb has large work, causing abort and fallback
    assert stats.strategy == "fallback"
    bound = (1 + 1.0) * F_true + 1
    assert stats.repair_work + stats.fallback_work <= bound, (
        f"Work {stats.repair_work + stats.fallback_work} exceeded bound {bound}"
    )


# ---------------------------------------------------------------------------
# T4.2-05: Same bound on random workloads (validation)
# ---------------------------------------------------------------------------

def test_t42_05_work_bound_random_workloads():
    """T4.2-05: Oracle mode work bound holds for all updates across 3 families."""
    c = 1.0
    families = [
        ("grid", grid(rows=8, cols=8, seed=11, wmin=1, wmax=5), 40),
        ("random_sparse", random_sparse(n=50, m=200, seed=11, wmin=1, wmax=5), 40),
        ("hub_spoke", hub_spoke(hubs=4, spokes_per_hub=15, seed=11), 30),
    ]

    for fam_name, g, count in families:
        updates = random_updates(g, count=count, seed=11, mode="uniform", p_delete=0.5)
        cand = BudgetedMaintainer(g, src=0, c=c, f_mode="oracle")

        for i, upd in enumerate(updates):
            # Compute F_true before maintainer applies update
            scratch_g = cand.graph.copy()
            apply_update(scratch_g, upd)
            scratch_counter = OpCounter()
            SPTState.build(scratch_g, 0, scratch_counter)
            F_true = scratch_counter.work

            stats = cand.apply(upd)

            bound = (1 + c) * F_true + 1
            total_algorithm_work = stats.repair_work + stats.fallback_work
            assert total_algorithm_work <= bound, (
                f"[{fam_name} step {i}] {total_algorithm_work} > bound {bound} (F_true={F_true})"
            )


# ---------------------------------------------------------------------------
# T4.2-06: F refresh (positive)
# ---------------------------------------------------------------------------

def test_t42_06_f_refresh_on_fallback():
    """T4.2-06: Read F before and after fallback; F equals the rebuild work just performed."""
    g = grid(rows=5, cols=5, seed=99, wmin=1, wmax=5)
    cand = BudgetedMaintainer(g, src=0, c=0.0)  # Forces fallback on sole-tight update

    # Find a sole-tight update
    sole_update = None
    for u, v in all_edges(g):
        if v != 0 and cand.state.dist[u] + g.weight(u, v) == cand.state.dist[v] and cand.state.tight[v] == 1:
            sole_update = Update(kind="delete", u=u, v=v)
            break

    assert sole_update is not None

    F_before = cand.F
    stats = cand.apply(sole_update)

    assert stats.strategy == "fallback"
    F_after = cand.F
    assert F_after == stats.fallback_work


# ---------------------------------------------------------------------------
# T4.2-07: Invalid c (negative)
# ---------------------------------------------------------------------------

def test_t42_07_invalid_c():
    """T4.2-07: Invalid c values raise ValueError or TypeError."""
    g = grid(rows=3, cols=3, seed=1, wmin=1, wmax=5)

    with pytest.raises(ValueError, match="non-negative"):
        BudgetedMaintainer(g, src=0, c=-1)

    with pytest.raises(ValueError, match="non-negative"):
        BudgetedMaintainer(g, src=0, c=-0.01)

    with pytest.raises(TypeError, match="non-negative number"):
        BudgetedMaintainer(g, src=0, c="a")  # type: ignore

    with pytest.raises(TypeError, match="non-negative number"):
        BudgetedMaintainer(g, src=0, c=None)  # type: ignore

    with pytest.raises(TypeError, match="non-negative number"):
        BudgetedMaintainer(g, src=0, c=True)  # type: ignore

    with pytest.raises(ValueError, match="Source vertex"):
        BudgetedMaintainer(g, src=-1)

    with pytest.raises(ValueError, match="Unknown f_mode"):
        BudgetedMaintainer(g, src=0, f_mode="bad_mode")


# ---------------------------------------------------------------------------
# T4.2-08: Stats consistency (validation)
# ---------------------------------------------------------------------------

def test_t42_08_stats_consistency():
    """T4.2-08: Sum of strategy counts equals number of updates applied."""
    g = random_sparse(n=60, m=300, seed=42, wmin=1, wmax=10)
    updates = random_updates(g, count=150, seed=42, mode="uniform", p_delete=0.5)
    cand = BudgetedMaintainer(g, src=0, c=1.0)

    counts = {"cert": 0, "alt": 0, "repair": 0, "fallback": 0}

    for upd in updates:
        stats = cand.apply(upd)
        counts[stats.strategy] += 1
        assert stats.strategy in counts

    assert sum(counts.values()) == 150
    # Confirm multiple strategies were exercised
    assert counts["cert"] > 0
    assert counts["repair"] + counts["fallback"] > 0


# ---------------------------------------------------------------------------
# T4.2-09: Injected internal fault (failure handling)
# ---------------------------------------------------------------------------

def test_t42_09_injected_internal_fault(monkeypatch):
    """T4.2-09: Internal errors other than BudgetExceeded propagate and are not swallowed."""
    g = grid(rows=4, cols=4, seed=42, wmin=1, wmax=5)
    cand = BudgetedMaintainer(g, src=0, c=1.0)

    def faulty_repair(*args, **kwargs):
        raise RuntimeError("injected fault in repair")

    monkeypatch.setattr("graphpulse.controller.repair", faulty_repair)

    # Find sole-tight update
    sole_update = None
    for u, v in all_edges(g):
        if v != 0 and cand.state.dist[u] + g.weight(u, v) == cand.state.dist[v] and cand.state.tight[v] == 1:
            sole_update = Update(kind="delete", u=u, v=v)
            break

    assert sole_update is not None

    with pytest.raises(RuntimeError, match="injected fault in repair"):
        cand.apply(sole_update)


# ---------------------------------------------------------------------------
# T4.2-10: Verify mode (integration)
# ---------------------------------------------------------------------------

def test_t42_10_verify_mode():
    """T4.2-10: verify=True runs check_state after every update across 1000 updates."""
    g = grid(rows=12, cols=12, seed=77, wmin=1, wmax=5)
    updates = random_updates(g, count=1000, seed=77, mode="uniform", p_delete=0.5)
    cand = BudgetedMaintainer(g, src=0, c=1.0, verify=True)

    for upd in updates:
        stats = cand.apply(upd)
        assert stats.work > 0


# ---------------------------------------------------------------------------
# T4.2-11: Degenerate graph (edge case)
# ---------------------------------------------------------------------------

def test_t42_11_degenerate_graph():
    """T4.2-11: n=1, F small/zero; update attempts handled cleanly without crash."""
    g = DiGraph(1)
    cand = BudgetedMaintainer(g, src=0, c=1.0)

    assert cand.dist() == [0.0]
    assert cand.parent() == [-1]
    assert cand.F <= 2  # Dijkstra runs 1 push + 1 pop = 2 operations

    # Non-existent edge update raises ValueError from apply_update
    with pytest.raises(ValueError, match="does not exist"):
        cand.apply(Update(kind="delete", u=0, v=0))


# ---------------------------------------------------------------------------
# Verification Checklist: Table of strategy shares for 3 families at c = 1
# ---------------------------------------------------------------------------

def test_t42_strategy_shares_table():
    """Record strategy shares (cert / alt / repair / fallback) for 3 families at c=1."""
    families = [
        ("grid_25x25", grid(rows=25, cols=25, seed=1234, wmin=1, wmax=10), 1000),
        ("random_sparse_250n", random_sparse(n=250, m=1800, seed=1234, wmin=1, wmax=10), 1000),
        ("hub_spoke_10h", hub_spoke(hubs=10, spokes_per_hub=100, seed=1234), 1000),
    ]

    results: dict[str, dict[str, int]] = {}

    for fam_name, g, count in families:
        updates = random_updates(g, count=count, seed=1234, mode="uniform", p_delete=0.5)
        cand = BudgetedMaintainer(g, src=0, c=1.0)
        counts = {"cert": 0, "alt": 0, "repair": 0, "fallback": 0}

        for upd in updates:
            stats = cand.apply(upd)
            counts[stats.strategy] += 1

        results[fam_name] = counts
        assert sum(counts.values()) == count

    # Output formatted strategy share table
    print("\n--- Strategy Shares at c = 1.0 ---")
    print(f"{'Family':<22} | {'Cert':<8} | {'Alt':<8} | {'Repair':<8} | {'Fallback':<8} | {'Total':<8}")
    print("-" * 75)
    for fam_name, counts in results.items():
        total = sum(counts.values())
        print(
            f"{fam_name:<22} | "
            f"{counts['cert']:<4} ({counts['cert']/total*100:4.1f}%) | "
            f"{counts['alt']:<4} ({counts['alt']/total*100:4.1f}%) | "
            f"{counts['repair']:<4} ({counts['repair']/total*100:4.1f}%) | "
            f"{counts['fallback']:<4} ({counts['fallback']/total*100:4.1f}%) | "
            f"{total:<8}"
        )
