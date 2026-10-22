"""Milestone 7.5: partial_comb, E3 scaling and E4 adversarial sweep (T7.5-01 .. T7.5-09)."""

from __future__ import annotations

import csv
import math

import pytest

from experiments import e3_scaling, e4_adversarial
from experiments.common import loglog_slope
from graphpulse.dijkstra import dijkstra
from graphpulse.generators import partial_comb
from graphpulse.opcount import OpCounter


def affected_count(n, frac):
    g = partial_comb(n, frac)
    before = dijkstra(g, 0, OpCounter())[0]
    g.remove_edge(0, 1)
    after = dijkstra(g, 0, OpCounter())[0]
    return sum(1 for x in range(n) if before[x] != after[x])


def test_t75_01_affected_count_exact():
    n, frac = 200, 0.3
    m = math.ceil(frac * (n - 1)) + 1
    assert affected_count(n, frac) == m - 1


def test_t75_02_fraction_sweep_monotone():
    counts = [affected_count(120, f / 20) for f in range(1, 21)]
    assert counts == sorted(counts) and counts[-1] == 119 and len(set(counts)) > 5


def test_t75_03_degenerate_fractions():
    for bad in (0, 0.0, -0.1, 1.01):
        with pytest.raises(ValueError):
            partial_comb(50, bad)
    g = partial_comb(50, 1.0)
    assert affected_count(50, 1.0) == 49 and g.n == 50
    with pytest.raises(ValueError):
        partial_comb(2, 0.5)


def test_t75_04_ratio_below_bound_and_05_tightness(tmp_path):
    e4_adversarial.run(quick=False, out_dir=tmp_path)
    with open(tmp_path / "e4_adversarial.csv", newline="") as f:
        rows = list(csv.DictReader(f))
    assert len(rows) >= 40 * 3 and all(r["bound_ok"] == "1" for r in rows)
    with open(tmp_path / "e4_summary.csv", newline="") as f:
        summ = {float(r["c"]): float(r["max_ratio"]) for r in csv.DictReader(f)}
    assert summ[1.0] >= 1.8                       # T7.5-05: tightness at c = 1
    assert summ[0.5] >= 1.8


def test_t75_06_scaling_table(tmp_path):
    e3_scaling.run(quick=True, out_dir=tmp_path)
    with open(tmp_path / "e3_scaling.csv", newline="") as f:
        rows = list(csv.DictReader(f))
    assert [r["side"] for r in rows] == ["6", "8"]
    for r in rows:
        assert float(r["gp_ops_per_update"]) < float(r["rebuild_ops_per_update"])


def test_t75_07_slope_fit_recovers_exponent():
    xs = [10.0, 20.0, 40.0, 80.0, 160.0]
    for p in (0.5, 1.0, 1.7):
        assert abs(loglog_slope(xs, [3.0 * x ** p for x in xs]) - p) < 0.01
    with pytest.raises(ValueError):
        loglog_slope([1.0], [1.0])


def test_t75_08_determinism(tmp_path):
    a, b = tmp_path / "a", tmp_path / "b"
    for d in (a, b):
        e3_scaling.run(quick=True, out_dir=d)
        e4_adversarial.run(quick=True, out_dir=d)
    for name in ("e3_scaling.csv", "e3_k.csv", "e3_slopes.csv", "e4_adversarial.csv", "e4_summary.csv"):
        assert (a / name).read_bytes() == (b / name).read_bytes(), name


@pytest.mark.slow
def test_t75_slow_e3_full_size_grid_runs():
    """One large instance (80x80, 6,400 vertices, k=8) completes and gp is far cheaper per update."""
    from graphpulse.generators import grid, random_updates

    g = grid(80, 80, seed=1)
    ups = random_updates(g, 100, seed=1, mode="uniform", p_delete=0.02)
    gp, rb = e3_scaling.measure_point(g, 8, ups, 5)
    assert gp < rb
