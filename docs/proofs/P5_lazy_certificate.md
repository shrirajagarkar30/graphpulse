# Proof P5: Soundness of the Lazy Tour Certificate

**Reviewer sign-off:** PENDING (requires two team members other than the author; not signed by the tool that drafted this file)

**Milestone 6.4/6.6.** Setting: terminal matrices `D_t` after updates `t = 0,1,2,…` obtained from a graph whose edge weights never decrease (deletion = weight ∞).

## 1. Monotonicity

**Lemma 3 (distances only grow).** If `w_t ≥ w_{t−1}` pointwise, then `dist_t(x,y) ≥ dist_{t−1}(x,y)` for all `x,y`.
*Proof.* Every path in `G_t` is a path in `G_{t−1}` of no greater length (deleted edges have weight ∞, so paths using them cost ∞); hence the minimum over paths cannot decrease. ∎

**Corollary 4.** `D_t[i][j] ≥ D_{t−1}[i][j]`, hence for every permutation `π`, `cost_t(π) ≥ cost_{t−1}(π)`, and `OPT_t ≥ OPT_{t−1}`. (Costs are sums of entries with non-negative coefficients; `INF` propagates.) The implementation enforces the hypothesis: `TerminalMatrix.refresh` and `TourCertificate` raise `InvariantViolation` on any decrease.

## 2. Exact keep (Lemma 5)

Let `T*` be optimal for `D_s` (the last exact solve) with used entries `U = {(0,π₁),(π₁,π₂),…,(π_k,0)}`. Let `t > s` and let `Δ = ⋃_{s<u≤t} changed_u` be all entries that changed since `s`.

**Lemma 5.** If `Δ ∩ U = ∅` then `T*` is optimal for `D_t`.
*Proof.* `cost_t(T*) = cost_s(T*) = OPT_s` because every used entry is unchanged. For any `π`, `cost_t(π) ≥ cost_s(π) ≥ OPT_s` (Corollary 4). So `cost_t(T*) ≤ cost_t(π)` for all `π`. ∎

*Implementation note.* `TourCertificate.decide` accumulates `changed` sets since the last `rebase`, so the union `Δ` — not just the latest per-update set — is tested. Without accumulation an earlier ε-keep followed by an update touching nothing would wrongly report KEEP (test `test_t64_accumulated_changes_after_eps_keep`).

*Conservativeness.* The converse fails: a used entry may change while `T*` stays optimal (e.g. an equal-cost alternative tour exists). The certificate then RESOLVES unnecessarily; this costs time, never correctness (T6.4-04).

## 3. Infeasible case
If `OPT_s = ∞` then `OPT_t ≥ OPT_s = ∞` by Corollary 4: no tour can become feasible. KEEP is sound, and the pipeline reports `infeasible` with zero DP transitions.

## 4. ε-tolerant keep
Let `LB = OPT_s` (stored at the last exact solve) and fix `ε ≥ 0`.

**Lemma 6.** If `cost_t(T*) ≤ (1+ε)·LB` then `cost_t(T*) ≤ (1+ε)·OPT_t`.
*Proof.* `OPT_t ≥ OPT_s = LB` (Corollary 4), so `cost_t(T*) ≤ (1+ε)LB ≤ (1+ε)OPT_t`. ∎

**Warning (ratchet bug).** `LB` must not be raised to `cost_t(T*)` when keeping under ε: a second keep would then compare against an inflated bound and the guarantee compounds to `(1+ε)²…`. `TourCertificate.decide_eps` never modifies `LB`; only `rebase` (after an exact solve) does (T6.4-07).

## 5. Empirical support (not part of the proof)
`tests/test_tourcert.py`: soundness of KEEP on 500 random cases, ε-bound on 500 random cases (ε ∈ {0.05, 0.2}); `tests/test_pipeline.py`: pipeline cost equals the recompute-everything reference after every update (exact mode) and stays within `(1+ε)` in ε-mode.
