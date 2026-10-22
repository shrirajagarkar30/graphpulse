"""Milestone 7.3: E1 budget sweep (T7.3-01 .. T7.3-07)."""

from __future__ import annotations

import csv
import math

import pytest

from experiments import e1_budget
from graphpulse.analysis import measure
from graphpulse.generators import comb_adversarial, grid, random_updates


@pytest.fixture(scope="module")
def quick_rows(tmp_path_factory):
    out = tmp_path_factory.mktemp("e1")
    e1_budget.run(quick=True, out_dir=out)
    with open(out / "e1_budget.csv", newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f)), out


def test_t73_01_ratio_within_bound(quick_rows):
    rows, _ = quick_rows
    assert rows
    for r in rows:
        assert r["bound_ok"] == "1"
        rho = float(r["rho"])
        if r["c"] != "random" and not math.isinf(rho):
            assert float(r["ratio"]) <= rho + float(r["slack"]) + 1e-9


def test_t73_02_c_zero_never_repairs(quick_rows):
    rows, _ = quick_rows
    zero = [r for r in rows if r["c"] == "0.0" or r["c"] == "0"]
    assert zero and all(int(r["n_repair"]) == 0 for r in zero)


def test_t73_03_c_inf_never_falls_back(quick_rows):
    rows, _ = quick_rows
    inf = [r for r in rows if r["c"] == "inf"]
    assert inf and all(int(r["n_fallback"]) == 0 and float(r["fallback_rate"]) == 0 for r in inf)


def test_t73_04_randomized_expectation():
    g = grid(8, 8, seed=2)
    ups = random_updates(g, 200, seed=2, mode="tree_edges", p_delete=0.02)
    ratios = [measure(g, ups, c="random", mode="oracle", seed=s).ratio for s in range(20)]
    assert sum(ratios) / 20 <= math.e / (math.e - 1) + 0.15


def test_t73_05_determinism(tmp_path):
    a, b = tmp_path / "a", tmp_path / "b"
    e1_budget.run(quick=True, out_dir=a)
    e1_budget.run(quick=True, out_dir=b)
    assert (a / "e1_budget.csv").read_bytes() == (b / "e1_budget.csv").read_bytes()
    assert (a / "e1_budget.md").read_bytes() == (b / "e1_budget.md").read_bytes()


def test_t73_06_table_schema(quick_rows):
    rows, out = quick_rows
    with open(out / "e1_budget.csv", encoding="utf-8") as f:
        assert f.readline().strip().split(",") == e1_budget.COLUMNS
    for r in rows:
        int(r["T_actual"]), int(r["online_cost"]), int(r["opt_cost"]), float(r["ratio"]), float(r["rho"])
        assert float(r["ratio"]) >= 1.0 - 1e-9              # online never beats the per-update optimum


def test_t73_07_correctness_inside_experiment():
    """The online maintainer is verified against structural invariants after every update."""
    g = comb_adversarial(60)
    ups = random_updates(g, 120, seed=1, mode="tree_edges", p_delete=0.05)
    for c in (0.5, 1.0, 2.0, "random"):
        measure(g, ups, c=c, mode="oracle", seed=3, verify=True)      # raises on any violation
