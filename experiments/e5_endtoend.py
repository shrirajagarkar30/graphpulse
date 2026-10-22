"""E5: end-to-end response cost, RoutingPipeline vs RecomputeEverything (Milestone 7.6).

Same update sequence for both; the runner cross-checks matrices and tour costs
after every update (a mismatch aborts the run).  Reported per configuration:
tree operations per update, Held-Karp transitions (and the fraction saved), and
the fraction of updates for which the tour was kept.

Real road data were NOT used (no dataset was obtained; see data/README.md), so
only synthetic families appear here and the paper must not claim "real road
networks".

Usage: python -m experiments.e5_endtoend [--quick] [--out DIR]
"""

from __future__ import annotations

import argparse
from pathlib import Path

from experiments.common import RESULTS, write_csv
from experiments.runner import RunConfig, run_group

COLUMNS = ["family", "k", "T_actual", "tree_ops_per_update_gp", "tree_ops_per_update_rebuild",
           "hk_transitions_gp", "hk_transitions_rebuild", "hk_saved_fraction", "kept_fraction", "resolved", "infeasible"]


def run(quick: bool = False, out_dir: Path | None = None) -> list[Path]:
    out_dir = out_dir or RESULTS
    T = 40 if quick else 1000
    specs = ({"grid": {"rows": 8, "cols": 8}, "random_sparse": {"n": 60, "m": 300}} if quick else
             {"grid": {"rows": 20, "cols": 20}, "random_sparse": {"n": 400, "m": 2000}})
    ks = [3] if quick else [6, 10]
    rows = []
    for fam, params in specs.items():
        for k in ks:
            base = RunConfig(family=fam, family_params=params, k=k, p_delete=0.02, T=T, seed=5)
            res = run_group(base, variants=("rebuild_always", "gp"))
            ref = next(r for r in res if r["variant"] == "rebuild_always")
            gp = next(r for r in res if r["variant"] == "gp")
            n = max(1, gp["T_actual"])
            hk_ref, hk_gp = ref["hk_transitions"], gp["hk_transitions"]
            rows.append({
                "family": fam, "k": k, "T_actual": gp["T_actual"],
                "tree_ops_per_update_gp": round(gp["tree_work"] / n, 3),
                "tree_ops_per_update_rebuild": round(ref["tree_work"] / n, 3),
                "hk_transitions_gp": hk_gp, "hk_transitions_rebuild": hk_ref,
                "hk_saved_fraction": round(1 - hk_gp / hk_ref, 6) if hk_ref else 0.0,
                "kept_fraction": round((gp["kept"] + gp["kept_eps"]) / n, 6),
                "resolved": gp["resolved"], "infeasible": gp["infeasible"],
            })
    return [write_csv(rows, COLUMNS, out_dir / "e5_endtoend.csv")]


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--quick", action="store_true")
    ap.add_argument("--out", type=Path, default=None)
    a = ap.parse_args()
    for p in run(a.quick, a.out):
        print("wrote", p)
