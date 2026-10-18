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
- **Affected Set Bound:** `find_affected` computes the structural tree subtree descending from edge $(u, v)$ with $O(|T(v)|)$ work, which is a sound superset of the exact metric affected set $\{x \mid dist_{old}[x] \neq dist_{new}[x]\}$. On graphs with alternative tight paths, vertices in $T(v)$ may retain identical distances; Dijkstra recompute localizes to this bounded neighborhood.
