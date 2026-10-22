"""E2: where the work goes, and what each mechanism is worth (Milestone 7.4).

Outputs (docs/results/):
  e2_shares.csv    strategy shares and per-strategy work, by family x update mode x deletion share
  e2_touched_k.csv touched / distance-changed trees versus k
  e2_skip.csv      lazy tour certificate skip rate versus k and update mode
  e2_ablation.csv  total operations, identical updates: rebuild_always, cert_only (c=0), gp (c=1),
                   repair_always (c=inf), gp_random; lazy tour off vs on; eps in {0, 0.05, 0.2}

All variants of the ablation run on the same update sequence and are cross-checked
against the exact reference (see experiments/runner.py).  Nothing is claimed in
advance about which mechanism wins; the tables report what the data show.

Usage: python -m experiments.e2_stages [--quick] [--out DIR]
"""

from __future__ import annotations

import argparse
import random
from pathlib import Path

from experiments.common import RESULTS, write_csv
from experiments.runner import COLUMNS as RUN_COLUMNS
from experiments.runner import RunConfig, run_group
from graphpulse.generators import comb_adversarial, grid, hub_spoke, random_sparse, random_updates
from graphpulse.pipeline import RoutingPipeline
from graphpulse.terminals import MultiTreeManager

MODES = ["uniform", "clustered", "near_source", "tree_edges"]
SHARE_COLS = ["family", "mode", "p_delete", "k", "T_actual", "share_cert", "share_alt", "share_repair",
              "share_fallback", "work_cert", "work_alt", "work_repair", "work_fallback", "mean_touched"]
TOUCH_COLS = ["family", "mode", "k", "T_actual", "mean_touched", "mean_dist_changed", "touched_fraction"]
SKIP_COLS = ["mode", "k", "T_actual", "kept", "resolved", "infeasible", "skip_rate"]


def _fams(quick: bool):
    if quick:
        return {"grid": lambda: grid(8, 8, seed=1), "random_sparse": lambda: random_sparse(60, 300, seed=1),
                "hub_spoke": lambda: hub_spoke(4, 10, seed=1), "comb": lambda: comb_adversarial(60)}
    return {"grid": lambda: grid(20, 20, seed=1), "random_sparse": lambda: random_sparse(400, 2000, seed=1),
            "hub_spoke": lambda: hub_spoke(10, 40, seed=1), "comb": lambda: comb_adversarial(200)}


def _terms(g, k, seed=1):
    return [0] + random.Random(seed).sample(range(1, g.n), k)


def shares(quick: bool) -> list[dict]:
    T, k = (60 if quick else 500), (4 if quick else 8)
    rows = []
    for fam, make in _fams(quick).items():
        g = make()
        for mode in MODES:
            for p in (0.2, 0.5, 0.8):
                ups = random_updates(g, T, seed=1, mode=mode, p_delete=p)
                mgr = MultiTreeManager(g, _terms(g, k), c=1.0)
                cnt = {"cert": 0, "alt": 0, "repair": 0, "fallback": 0}
                wk = {"cert": 0, "alt": 0, "repair": 0, "fallback": 0}
                touched = 0
                for u in ups:
                    st = mgr.apply(u)
                    touched += st.touched_trees
                    for s in st.per_tree:
                        cnt[s.strategy] += 1
                        wk[s.strategy] += s.work
                total = max(1, sum(cnt.values()))
                rows.append({
                    "family": fam, "mode": mode, "p_delete": p, "k": k, "T_actual": len(ups),
                    **{f"share_{s}": round(cnt[s] / total, 6) for s in cnt},
                    **{f"work_{s}": wk[s] for s in wk},
                    "mean_touched": round(touched / max(1, len(ups)), 6),
                })
    return rows


def touched_vs_k(quick: bool) -> list[dict]:
    T = 60 if quick else 400
    ks = [2, 4] if quick else [4, 8, 12, 16]
    rows = []
    fams = _fams(quick)
    for fam in ("grid", "random_sparse"):
        g = fams[fam]()
        for mode in ("uniform", "tree_edges"):
            ups = random_updates(g, T, seed=2, mode=mode, p_delete=0.05)
            for k in ks:
                mgr = MultiTreeManager(g, _terms(g, k, 2), c=1.0)
                touched = changed = 0
                for u in ups:
                    st = mgr.apply(u)
                    assert 0 <= st.touched_trees <= k + 1
                    touched += st.touched_trees
                    changed += st.dist_changed_trees
                n = max(1, len(ups))
                rows.append({"family": fam, "mode": mode, "k": k, "T_actual": len(ups),
                             "mean_touched": round(touched / n, 6), "mean_dist_changed": round(changed / n, 6),
                             "touched_fraction": round(touched / n / (k + 1), 6)})
    return rows


def skip_rates(quick: bool) -> list[dict]:
    T = 60 if quick else 300
    ks = [2, 4] if quick else [4, 8, 12]
    g = _fams(quick)["grid"]()
    rows = []
    for mode in ("uniform", "near_source", "tree_edges"):
        ups = random_updates(g, T, seed=3, mode=mode, p_delete=0.05)
        for k in ks:
            pipe = RoutingPipeline(g, _terms(g, k, 3), c=1.0)
            acts = {"kept": 0, "kept_eps": 0, "resolved": 0, "infeasible": 0}
            for u in ups:
                acts[pipe.apply(u).route_action] += 1
            n = max(1, len(ups))
            rows.append({"mode": mode, "k": k, "T_actual": len(ups), "kept": acts["kept"],
                         "resolved": acts["resolved"], "infeasible": acts["infeasible"],
                         "skip_rate": round((acts["kept"] + acts["kept_eps"]) / n, 6)})
            assert 0.0 <= rows[-1]["skip_rate"] <= 1.0
    return rows


def ablation(quick: bool) -> list[dict]:
    T, k = (40 if quick else 300), (4 if quick else 8)
    fam_specs = ({"grid": {"rows": 8, "cols": 8}, "random_sparse": {"n": 60, "m": 300}} if quick else
                 {"grid": {"rows": 20, "cols": 20}, "random_sparse": {"n": 400, "m": 2000}})
    rows: list[dict] = []
    for fam, params in fam_specs.items():
        for mode in ("uniform", "tree_edges"):
            base = RunConfig(family=fam, family_params=params, k=k, mode=mode, p_delete=0.05, T=T, seed=1)
            rows += run_group(base, lazy_flags=(True, False))
            for eps in (0.05, 0.2):
                e = RunConfig(**{**base.__dict__, "eps": eps})
                rows += [r for r in run_group(e, variants=("gp",))]
    return rows


def run(quick: bool = False, out_dir: Path | None = None) -> list[Path]:
    out_dir = out_dir or RESULTS
    out = [
        write_csv(shares(quick), SHARE_COLS, out_dir / "e2_shares.csv"),
        write_csv(touched_vs_k(quick), TOUCH_COLS, out_dir / "e2_touched_k.csv"),
        write_csv(skip_rates(quick), SKIP_COLS, out_dir / "e2_skip.csv"),
    ]
    cols = [c for c in RUN_COLUMNS if c not in ("wall_seconds",)]
    out.append(write_csv(ablation(quick), cols, out_dir / "e2_ablation.csv"))
    return out


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--quick", action="store_true")
    ap.add_argument("--out", type=Path, default=None)
    a = ap.parse_args()
    for p in run(a.quick, a.out):
        print("wrote", p)
