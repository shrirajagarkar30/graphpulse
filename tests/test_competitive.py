"""Tests for competitive ratio analysis and randomized budget (Milestone 4.3).

Test cases:
- T4.3-01: Deterministic worst case (simulated cost pairs r = cF + 1, ratio matches max(1+c, (1+c)/c))
- T4.3-02: Best deterministic budget (sweep c in [0.1, 5], unique minimum at c=1.0 with value 2.0)
- T4.3-03: Sampler distribution (200,000 samples of x in [0, 1), mean within 0.01 of 1/(e-1) ≈ 0.582)
- T4.3-04: Randomized expected ratio (simulated r/F in {0.1, 0.5, 1, 2}, expected ratio within 2% of 1.582)
- T4.3-05: Seed reproducibility (same seed yields identical budget sequences, different seeds diverge)
- T4.3-06: Real maintainer in oracle mode across 3 families + comb (online <= ratio(c) * OPT + T)
- T4.3-07: Adversarial comb tightness (measured ratio close to 2.0 at c = 1.0)
- T4.3-08: Randomized budget on real workloads (correctness verified, ratio <= 1.582 + slack)
- T4.3-09: Stale-F deviation recorded (mode='last' vs mode='oracle' reported in a table)
- T4.3-10: Invalid inputs handled cleanly (empty list, invalid mode, invalid c, etc.)
"""

from __future__ import annotations

import math
import pytest

from graphpulse.analysis import (
    MeasurementResult,
    measure,
    theoretical_competitive_ratio,
)
from graphpulse.controller import BudgetedMaintainer, RandomizedBudget
from graphpulse.generators import (
    Update,
    comb_adversarial,
    grid,
    hub_spoke,
    random_sparse,
    random_updates,
)
from graphpulse.maintainer import RecomputeMaintainer
from graphpulse.verify import check_state


# ---------------------------------------------------------------------------
# T4.3-01: Deterministic worst case
# ---------------------------------------------------------------------------
def test_t4_3_01_deterministic_worst_case():
    """Simulated cost pairs with r = ceil(c * F) + 1.

    Online budget B = ceil(c * F). Since r > B, online incurs B + 1 wasted work
    and then F for full rebuild, totaling B + 1 + F.
    OPT chooses min(r, F).
    Ratio matches max(1 + c, (1 + c) / c) within 1%.
    """
    c_values = [0.25, 0.5, 1.0, 2.0, 4.0]
    F = 100_000  # large F to eliminate integer discretization noise

    for c in c_values:
        B = math.ceil(c * F)
        r = B + 1  # worst-case repair cost just above the budget
        wasted = B + 1
        online_cost = wasted + F
        opt_cost = min(r, F)

        simulated_ratio = online_cost / opt_cost
        theoretical_ratio = theoretical_competitive_ratio(c)

        # Within 1% of theoretical ratio
        assert math.isclose(simulated_ratio, theoretical_ratio, rel_tol=0.01), (
            f"c={c}: simulated {simulated_ratio} != theoretical {theoretical_ratio}"
        )


# ---------------------------------------------------------------------------
# T4.3-02: Best deterministic budget
# ---------------------------------------------------------------------------
def test_t4_3_02_best_deterministic_budget():
    """Sweep c from 0.1 to 5.0 to verify unique minimum at c = 1.0 with value 2.0."""
    c_steps = [round(0.1 + 0.05 * i, 2) for i in range(99)]
    min_ratio = float("inf")
    best_c = None

    for c in c_steps:
        ratio = theoretical_competitive_ratio(c)
        if ratio < min_ratio:
            min_ratio = ratio
            best_c = c

    assert best_c == 1.0, f"Expected minimum at c=1.0, got {best_c}"
    assert math.isclose(min_ratio, 2.0, abs_tol=1e-9), f"Expected min ratio 2.0, got {min_ratio}"

    # Verify that for any c != 1.0, ratio is strictly greater than 2.0
    for c in (0.5, 0.8, 0.99, 1.01, 1.5, 2.0):
        assert theoretical_competitive_ratio(c) > 2.0


# ---------------------------------------------------------------------------
# T4.3-03: Sampler distribution
# ---------------------------------------------------------------------------
def test_t4_3_03_sampler_distribution():
    """200,000 samples of x from RandomizedBudget.

    All x in [0, 1), sample mean within 0.01 of 1 / (e - 1) ≈ 0.5819767.
    """
    rb = RandomizedBudget(seed=42)
    n_samples = 200_000
    samples = [rb.sample_x() for _ in range(n_samples)]

    # Bounds check
    assert all(0.0 <= x < 1.0 for x in samples), "Sample outside [0, 1)"

    # Mean check: theoretical mean is 1 / (e - 1) ≈ 0.5819767
    sample_mean = sum(samples) / n_samples
    theoretical_mean = 1.0 / (math.e - 1.0)
    assert abs(sample_mean - theoretical_mean) < 0.01, (
        f"Sample mean {sample_mean} deviates from {theoretical_mean} by >= 0.01"
    )

    # Variance check: theoretical Var(X) = (e^2 - 3e + 1) / (e - 1)^2 ≈ 0.07934
    sample_var = sum((x - sample_mean) ** 2 for x in samples) / (n_samples - 1)
    theoretical_var = (math.e**2 - 3.0 * math.e + 1.0) / ((math.e - 1.0) ** 2)
    assert abs(sample_var - theoretical_var) < 0.01


# ---------------------------------------------------------------------------
# T4.3-04: Randomized expected ratio
# ---------------------------------------------------------------------------
def test_t4_3_04_randomized_expected_ratio():
    """Simulated r/F in {0.1, 0.5, 1.0, 2.0} over 50,000 draws.

    Expected ratio is within 2% of e / (e - 1) ≈ 1.5819767 for each.
    """
    F = 10_000
    ratios_to_test = [0.1, 0.5, 1.0, 2.0]
    n_draws = 50_000
    target_ratio = math.e / (math.e - 1.0)  # ≈ 1.5819767

    for alpha in ratios_to_test:
        r = round(alpha * F)
        opt_cost = min(r, F)

        rb = RandomizedBudget(seed=100 + int(alpha * 100))
        total_online = 0
        for _ in range(n_draws):
            B = rb.budget(F)
            if r <= B:
                online_cost = r
            else:
                online_cost = B + 1 + F
            total_online += online_cost

        avg_online = total_online / n_draws
        empirical_ratio = avg_online / opt_cost

        assert math.isclose(empirical_ratio, target_ratio, rel_tol=0.02), (
            f"alpha={alpha}: empirical ratio {empirical_ratio} not within 2% of {target_ratio}"
        )


# ---------------------------------------------------------------------------
# T4.3-05: Seed reproducibility
# ---------------------------------------------------------------------------
def test_t4_3_05_seed_reproducibility():
    """Same seed yields identical budget sequences; different seeds diverge."""
    rb1 = RandomizedBudget(seed=12345)
    rb2 = RandomizedBudget(seed=12345)
    rb3 = RandomizedBudget(seed=54321)

    seq1 = [rb1.budget(1000 + i) for i in range(500)]
    seq2 = [rb2.budget(1000 + i) for i in range(500)]
    seq3 = [rb3.budget(1000 + i) for i in range(500)]

    assert seq1 == seq2, "Identical seeds produced different budget sequences"
    assert seq1 != seq3, "Different seeds produced identical sequences unexpectedly"


# ---------------------------------------------------------------------------
# T4.3-06: Real maintainer, oracle mode
# ---------------------------------------------------------------------------
def test_t4_3_06_real_maintainer_oracle_mode():
    """Measure online vs offline costs across 3 families + comb in oracle mode.

    Verifies online <= ratio(c) * OPT + T (plus per-update work bound).
    """
    c_values = [0.5, 1.0, 2.0]
    graphs = [
        ("grid", grid(6, 6, seed=1)),
        ("random_sparse", random_sparse(35, 100, seed=2)),
        ("hub_spoke", hub_spoke(4, 6, seed=3)),
        ("comb", comb_adversarial(25, seed=0)),
    ]

    for g_name, g in graphs:
        updates = random_updates(g, 30, seed=42, p_delete=0.6)

        for c in c_values:
            res = measure(g, updates, c=c, mode="oracle")
            R_c = theoretical_competitive_ratio(c)

            # Check sequence-level bound: online <= R_c * OPT + T
            assert res.online_cost <= R_c * res.opt_cost + len(updates), (
                f"{g_name} c={c}: online {res.online_cost} > {R_c} * opt {res.opt_cost} + {len(updates)}"
            )

            # Check per-update bound: online_t <= R_c * opt_t + 1
            for t, (on_t, opt_t) in enumerate(zip(res.per_update_online, res.per_update_opt)):
                assert on_t <= R_c * opt_t + 1, (
                    f"{g_name} c={c} update {t}: on_t={on_t} > {R_c} * opt_t={opt_t} + 1"
                )


# ---------------------------------------------------------------------------
# T4.3-07: Adversarial tightness
# ---------------------------------------------------------------------------
def test_t4_3_07_adversarial_tightness():
    """Comb graph with c = 1.0 where repair attempts work up to F and aborts.

    Measured ratio is close to 2.0 (>= 1.95).
    """
    g = comb_adversarial(50)
    upd = [Update(kind="delete", u=0, v=1)]

    res = measure(g, upd, c=1.0, mode="oracle")

    assert res.strategy_counts["fallback"] == 1
    # Check that ratio is very close to 2.0
    assert 1.95 <= res.ratio <= 2.05, f"Expected ratio ~2.0, got {res.ratio}"


# ---------------------------------------------------------------------------
# T4.3-08: Randomized on real workloads
# ---------------------------------------------------------------------------
def test_t4_3_08_randomized_on_real_workloads():
    """Randomized budget on real graph families.

    Verifies state correctness against RecomputeMaintainer and competitive ratio.
    """
    families = [
        ("grid", grid(6, 6, seed=10)),
        ("random_sparse", random_sparse(30, 90, seed=20)),
        ("hub_spoke", hub_spoke(4, 5, seed=30)),
    ]

    for name, g in families:
        updates = random_updates(g, 25, seed=777, p_delete=0.5)

        # Cross-validate against independent RecomputeMaintainer
        oracle = RecomputeMaintainer(g.copy(), src=0)
        maintainer = BudgetedMaintainer(g.copy(), src=0, c="random", f_mode="oracle", seed=42)

        for upd in updates:
            oracle.apply(upd)
            maintainer.apply(upd)
            assert maintainer.dist() == oracle.dist()
            check_state(maintainer.graph, maintainer.state)

        # Compute OPT cost
        opt_cost = measure(g, updates, c=1.0, mode="oracle").opt_cost

        # Average online cost over randomized draws to estimate expectation
        n_seeds = 25
        total_online = 0
        for s in range(n_seeds):
            run_res = measure(g, updates, c="random", mode="oracle", seed=s)
            # Individual run must never suffer catastrophic blowup (bounded by 2.5 * OPT + slack)
            assert run_res.online_cost <= 2.5 * opt_cost + 2 * len(updates)
            total_online += run_res.online_cost

        avg_online = total_online / n_seeds

        # Competitive ratio check: expected ratio <= e / (e - 1) ≈ 1.582 plus additive slack
        # Additive slack covers discrete ceil rounding and +1 abort slack across updates
        slack = 0.1 * opt_cost + 2 * len(updates)
        max_allowed_online = (math.e / (math.e - 1.0)) * opt_cost + slack
        assert avg_online <= max_allowed_online, (
            f"{name}: avg_online {avg_online} > max allowed {max_allowed_online}"
        )


# ---------------------------------------------------------------------------
# T4.3-09: Stale-F deviation recorded
# ---------------------------------------------------------------------------
def test_t4_3_09_stale_f_deviation_recorded(capsys):
    """Compare f_mode='last' vs f_mode='oracle' across graph families.

    Deviation reported in a summary table; no assertion failure per playbook.
    """
    families = [
        ("grid_6x6", grid(6, 6, seed=101)),
        ("random_sparse_35", random_sparse(35, 100, seed=102)),
        ("hub_spoke_4x6", hub_spoke(4, 6, seed=103)),
    ]

    rows = []
    for name, g in families:
        updates = random_updates(g, 30, seed=888, p_delete=0.5)

        res_oracle = measure(g, updates, c=1.0, mode="oracle")
        res_last = measure(g, updates, c=1.0, mode="last")

        dev = abs(res_last.online_cost - res_oracle.online_cost)
        pct_dev = (dev / res_oracle.online_cost * 100.0) if res_oracle.online_cost > 0 else 0.0

        rows.append((name, res_oracle.online_cost, res_last.online_cost, dev, pct_dev))

    print("\n" + "=" * 70)
    print("STALE-F DEVIATION SUMMARY TABLE: mode='oracle' vs mode='last' (c=1.0)")
    print("=" * 70)
    print(f"{'Graph Family':<20} {'Oracle Cost':<14} {'Last Cost':<14} {'Dev (ops)':<12} {'% Dev':<8}")
    print("-" * 70)
    for name, oc, lc, dev, pct in rows:
        print(f"{name:<20} {oc:<14} {lc:<14} {dev:<12} {pct:<8.2f}%")
    print("=" * 70)

    # Informational table captured cleanly; no failure assertion
    captured = capsys.readouterr()
    assert "STALE-F DEVIATION SUMMARY TABLE" in captured.out


# ---------------------------------------------------------------------------
# T4.3-10: Invalid analysis input
# ---------------------------------------------------------------------------
def test_t4_3_10_invalid_analysis_input():
    """Invalid and boundary inputs handled cleanly."""
    g = grid(4, 4, seed=0)

    # Empty update list: zero totals handled cleanly
    res_empty = measure(g, [])
    assert res_empty.online_cost == 0
    assert res_empty.opt_cost == 0
    assert res_empty.ratio == 1.0
    assert res_empty.updates_count == 0
    assert len(res_empty.per_update_online) == 0

    # Tuple unpacking on empty
    online_zero, opt_zero = res_empty
    assert online_zero == 0 and opt_zero == 0

    # Invalid mode
    with pytest.raises(ValueError, match="expected 'oracle' or 'last'"):
        measure(g, [Update(kind="delete", u=0, v=1)], mode="invalid_mode")

    # updates is None
    with pytest.raises(TypeError, match="updates cannot be None"):
        measure(g, None)

    # make_graph is invalid type
    with pytest.raises(TypeError, match="make_graph must be a callable or DiGraph"):
        measure("not_a_graph", [])

    # theoretical_competitive_ratio with c <= 0
    with pytest.raises(ValueError, match="Multiplier c must be positive"):
        theoretical_competitive_ratio(0)
    with pytest.raises(ValueError, match="Multiplier c must be positive"):
        theoretical_competitive_ratio(-1.5)

    # theoretical_competitive_ratio with randomized
    r_rand = theoretical_competitive_ratio("random")
    assert math.isclose(r_rand, math.e / (math.e - 1.0))
    r_rb = theoretical_competitive_ratio(RandomizedBudget())
    assert math.isclose(r_rb, math.e / (math.e - 1.0))

    # MeasurementResult indexing out of range
    res = measure(g, [])
    with pytest.raises(IndexError):
        _ = res[2]
