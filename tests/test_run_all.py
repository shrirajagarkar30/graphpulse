"""Milestone 7.6: E5, figures and one-command reproduction (T7.6-01 .. T7.6-08)."""

from __future__ import annotations

import csv
import json
from pathlib import Path

import pytest

from experiments import e5_endtoend, run_all

ROOT = Path(__file__).resolve().parent.parent
FIGS = ["fig_a_ratio_vs_rho", "fig_b_strategy_shares", "fig_c_scaling", "fig_d_adversarial", "fig_e_endtoend"]
TABLES = ["e1_budget.csv", "e1_budget.md", "e2_shares.csv", "e2_touched_k.csv", "e2_skip.csv", "e2_ablation.csv",
          "e3_scaling.csv", "e3_k.csv", "e3_slopes.csv", "e4_adversarial.csv", "e4_summary.csv", "e5_endtoend.csv"]


@pytest.fixture(scope="module")
def quick_run(tmp_path_factory):
    out = tmp_path_factory.mktemp("quick")
    assert run_all.main(["--quick", "--out", str(out)]) == 0
    return out


def test_t76_01_quick_mode_runs(quick_run):
    for t in TABLES:
        assert (quick_run / "results" / t).is_file(), t
    for f in FIGS:
        for ext in ("pdf", "png"):
            assert (quick_run / "figures" / f"{f}.{ext}").is_file()
    assert (quick_run / "results" / "MANIFEST.json").is_file()


def test_t76_02_quick_mode_deterministic(quick_run, tmp_path):
    assert run_all.main(["--quick", "--out", str(tmp_path)]) == 0
    for t in TABLES:
        assert (quick_run / "results" / t).read_bytes() == (tmp_path / "results" / t).read_bytes(), t


def test_t76_03_manifest_matches_and_detects_edits(quick_run, tmp_path):
    mp = quick_run / "results" / "MANIFEST.json"
    assert run_all.verify_manifest(mp) == []
    assert json.loads(mp.read_text())["git_hash"]
    # tamper with a copy of the tree
    import shutil

    copy = tmp_path / "copy"
    shutil.copytree(quick_run, copy)
    with open(copy / "results" / "e1_budget.csv", "a", encoding="utf-8") as f:
        f.write("tampered\n")
    assert any("hash mismatch" in p for p in run_all.verify_manifest(copy / "results" / "MANIFEST.json"))


def test_t76_04_failure_propagates_and_writes_no_manifest(monkeypatch, tmp_path):
    def boom(quick, out_dir):
        raise RuntimeError("injected failure")

    monkeypatch.setattr(run_all, "STEPS", [("E1", boom)])
    assert run_all.main(["--quick", "--out", str(tmp_path)]) == 1
    assert not (tmp_path / "results" / "MANIFEST.json").exists()


def test_t76_05_e5_correctness(tmp_path):
    e5_endtoend.run(quick=True, out_dir=tmp_path)        # run_group raises on any cost / matrix mismatch
    with open(tmp_path / "e5_endtoend.csv", newline="") as f:
        rows = list(csv.DictReader(f))
    assert rows and all(0.0 <= float(r["hk_saved_fraction"]) <= 1.0 for r in rows)


def test_t76_06_figures_are_nonempty(quick_run):
    for f in FIGS:
        assert (quick_run / "figures" / f"{f}.png").stat().st_size > 3000
        assert (quick_run / "figures" / f"{f}.pdf").stat().st_size > 3000


def test_t76_07_committed_figure_sizes():
    d = ROOT / "docs" / "figures"
    if not d.exists():
        pytest.skip("figures not generated yet")
    for p in d.iterdir():
        assert p.stat().st_size < 1_000_000, p
