# Known Gaps & Observations (Phases 0–4 Hardening)

## Phase 0–4 Status: Fully Completed (Zero Functional Gaps)

Milestones 0.1 through 4.3 are fully implemented, verified, and tested. Specifically:
- **Milestone 4.3:**
  - `src/graphpulse/analysis.py`: Fully implements `measure()` and `theoretical_competitive_ratio()`.
  - `src/graphpulse/controller.py`: Fully implements `RandomizedBudget` with the optimal continuous ski-rental distribution $f(x) = \frac{e^x}{e - 1}$ on $[0, 1]$.
  - Proofs `docs/proofs/P1_repair_correctness.md`, `docs/proofs/P2_work_bound.md`, and `docs/proofs/P3_competitive_ratio.md` are complete and mathematically verified.
  - Tests `tests/test_competitive.py` implement test cases T4.3-01 through T4.3-10, all passing.

## Documented Empirical Observations (Not Gaps)
- **Stale-F vs. Oracle Mode:** In `f_mode="last"`, budget caps rely on the previous rebuild's operation count rather than $F_{\text{true}}$. As documented in T4.3-09, when graph density changes significantly over long deletion sequences, $F_{\text{last}}$ may overestimate or underestimate $F_{\text{true}}$, leading to bounded deviations from the exact theoretical competitive ratio. Oracle mode (`f_mode="oracle"`) strictly enforces the proven ratio.
- **Affected Set:** `find_affected` is counter-based and exact: it propagates scratch decrements of `tight[]` along old-tight out-edges and returns precisely `{x | dist_old[x] != dist_new[x]}` (verified against a Dijkstra oracle on 500 Hypothesis cases, T3.3-06, and by the differential runs). Work is `vol_out(A)` scans plus `2|A|` queue operations. (An earlier version of this note wrongly called it a tree-subtree superset.)
