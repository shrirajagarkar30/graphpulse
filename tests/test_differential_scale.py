"""Real-scale differential testing for GraphPulse-R (Harden Item 3).

Executes at least 100,000 mixed updates (uniform mix of deletions and weight increases)
across all four graph families (grid, hub_spoke, random_sparse, comb_adversarial)
over 5 distinct seeds, comparing BudgetedMaintainer against RecomputeMaintainer
and certifying the full structured SPTState invariants via verify_structured
after every single update.
"""

from __future__ import annotations

import time
import pytest

from graphpulse.controller import BudgetedMaintainer
from graphpulse.generators import (
    comb_adversarial,
    grid,
    hub_spoke,
    random_sparse,
    random_updates,
)
from graphpulse.maintainer import RecomputeMaintainer
from graphpulse.verify import verify_structured


@pytest.mark.slow
@pytest.mark.parametrize("seed", [0, 1, 2, 3, 4])
def test_real_scale_differential_100k(seed: int):
    """Run 20,000 mixed updates per seed across 4 families (100,000 updates total).

    Uniform mix of deletions and increases (p_delete=0.5).
    Verifies exact distance equality against RecomputeMaintainer and executes
    verify_structured after every single update.
    """
    total_seed_updates = 0
    t0 = time.perf_counter()

    # 1. Grid (5,000 updates across 5 batches)
    for b in range(5):
        g = grid(rows=20, cols=20, seed=seed * 10 + b, wmin=1, wmax=10)
        upds = random_updates(
            g, count=1000, seed=seed * 10 + b, mode="uniform", p_delete=0.5, w_increase_max=50
        )
        assert len(upds) == 1000
        cand = BudgetedMaintainer(g, src=0, c=1.0)
        ref = RecomputeMaintainer(g, src=0)
        for u in upds:
            ref.apply(u)
            cand.apply(u)
            assert cand.dist() == ref.dist(), f"[grid seed={seed} batch={b}] Mismatch on {u}"
            verify_structured(cand.graph, cand.state)
            total_seed_updates += 1

    # 2. Hub-Spoke (5,000 updates across 5 batches)
    for b in range(5):
        g = hub_spoke(hubs=10, spokes_per_hub=40, seed=seed * 10 + b)
        upds = random_updates(
            g, count=1000, seed=seed * 10 + b, mode="uniform", p_delete=0.5, w_increase_max=50
        )
        assert len(upds) == 1000
        cand = BudgetedMaintainer(g, src=0, c=1.0)
        ref = RecomputeMaintainer(g, src=0)
        for u in upds:
            ref.apply(u)
            cand.apply(u)
            assert cand.dist() == ref.dist(), f"[hub_spoke seed={seed} batch={b}] Mismatch on {u}"
            verify_structured(cand.graph, cand.state)
            total_seed_updates += 1

    # 3. Random Sparse (5,000 updates across 5 batches)
    for b in range(5):
        g = random_sparse(n=250, m=1500, seed=seed * 10 + b, wmin=1, wmax=10)
        upds = random_updates(
            g, count=1000, seed=seed * 10 + b, mode="uniform", p_delete=0.5, w_increase_max=50
        )
        assert len(upds) == 1000
        cand = BudgetedMaintainer(g, src=0, c=1.0)
        ref = RecomputeMaintainer(g, src=0)
        for u in upds:
            ref.apply(u)
            cand.apply(u)
            assert cand.dist() == ref.dist(), f"[random_sparse seed={seed} batch={b}] Mismatch on {u}"
            verify_structured(cand.graph, cand.state)
            total_seed_updates += 1

    # 4. Comb Adversarial (5,000 updates across 5 batches)
    for b in range(5):
        g = comb_adversarial(n=250)
        upds = random_updates(
            g, count=1000, seed=seed * 10 + b, mode="uniform", p_delete=0.5, w_increase_max=50
        )
        assert len(upds) == 1000
        cand = BudgetedMaintainer(g, src=0, c=1.0)
        ref = RecomputeMaintainer(g, src=0)
        for u in upds:
            ref.apply(u)
            cand.apply(u)
            assert cand.dist() == ref.dist(), f"[comb seed={seed} batch={b}] Mismatch on {u}"
            verify_structured(cand.graph, cand.state)
            total_seed_updates += 1

    t1 = time.perf_counter()
    assert total_seed_updates == 20000, f"Expected 20,000 updates for seed {seed}, got {total_seed_updates}"
    print(f"\n[Scale Differential] Seed {seed}: 20,000 updates verified in {t1 - t0:.2f}s with 0 mismatches.")
