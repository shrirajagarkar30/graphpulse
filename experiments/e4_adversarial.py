"""E4: inputs that make the competitive-ratio bound tight (Milestone 7.5).

`partial_comb(n, frac)` lets r/F be tuned continuously: deleting (0, 1) changes
the distance of exactly vertices 1..m-1.  For each budget c we sweep `frac`,
measure r and F on the single deletion, and the ratio online / min(r, F), and
report the maximum measured ratio next to rho(c) = (1+c)/min(c,1).

The ratio peaks (i) just above r = c*F for c < 1 (near (1+c)/c) and (ii) once
r > F for c >= 1 (near 1+c).  A maximum far below rho(c) means the sweep needs
retuning, not that the theory is wrong (see docs/results/NOTES.md).

Usage: python -m experiments.e4_adversarial [--quick] [--out DIR]
"""

from __future__ import annotations

import argparse
import math
from pathlib import Path

from experiments.common import RESULTS, write_csv
from graphpulse.analysis import measure, theoretical_competitive_ratio
from graphpulse.generators import Update, apply_update, partial_comb
from graphpulse.opcount import OpCounter
from graphpulse.repair import repair
from graphpulse.spt import SPTState

COLUMNS = ["c", "frac", "m", "affected", "r", "F", "r_over_F", "online", "opt", "ratio", "rho", "bound_ok"]
SUMMARY_COLS = ["c", "max_ratio", "at_frac", "rho", "max_over_rho"]


def single_deletion(n: int, frac: float, c: float) -> dict:
    g = partial_comb(n, frac)
    upd = Update(kind="delete", u=0, v=1)
    # r and F on the updated graph (oracle quantities)
    st = SPTState.build(g, 0, OpCounter())
    g2 = g.copy()
    apply_update(g2, upd)
    rc = OpCounter()
    st_copy = st.copy()
    from graphpulse.repair import find_affected
    affected = len(find_affected(st, g2, 1))
    repair(st_copy, g2, 0, 1, budget=None, counter=rc)
    r = rc.work
    F = SPTState.build(g2, 0, OpCounter()).F
    res = measure(g, [upd], c=c, mode="oracle", src=0)
    rho = theoretical_competitive_ratio(c)
    slack = 2.0 / res.opt_cost
    return {"c": c, "frac": frac, "m": math.ceil(frac * (n - 1)) + 1, "affected": affected, "r": r, "F": F,
            "r_over_F": round(r / F, 6), "online": res.online_cost, "opt": res.opt_cost,
            "ratio": round(res.ratio, 6), "rho": rho, "bound_ok": int(res.ratio <= rho + slack)}


def run(quick: bool = False, out_dir: Path | None = None) -> list[Path]:
    out_dir = out_dir or RESULTS
    n = 40 if quick else 400
    steps = 20 if quick else 100
    rows = []
    for c in (0.5, 1.0, 2.0):
        for i in range(1, steps + 1):
            row = single_deletion(n, i / steps, c)
            if not row["bound_ok"]:
                raise AssertionError(f"ratio {row['ratio']} exceeds rho(c)={row['rho']} + slack at {row}")
            rows.append(row)
    paths = [write_csv(rows, COLUMNS, out_dir / "e4_adversarial.csv")]
    summary = []
    for c in (0.5, 1.0, 2.0):
        best = max((r for r in rows if r["c"] == c), key=lambda r: r["ratio"])
        summary.append({"c": c, "max_ratio": best["ratio"], "at_frac": best["frac"], "rho": best["rho"],
                        "max_over_rho": round(best["ratio"] / best["rho"], 6)})
    paths.append(write_csv(summary, SUMMARY_COLS, out_dir / "e4_summary.csv"))
    return paths


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--quick", action="store_true")
    ap.add_argument("--out", type=Path, default=None)
    a = ap.parse_args()
    for p in run(a.quick, a.out):
        print("wrote", p)
