# GraphPulse-R — Repository Analysis Report (Phases 1–5 of the analysis brief)

**Analysed:** 2026-10-20 · **Commit:** `main` @ `0e02495` · **Env:** Windows 11, Python 3.14.7, fresh `.venv` from pinned `requirements-dev.txt`
**Inputs:** the repository, `docs/PLAYBOOK.md` (first half, in-repo), and *GraphPulse-R Playbook — Second 50 %* (Phases 5–8, external file).
**Related:** [`TECHNICAL_SOURCE_OF_TRUTH.md`](TECHNICAL_SOURCE_OF_TRUTH.md) · [`PROJECT_LOGBOOK.md`](PROJECT_LOGBOOK.md)

Nothing in `src/`, `tests/`, `experiments/` or `web/` was modified. Only the three `docs/` files were added.

---

## 1. Executive summary

GraphPulse-R maintains, under edge deletions and weight increases, an **exact shortest-path tree with tight-edge counters**, using a decision cascade (certificate → alternative support → budgeted repair → rebuild) with a provable work bound and competitive ratio. The first half (Phases 0–4: ~3,650 lines of source, 207 tests) is implemented and passes. The second half (multi-terminal trees, terminal matrix, Held–Karp, lazy tour certificate, real road data, experiments, paper) has **no code yet**.

**Headline findings**
1. The core is sound: 201/201 fast tests pass; the slow suite (including the 100,000-update differential run with the structural verifier after every update) result is recorded in §5. A scratch check found repaired state identical to rebuilt state in 14,400 sampled updates (not yet a committed test).
2. The brief's "≈240 tests" is **207** in the repository.
3. **Gate to the second half is not fully satisfied** (§2): G8 (`phase-4-done` tag missing), G1 (wrong wording and constant still in `web/index.html`), G4 (three percentage claims in `EMPIRICAL_EVALUATION.md` contradict its own table; an unsupported "95–99 %" in the dashboard), G10 (status table). None of these is an algorithmic defect. All are cheap to fix and must be fixed *before* Milestone 5.1 (Playbook §A).
4. The proven guarantees hold for **oracle F**, which is not deployable; the deployable `last`-F mode has no theorem. The paper must say so.
5. The only quantitative evidence today is one seeded benign-workload table; the worst-case bound has not been exercised at scale on a tight instance (no fallback occurred in any family).
6. `server.py` and `__main__.py` have 0 % test coverage and several hardening gaps; they are outside the algorithmic claim and belong to Milestone 8.1.

---

## 2. The 50 % gate (Playbook §A) — independent verification

| # | Item | Result | Evidence | Fix |
|---|---|---|---|---|
| G1 | Competitive-ratio wording | ❌ **FAIL** (partial) | `src/`, `SPEC.md`, `AGENTS.md`, `analysis.py` are correct (`max(1+c,(1+c)/c)`, work bound `(1+c)F+2`). **`web/index.html:816`** still reads "Guarantees competitive ratio … `(1 + c)·F + 1`". `P2_work_bound.md` lines 50–99 use "+1" before its final "+2". `PLAYBOOK.md` checklist says "+1" (historical) | Reword the dashboard string; align P2 intermediate lines |
| G2 | 4.3 complete: `analysis.py`, randomised budget, P1–P3 | ✅ PASS | files exist; `test_competitive.py` 10 tests pass | Add reviewer sign-off lines (needed by 8.2 lint) |
| G3 | ≥100,000 mixed updates, 4 families, 5 seeds, `verify_structured` each | ✅ PASS by construction; result in §5 | `tests/test_differential_scale.py`: 5 seeds × 4 families × 5 batches × 1,000 = 100,000 | — |
| G4 | Every empirical % claim seeded or deleted | ❌ **FAIL** | `EMPIRICAL_EVALUATION.md` "Key findings": "70–94 %" (table: 70.6–97.7), "65–92 % savings" (table: 97.7–99.8), comb "1.5–2.0× rebuild" (table: 0.006×, 0 fallbacks); `web/js/demo_flow.js:175` "95–99 %" unsupported. Table itself regenerates byte-identically (18 s) | Rewrite findings from the table; delete/qualify dashboard figure; fix generator text in `bench_empirical_claims.py:160-162` |
| G5 | Test counts reconciled | ✅ PASS | `--collect-only` = 207; `AGENTS.md`/`PLAYBOOK.md` say 207 (201 fast + 6 slow). README has no count | Playbook 8.2 will forbid hard-coded counts later |
| G6 | `find_affected` equals oracle on 500 cases | ✅ PASS (with caveat) | `test_affected.py::test_t33_06` `max_examples=500`; deletions only, n≤9. `KNOWN_GAPS.md` wrongly calls it a "superset" | Correct `KNOWN_GAPS.md`; optionally add an increase-case oracle |
| G7 | Dependency statement true | ✅ PASS | import scan of `src/graphpulse/*.py`: stdlib only; `requirements-dev.txt`: pytest, hypothesis, networkx | — |
| G8 | Tags `m0.1…m4.3`, `phase-0-done…phase-4-done` | ❌ **FAIL** | present: `m0.1…m4.3`, `phase-0…3-done`, `v0.5-half`. **`phase-4-done` absent** | `git tag -a phase-4-done 8708835` (needs approval) |
| G9 | `v0.5-half` on `main` | ✅ PASS, with a trap | tag → `c5636be`, an ancestor of `main`; `main` is 7 commits ahead (the hardening commits) | See D-004: add a newer stable tag; never move `v0.5-half` |
| G10 | `AGENTS.md` status table | 🟡 PARTIAL | `docs/AGENTS.md` §12 says Phase 4 ✅, current `4.3`; correct for the first half but not yet reflecting gate state | Update when the user approves proceeding |

**Verdict at analysis time: NO-GO for Milestone 5.1 until G1, G4, G8 (and the G6/G10 doc corrections) were done.**

**Remediation (2026-10-20, branch `gate-fixes`, local):** G1 dashboard string fixed (P2 was in fact consistent: +1 for integer c·F, +2 in general); G4 benchmark findings now computed from the table, dashboard figure removed; G6 `KNOWN_GAPS.md` corrected; G8 tag `phase-4-done` created on `8708835`; G10 `AGENTS.md` updated; stable tag `v0.5.1-gated` created after merge. Fast suite 201 passed after the changes. Gate: **GO**.

---

## 3. Exact project status

Status key: ✅ COMPLETE · 🟡 PARTIALLY COMPLETE · 🔴 NOT STARTED · ⚠️ NEEDS VALIDATION · ❌ BROKEN. "Complete" requires implementation + integration + passing tests + methodology match + documentation.

| Phase | Component | Status | Evidence | Remaining work |
|---|---|---|---|---|
| 0 | Frozen spec, cost model, golden graphs | ✅ | `SPEC.md`, `tests/golden/*`, `test_golden_files` (5) | — |
| 0 | `DiGraph` | ✅ | `graph.py`, `test_graph` (12) | — |
| 1 | Op counter, counted heap | ✅ | `opcount.py`, `test_opcount` (8) | — |
| 1 | Counted Dijkstra | ✅ | `test_dijkstra` (11), SPEC §6 anchors | — |
| 1 | Invariant checker (`check_spt`/`check_state`) | ✅ | `test_verify` (12), mutation property test, networkx oracle | — |
| 2 | Generators, updates | ✅ | `test_generators` (21), `test_updates` (14) | Add `tree_edges`, `partial_comb` (7.4/7.5) |
| 2 | Differential harness | ✅ | `test_harness` (12) | — |
| 3 | `SPTState` | ✅ | `test_spt` (19) | — |
| 3 | Certificate + alternative support | ✅ | `test_cert` (11) | — |
| 3 | `find_affected` | ✅ | `test_affected` (13), 500-case oracle | Fix `KNOWN_GAPS.md` text; add increase-case oracle |
| 3 | Repair (deletion, increase) | ✅ | `test_repair_delete` (13), `test_repair_increase` (13) | — |
| 4 | Overlay + abortable budgeted repair | ✅ | `test_overlay_budget` (13, 1 slow) | — |
| 4 | `BudgetedMaintainer`, `RandomizedBudget` | ✅ | `test_controller` (14) | Entry-point split (5.1) |
| 4 | Analysis (`measure`, ratio) | ✅ | `test_competitive` (10) | c∈{0,∞} handling for E1 |
| 4 | Proofs P1–P3 | 🟡 | files exist | reviewer sign-off; P2 constant tidy; add canonical-state lemma to P3 |
| 4 | 100k differential | ✅ / see §5 | `test_differential_scale.py` | — |
| 4 | Seeded empirical table | ✅ | regenerated byte-identical | — |
| 4 | Empirical **prose** | ❌ | contradicts own table (§2 G4) | Rewrite |
| 4 | CLI demo (`demo.py`) | ✅ | runs headless, exit 0 | no tests (0 % coverage) — acceptable for a demo |
| 4 | Dashboard (`server.py`, `web/`) | 🟡 | runs; **no tests**; hard-coded `project_progress: 50`; no lock/size limit; CORS `*`; prefix path check | Milestone 8.1 |
| 5 | Shared-graph entry point (5.1) | ✅ | `test_shared_graph`, slow suite unchanged | — |
| 5 | `MultiTreeManager` (5.2) | ✅ | `test_multitree` | — |
| 5 | `TerminalMatrix` + guard (5.3) | ✅ | `test_matrix`; guard seen to fire | — |
| 5 | Multi-tree hardening, touched-tree stat (5.4) | ✅ | `test_multitree_slow`; 60,000 updates, 0 mismatches | Phase 7 regenerates touched-tree numbers |
| 6 | Tour cost, brute force (6.1) | 🔴 | worked examples verified by scratch script | |
| 6 | Held–Karp (6.2) | 🔴 | formula verified combinatorially | |
| 6 | NN + branch-and-bound (6.3) | 🔴 | | |
| 6 | Lazy tour certificate (6.4) | 🔴 | | |
| 6 | `RoutingPipeline` (6.5) | 🔴 | | |
| 6 | P4 (NP-hardness), P5 (certificate) (6.6) | 🔴 | | |
| 7 | Road loader (7.1) → experiments E1–E5 (7.2–7.6) | 🔴 | no data source chosen | decide A7 |
| 8 | API/dashboard routing, claims audit, paper, release | 🔴 | | |

**Overall:** Phases 0–4 ≈ complete (the "first 50 %"); Phases 5–8 not started. Work is *not* yet 50 % of the effort: the second half contains all the research-evidence work (experiments, paper).

---

## 4. Playbook ↔ repository discrepancies

See `TECHNICAL_SOURCE_OF_TRUTH.md` Appendix A (D-001 … D-010). The ones that change the plan:

- **D-004** — the rollback tag `v0.5-half` predates the hardening commits; rolling back to it would lose the 100k test.
- **D-005** — `touched_trees` as defined counts `alt` events that change no distance; record both statistics.
- **D-007 / L11** — E1 sweeps c=0 and c=∞ but `theoretical_competitive_ratio` rejects c≤0.
- **Playbook 7.5 note** — `partial_comb` replaces the existing heavy shortcut `0→m` (weight `m+K`) by the protecting one (weight `m`); adding it as a second edge would be a duplicate-edge error in `DiGraph`. For m = n there is no protecting edge. (Checked by hand: deleting (0,1) then changes exactly vertices 1…m−1.)

---

## 5. Testing and validation audit

| Quantity | Value |
|---|---|
| Collected | **207** |
| Fast (`-m "not slow"`) | **201 passed, 0 failed** (51–61 s) |
| Slow (`-m slow`) | **6 passed**, 0 failed (643 s) |
| Tests asserting wall-clock | **0** (`perf_counter` used only to print elapsed time in the slow test) |
| Coverage (fast tests, venv-only `coverage.py`) | algorithmic modules 82–100 %; `server.py` 0 %, `__main__.py` 0 %; total 64 % |

Per file: affected 13 · cert 11 · competitive 10 · controller 14 · differential_scale 5 (slow) · dijkstra 11 · generators 21 · golden 5 · graph 12 · harness 12 · opcount 8 · overlay_budget 13 (1 slow) · repair_delete 13 · repair_increase 13 · smoke 1 · spt 19 · updates 14 · verify 12.

| Category | Present? | Where |
|---|---|---|
| Correctness vs oracle | ✅ | harness vs `RecomputeMaintainer`; `networkx` in `test_verify` |
| Randomised / property | ✅ | Hypothesis in affected, dijkstra, graph, opcount, overlay_budget, spt, verify |
| Edge cases | ✅ | disconnection, INF guard, c∈{0,∞}, source in-edges, degenerate graphs, golden graphs |
| Stress | ✅ | 100k differential; 20k unlimited-budget regression |
| Fault injection | ✅ for verifier and controller (T4.2-09); ⬜ for matrix/tour (not yet written) |
| Regression | ✅ (milestone re-runs) | |
| Performance tests | ❌ none in suite (by design: op counts asserted in unit tests, performance in experiments) | |
| Server / API | ❌ none | 8.1 |
| Hypothesis reproducibility | ⚠️ examples not derandomised; failures print a reproducer but runs differ | consider `derandomize=True` in CI profile |

**Missing experiments/tests needed for a paper:** E1–E5 (Playbook 7.3–7.6); a *worst-case-at-scale* run showing fallbacks occur and stay within `(1+c)F+2`; a committed canonical-state test (repair == rebuild); an increase-case oracle for `find_affected`; stale-F quantification (`last` vs `oracle`); multi-tree differential (60,000 updates); fault-injection tests for the matrix guard and tour certificate; Held–Karp vs brute-force vs B&B agreement; pipeline vs RecomputeEverything at every update.

---

## 6. Research contribution (what could become the paper)

1. A **certificate-first, budgeted-repair controller** with (a) abort-free overlay, (b) work bound `(1+c)F+2`, (c) competitive ratio `(1+c)/min(c,1)` with unique optimum at c=1, and randomised `e/(e−1)`, **plus an honest account of the oracle-F vs deployable-F gap**.
2. The **cross-layer lazy tour certificate** (including ε-mode with a non-ratcheting lower bound) — the most likely novel element, *pending* the literature check.
3. **End-to-end evaluation in machine-independent operation counts**, including adversarial tightness (`partial_comb`) and negative results.
Not claimable today: speed-ups on real roads; any statement about the routing layer.

---

## 7. Remaining development roadmap (ordered per the brief)

| # | Step | Playbook | Depends on | Exit criterion |
|---|---|---|---|---|
| 0 | **Gate remediation** (G1, G4, G6 doc, G8, G10, P2 tidy, sign-off lines) on branch `gate-fixes` | §A | — | Gate table all ✅; full + slow suite green; new stable tag |
| 1 | Record baseline: full + slow suite on current code (T5.1-01) | 5.1 | 0 | counts saved in logbook |
| 2 | Shared-graph entry point | 5.1 | 1 | T5.1-01…08; 20k single-tree differential clean |
| 3 | `MultiTreeManager` | 5.2 | 2 | T5.2-01…11 |
| 4 | `TerminalMatrix` + monotonicity guard (seen to fire) | 5.3 | 3 | T5.3-01…10 |
| 5 | Multi-tree hardening, 60k updates, touched-tree script | 5.4 | 4 | T5.4-01…08 |
| 6 | Tour cost + brute force → Held–Karp → NN/B&B *(can start any time after gate; independent of 5)* | 6.1–6.3 | gate | T6.1–T6.3 |
| 7 | Lazy tour certificate | 6.4 | 6.2 | T6.4-01…10 |
| 8 | `RoutingPipeline` | 6.5 | 5.3, 6.2, 6.4 | T6.5-01…10, 20k slow |
| 9 | P4/P5 proofs + executable reduction | 6.6 | 6.5 | reviewed |
| 10 | Road loader; **decide data source first** | 7.1 | gate | tests + one ~5k-vertex subgraph hashed |
| 11 | Runner → E1 → E2 → E3/E4 → E5 + figures + `run_all` | 7.2–7.6 | 5.4, 6.5 | all variants agree; tables byte-identical |
| 12 | Dashboard routing + API hardening | 8.1 | 7 | T8.1-01…12 |
| 13 | Claims audit + docs lint | 8.2 | 12 | lint green |
| 14 | Paper + related-work check | 8.3 | 13 | builds; numbers generated |
| 15 | Reproducibility, release | 8.4 | 14 | clean clone on two machines |

**Parallelism (team of 4):** step 6 and step 10 are independent of Phase 5. Nothing in Phase 7 is *measured* before 5.4 and 6.5.

---

## 8. First recommended development task

**Gate remediation, as a documentation/tag/string-only change (no algorithm touched):**
1. Rewrite the three false findings in `experiments/bench_empirical_claims.py` (the template) and regenerate `docs/EMPIRICAL_EVALUATION.md`; check `git diff` shows only prose changed.
2. Fix `web/index.html:816` and `web/js/demo_flow.js:175`.
3. Correct `docs/KNOWN_GAPS.md` (find_affected is exact).
4. Make `docs/proofs/P2_work_bound.md` intermediate constants agree with its final "+2"; add reviewer sign-off lines (the team must actually review; this report cannot sign for them).
5. Update `docs/AGENTS.md` §12; add the rule "update TSoT + logbook with every milestone".
6. Tag `phase-4-done` (on `8708835`) and, after the above is green, a new stable tag.

Then Milestone 5.1 (record baseline first).
