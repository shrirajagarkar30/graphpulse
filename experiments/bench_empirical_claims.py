"""Empirical validation of certificate hit rate, operation savings, and adversarial bounds.

Measures UpdateStats.strategy and UpdateStats.work directly across all four graph families
(grid, hub_spoke, random_sparse, comb_adversarial) under a fixed seed (at least 1,000 updates per family).
Saves output as a structured Markdown table in docs/EMPIRICAL_EVALUATION.md.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from graphpulse.controller import BudgetedMaintainer
from graphpulse.generators import (
    comb_adversarial,
    grid,
    hub_spoke,
    random_sparse,
    random_updates,
)
from graphpulse.maintainer import RecomputeMaintainer


@dataclass
class FamilyMetrics:
    family: str
    n: int
    m: int
    updates: int
    cert_count: int
    alt_count: int
    repair_count: int
    fallback_count: int
    online_work: int
    rebuild_work: int

    @property
    def cert_hit_rate(self) -> float:
        """Percentage of updates resolved purely by O(1) certificate."""
        return (self.cert_count / self.updates) * 100.0

    @property
    def filter_hit_rate(self) -> float:
        """Percentage of updates resolved without bounded Dijkstra (cert + alt)."""
        return ((self.cert_count + self.alt_count) / self.updates) * 100.0

    @property
    def savings_pct(self) -> float:
        """Percentage savings in work compared to full from-scratch recomputation."""
        if self.rebuild_work == 0:
            return 0.0
        return (1.0 - (self.online_work / self.rebuild_work)) * 100.0

    @property
    def work_ratio(self) -> float:
        """Ratio of online work to rebuild work."""
        if self.rebuild_work == 0:
            return 0.0
        return self.online_work / self.rebuild_work


def run_benchmark(seed: int = 42, updates_per_family: int = 1000) -> list[FamilyMetrics]:
    families = [
        ("grid", grid(rows=35, cols=35, seed=seed, wmin=1, wmax=10)),
        ("hub_spoke", hub_spoke(hubs=15, spokes_per_hub=150, seed=seed)),
        ("random_sparse", random_sparse(n=400, m=4000, seed=seed, wmin=1, wmax=10)),
        ("comb_adversarial", comb_adversarial(n=450)),
    ]

    results: list[FamilyMetrics] = []

    for name, g in families:
        upds = random_updates(
            g, count=updates_per_family, seed=seed, mode="uniform", p_delete=0.4, w_increase_max=50
        )
        assert len(upds) == updates_per_family, f"Failed to generate {updates_per_family} for {name}"

        cand = BudgetedMaintainer(g, src=0, c=1.0)
        ref = RecomputeMaintainer(g, src=0)

        cert_cnt = 0
        alt_cnt = 0
        repair_cnt = 0
        fallback_cnt = 0
        total_online_work = 0
        total_rebuild_work = 0

        for u in upds:
            s_ref = ref.apply(u)
            s_cand = cand.apply(u)

            total_online_work += s_cand.work
            total_rebuild_work += s_ref.work

            if s_cand.strategy == "cert":
                cert_cnt += 1
            elif s_cand.strategy == "alt":
                alt_cnt += 1
            elif s_cand.strategy == "repair":
                repair_cnt += 1
            elif s_cand.strategy == "fallback":
                fallback_cnt += 1

        results.append(
            FamilyMetrics(
                family=name,
                n=g.n,
                m=g.m,
                updates=updates_per_family,
                cert_count=cert_cnt,
                alt_count=alt_cnt,
                repair_count=repair_cnt,
                fallback_count=fallback_cnt,
                online_work=total_online_work,
                rebuild_work=total_rebuild_work,
            )
        )

    return results


def generate_markdown_report(metrics: list[FamilyMetrics], seed: int) -> str:
    lines = [
        "# Empirical Benchmark Evaluation (Milestone 4 Hardening)",
        "",
        f"**Benchmark Configuration:** Fixed Seed = `{seed}`, `updates_per_family = 1,000`, `c = 1.0`, `p_delete = 0.4`.",
        "Measurements captured directly from `UpdateStats.strategy` and `UpdateStats.work` against baseline `RecomputeMaintainer`.",
        "",
        "## Summary Results Table",
        "",
        "| Topology Family | Vertices ($n$) | Edges ($m$) | Updates | Pure Cert Hit Rate (%) | Cert + Alt Hit Rate (%) | Online Work | Rebuild Work | Work Savings (%) | Online / Rebuild Ratio |",
        "|---|---|---|---|---|---|---|---|---|---|",
    ]

    for m in metrics:
        ratio_str = f"{m.work_ratio:.3f}x"
        savings_str = f"{m.savings_pct:+.1f}%"
        lines.append(
            f"| `{m.family}` | {m.n:,} | {m.m:,} | {m.updates:,} | {m.cert_hit_rate:.1f}% | {m.filter_hit_rate:.1f}% | {m.online_work:,} | {m.rebuild_work:,} | {savings_str} | {ratio_str} |"
        )

    lines.extend([
        "",
        "## Empirical Strategy Distribution",
        "",
        "| Topology Family | Total Updates | `cert` (1 SCAN) | `alt` (O(indeg)) | `repair` (<= B) | `fallback` (Abort + Rebuild) |",
        "|---|---|---|---|---|---|",
    ])

    for m in metrics:
        lines.append(
            f"| `{m.family}` | {m.updates:,} | {m.cert_count:,} ({m.cert_hit_rate:.1f}%) | {m.alt_count:,} | {m.repair_count:,} | {m.fallback_count:,} |"
        )

    benign = [m for m in metrics if m.family != "comb_adversarial"]
    cert_lo = min(m.cert_hit_rate for m in benign)
    cert_hi = max(m.cert_hit_rate for m in benign)
    sav_lo = min(m.savings_pct for m in metrics)
    sav_hi = max(m.savings_pct for m in metrics)
    total_fallbacks = sum(m.fallback_count for m in metrics)
    lines.extend([
        "",
        "## Observations (computed from the tables above)",
        "",
        f"1. **Certificate hit rate** on grid, hub_spoke and random_sparse ranged from {cert_lo:.1f}% to {cert_hi:.1f}% (single seed).",
        f"2. **Work savings** versus Dijkstra-only recomputation ranged from {sav_lo:.1f}% to {sav_hi:.1f}% across all four families.",
        f"3. **Fallbacks:** {total_fallbacks} in total. Uniform random updates rarely delete the critical chain edge of `comb_adversarial`, so this run does *not* exercise the worst case of the work bound (1 + c)F + 2; adversarial tightness is a Phase 7 experiment (E4).",
        "",
        "**Scope:** one seed, 1,000 uniform random updates per family, c = 1, `f_mode=\"last\"`; the rebuild baseline is Dijkstra only (F additionally includes the tight-edge recount). These are benign-workload measurements, not worst-case guarantees.",
        "",
    ])

    return "\n".join(lines)


def main() -> None:
    seed = 42
    print(f"Running empirical benchmarks across 4 graph families (seed={seed}, 1000 updates each)...")
    results = run_benchmark(seed=seed, updates_per_family=1000)

    report_md = generate_markdown_report(results, seed=seed)
    out_path = Path("docs/EMPIRICAL_EVALUATION.md")
    out_path.write_text(report_md, encoding="utf-8")
    print(f"Empirical evaluation table successfully generated at {out_path.resolve()}")
    try:
        print(report_md)
    except UnicodeEncodeError:
        print(report_md.encode("ascii", errors="replace").decode("ascii"))


if __name__ == "__main__":
    main()
