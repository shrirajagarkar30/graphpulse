"""Small helpers shared by the experiment scripts (CSV + Markdown output)."""

from __future__ import annotations

import csv
import math
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
RESULTS = ROOT / "docs" / "results"


def fmt(x) -> str:
    if isinstance(x, float):
        if math.isinf(x):
            return "inf"
        return f"{x:.6g}"
    return str(x)


def write_csv(rows: list[dict], columns: list[str], path: Path) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=columns, lineterminator="\n")
        w.writeheader()
        for r in rows:
            w.writerow({c: fmt(r[c]) for c in columns})
    return path


def write_markdown(rows: list[dict], columns: list[str], path: Path, title: str, note: str = "") -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    lines = [f"# {title}", ""]
    if note:
        lines += [note, ""]
    lines += ["| " + " | ".join(columns) + " |", "|" + "|".join("---" for _ in columns) + "|"]
    for r in rows:
        lines.append("| " + " | ".join(fmt(r[c]) for c in columns) + " |")
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return path


def loglog_slope(xs: list[float], ys: list[float]) -> float:
    """Least-squares slope of log(y) against log(x), written by hand (no numpy)."""
    if len(xs) != len(ys) or len(xs) < 2:
        raise ValueError("need at least two (x, y) points of equal length")
    if any(x <= 0 for x in xs) or any(y <= 0 for y in ys):
        raise ValueError("log-log fit needs positive values")
    lx = [math.log(x) for x in xs]
    ly = [math.log(y) for y in ys]
    mx, my = sum(lx) / len(lx), sum(ly) / len(ly)
    num = sum((a - mx) * (b - my) for a, b in zip(lx, ly))
    den = sum((a - mx) ** 2 for a in lx)
    if den == 0:
        raise ValueError("x values must not all be equal")
    return num / den
