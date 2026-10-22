"""Milestone 7.2: experiment runner (T7.2-01 .. T7.2-09)."""

from __future__ import annotations

import json
import subprocess
from dataclasses import asdict
from pathlib import Path

import pytest

import graphpulse.pipeline as pipeline_mod
from experiments.runner import (
    COLUMNS, VARIANTS, CrossVariantMismatch, RunConfig, build_instance, run_group, run_one,
    write_meta, write_rows,
)

GRID = {"rows": 12, "cols": 12}


def cfg(**kw):
    base = dict(family="grid", family_params=GRID, k=6, variant="gp", mode="uniform", p_delete=0.02, T=500, seed=3)
    base.update(kw)
    return RunConfig(**base)


def strip(rows):
    return [{k: v for k, v in r.items() if k != "wall_seconds"} for r in rows]


def test_t72_01_determinism():
    a = run_group(cfg(T=150))
    b = run_group(cfg(T=150))
    assert strip(a) == strip(b)


def test_t72_02_variants_agree_all():
    rows = run_group(cfg(), lazy_flags=(True, False))
    assert {r["variant"] for r in rows} == set(VARIANTS)
    assert len({r["matrix_sha"] for r in rows}) == 1


def test_t72_03_same_update_sequence():
    rows = run_group(cfg(T=100))
    assert len({r["updates_sha"] for r in rows}) == 1
    for v in ("gp", "cert_only"):
        assert build_instance(cfg(variant=v, T=100)).updates_sha == rows[0]["updates_sha"]


def test_t72_04_strategy_counts_consistent():
    for r in run_group(cfg(T=200)):
        total = r["strat_cert"] + r["strat_alt"] + r["strat_repair"] + r["strat_fallback"] + r["strat_rebuild"]
        assert total == r["T_actual"] * (r["k"] + 1)


def test_t72_05_unknown_variant():
    with pytest.raises(ValueError):
        run_one(cfg(variant="x"))


@pytest.mark.parametrize("kw", [dict(c=-1.0), dict(T=0), dict(k=19), dict(eps=-0.1), dict(p_delete=1.5), dict(mode="zzz")])
def test_t72_06_invalid_config(kw):
    with pytest.raises(ValueError):
        run_one(cfg(**kw))


def test_t72_07_metadata(tmp_path):
    write_meta(tmp_path / "meta.json", [3, 1, 3], {"note": "x"})
    m = json.loads((tmp_path / "meta.json").read_text())
    assert m["seeds"] == [1, 3] and m["python"] and "git_hash" in m and m["utc_time"]
    assert "pytest" in m["packages"]


def test_t72_08_injected_disagreement_fails_loudly(monkeypatch):
    """A variant that returns a valid but worse tour must trip the cross-variant check."""
    real = pipeline_mod.held_karp
    from graphpulse.tour import tour_cost

    def worse(D, counter=None):
        c, o = real(D, counter)
        if not o:
            return c, o
        o2 = o[1:] + o[:1]                      # a different valid permutation
        return tour_cost(D, o2), o2

    monkeypatch.setattr(pipeline_mod, "held_karp", worse)
    with pytest.raises(CrossVariantMismatch):
        run_group(cfg(T=60), variants=("gp",))


def test_t72_08b_corrupted_cost_is_rejected_by_certificate(monkeypatch):
    real = pipeline_mod.held_karp
    monkeypatch.setattr(pipeline_mod, "held_karp", lambda D, counter=None: (lambda r: (r[0] + 1, r[1]))(real(D, counter)))
    with pytest.raises(ValueError):
        run_group(cfg(T=40), variants=("gp",))


def test_t72_09_output_not_tracked(tmp_path):
    root = Path(__file__).resolve().parent.parent
    rows = run_group(cfg(T=30), variants=("gp",))
    out = root / "experiments" / "output" / "pytest_probe" / "rows.csv"
    write_rows(rows, out)
    try:
        assert out.read_text().splitlines()[0].split(",") == COLUMNS
        r = subprocess.run(["git", "check-ignore", "-q", str(out)], cwd=root)
        assert r.returncode == 0
    finally:
        out.unlink()
        out.parent.rmdir()


def test_t72_epsilon_group_within_bound():
    rows = run_group(cfg(T=200, eps=0.1), variants=("gp", "repair_always"))
    assert len(rows) == 2


def test_t72_lazy_off_has_no_kept():
    rows = run_group(cfg(T=120), variants=("gp",), lazy_flags=(False,))
    assert rows[0]["kept"] == 0 and rows[0]["kept_eps"] == 0
