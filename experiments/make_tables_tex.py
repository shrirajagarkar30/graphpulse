"""Generate paper/generated/*.tex from docs/results/*.csv (Milestone 8.3).

No number in the paper's Results section is typed by hand: every table and every
quoted figure is produced here from the committed CSVs (macros in numbers.tex).

Usage: python -m experiments.make_tables_tex [--results DIR] [--out DIR]
"""

from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd

from experiments.common import RESULTS, ROOT

OUT = ROOT / "paper" / "generated"


def esc(x) -> str:
    return str(x).replace("_", r"\_").replace("%", r"\%")


def num(x, nd=3) -> str:
    if isinstance(x, str):
        return esc(x)
    if pd.isna(x):
        return "--"
    if float(x) == float("inf"):
        return r"$\infty$"
    if float(x).is_integer() and abs(x) >= 100:
        return f"{int(x):,}".replace(",", r"\,")
    return f"{x:.{nd}f}".rstrip("0").rstrip(".") if isinstance(x, float) else str(x)


def tabular(df: pd.DataFrame, header: list[str], caption: str, label: str, align: str | None = None) -> str:
    align = align or "l" + "r" * (len(header) - 1)
    lines = [r"\begin{table}[t]", r"\centering", r"\caption{" + caption + "}", r"\label{" + label + "}",
             r"\small", r"\begin{tabular}{" + align + "}", r"\hline",
             " & ".join(esc(h) for h in header) + r" \\", r"\hline"]
    for row in df.itertuples(index=False):
        lines.append(" & ".join(num(v) for v in row) + r" \\")
    lines += [r"\hline", r"\end{tabular}", r"\end{table}", ""]
    return "\n".join(lines)


def build(results: Path) -> dict[str, str]:
    out: dict[str, str] = {}
    macros: list[str] = []

    e1 = pd.read_csv(results / "e1_budget.csv", dtype={"c": str})
    det = e1[~e1["c"].isin(["random"])].copy()
    det["rho"] = det["rho"].astype(float)
    agg = det.groupby("c", sort=False).agg(max_ratio=("ratio", "max"), mean_ratio=("ratio", "mean"),
                                            rho=("rho", "first"), fallback=("fallback_rate", "mean")).reset_index()
    agg["c"] = agg["c"].map(lambda s: r"$\infty$" if s == "inf" else s)
    out["e1_summary.tex"] = tabular(agg, ["c", "max ratio", "mean ratio", r"$\rho(c)$", "fallback rate"],
                                    "E1: measured online/offline cost ratio over all families, update modes and seeds "
                                    "(oracle-F mode) against the proven bound.", "tab:e1")
    macros.append(r"\newcommand{\EOneRows}{" + str(len(e1)) + "}")

    e2 = pd.read_csv(results / "e2_shares.csv")
    sub = e2[(e2["mode"] == "uniform") & (e2["p_delete"] == 0.5)][
        ["family", "T_actual", "share_cert", "share_alt", "share_repair", "share_fallback", "mean_touched"]]
    out["e2_shares.tex"] = tabular(sub, ["family", "updates", "cert", "alt", "repair", "fallback", "touched trees"],
                                   "E2: strategy shares over all tree-updates (uniform updates, deletion share 0.5, "
                                   "k fixed in the experiment configuration).", "tab:e2shares")

    ab = pd.read_csv(results / "e2_ablation.csv")
    ab = ab[(ab["family"] == "grid") & (ab["mode"] == "uniform") & (ab["eps"] == 0)]
    abt = ab[["variant", "lazy_tour", "tree_work", "hk_transitions", "strat_fallback"]]
    out["e2_ablation.tex"] = tabular(abt, ["variant", "lazy tour", "tree work", "HK transitions", "fallbacks"],
                                     "E2 ablation on the grid (identical updates, exact tours): total tree operations "
                                     "and Held--Karp transitions.", "tab:e2abl")

    e3 = pd.read_csv(results / "e3_scaling.csv")
    out["e3_scaling.tex"] = tabular(
        e3[["side", "n", "gp_ops_per_update", "rebuild_ops_per_update", "T_rebuild", "ratio"]],
        ["side", "$n$", "GraphPulse-R ops/update", "rebuild ops/update", r"$T_{\mathrm{rebuild}}$", "ratio"],
        "E3: mean tree operations per update on $s\\times s$ grids. The rebuild baseline is measured on the first "
        "$T_{\\mathrm{rebuild}}$ updates only.", "tab:e3")
    sl = pd.read_csv(results / "e3_slopes.csv")
    for r in sl.itertuples():
        name = {"gp_ops_vs_n": "EThreeSlopeGP", "rebuild_ops_vs_n": "EThreeSlopeRebuild"}[r.series]
        macros.append(r"\newcommand{\%s}{%.2f}" % (name, r.slope_loglog))

    e4 = pd.read_csv(results / "e4_summary.csv")
    out["e4_summary.tex"] = tabular(e4[["c", "max_ratio", "at_frac", "rho", "max_over_rho"]],
                                    ["c", "max measured", "at frac", r"$\rho(c)$", "max / $\\rho$"],
                                    "E4: maximum measured ratio on the \\texttt{partial\\_comb} sweep.", "tab:e4")
    for r in e4.itertuples():
        macros.append(r"\newcommand{\EFourMax%s}{%.3f}" % ({0.5: "Half", 1.0: "One", 2.0: "Two"}[r.c], r.max_ratio))

    e5 = pd.read_csv(results / "e5_endtoend.csv")
    out["e5_endtoend.tex"] = tabular(
        e5[["family", "k", "T_actual", "tree_ops_per_update_gp", "tree_ops_per_update_rebuild", "hk_saved_fraction",
            "kept_fraction"]],
        ["family", "$k$", "updates", "ops/update GP", "ops/update rebuild", "HK saved", "tour kept"],
        "E5: end-to-end pipeline versus recompute-everything (synthetic graphs only).", "tab:e5")

    out["numbers.tex"] = "\n".join(macros) + "\n"
    return out


def run(results: Path | None = None, out_dir: Path | None = None) -> list[Path]:
    results, out_dir = results or RESULTS, out_dir or OUT
    out_dir.mkdir(parents=True, exist_ok=True)
    paths = []
    for name, text in build(results).items():
        p = out_dir / name
        p.write_text(text, encoding="utf-8", newline="\n")
        paths.append(p)
    return paths


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--results", type=Path, default=None)
    ap.add_argument("--out", type=Path, default=None)
    a = ap.parse_args()
    for p in run(a.results, a.out):
        print("wrote", p)
