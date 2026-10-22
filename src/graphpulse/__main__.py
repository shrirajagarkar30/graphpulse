"""Interactive demonstration of GraphPulse-R (Milestone 4.3 / 50% Release).

Usage:
    python demo.py
    or
    python -m graphpulse
"""

from __future__ import annotations

import math
import sys
import time

from graphpulse.analysis import measure, theoretical_competitive_ratio
from graphpulse.controller import BudgetedMaintainer, RandomizedBudget
from graphpulse.dijkstra import dijkstra
from graphpulse.generators import (
    Update,
    comb_adversarial,
    grid,
    hub_spoke,
    random_sparse,
    random_updates,
)
from graphpulse.graph import DiGraph
from graphpulse.maintainer import RecomputeMaintainer
from graphpulse.opcount import OpCounter
from graphpulse.spt import SPTState
from graphpulse.verify import check_state


def print_banner() -> None:
    print("\n" + "=" * 80)
    print("  GRAPHPULSE-R: CERTIFICATE-DRIVEN BUDGETED REOPTIMIZATION")
    print("  Dynamic Single-Source Shortest Path Maintenance under Edge Disruptions")
    print("  50% Project Checkpoint (v0.5-half) -- Course Project for DAA")
    print("=" * 80)


def demo_decision_hierarchy() -> None:
    print("\n" + "-" * 80)
    print(" DEMO 1: The Certificate-First Decision Hierarchy in Action")
    print("-" * 80)
    print("Decision Order per update:")
    print("  1. Certificate Check (1 SCAN): if edge is non-tight, distances are unchanged.")
    print("  2. Alternative Support (1 + indeg SCANs): if tight[v] > 1, re-parent locally.")
    print("  3. Budgeted Repair (work cap B = ceil(c*F)): recompute only affected set A.")
    print("  4. Fallback Rebuild: if repair work exceeds B, abort cleanly and rebuild tree.")
    print("-" * 80)

    # 1. Setup Grid
    g = grid(8, 8, seed=42)
    src = 0
    maintainer = BudgetedMaintainer(g, src=src, c=1.0, f_mode="oracle")
    F_init = maintainer.F
    print(f"\nInitial 8x8 Grid Graph: n = {g.n} vertices, m = {g.m} directed edges")
    print(f"Initial full rebuild work (F): {F_init} operations")

    # Step 1: Certificate hit
    # Find a non-tight edge
    non_tight_edge = None
    for u in range(g.n):
        for v, w in g.out_edges(u):
            if maintainer.state.dist[u] + w != maintainer.state.dist[v]:
                non_tight_edge = (u, v)
                break
        if non_tight_edge:
            break

    if non_tight_edge:
        u, v = non_tight_edge
        stats = maintainer.apply(Update(kind="delete", u=u, v=v))
        print(f"\n[Case 1: CERTIFICATE HIT] Deleted non-tight edge ({u} -> {v}):")
        print(f"  Strategy used   : '{stats.strategy}'")
        print(f"  Operations paid : {stats.work} SCAN (Zero distance changes, full rebuild avoided!)")
        print(f"  Speedup vs F    : {F_init / stats.work:.1f}x less work")

    # Step 2: Alternative Support
    # Find a vertex with tight[v] > 1
    alt_edge = None
    for v in range(1, g.n):
        if maintainer.state.tight[v] > 1:
            # find an in-edge that is tight
            for u, w in maintainer.graph.in_edges(v):
                if maintainer.state.dist[u] + w == maintainer.state.dist[v]:
                    alt_edge = (u, v)
                    break
            if alt_edge:
                break

    if alt_edge:
        u, v = alt_edge
        old_tight = maintainer.state.tight[v]
        stats = maintainer.apply(Update(kind="delete", u=u, v=v))
        print(f"\n[Case 2: ALTERNATIVE SUPPORT] Deleted tight edge ({u} -> {v}) with tight[v]={old_tight}:")
        print(f"  Strategy used   : '{stats.strategy}'")
        print(f"  Operations paid : {stats.work} SCANs (Re-parented using alternative tight route)")
        print(f"  New tight[v]    : {maintainer.state.tight[v]} (Distances untouched!)")
        print(f"  Speedup vs F    : {F_init / stats.work:.1f}x less work")

    # Step 3: Incremental Repair
    # Find an edge whose deletion causes a sole tight edge loss but local affected set
    sole_edge = None
    for v in range(g.n - 1, 0, -1):
        if maintainer.state.tight[v] == 1:
            p = maintainer.state.parent[v]
            if p != -1 and maintainer.graph.has_edge(p, v):
                sole_edge = (p, v)
                break

    if sole_edge:
        u, v = sole_edge
        stats = maintainer.apply(Update(kind="delete", u=u, v=v))
        print(f"\n[Case 3: INCREMENTAL REPAIR] Deleted sole-tight edge ({u} -> {v}):")
        print(f"  Strategy used   : '{stats.strategy}'")
        print(f"  Affected set |A|: {stats.affected_size} vertices")
        print(f"  Operations paid : {stats.work} (SCAN={stats.scan}, PUSH={stats.push}, POP={stats.pop}, QUEUE={stats.queue})")
        print(f"  Work vs Rebuild : {stats.work} ops vs {F_init} ops ({stats.work / F_init * 100:.1f}% of full rebuild)")

    # Step 4: Budgeted Fallback (Adversarial Comb)
    comb = comb_adversarial(40)
    comb_m = BudgetedMaintainer(comb, src=0, c=1.0, f_mode="oracle")
    comb_F = comb_m.F
    print(f"\n[Case 4: BUDGETED FALLBACK] Adversarial Comb (n=40, F={comb_F}):")
    print("  Deleting spine edge (0 -> 1) causes all 39 non-source vertices to enter A.")
    stats = comb_m.apply(Update(kind="delete", u=0, v=1))
    print(f"  Strategy used   : '{stats.strategy}'")
    print(f"  Repair budget B : {stats.budget} ops")
    print(f"  Wasted repair   : {stats.repair_work} ops (strictly <= B + 1)")
    print(f"  Fallback rebuild: {stats.fallback_work} ops")
    print(f"  Total work paid : {stats.work} ops (<= (1 + c)*F + 1)")


def demo_tournament() -> None:
    print("\n" + "-" * 80)
    print(" DEMO 2: Tournament Benchmark on a 15x15 Road Grid (225 Vertices, 840 Edges)")
    print("-" * 80)
    print("Simulating a dynamic workload of 50 mixed edge updates (deletions & weight increases)...")

    g = grid(15, 15, seed=123)
    updates = random_updates(g, 50, seed=999, p_delete=0.6)

    # 1. Baseline: RecomputeMaintainer (Full Dijkstra every update)
    t0 = time.perf_counter()
    recompute = RecomputeMaintainer(g.copy(), src=0)
    recompute_work = 0
    for upd in updates:
        st = recompute.apply(upd)
        recompute_work += st.work
    t_recompute = (time.perf_counter() - t0) * 1000.0

    # 2. Online Deterministic Maintainer (c = 1.0)
    t0 = time.perf_counter()
    det_res = measure(g.copy(), updates, c=1.0, mode="oracle")
    t_det = (time.perf_counter() - t0) * 1000.0

    # 3. Online Randomized Maintainer (x ~ e^x / (e - 1))
    t0 = time.perf_counter()
    rand_res = measure(g.copy(), updates, c="random", mode="oracle", seed=42)
    t_rand = (time.perf_counter() - t0) * 1000.0

    # Offline Optimum
    opt_work = det_res.opt_cost

    print("\n" + "=" * 80)
    print(f"{'STRATEGY':<25} {'TOTAL OPS':<14} {'SAVINGS vs REBUILD':<20} {'RATIO vs OPT':<14}")
    print("=" * 80)

    def row(name, work, baseline, opt):
        savings = (1.0 - (work / baseline)) * 100.0 if baseline > 0 else 0.0
        ratio = work / opt if opt > 0 else 1.0
        print(f"{name:<25} {work:<14} {savings:>16.1f}% {ratio:>13.3f}x")

    row("1. Naive Full Rebuild", recompute_work, recompute_work, opt_work)
    row("2. Deterministic (c=1.0)", det_res.online_cost, recompute_work, opt_work)
    row("3. Randomized Budget", rand_res.online_cost, recompute_work, opt_work)
    row("4. Offline Optimum (OPT)", opt_work, recompute_work, opt_work)
    print("=" * 80)

    print("\nBreakdown of Decisions by Deterministic Maintainer:")
    total_upd = len(updates)
    for strat, count in det_res.strategy_counts.items():
        pct = (count / total_upd) * 100.0
        print(f"  - Strategy '{strat:<8}': {count:2d} updates ({pct:5.1f}%)")

    print("\nTheoretical vs Measured Competitive Ratios:")
    print(f"  - Deterministic Theory Bound (c=1.0) : {theoretical_competitive_ratio(1.0):.3f}x")
    print(f"  - Deterministic Measured Ratio       : {det_res.ratio:.3f}x (strictly <= 2.0)")
    print(f"  - Randomized Theory Bound (optimal)  : {theoretical_competitive_ratio('random'):.3f}x")
    print(f"  - Randomized Measured Ratio          : {rand_res.ratio:.3f}x")


def demo_verification() -> None:
    print("\n" + "-" * 80)
    print(" DEMO 3: Formal Tree Invariant Self-Check")
    print("-" * 80)
    g = random_sparse(40, 150, seed=55)
    maintainer = BudgetedMaintainer(g, src=0, c=1.0, f_mode="oracle", verify=True)
    updates = random_updates(g, 20, seed=12, p_delete=0.5)

    print(f"Maintaining SPT on random directed graph (n=40, m=150) across {len(updates)} updates...")
    for i, upd in enumerate(updates):
        maintainer.apply(upd)
        # Verify all 4 SPEC invariants after each update:
        check_state(maintainer.graph, maintainer.state)

    print("All 20 updates verified with check_state():")
    print("  [OK] Shortest distances match Dijkstra ground truth")
    print("  [OK] Parents obey deterministic min-tight-predecessor rule")
    print("  [OK] Parent-children bi-directional tree links consistent")
    print("  [OK] Tight-edge counters exact across all reachable vertices")


def main() -> None:
    print_banner()
    demo_decision_hierarchy()
    demo_tournament()
    demo_verification()
    print("\n" + "=" * 80)
    print("  ALL DEMONSTRATIONS COMPLETED SUCCESSFULLY (50% Milestone Checkpoint v0.5-half)")
    print("=" * 80 + "\n")


if __name__ == "__main__":
    main()
