"""Generate every figure from the committed result CSVs (Milestone 7.6).

Figures are never edited by hand.  Style is print-safe in grayscale: distinct
markers and line styles, no colour-only encoding.

  Fig A  measured ratio versus rho(c)        <- e1_budget.csv, e4_adversarial.csv
  Fig B  stacked strategy shares per family  <- e2_shares.csv
  Fig C  ops per update versus n (log-log)   <- e3_scaling.csv
  Fig D  adversarial sweep                   <- e4_adversarial.csv
  Fig E  end-to-end savings                  <- e5_endtoend.csv

Usage: python -m experiments.make_figures [--results DIR] [--out DIR]
"""

from __future__ import annotations

import argparse
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402
import pandas as pd  # noqa: E402

from experiments.common import RESULTS, ROOT  # noqa: E402

FIGURES = ROOT / "docs" / "figures"
MARKERS = ["o", "s", "^", "D", "v", "P"]
STYLES = ["-", "--", "-.", ":"]
HATCHES = ["", "//", "..", "xx"]
plt.rcParams.update({"font.size": 9, "axes.grid": True, "grid.alpha": 0.3, "figure.dpi": 100,
                     "pdf.fonttype": 42, "svg.hashsalt": "graphpulse"})


def _save(fig, out: Path, name: str) -> list[Path]:
    out.mkdir(parents=True, exist_ok=True)
    paths = []
    for ext in ("pdf", "png"):
        p = out / f"{name}.{ext}"
        fig.savefig(p, bbox_inches="tight", metadata={"Creator": "graphpulse", "CreationDate": None} if ext == "pdf" else None)
        paths.append(p)
    plt.close(fig)
    return paths


def fig_a(res: Path, out: Path) -> list[Path]:
    e4 = pd.read_csv(res / "e4_summary.csv")
    e1 = pd.read_csv(res / "e1_budget.csv")
    e1 = e1[~e1["c"].isin(["0", "inf", "random", "0.0"])].copy()
    e1["c"] = e1["c"].astype(float)
    e1m = e1.groupby("c")["ratio"].max().reset_index()
    fig, ax = plt.subplots(figsize=(4.6, 3.2))
    cs = [x / 20 for x in range(4, 61)]
    ax.plot(cs, [max(1 + c, (1 + c) / c) for c in cs], "k-", label=r"proven $\rho(c)=(1+c)/\min(c,1)$")
    ax.plot(e1m["c"], e1m["ratio"], marker="o", linestyle="--", color="0.35", label="E1 max measured (benign + tree-edge updates)")
    ax.plot(e4["c"], e4["max_ratio"], marker="^", linestyle="-.", color="0.1", label="E4 max measured (adversarial sweep)")
    ax.set_xlabel("budget multiplier c")
    ax.set_ylabel("online cost / offline optimum")
    ax.set_ylim(0.9, 6)
    ax.legend(fontsize=7)
    return _save(fig, out, "fig_a_ratio_vs_rho")


def fig_b(res: Path, out: Path) -> list[Path]:
    df = pd.read_csv(res / "e2_shares.csv")
    sub = df[(df["mode"] == "uniform") & (df["p_delete"] == 0.5)]
    fig, ax = plt.subplots(figsize=(4.6, 3.2))
    bottom = [0.0] * len(sub)
    for i, s in enumerate(["cert", "alt", "repair", "fallback"]):
        vals = list(sub[f"share_{s}"])
        ax.bar(list(sub["family"]), vals, bottom=bottom, label=s, color=str(0.15 + 0.22 * i), hatch=HATCHES[i], edgecolor="k")
        bottom = [b + v for b, v in zip(bottom, vals)]
    ax.set_ylabel("share of tree-updates")
    ax.set_title("strategy shares (uniform updates, p_delete=0.5)", fontsize=8)
    ax.tick_params(axis="x", labelrotation=15)
    ax.legend(fontsize=7, ncol=4, loc="upper center", bbox_to_anchor=(0.5, -0.22))
    return _save(fig, out, "fig_b_strategy_shares")


def fig_c(res: Path, out: Path) -> list[Path]:
    df = pd.read_csv(res / "e3_scaling.csv")
    fig, ax = plt.subplots(figsize=(4.6, 3.2))
    ax.loglog(df["n"], df["gp_ops_per_update"], marker="o", linestyle="-", color="k", label="GraphPulse-R (gp, c=1)")
    ax.loglog(df["n"], df["rebuild_ops_per_update"], marker="s", linestyle="--", color="0.4", label="rebuild every tree")
    ax.set_xlabel("vertices n")
    ax.set_ylabel("operations per update")
    ax.legend(fontsize=7)
    return _save(fig, out, "fig_c_scaling")


def fig_d(res: Path, out: Path) -> list[Path]:
    df = pd.read_csv(res / "e4_adversarial.csv")
    fig, ax = plt.subplots(figsize=(4.6, 3.2))
    for i, (c, grp) in enumerate(df.groupby("c")):
        ax.plot(grp["r_over_F"], grp["ratio"], marker=MARKERS[i], linestyle=STYLES[i], color="k", markersize=3,
                label=f"c={c:g} (rho={grp['rho'].iloc[0]:g})")
    ax.set_xlabel("r / F (repair cost over rebuild cost)")
    ax.set_ylabel("online / min(r, F)")
    ax.legend(fontsize=7)
    return _save(fig, out, "fig_d_adversarial")


def fig_e(res: Path, out: Path) -> list[Path]:
    df = pd.read_csv(res / "e5_endtoend.csv")
    labels = [f"{r.family}\nk={r.k}" for r in df.itertuples()]
    fig, ax = plt.subplots(figsize=(4.6, 3.2))
    x = range(len(df))
    ax.bar([i - 0.2 for i in x], 1 - df["tree_ops_per_update_gp"] / df["tree_ops_per_update_rebuild"], width=0.4,
           color="0.3", hatch="//", edgecolor="k", label="tree-operation savings")
    ax.bar([i + 0.2 for i in x], df["hk_saved_fraction"], width=0.4, color="0.75", hatch="..", edgecolor="k",
           label="Held-Karp transitions saved")
    ax.set_xticks(list(x))
    ax.set_xticklabels(labels, fontsize=7)
    ax.set_ylabel("fraction saved vs recompute-everything")
    ax.set_ylim(0, 1.05)
    ax.legend(fontsize=7, loc="lower right")
    return _save(fig, out, "fig_e_endtoend")


def run(results: Path | None = None, out_dir: Path | None = None) -> list[Path]:
    results, out_dir = results or RESULTS, out_dir or FIGURES
    paths: list[Path] = []
    for f in (fig_a, fig_b, fig_c, fig_d, fig_e):
        paths += f(results, out_dir)
    return paths


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--results", type=Path, default=None)
    ap.add_argument("--out", type=Path, default=None)
    a = ap.parse_args()
    for p in run(a.results, a.out):
        print("wrote", p)
