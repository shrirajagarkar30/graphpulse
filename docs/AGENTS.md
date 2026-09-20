# AGENTS.md: GraphPulse-R

Read this file completely at the start of every session. It tells you which project this is, what is in and out of scope, the rules you must not break, and how to work with this team.

## 1. What this project is

**Name:** GraphPulse-R
**Full title:** Certificate-Driven, Budgeted Reoptimization for Dynamic Delivery Routing
**Type:** Semester-long course project for *Design and Analysis of Algorithms (DAA)*, Computer Engineering, VIT (syllabus AY 2026-27). Team of 4 students.

**One-sentence summary:** When roads in a network close or slow down, maintain exact shortest-path distances by *repairing* the previous solution instead of recomputing from scratch, decide repair-versus-recompute with a provable work budget, and use the repaired distances to solve a delivery tour exactly.

This is a DAA project, so **correctness, proofs, complexity analysis and measured operation counts matter more than UI or features**. Do not turn it into a route-finding app or a machine-learning project.

## 2. The problem

- Input: a directed graph `G = (V, E, w)` with strictly positive **integer** weights; a depot and `k` delivery stops (the *terminals*); a sequence of updates.
- Updates: **edge deletion** (road closure) and **weight increase** (slowdown).
- After every update, maintain (1) exact shortest-path distances from each terminal, (2) the terminal-to-terminal distance matrix, (3) a minimum-cost single-vehicle tour of the depot and all stops.
- Goal: minimize total work over the update sequence, measured in machine-independent operation counts, while staying exactly correct.

## 3. Scope

**In scope:** deletions and weight increases; one vehicle; fixed terminals; `k` up to about 18 (Held-Karp memory limit); Python 3.11+.
**Out of scope unless the team explicitly asks:** edge insertions and weight decreases, multiple vehicles, time windows, machine-learned predictors, GUI beyond a small demo.

## 4. Core ideas (the novelty claim)

1. **Budgeted repair.** Incremental repair runs under a work cap `B = c * F`, where `F` is the work of a full tree rebuild. If the cap is exceeded, discard the repair and rebuild with Dijkstra. This is a ski-rental-style online problem: with `c = 1` the strategy is 2-competitive against an offline oracle that always picks the cheaper of repair and rebuild; a randomized budget (`x = ln(1 + (e - 1) * U)`, budget `x * F`) gives expected ratio `e / (e - 1)`.
2. **Free structural certificate (shortest-path layer).** If an updated edge is not tight (`dist[u] + w != dist[v]`, or `dist[u]` is INF), no distance changes and the cost is exactly 1 operation. If it is tight but `tight[v] > 1`, another tight edge supports `v`; only counters and the parent pointer change.
3. **Cross-layer certificate (routing layer, second half).** If distances only increase and no distance-matrix entry used by the current optimal tour changed, that tour is still optimal, so Held-Karp is skipped.

Every ingredient has prior art. The honest claim is the integration, the competitive analysis and the certificates, evaluated end to end. Do not describe this as a "new algorithm" in code comments, docs or reports.

## 5. Non-negotiable technical rules

- **Weights are strictly positive integers.** Repair depends on exact equality `dist[u] + w == dist[v]`. Never introduce float weights.
- **INF guard.** `INF = float("inf")`. Every tight-edge test must first check `dist[u] != INF`, because `inf + w == inf` would wrongly mark edges between two unreachable vertices as tight.
- **Definitions (authoritative in `docs/SPEC.md`):** tight edge; `tight[v]` = number of tight in-edges; affected set `A` = vertices whose distance changes; `F` = work of the last full rebuild (Dijkstra plus tight recount); `r` = work of a completed repair; budget `B = ceil(c * F)`.
- **Tight-edge subgraph is acyclic** (positive weights). Repair correctness relies on this.
- **Repair rule:** a vertex with a tight in-edge from an unaffected vertex keeps its distance; a vertex that loses all tight in-edges gets a strictly larger distance. Non-affected `tight` counts only decrease during repair.
- **Abort must be free.** Repair writes to an overlay; abort discards it; commit applies it. State must be byte-identical after an abort.
- **Only `BudgetExceeded` triggers a fallback.** Any other exception must propagate. Never swallow errors.
- **Tests assert operation counts, not wall-clock time.**

## 6. Cost model (one shared definition)

| Operation | Charged when |
|---|---|
| SCAN | each adjacency entry examined (forward or reverse), and the single O(1) certificate check |
| PUSH | each heap push |
| POP | each heap pop, including stale entries |
| QUEUE | each enqueue or dequeue during affected-set propagation |

State writes are not charged separately (each is caused by an already-charged operation). Pass an `OpCounter` explicitly; never use a global counter.

## 7. Tech stack and dependencies

- Python 3.11+, standard library only for algorithms (`heapq`, `dataclasses`, `random.Random(seed)`).
- Dev only: `pytest`, `hypothesis` (property-based tests and shrinking), `networkx` (independent Dijkstra oracle, **tests only**).
- **Do not add any library, framework or tool without asking and explaining why it is needed.** Later phases may add `osmnx`, `matplotlib`, and Streamlit or Folium, but only when the playbook reaches that milestone.

## 8. Repository layout

```
graphpulse/
├── AGENTS.md                      # this file
├── pyproject.toml, requirements-dev.txt, README.md, .gitignore
├── docs/
│   ├── SPEC.md                    # model, update model, cost model
│   ├── PLAYBOOK.md                # milestone-by-milestone plan (source of truth for order)
│   └── proofs/                    # P1 repair correctness, P2 work bound, P3 competitive ratio
├── src/graphpulse/
│   ├── graph.py        opcount.py     dijkstra.py    verify.py
│   ├── generators.py   maintainer.py  harness.py
│   ├── spt.py          repair.py      controller.py  analysis.py
├── tests/  (golden/, failures/ [gitignored], test_*.py)
└── experiments/  (benchmark scripts; outputs are not committed)
```

## 9. How you must work

1. **Follow `docs/PLAYBOOK.md` milestone by milestone, in order.** Never start a milestone whose prerequisite is not complete. Do not jump ahead to "the full implementation".
2. Before coding a milestone, restate its objective and task list to the user, and list the files you expect to touch.
3. Implement only that milestone. Keep changes small enough to test and commit independently.
4. Write or update the tests listed for the milestone (IDs like `T3.2-04`), run the **full** suite, and report results honestly, including failures.
5. If you change an existing, already-proven feature, add regression tests and re-run the differential harness.
6. Proofs (`docs/proofs/`) are part of the deliverable. Write them alongside code; do not claim a bound that the cost model does not support.
7. If something is ambiguous or missing (language, scope, a definition), **ask instead of assuming**.
8. Prefer a failing test that exposes a bug over hiding it. Never weaken or delete a test to make the suite pass.

## 10. Commands

```
python -m venv .venv
source .venv/bin/activate              # Windows PowerShell: .venv\Scripts\Activate.ps1
pip install -e . -r requirements-dev.txt
python -m pytest -q -m "not slow"      # quick loop
python -m pytest -q                    # full suite: required before every push
```

## 11. Git rules

- `main` is always stable. One branch per phase (`phase-N-name`). One tag per milestone (`mX.Y`).
- Commit format: `type(scope): summary` (`feat`, `test`, `docs`, `refactor`, `chore`).
- Only commit after the milestone's tests and verification checklist pass. Every push is a stable checkpoint.
- Before pushing: `git status`, read the file list, `git pull --rebase origin <branch>`.
- **Never** `git push --force` on a shared branch. To undo a pushed commit use `git revert <hash>`.
- **Never commit:** `.venv/`, `__pycache__/`, `.pytest_cache/`, `.hypothesis/`, `tests/failures/`, `experiments/output/`, `.env`, secrets, IDE folders, large data files.

## 12. Roadmap and current status

Update the status column as milestones finish.

| Phase | Content | Milestones | Status |
|---|---|---|---|
| 0 | Setup, spec freeze, graph structure | 0.1, 0.2, 0.3 | ✅ completed |
| 1 | Counted Dijkstra, invariant checker, oracle | 1.1, 1.2, 1.3 | ✅ completed |
| 2 | Generators, update sequences, differential harness | 2.1, 2.2, 2.3 | ⏳ in progress (2.1 done) |
| 3 | Incremental repair (tight counters, affected set, deletions, increases) | 3.1 to 3.5 | ☐ |
| 4 | Budgeted controller, competitive-ratio proofs (**50% checkpoint, tag `v0.5-half`**) | 4.1, 4.2, 4.3 | ☐ |
| 5 | Multi-terminal trees and distance matrix | (second half) | ☐ |
| 6 | Held-Karp, lazy re-solve certificate, baselines, NP-hardness write-up | (second half) | ☐ |
| 7 | Real road data, experiments, ablations, adversarial tightness | (second half) | ☐ |
| 8 | Demo, final report, release checklist | (second half) | ☐ |

**Current milestone:** `2.1` (completed)
**Last stable tag:** `m2.1`
**Known issues:** None

Phases 5 to 8 are described here only so you understand the direction. **Do not implement them until the 50% checkpoint is tagged and the team asks.**

## 13. Definition of done (any milestone)

- All listed tests pass and the full suite is green.
- The verification checklist is ticked, and the differential harness shows zero mismatches where relevant.
- Docs and proofs for that milestone are updated.
- The commit follows the Git rules above and has a milestone tag.

## 14. What not to do

- Do not add features, dependencies, files or abstractions the current milestone does not call for.
- Do not use floats for weights, global counters, or wall-clock assertions in tests.
- Do not claim novelty, speedups or bounds that have not been proven or measured.
- Do not fake results, hard-code expected values from your own output, or modify golden files to match your code.
- Do not touch second-half phases early.

## 15. Glossary

- **Terminal:** the depot or a delivery stop (a source for its own shortest-path tree).
- **Tight edge:** an edge `(u, v)` with `dist[u] + w(u, v) == dist[v]` and `dist[u]` finite.
- **Affected set:** vertices whose shortest distance changes after an update.
- **Certificate:** a cheap test that proves the previous solution is still valid, so no work is needed.
- **Fallback / rebuild:** rerun Dijkstra for the tree and recompute tight counters.
- **Competitive ratio:** worst-case online cost divided by the offline optimum `min(r, F)`.
