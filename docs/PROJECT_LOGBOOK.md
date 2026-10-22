# GraphPulse-R — Project Logbook (living)

> Answers, at a glance: *what is done · what is in progress · what remains · why decisions were made · which experiments ran · what failed · what to build next.*
> **Rule:** every milestone commit also appends a row to §1, updates §2 and the relevant lists below, and — if methodology changed — `TECHNICAL_SOURCE_OF_TRUTH.md`. Evidence must be a commit, tag, test ID or committed table; never a recollection.
> Entries before 2026-10-20 were **reconstructed from git history** (dates are commit dates; the whole first half was committed on 2026-09-20, hardening on 2026-10-18).

Statuses: ✅ complete · 🟡 partial · 🔴 not started · ⚠️ needs validation · ❌ broken · ⏳ in progress

---

## 1. Chronological log

| Date | Phase | Task | Status | Work Performed | Result | Evidence | Next Action |
|---|---|---|---|---|---|---|---|
| 2026-09-20 | 0 / M0.1 | Project skeleton, pinned tooling, smoke test | ✅ | Repo, `pyproject`, pinned dev deps | Smoke test passes | tag `m0.1` (`e9beccc`…`01a7cdb`) | M0.2 |
| 2026-09-20 | 0 / M0.2 | Freeze spec, cost model, golden graphs | ✅ | `SPEC.md`, `tests/golden/*` | Cost model fixed: SCAN/PUSH/POP/QUEUE | tag `m0.2` (`101af9c`) | M0.3 |
| 2026-09-20 | 0 / M0.3 | Validated `DiGraph` | ✅ | forward+reverse adjacency, strict validation | 12 tests | tag `m0.3` (`b0e9df9`), `phase-0-done` | Phase 1 |
| 2026-09-20 | 1 / M1.1 | `OpCounter`, `CountedHeap` | ✅ | explicit counters, budget hook | 8 tests | tag `m1.1` (`01b847e`) | M1.2 |
| 2026-09-20 | 1 / M1.2 | Counted Dijkstra | ✅ | lazy-deletion heap | SPEC §6 anchors reproduced | tag `m1.2` (`bba0398`) | M1.3 |
| 2026-09-20 | 1 / M1.3 | Invariant checker + networkx oracle | ✅ | `check_spt`, mutation tests | checker catches injected faults | tag `m1.3` (`711ed27`), `phase-1-done` | Phase 2 |
| 2026-09-20 | 2 / M2.1–2.3 | Generators, update model, differential harness | ✅ | 4 families, `random_updates`, reproducer dumps | harness detects injected bugs | tags `m2.1–m2.3`, `phase-2-done` (`5fd087c`) | Phase 3 |
| 2026-09-20 | 3 / M3.1–3.5 | SPT state, certificate, affected set, repair (delete, increase) | ✅ | tight counters, `find_affected` vs oracle, exact state repair | all Phase 3 tests pass | tags `m3.1–m3.5`, `phase-3-done` (`6788db5`) | Phase 4 |
| 2026-09-20 | 4 / M4.1 | Overlay + budgeted abortable repair | ✅ | copy-on-write overlay, `BudgetExceeded` | abort leaves state identical | tag `m4.1` (`187e231`) | M4.2 |
| 2026-09-20 | 4 / M4.2 | Budgeted controller | ✅ | cert → alt → repair → fallback | work bound tests pass | tag `m4.2` (`e08768b`) | M4.3 |
| 2026-09-20 | 4 / M4.3 | Competitive analysis, randomised budget, P1–P3 | ✅ | `analysis.py`, proofs | R(c)=max(1+c,(1+c)/c) | tag `m4.3` (`2652eda`); merge `8708835` | checkpoint |
| 2026-09-20 | 4 | 50 % checkpoint, demo, dashboard | ✅ | merge phase 4; `demo.py`; web UI | tag `v0.5-half` → `c5636be` | `c5636be`, `f4cfe63`, `dd68d44` | hardening |
| 2026-10-18 | 4 hardening | Ratio wording fix (G1), pytest config | 🟡 | `42f9258` fixed src/SPEC wording | web string left behind | `42f9258` | see 2026-10-20 |
| 2026-10-18 | 4 hardening | Known-gaps audit | 🟡 | `KNOWN_GAPS.md` | contains an incorrect description of `find_affected` | `cde75aa` | correct it |
| 2026-10-18 | 4 hardening | 100k differential (G3) | ✅ | 5 seeds × 4 families, verifier each update | passed in 202.87 s (as recorded in PLAYBOOK, not re-timed by me) | `aed4f3b` | re-run in analysis |
| 2026-10-18 | 4 hardening | Seeded empirical table (G4) | 🟡 | `bench_empirical_claims.py` → `EMPIRICAL_EVALUATION.md` | table OK, prose contradicts it | `b4fece1` | rewrite prose |
| 2026-10-18 | 4 hardening | Reconcile test counts (G5) | ✅ | 207 collected | consistent | `0e02495` | — |
| 2026-10-20 | Analysis A1 | Clone, inspect structure, history, docs | ✅ | cloned `main` (default branch of the clone was `phase-0-setup`!) | `main` is 7 commits ahead of `v0.5-half` | `git log`, `git tag --list` | A2 |
| 2026-10-20 | Analysis A2 | Environment | ✅ | fresh `.venv`, `pip install -e . -r requirements-dev.txt` | Python 3.14.7; collection initially failed without install (missing `graphpulse`, `hypothesis`) | pip list | A3 |
| 2026-10-20 | Analysis A3 | Fast suite | ✅ | `pytest -q -m "not slow"` | **201 passed** (51–61 s) | run output | A4 |
| 2026-10-20 | Analysis A4 | Slow suite (G3) | ✅ | `pytest -m slow` | **6 passed in 643 s** | local run log | — |
| 2026-10-20 | Analysis A5 | Reproduce seeded table | ✅ | re-ran `bench_empirical_claims.py` | **byte-identical** (18 s) | `git diff` empty | A6 |
| 2026-10-20 | Analysis A6 | Canonical-state probe | 🟡 | scratch script, 14,400 states | 0 non-canonical (supports P3 per-update independence) | scratch only | promote to committed test |
| 2026-10-20 | Analysis A7 | Coverage probe | ✅ | `coverage.py` in venv | core 82–100 %; server/__main__ 0 % | local | note in TSoT V1b |
| 2026-10-20 | Analysis A8 | Playbook value check | ✅ | brute force for T6.1-01/02, HK formula | 80 / [1,3,2]; 21 / [2,3,1]; formula OK | scratch | — |
| 2026-10-20 | Analysis A9 | Gate audit G1–G10 | ✅ | see `ANALYSIS_REPORT.md` §2 | **G1, G4, G8 fail; G10 partial** | report | gate remediation |
| 2026-10-20 | Gate | Gate remediation (G1, G4, G6, G8, G10) | ✅ | fixed dashboard strings, benchmark prose (computed), KNOWN_GAPS, AGENTS; tags `phase-4-done`, `v0.5.1-gated` (local) | tables unchanged; 201 fast passed | branch `gate-fixes` | Milestone 5.1 |
| 2026-10-20 | 5 / M5.1 | Shared-graph entry point | ✅ | `apply_update` returns old weight; `BudgetedMaintainer.handle_applied(upd, old_w)` and `own_graph=False`; `apply` = apply_update + handle_applied | T5.1-01…08 pass; old 6 slow tests unchanged (699 s) | tag `m5.1`; `tests/test_shared_graph.py` | M5.2 |
| 2026-10-20 | 5 / M5.2 | `MultiTreeManager` | ✅ | k+1 trees, one graph mutation, per-tree F and budget, `MultiStats` (+`dist_changed_trees`) | T5.2-01…11 pass; differential on 3 families | tag `m5.3` (m5.2 shares the commit; `terminals.py` holds both classes) | M5.3 |
| 2026-10-20 | 5 / M5.3 | `TerminalMatrix` + monotonicity guard | ✅ | changed set, snapshot, `is_complete`, `matrix_cells` counter | guard fires on injected decrease; matrix = oracle after 5,000 updates ×2 (66–73 s each) | tag `m5.3`; `tests/test_matrix.py` | M5.4 |
| 2026-10-20 | 5 / M5.4 | Hardening + touched-tree script | ✅ | 3×20,000-update differential, work bound per tree, comb case, `experiments/touched_trees.py` | 5 slow tests passed in 1,077 s; 60,000 updates, 0 mismatches | tag `m5.4`; `tests/test_multitree_slow.py` | **Phase 5 complete — awaiting go-ahead for Phase 6** |
| 2026-10-22 | 6 / M6.1–6.3 | Tour cost, brute force, Held–Karp, NN, branch-and-bound | ✅ | `tour.py`; `OpCounter.dp` excluded from work | 40 tests; HK = brute force on 300 matrices; B&B = HK; formula exact | tags `m6.1`,`m6.2`,`m6.3` (one commit) | M6.4 |
| 2026-10-22 | 6 / M6.4 | Lazy tour certificate | ✅ | `tourcert.py` with accumulated changes and non-ratcheted LB | 11 tests; soundness 500 cases, ε-bound 500 cases | tag `m6.4` | M6.5 |
| 2026-10-22 | 6 / M6.5 | `RoutingPipeline` | ✅ | trees → matrix → certificate → Held–Karp; reference isolated | 12 fast tests + 20,000-update slow test: 0 cost mismatches | tag `m6.5` | M6.6 |
| 2026-10-22 | 6 / M6.6 | NP-hardness + certificate proofs | 🟡 | P4, P5 drafted; reduction executable | 5 tests pass; **sign-off PENDING (team)** | tag `m6.6` | Phase 7 |
| 2026-10-22 | 7 / M7.1 | Road loader | ✅ | `roadnet.py`, `tests/data/tiny.gr`, `data/README.md` | 19 tests; **no real dataset used** (decision: synthetic only) | tag `m7.1` | M7.2 |
| 2026-10-22 | 7 / M7.2 | Experiment runner | ✅ | seeded runner, cross-variant check, metadata | determinism, injected-fault tests | tag `m7.2` | E1 |
| 2026-10-22 | 7 / M7.3–7.5 | E1, E2, E3, E4 | ✅ | `e1_budget` … `e4_adversarial`, `partial_comb`, `tree_edges` mode | bound held in all 168 E1 runs; E4 tight for c=0.5, 1 | tags `m7.3`–`m7.5` | E5 |
| 2026-10-22 | 7 / M7.6 | E5, figures, `run_all`, MANIFEST | ✅ | full run 1,440 s total; manifest verified | 0 cross-variant disagreements | tag `m7.6`; `docs/results/` | Phase 8 |
| 2026-10-22 | 8 / M8.1 (backend) | Routing API, validation, lock, safe static, local-only | ✅ | `server.py`, `docs/API.md` | 30 API tests incl. traversal, 413, concurrency | commit on `phase-7-experiments` | UI redesign |
| 2026-10-22 | 8 / M8.2 | Claims audit + lint | ✅ | `CLAIMS.md`, `test_docs_lint.py` | dashboard-text lint expected to fail until redesign (xfail) | | remove xfail after UI |
| 2026-10-22 | 8 / M8.3 | Paper sources | 🟡 | `paper/`, generated tables, asset tests | not compiled (no LaTeX); bibliography unverified | | team review |
| 2026-10-20 | Analysis A10 | Documentation | ✅ | created TSoT, logbook, analysis report | — | `docs/` | **await user go-ahead** |

---

## 2. Milestones

| Milestone | Status | Completion | Remaining Work |
|---|---|---:|---|
| Phase 0 — spec, graph | ✅ | 100 % | — |
| Phase 1 — Dijkstra, counters, checker | ✅ | 100 % | — |
| Phase 2 — generators, harness | ✅ | 100 % | `tree_edges`, `partial_comb` modes come in 7.4/7.5 |
| Phase 3 — repair | ✅ | 100 % | fix `KNOWN_GAPS.md` text |
| Phase 4 — controller, proofs | 🟡 | 95 % | sign-offs, P2 constant tidy, canonical-state lemma, `phase-4-done` tag |
| **Gate to second half** | ✅ | 100 % | closed 2026-10-20 (`v0.5.1-gated`) |
| Phase 5 — multi-terminal | ✅ | 100 % | merged, tag `phase-5-done` |
| Phase 6 — routing layer | ✅ | 100 % (proof sign-offs pending) | — |
| Phase 7 — experiments | ✅ | 100 % | real-data runs not done (no dataset) |
| Phase 8 — demo, paper, release | 🟡 | 55 % | UI redesign + routing panel, release candidate, human gates |

---

## 3. Completed
- Phase 6 (6.1–6.6): tours, lazy certificate, pipeline, proofs P4/P5 — see TSoT V6.
- Phase 5 (5.1–5.4): multi-terminal engine, matrix, hardening — see TSoT V5.
- Gate remediation.
- Phases 0–4 (first-half playbook), tags `m0.1 … m4.3`, `phase-0-done … phase-3-done`, `v0.5-half`.
- Hardening: 100k differential test, seeded empirical table, test-count reconciliation.
- Analysis: gate audit; re-validation of test suite and empirical table; three `docs/` documents.

## 4. In progress
- (none)

## 5. Remaining
See `ANALYSIS_REPORT.md` §7. Next: Phase 7 (experiments).

## 6. Blocked
| Item | Blocked on |
|---|---|
| Phase 7.1 (real road data) | Choice and permission to download a DIMACS `.gr` / OSM extract (Playbook A7) |
| Tags `phase-4-done`, new stable tag; any push | User approval (outward-facing / shared repo) |
| Proof sign-offs P1–P5 (G2 / 8.2) | Two team members actually reviewing; every proof file carries `Reviewer sign-off: PENDING` |

## 7. Bugs and defects
| ID | Severity | Description | Location | Status |
|---|---|---|---|---|
| B-1 | Medium (credibility) | Dashboard states "Guarantees competitive ratio … `(1+c)·F + 1`" — wrong term and constant | `web/index.html:816` | fixed (gate-fixes) |
| B-2 | Medium (credibility) | Three empirical findings contradict the table beside them | `docs/EMPIRICAL_EVALUATION.md`, generator `bench_empirical_claims.py:160-162` | fixed (gate-fixes) |
| B-3 | Low | Unsupported "95–99 %" claim in UI | `web/js/demo_flow.js:175` | fixed (gate-fixes) |
| B-4 | Low | `KNOWN_GAPS.md` mis-describes `find_affected` as a superset | `docs/KNOWN_GAPS.md:14` | fixed (gate-fixes) |
| B-5 | Low | Missing tag `phase-4-done` | git | open |
| B-6 | — | P2 "+1"/"+2": **withdrawn** — the proof is consistent (+1 for integer c·F, +2 in general, as its theorem states) | `docs/proofs/P2_work_bound.md` | not a defect |
| B-7 | Low (hardening) | Server: global state without lock under `ThreadingHTTPServer`, no body limit, CORS `*`, `startswith` path-prefix check (sibling-dir `web*` would pass), hard-coded `project_progress: 50`, returns 403 not 404 | `src/graphpulse/server.py` | open → 8.1 |
| B-8 | Info | `check_state` annotated with `Any` but `Any` is not imported (harmless under `from __future__ import annotations`; breaks `typing.get_type_hints`) | `verify.py:130` | open |
| B-9 | Info | README layout lists only `__init__.py`; says "## 4" twice | `README.md` | open |
| B-10 | Info | Bare checkout: `pytest` fails to collect until `pip install -e . -r requirements-dev.txt` | README/pyproject | doc fix |

No algorithmic bug was found.

## 8. Experiments
| ID | Date | Description | Config | Result | Evidence |
|---|---|---|---|---|---|
| X-1 | 2026-10-18 (re-run 2026-10-20) | Strategy shares and work vs recompute | seed 42, 4 families, 1,000 updates, c=1, p_delete=0.4 | online/rebuild 0.002–0.023; 0 fallbacks | `docs/EMPIRICAL_EVALUATION.md`, byte-identical regen |
| X-2 | 2026-10-20 | Canonical-state probe | 4 families × c∈{0,½,1,∞} × 3 seeds × 300 updates | 0 / 14,400 differences | scratch (to be committed) |
| X-3 | 2026-10-20 | 100k differential | 5 seeds × 4 families | 6 passed, 0 mismatches over 100,000 updates | `tests/test_differential_scale.py` |
| X-5 | 2026-10-22 | E1–E5 full run | see TSoT V7 | all variants agree | `docs/results/` |
| X-4 | 2026-10-20 | Multi-tree differential (E0) | 3×20,000 updates + 2×5,000 matrix | 0 mismatches | `test_multitree_slow.py`, `test_matrix.py` |
| E1–E5 | — | Phase 7 experiments | — | **PENDING EXPERIMENT** | — |

## 9. Research decisions
| ID | Decision | Why |
|---|---|---|
| R-1 | Weights are strictly positive **integers** | Repair relies on exact equality `dist[u]+w==dist[v]`; floats would break tightness |
| R-2 | Cost model = SCAN+PUSH+POP+QUEUE, state writes uncharged | Machine-independent; each write is caused by a charged op (SPEC §4) |
| R-3 | Report **operation counts** primarily; wall-clock secondary | Reproducibility across machines (Playbook A9) |
| R-4 | Claim = integration + competitive analysis + certificates; never "new algorithm" | Every ingredient has prior art (AGENTS §4) |
| R-5 | Competitive ratio is against per-update OPT=min(r,F) | Makes ski-rental analysis applicable; relies on canonical state (open lemma) |
| R-6 | State canonical: parent = min tight predecessor | Determinism; repair ≡ rebuild; simplifies proofs and tests |
| R-7 | Report losses and benign-workload caveats | Release checklist; avoid unsupported speed-up claims |
| R-8 | Rejected claims are quarantined in TSoT §10.2 until regenerated from a seeded table | Rule 1 (never fabricate) |

## 10. Architecture decisions
| ID | Decision | Why / consequence |
|---|---|---|
| A-1 | `SPTState` holds `dist,parent,children,tight,F_ops` | O(1) certificate and alt-support need `tight[]`; F is stored for the budget |
| A-2 | Copy-on-write `Overlay` for repair | Abort must be free; commit publishes |
| A-3 | `BudgetedMaintainer` copies the graph it is given | Simple isolation; **must change** in 5.1 so k+1 trees share one graph |
| A-4 | Only `BudgetExceeded` triggers fallback | Never swallow other errors |
| A-5 | Algorithms stdlib-only; networkx/hypothesis/pytest tests-only | Playbook G7 |
| A-6 | Stdlib `ThreadingHTTPServer` for the dashboard | No framework; but needs lock (B-7) |
| A-7 | Cascade duplicated in `RepairMaintainer.apply` and `BudgetedMaintainer.apply` | Historical; refactor with care in 5.1 (both keep their tests) |

## 11. Performance results
Only X-1 exists (benign workloads, one seed). **No scaling, adversarial, routing or end-to-end numbers exist.** Do not quote any until E1–E5 run.

## 11b. Findings during Phase 5
- `random_updates` exhausts its edge pool when `p_delete` is high ("2000 updates" gives about 210 on a 6×6 grid). Tests now assert actual counts. A trap for claims, not a generator defect.
- `m5.2` and `m5.3` share one commit because `terminals.py` holds both classes.

- A first design of the certificate used only the per-update `changed` set; an ε-keep followed by an update touching nothing would then wrongly report exact KEEP. Fixed by accumulating changes since the last rebase (test `test_t64_accumulated_changes_after_eps_keep`, P5 §2).

## 12. Failed approaches / rejected claims
| What | Why it failed |
|---|---|
| The "c-plus-one competitive" phrasing | Wrong: work bound ≠ competitive ratio; ratio is `(1+c)/min(c,1)` and equals 2 only at c=1 |
| Empirical prose "70–94 %", "65–92 %", "1.5–2.0×" | Not produced by the table; rejected |
| Treating `find_affected` as a tree-subtree superset (KNOWN_GAPS) | Code is counter-based and exact |
| Relying on `v0.5-half` as rollback point | Predates hardening; superseded by a new tag after the gate |

## 13. Future work
- **Next (needs user go-ahead):** gate remediation → 5.1.
- Promote the canonical-state probe to a committed test and add the lemma to P3.
- Increase-case oracle for `find_affected`.
- Quantify stale-F effect (`last` vs `oracle`) in E1.
- `dist_changed_trees` statistic alongside `touched_trees` (D-005).
- Out of scope unless asked: insertions/decreases, multi-vehicle, time windows, ML predictors.

---

### How to append an entry
1. Add one row to §1 (date, phase, task, status, work, result, evidence, next action).
2. Update the §2 completion % and the §3–§13 list that changed.
3. If methodology/code changed, update `TECHNICAL_SOURCE_OF_TRUTH.md` in the *same commit* (mark labels IMPLEMENTED → VALIDATED → EXPERIMENTALLY VERIFIED only when the evidence exists).
4. Commit message: `type(scope): summary`; tag per milestone as in `AGENTS.md` §11.
