"""Milestone 7.4: E2 stage shares, hit rates, ablations (T7.4-01 .. T7.4-07)."""

from __future__ import annotations

import csv

import pytest

from experiments import e2_stages
from experiments.runner import RunConfig, run_group
from graphpulse.dijkstra import INF, dijkstra
from graphpulse.generators import Update, apply_update, grid, random_updates
from graphpulse.opcount import OpCounter


@pytest.fixture(scope="module")
def quick_out(tmp_path_factory):
    out = tmp_path_factory.mktemp("e2")
    e2_stages.run(quick=True, out_dir=out)
    return out


def read(path):
    with open(path, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def test_t74_01_tree_edges_mode_only_tight_edges():
    g = grid(8, 8, seed=2)
    ups = random_updates(g, 500, seed=4, mode="tree_edges", p_delete=0.05)
    assert len(ups) == 500
    work = g.copy()
    for u in ups:
        d, _ = dijkstra(work, 0, OpCounter())
        w = work.weight(u.u, u.v)
        assert d[u.u] != INF and d[u.u] + w == d[u.v], f"edge {(u.u, u.v)} was not tight at generation time"
        apply_update(work, u)


def test_t74_02_shares_sum_to_one(quick_out):
    rows = read(quick_out / "e2_shares.csv")
    assert rows
    for r in rows:
        s = sum(float(r[f"share_{x}"]) for x in ("cert", "alt", "repair", "fallback"))
        assert abs(s - 1.0) < 1e-5


def test_t74_03_ablation_consistency():
    base = RunConfig(family="grid", family_params={"rows": 8, "cols": 8}, k=4, mode="tree_edges",
                     p_delete=0.05, T=60, seed=1)
    rows = run_group(base, lazy_flags=(True, False))          # raises on any disagreement
    assert len({r["matrix_sha"] for r in rows}) == 1


def test_t74_04_lazy_off_equals_reference_transitions():
    base = RunConfig(family="grid", family_params={"rows": 8, "cols": 8}, k=4, p_delete=0.05, T=80, seed=2)
    rows = run_group(base, variants=("rebuild_always", "gp"), lazy_flags=(False,))
    by = {r["variant"]: r for r in rows}
    assert by["gp"]["hk_transitions"] == by["rebuild_always"]["hk_transitions"]


def test_t74_05_skip_rate_bounds(quick_out):
    for r in read(quick_out / "e2_skip.csv"):
        assert 0.0 <= float(r["skip_rate"]) <= 1.0


def test_t74_06_touched_at_most_k_plus_one(quick_out):
    for r in read(quick_out / "e2_touched_k.csv"):
        assert float(r["mean_touched"]) <= int(r["k"]) + 1
        assert float(r["mean_dist_changed"]) <= float(r["mean_touched"]) + 1e-9
        assert 0.0 <= float(r["touched_fraction"]) <= 1.0


def test_t74_07_determinism(tmp_path):
    a, b = tmp_path / "a", tmp_path / "b"
    e2_stages.run(quick=True, out_dir=a)
    e2_stages.run(quick=True, out_dir=b)
    for name in ("e2_shares.csv", "e2_touched_k.csv", "e2_skip.csv", "e2_ablation.csv"):
        assert (a / name).read_bytes() == (b / name).read_bytes(), name
