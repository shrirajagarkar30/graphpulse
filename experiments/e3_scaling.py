"""E3: growth of per-update cost with graph size n and with k (Milestone 7.5).

Mean operations per update of the multi-tree engine (`gp`, c = 1) against full
recomputation of every tree (`rebuild_always`, each tree rebuilt with
SPTState.build, i.e. F including the tight recount).  Held-Karp is excluded here
(it depends on k only, not on n); it is covered by E2 / E5.

HONESTY NOTE (recorded in the CSV): on the large grids a full rebuild of every
tree after every update is very slow in pure Python, so `rebuild_always` is
measured on the first `T_rebuild` updates only (all T updates for small grids).
Its per-update mean is therefore a sampled estimate over `T_rebuild` updates,
and the column `T_rebuild` says exactly how many.

Usage: python -m experiments.e3_scaling [--quick] [--out DIR]
"""

from __future__ import annotations

import argparse
import random
from pathlib import Path

from experiments.common import RESULTS, loglog_slope, write_csv
from graphpulse.generators import apply_update, grid, random_updates
from graphpulse.opcount import OpCounter
from graphpulse.spt import SPTState
from graphpulse.terminals import MultiTreeManager

SCALE_COLS = ["side", "n", "m", "k", "T_gp", "gp_ops_per_update", "T_rebuild", "rebuild_ops_per_update", "ratio"]
K_COLS = ["k", "n", "T_gp", "gp_ops_per_update", "T_rebuild", "rebuild_ops_per_update", "ratio"]
SLOPE_COLS = ["series", "slope_loglog"]


def _terms(g, k, seed=1):
    return [0] + random.Random(seed).sample(range(1, g.n), k)


def measure_point(g, k: int, updates, t_rebuild: int, seed: int = 1) -> tuple[float, float]:
    """Return (gp mean ops/update over all updates, rebuild mean ops/update over the first t_rebuild)."""
    terms = _terms(g, k, seed)
    mgr = MultiTreeManager(g, terms, c=1.0)
    gp = sum(mgr.apply(u).total_work for u in updates)

    work = g.copy()
    rb = 0
    used = updates[:t_rebuild]
    for u in used:
        apply_update(work, u)
        for t in terms:
            c = OpCounter()
            SPTState.build(work, t, c)
            rb += c.work
    return gp / max(1, len(updates)), rb / max(1, len(used))


def run(quick: bool = False, out_dir: Path | None = None) -> list[Path]:
    out_dir = out_dir or RESULTS
    sides = [6, 8] if quick else [20, 40, 80, 160]
    T = 30 if quick else 1000
    k = 4 if quick else 8
    rb_cap = {6: 30, 8: 30} if quick else {20: 1000, 40: 1000, 80: 100, 160: 20}
    rows = []
    for side in sides:
        g = grid(side, side, seed=1)
        ups = random_updates(g, T, seed=1, mode="uniform", p_delete=0.02)
        gp, rb = measure_point(g, k, ups, min(rb_cap[side], len(ups)))
        rows.append({"side": side, "n": g.n, "m": g.m, "k": k, "T_gp": len(ups), "gp_ops_per_update": round(gp, 3),
                     "T_rebuild": min(rb_cap[side], len(ups)), "rebuild_ops_per_update": round(rb, 3),
                     "ratio": round(gp / rb, 6)})
    paths = [write_csv(rows, SCALE_COLS, out_dir / "e3_scaling.csv")]

    ns = [float(r["n"]) for r in rows]
    slopes = [
        {"series": "gp_ops_vs_n", "slope_loglog": round(loglog_slope(ns, [r["gp_ops_per_update"] for r in rows]), 4)},
        {"series": "rebuild_ops_vs_n", "slope_loglog": round(loglog_slope(ns, [r["rebuild_ops_per_update"] for r in rows]), 4)},
    ]
    paths.append(write_csv(slopes, SLOPE_COLS, out_dir / "e3_slopes.csv"))

    side_k = 8 if quick else 30
    g = grid(side_k, side_k, seed=1)
    Tk = 30 if quick else 200
    ups = random_updates(g, Tk, seed=1, mode="uniform", p_delete=0.02)
    krows = []
    for kk in ([2, 4] if quick else [4, 8, 12, 16]):
        gp, rb = measure_point(g, kk, ups, min(Tk, len(ups)))
        krows.append({"k": kk, "n": g.n, "T_gp": len(ups), "gp_ops_per_update": round(gp, 3),
                      "T_rebuild": len(ups), "rebuild_ops_per_update": round(rb, 3), "ratio": round(gp / rb, 6)})
    paths.append(write_csv(krows, K_COLS, out_dir / "e3_k.csv"))
    return paths


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--quick", action="store_true")
    ap.add_argument("--out", type=Path, default=None)
    a = ap.parse_args()
    for p in run(a.quick, a.out):
        print("wrote", p)
