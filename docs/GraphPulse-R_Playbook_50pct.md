# GraphPulse-R Development Playbook: First 50% (Phases 0 to 4)

**Project:** Certificate-driven, budgeted reoptimization for dynamic delivery routing
**This playbook covers:** everything up to and including the *budgeted single-source shortest-path layer* (the algorithmic core and its proofs). The routing layer, real road data, experiments and demo are the second 50% and are listed at the end.

**Milestone order (each requires the previous one unless stated):**
`0.1 → 0.2 → 0.3 → 1.1 → 1.2 → 1.3 → 2.1 → 2.2 → 2.3 → 3.1 → 3.2 → 3.3 → 3.4 → 3.5 → 4.1 → 4.2 → 4.3`

Team note: after 1.3, milestones 2.1 and 2.2 can be built by two people in parallel. Proof drafting (`docs/proofs/`) should run alongside coding in Phases 3 and 4, not after.

---

## A. Missing information and assumptions (confirm or correct before Milestone 0.1)

You asked me to identify missing information instead of assuming silently. These are the gaps. I proceeded with the assumption shown so the playbook is usable; changing one changes only the listed items.

| # | Missing information | Assumption used | Why | If you change it |
|---|---|---|---|---|
| A1 | Implementation language | Python 3.11+ only | Correctness and operation counts (not wall-clock) are what the first half is judged on, and Python makes differential testing fast to write. (I earlier suggested a C++ core; that is deferred to the second half as an optional port.) | Commands in 0.1 and all file extensions change. Milestone logic does not. |
| A2 | Git host and branch policy | GitHub; `main` is always stable; one branch per phase (`phase-N-...`); tags `mX.Y` per milestone | Gives every push a named recovery point | Only the remote URL and branch names change. |
| A3 | Operating system | Commands shown for Linux/macOS; Windows alternatives given where they differ | Not stated | None |
| A4 | Team ownership | Not assigned; any member can take any milestone | Not stated | Add an owner line per milestone |
| A5 | Weight type | Strictly positive **integers** (for example seconds) | Repair relies on exact tight-edge equality `d[u] + w == d[v]`; floats would break it | Repair correctness argument must be redone |
| A6 | Update model | Edge deletion and weight increase only, single source per tree | Matches the agreed scope | Insertions and decreases are second-half stretch |

**Not applicable in this half (so intentionally no test categories for them):** database and API schema tests, authentication and authorization, AI/ML model validation, offline and sync. The project has none of these. Security is limited to "no secrets, pinned dependencies, no network access" (see the release checklist).

---

## B. Repository layout (built up over the milestones)

```
graphpulse/
├── pyproject.toml
├── requirements-dev.txt
├── README.md
├── .gitignore
├── docs/
│   ├── SPEC.md                    # model, update model, cost model (Milestone 0.2)
│   └── proofs/                    # P1 repair correctness, P2 work bound, P3 competitive ratio
├── src/graphpulse/
│   ├── __init__.py
│   ├── graph.py                   # 0.3
│   ├── opcount.py                 # 1.1
│   ├── dijkstra.py                # 1.2
│   ├── verify.py                  # 1.3 (extended in 3.1)
│   ├── generators.py              # 2.1, 2.2
│   ├── maintainer.py              # 2.3 (interface and recompute baseline)
│   ├── harness.py                 # 2.3
│   ├── spt.py                     # 3.1
│   ├── repair.py                  # 3.2 to 3.5, overlay in 4.1
│   ├── controller.py              # 4.2, 4.3
│   └── analysis.py                # 4.3
├── tests/
│   ├── golden/                    # 0.2
│   ├── failures/                  # gitignored reproducer dumps
│   └── test_*.py
└── experiments/                   # benchmark scripts (outputs are not committed)
```

## C. Global rules

- **Dev dependencies and why:** `pytest` (test runner); `hypothesis` (property-based testing: repair bugs hide in rare graph shapes, and Hypothesis generates and shrinks counterexamples); `networkx` (an *independent* Dijkstra implementation used only in tests as an oracle). Nothing else is added in this half.
- **Test commands:** quick loop `python -m pytest -q -m "not slow"`. Before every push run the full suite `python -m pytest -q`.
- **Test ID scheme:** `T<milestone>-<nn>`, for example `T3.2-04`. The Status column uses `☐` not run, `✅` pass, `❌` fail.
- **Tests assert operation counts, never wall-clock time.** Wall-clock is flaky and machine-dependent.
- **Commit format:** `type(scope): summary`, with types `chore`, `docs`, `feat`, `test`, `refactor`.
- **Before every push:** run the full suite, then `git status`, and read the file list. Never commit if it contains anything from the "Do NOT commit" line of the milestone.

### Global Git protocol

Once per phase: `git checkout main && git pull origin main && git checkout -b phase-N-name`.
Per milestone use the exact command block in that milestone. Because four people push to the same phase branch, the block includes `git pull --rebase` before the push.

**Recovery procedure R1 (a bad milestone was already pushed).** This never rewrites shared history.
```
git log --oneline -5                       # find the bad commit hash
git revert --no-edit <bad-commit-hash>     # creates a new commit that undoes it
python -m pytest -q                        # confirm the last stable state is back
git push origin <phase-branch>
```
To inspect the last stable checkpoint without touching your branch: `git switch -c recover-<tag> <tag>` (for example `git switch -c recover-m0.2 m0.2`).

**Recovery procedure R2 (not pushed yet).** `git restore .` discards unstaged edits; `git reset --hard HEAD` discards all uncommitted work (irreversible); `git reset --soft HEAD~1` undoes the last local commit but keeps the changes.

**Never** use `git push --force` on a shared branch.

---

# Phase 0: Project Setup and Baseline

Branch: `phase-0-setup`

## Milestone 0.1: Repository, environment and tooling skeleton

**1. Milestone Name.** Working repository with reproducible environment and a passing smoke test.

**2. Objective.** Anyone on the team can clone, install and run tests with identical results. No algorithm code yet.

**3. Tasks to Complete.**
- [ ] Create the GitHub repo `graphpulse`, add all four members, clone it.
- [ ] `python --version` shows 3.11 or newer.
- [ ] Create and activate a virtual environment: `python -m venv .venv`, then `source .venv/bin/activate` (Windows PowerShell: `.venv\Scripts\Activate.ps1`).
- [ ] Write `pyproject.toml` (below) and `requirements-dev.txt` containing `pytest`, `hypothesis`, `networkx`.
- [ ] `pip install -e . -r requirements-dev.txt`, then pin the installed versions in `requirements-dev.txt` (check with `pip list`).
- [ ] Create `src/graphpulse/__init__.py` with `__version__ = "0.1.0"`.
- [ ] Create `tests/test_smoke.py` asserting the package imports and the version string.
- [ ] Write `.gitignore` and a `README.md` with the install and test commands.

**4. Files / Modules Affected.** New: `pyproject.toml`, `requirements-dev.txt`, `README.md`, `.gitignore`, `src/graphpulse/__init__.py`, `tests/test_smoke.py`.

**5. Implementation Guidance.**
- *src layout* (`src/graphpulse/`): tests run against the installed package, so you never accidentally test uncommitted local files.
- `pyproject.toml`:
```toml
[build-system]
requires = ["setuptools>=68"]
build-backend = "setuptools.build_meta"

[project]
name = "graphpulse"
version = "0.1.0"
requires-python = ">=3.11"

[tool.setuptools.packages.find]
where = ["src"]

[tool.pytest.ini_options]
testpaths = ["tests"]
markers = ["slow: long-running randomized tests"]
```
- `.gitignore` must contain: `.venv/`, `__pycache__/`, `*.pyc`, `.pytest_cache/`, `.hypothesis/`, `*.egg-info/`, `tests/failures/`, `experiments/output/`, `.env`, `.vscode/`, `.idea/`, `*.log`.

**6. Test Cases.**

| Test Case ID | Test Scenario | Preconditions | Steps | Expected Result | Status |
|---|---|---|---|---|---|
| T0.1-01 | Clean-clone install (integration) | Fresh directory, Python 3.11+ | Clone, create venv, `pip install -e . -r requirements-dev.txt` | Install succeeds with no errors | ☐ |
| T0.1-02 | Smoke test passes (positive) | Installed | `python -m pytest -q` | 1 test passed | ☐ |
| T0.1-03 | Package import (positive) | Installed | `python -c "import graphpulse; print(graphpulse.__version__)"` | Prints `0.1.0` | ☐ |
| T0.1-04 | Wrong Python blocked (negative) | Python 3.9 available | `pip install -e .` under 3.9 | Pip refuses due to `requires-python` | ☐ |
| T0.1-05 | Ignore rules work (validation) | Venv and pytest already run | `git status` | Untracked list shows only intended files, none of `.venv`, `__pycache__`, `.pytest_cache` | ☐ |
| T0.1-06 | Tests before install (failure handling) | Fresh venv, no `pip install -e .` | `python -m pytest -q` | Fails with `ModuleNotFoundError`; README documents the install step | ☐ |

**7. Verification Checklist.**
- [ ] T0.1-01 to T0.1-06 pass.
- [ ] A second team member repeats T0.1-01 on their own machine.
- [ ] `git ls-files` contains no `.venv` or cache files.

**8. Milestone Completion Criteria.** All six tests pass on two different machines; the repo contains only the files listed in section 4.

**9. Git Checkpoint.**
```
git checkout -b phase-0-setup
git status
git add .
git commit -m "chore: project skeleton, pinned dev tooling and smoke test"
git pull --rebase origin phase-0-setup   # skip on the very first push
git push -u origin phase-0-setup
git tag -a m0.1 -m "Milestone 0.1 done" && git push origin m0.1
```
Do NOT commit: `.venv/`, caches, `.env`, IDE folders.

**10. Rollback / Recovery.** Use R1. There is no earlier stable tag, so if the skeleton itself is broken, fix forward in a new commit.

## Milestone 0.2: Specification freeze and golden examples

**Requires:** 0.1

**1. Milestone Name.** Frozen model, cost model and hand-verified golden examples.

**2. Objective.** Every later proof, counter and test uses the same definitions. Golden examples give hand-computed ground truth independent of any code.

**3. Tasks to Complete.**
- [ ] Write `docs/SPEC.md` containing the sections in guidance.
- [ ] Create three golden graphs as JSON with hand-computed distances.
- [ ] Write a schema validator test for the golden files.

**4. Files / Modules Affected.** New: `docs/SPEC.md`, `tests/golden/g1_diamond.json`, `g2_chain.json`, `g3_unreachable.json`, `tests/test_golden_files.py`.

**5. Implementation Guidance.** `SPEC.md` must fix these:
- **Graph:** simple directed graph (no self-loops, no parallel edges), vertices `0..n-1`, edge weights strictly positive integers. Unreachable distance is `INF = float("inf")`. **Every "is this edge tight" test must first check `dist[u] != INF`**, because `inf + w == inf` would wrongly mark edges between two unreachable vertices as tight.
- **Updates:** `delete(u, v)`; `increase(u, v, new_w)` with `new_w > old_w`.
- **Definitions:** tight edge `(u,v)` means `dist[u] != INF and dist[u] + w(u,v) == dist[v]`; tight count `tight[v]`; affected set `A` = vertices whose distance changes; `F` = work of the last full rebuild of the tree (Dijkstra plus tight recount); `r` = work of a completed repair; budget `B = ceil(c * F)`.
- **Cost model (one shared table):**

| Operation | Charged when |
|---|---|
| SCAN | each adjacency entry examined (forward or reverse), and the single O(1) certificate check |
| PUSH | each heap push |
| POP | each heap pop, including stale entries |
| QUEUE | each enqueue or dequeue in affected-set propagation |

`F` counts SCAN, PUSH and POP of a complete tree rebuild: the Dijkstra part plus the in-edge scan that recomputes tight counts (defined in 3.1). State writes are not charged separately (each write is caused by an already-charged operation, a constant-factor modeling assumption to state in the proofs).
- **Golden graphs:** g1 diamond `0→1 (1), 0→2 (1), 1→3 (1), 2→3 (1)` (two equal shortest paths, `tight[3] = 2`); g2 chain `0→1→2→3` weights `2, 3, 4`; g3 has vertex 4 with no in-edges (unreachable). Store expected `dist` (with `null` for INF) and `tight`.

**6. Test Cases.**

| Test Case ID | Test Scenario | Preconditions | Steps | Expected Result | Status |
|---|---|---|---|---|---|
| T0.2-01 | All golden files load (positive) | Files exist | Run schema test | All three parse; keys `n`, `edges`, `source`, `dist`, `tight` present | ☐ |
| T0.2-02 | Non-positive weight rejected (negative) | Temp copy of g1 with weight 0 | Run schema validator on it | Validator raises | ☐ |
| T0.2-03 | Duplicate edge rejected (validation) | Temp copy with repeated edge | Validate | Raises | ☐ |
| T0.2-04 | INF encoding (edge case) | g3 | Read `dist[4]` | `null` | ☐ |
| T0.2-05 | Hand-check independent of code (validation) | Two team members | Each recomputes g1 to g3 distances on paper | Both match the JSON | ☐ |

**7. Verification Checklist.**
- [ ] `SPEC.md` contains all five definition groups above.
- [ ] Two members signed off the golden values by hand.
- [ ] Tests T0.2-01 to T0.2-05 pass.

**8. Milestone Completion Criteria.** Spec reviewed by all four members; golden tests green.

**9. Git Checkpoint.**
```
git status
git add .
git commit -m "docs: freeze spec, cost model and golden examples"
git pull --rebase origin phase-0-setup
git push origin phase-0-setup
git tag -a m0.2 -m "Milestone 0.2 done" && git push origin m0.2
```
Do NOT commit: scratch files with paper calculations, temp copies of the golden files.

**10. Rollback / Recovery.** R1 with stable tag `m0.1`. A wrong spec is cheaper to fix now than after Phase 3, so amend it via a new commit.

## Milestone 0.3: Validated directed graph

**Requires:** 0.2

**1. Milestone Name.** `DiGraph` with forward and reverse adjacency and strict validation.

**2. Objective.** A graph type that supports the deletions and weight increases the project needs, and rejects every invalid input.

**3. Tasks to Complete.**
- [ ] Implement `DiGraph(n)` with `add_edge`, `remove_edge`, `increase_weight`, `has_edge`, `weight`, `out_edges(u)`, `in_edges(v)`, `copy`, properties `n` and `m`.
- [ ] Add `DiGraph.from_json(path)` for the golden files.
- [ ] Write unit tests and one Hypothesis test.

**4. Files / Modules Affected.** New: `src/graphpulse/graph.py`, `tests/test_graph.py`.

**5. Implementation Guidance.**
- Storage: `out[u]: dict[int, int]` and `inn[v]: dict[int, int]`. Dicts give O(1) edge lookup and delete, and deterministic iteration order (insertion order).
- Validation: vertex in range; weight is `int` and `> 0` (reject `bool` and floats); no self-loop; no duplicate; `increase_weight` requires strictly larger weight; `remove_edge` and `increase_weight` on a missing edge raise `KeyError`.
- Keep `out` and `inn` updated together in one method so they cannot diverge.

**6. Test Cases.**

| Test Case ID | Test Scenario | Preconditions | Steps | Expected Result | Status |
|---|---|---|---|---|---|
| T0.3-01 | Add and query edges (positive) | Empty graph n=4 | Add 3 edges, query weight, out and in edges | Values match; `m == 3` | ☐ |
| T0.3-02 | Remove edge (positive) | Graph with edge | `remove_edge` | Gone from both `out` and `inn`; `m` decreases | ☐ |
| T0.3-03 | Duplicate edge (negative) | Edge exists | `add_edge` again | `ValueError` | ☐ |
| T0.3-04 | Self-loop (negative) | Any graph | `add_edge(2,2,1)` | `ValueError` | ☐ |
| T0.3-05 | Bad weights (validation) | Any graph | Weights 0, -3, 2.5, `True` | Each raises | ☐ |
| T0.3-06 | Vertex out of range (validation) | n=4 | `add_edge(0,4,1)` and `add_edge(-1,2,1)` | `IndexError` or `ValueError` | ☐ |
| T0.3-07 | Missing edge operations (failure handling) | Edge absent | `remove_edge`, `increase_weight` | `KeyError`; graph unchanged | ☐ |
| T0.3-08 | Increase rules (validation) | Edge weight 5 | `increase_weight(...,5)`, `(...,3)`, `(...,9)` | First two raise; third sets weight 9 in both maps | ☐ |
| T0.3-09 | Copy independence (edge case) | Graph | Copy, mutate copy | Original unchanged | ☐ |
| T0.3-10 | Adjacency consistency (property test) | Hypothesis, 200 examples | Random sequences of valid operations | `out` and `inn` describe the same edge set after every step | ☐ |
| T0.3-11 | Boundary sizes (edge case) | None | `n=0`, `n=1` with no edges; `n=100000` build with 200000 edges | No errors | ☐ |
| T0.3-12 | Golden integration | 0.2 files | `from_json` on all three | Correct `n` and `m` | ☐ |

**7. Verification Checklist.**
- [ ] All twelve tests pass and `pytest -q` for the whole repo is green.
- [ ] No public method can leave `out` and `inn` inconsistent (confirmed by T0.3-10).

**8. Milestone Completion Criteria.** Tests green; a teammate not on this milestone reviewed `graph.py`.

**9. Git Checkpoint.**
```
git status
git add .
git commit -m "feat(graph): validated directed graph with forward and reverse adjacency"
git pull --rebase origin phase-0-setup
git push origin phase-0-setup
git tag -a m0.3 -m "Milestone 0.3 done" && git push origin m0.3
```
Do NOT commit: `.hypothesis/`, generated large-graph files.

**10. Rollback / Recovery.** R1 with stable tag `m0.2`.

## Phase 0 Completion Checkpoint

| Item | Record |
|---|---|
| Completed milestones | 0.1, 0.2, 0.3 |
| Tests passed | ___ / ___ (run `python -m pytest -q`) |
| Known issues | ___ |
| Git commit hash | `git rev-parse --short HEAD` → ___ |
| Overall verification | Clean clone installs and passes on 2 machines; spec signed off |
| **Go/No-Go for Phase 1** | **GO only if** all tests are green, the spec has no open questions, and the branch is merged to `main` |

```
git checkout main && git pull origin main
git merge --no-ff phase-0-setup -m "merge: phase 0 complete"
git push origin main
git tag -a phase-0-done -m "Phase 0 complete" && git push origin phase-0-done
```

---

# Phase 1: Baseline Shortest Paths and Measurement

Branch: `phase-1-baseline` (create from updated `main`)

## Milestone 1.1: Operation counter and counted heap

**Requires:** 0.3

**1. Milestone Name.** Machine-independent work measurement.

**2. Objective.** Every later claim (budgets, competitive ratios, speedups) is measured in the operation counts fixed in `SPEC.md`, not seconds.

**3. Tasks to Complete.**
- [ ] `OpCounter` with fields `scan`, `push`, `pop`, `queue`.
- [ ] Properties `dijkstra_work` (scan + push + pop) and `work` (all four).
- [ ] `snapshot()` and `since(snapshot)` for measuring a region of code.
- [ ] `CountedHeap` wrapping `heapq` that increments `push` and `pop`.

**4. Files / Modules Affected.** New: `src/graphpulse/opcount.py`, `tests/test_opcount.py`.

**5. Implementation Guidance.** Use `heapq` from the standard library (no new dependency). Heap items are `(distance, vertex)` tuples. The counter is passed explicitly to algorithms; do not use a global, because tests and the controller need separate counters.

**6. Test Cases.**

| Test Case ID | Test Scenario | Preconditions | Steps | Expected Result | Status |
|---|---|---|---|---|---|
| T1.1-01 | Initial state (positive) | New counter | Read fields | All zero | ☐ |
| T1.1-02 | Push and pop counting (positive) | Counted heap | 5 pushes, 3 pops | `push=5`, `pop=3` | ☐ |
| T1.1-03 | Heap order (property) | 200 random lists | Push all, pop all | Non-decreasing order | ☐ |
| T1.1-04 | Pop from empty (negative) | Empty heap | `pop()` | `IndexError`; counters unchanged | ☐ |
| T1.1-05 | Equal keys (edge case) | Items `(5,1)`, `(5,2)` | Push and pop | Both returned, no comparison error | ☐ |
| T1.1-06 | Snapshot delta (positive) | Counter with activity | `s=snapshot()`, more ops, `since(s)` | Delta equals the extra ops only | ☐ |
| T1.1-07 | Counter independence (validation) | Two counters | Increment one | Other stays zero | ☐ |
| T1.1-08 | Work definitions (validation) | Counter with all four fields set | Read `dijkstra_work`, `work` | `work - dijkstra_work == queue` | ☐ |

**7. Verification Checklist.**
- [ ] T1.1-01 to T1.1-08 pass; full suite green.
- [ ] No global mutable counter exists (`grep -n "global" src/graphpulse/opcount.py` is empty).

**8. Milestone Completion Criteria.** Tests green; definitions match `SPEC.md` exactly.

**9. Git Checkpoint.**
```
git checkout -b phase-1-baseline
git status
git add .
git commit -m "feat(opcount): operation counter and counted heap"
git pull --rebase origin phase-1-baseline
git push -u origin phase-1-baseline
git tag -a m1.1 -m "Milestone 1.1 done" && git push origin m1.1
```
Do NOT commit: `.hypothesis/`, caches.

**10. Rollback / Recovery.** R1 with stable tag `m0.3`.

## Milestone 1.2: Counted Dijkstra baseline

**Requires:** 1.1

**1. Milestone Name.** Heap-based Dijkstra returning distances, parents and exact work.

**2. Objective.** The trusted baseline, and the main component of `F` (the rebuild work the budget controller compares against).

**3. Tasks to Complete.**
- [ ] `dijkstra(g, src, counter) -> (dist, parent)` with lazy deletion.
- [ ] `dist[v] = INF` and `parent[v] = -1` for unreachable vertices; `parent[src] = -1`.
- [ ] Validate `src` in range.

**4. Files / Modules Affected.** New: `src/graphpulse/dijkstra.py`, `tests/test_dijkstra.py`. Modified: `graph.py` (only if an iteration helper is needed).

**5. Implementation Guidance.** Process a vertex only when the popped distance equals the stored one (skip stale entries, but still count the pop). Charge one SCAN per adjacency entry examined. Deterministic tie-breaking is not required; tests compare distances and verify parents with the invariant checker (1.3), never parents against a fixed answer. Because a push happens only on strict improvement, `pop == push` at the end.

**6. Test Cases.**

| Test Case ID | Test Scenario | Preconditions | Steps | Expected Result | Status |
|---|---|---|---|---|---|
| T1.2-01 | Golden graphs (positive) | 0.2 files | Run on g1, g2, g3 | Distances equal the JSON (INF for vertex 4) | ☐ |
| T1.2-02 | Single vertex (edge case) | `n=1` | Run | `dist=[0]` | ☐ |
| T1.2-03 | Source has no out-edges (edge case) | Isolated source | Run | Everything else INF | ☐ |
| T1.2-04 | Equal-cost paths (edge case) | g1 | Run | `dist[3]=2` regardless of the parent chosen | ☐ |
| T1.2-05 | Very large weights (edge case) | Weights 10^12 | Run | Exact integer distances, no overflow | ☐ |
| T1.2-06 | Bad source (negative) | n=4 | `src=4` and `src=-1` | Raises | ☐ |
| T1.2-07 | Exact scan count (validation) | Random graph | Run | `scan == sum(outdeg(v) for reachable v)` | ☐ |
| T1.2-08 | Heap balance (validation) | Random graph | Run | `push == pop`; `push <= 1 + scan` | ☐ |
| T1.2-09 | Parents form a tree (integration) | Random graph | Follow parent chains | Every reachable vertex reaches the source; `dist[parent[v]] < dist[v]` | ☐ |

**7. Verification Checklist.**
- [ ] T1.2-01 to T1.2-09 pass.
- [ ] Counts for the golden graphs are written into `SPEC.md` as worked examples.

**8. Milestone Completion Criteria.** Tests green; exact-count identities T1.2-07 and T1.2-08 hold on 100 random graphs.

**9. Git Checkpoint.**
```
git status
git add .
git commit -m "feat(dijkstra): counted heap-based Dijkstra baseline"
git pull --rebase origin phase-1-baseline
git push origin phase-1-baseline
git tag -a m1.2 -m "Milestone 1.2 done" && git push origin m1.2
```
Do NOT commit: benchmark output files.

**10. Rollback / Recovery.** R1 with stable tag `m1.1`.

## Milestone 1.3: Invariant checker and independent oracle

**Requires:** 1.2

**1. Milestone Name.** Shortest-path invariant checker plus cross-check against `networkx`.

**2. Objective.** A checker that certifies any `(dist, parent)` pair without trusting the algorithm that produced it. It is the safety net for all repair work.

**3. Tasks to Complete.**
- [ ] `check_spt(g, src, dist, parent)` raising `InvariantViolation` with a precise message.
- [ ] Oracle test comparing Dijkstra with `networkx.single_source_dijkstra_path_length`.
- [ ] Mutation tests proving the checker rejects corrupted answers.
- [ ] `experiments/bench_dijkstra.py` printing the Dijkstra work for a 100x100 grid (output not committed).

**4. Files / Modules Affected.** New: `src/graphpulse/verify.py`, `tests/test_verify.py`, `experiments/bench_dijkstra.py`.

**5. Implementation Guidance.** The checker verifies: (a) `dist[src] == 0`; (b) for every edge `(u,v)` with finite `dist[u]`: `dist[v] <= dist[u] + w` (this also rejects a finite predecessor with INF successor); (c) for every reachable `v != src`, the parent edge is tight and `dist[parent[v]] < dist[v]`; (d) unreachable vertices have `dist == INF` and `parent == -1`. Condition (b) with (c) proves optimality: distances are feasible potentials realized by actual paths.

**6. Test Cases.**

| Test Case ID | Test Scenario | Preconditions | Steps | Expected Result | Status |
|---|---|---|---|---|---|
| T1.3-01 | Accepts correct output (positive) | Dijkstra results on golden graphs | `check_spt` | No exception | ☐ |
| T1.3-02 | Rejects dist too small (mutation) | Correct result | Subtract 1 from one reachable `dist[v]` | `InvariantViolation` | ☐ |
| T1.3-03 | Rejects dist too large (mutation) | Correct result | Add 1 to one `dist[v]` | Violation (fails condition b or c) | ☐ |
| T1.3-04 | Rejects wrong parent (mutation) | Correct result | Point parent to a non-tight neighbor | Violation | ☐ |
| T1.3-05 | Rejects reachable marked INF (mutation) | Correct result | Set a reachable `dist[v]=INF` | Violation | ☐ |
| T1.3-06 | Oracle agreement (property) | Hypothesis, 300 random graphs | Compare with networkx | Identical distances | ☐ |
| T1.3-07 | Unreachable vertices (edge case) | g3 | Check | Accepted only with INF and parent -1 | ☐ |
| T1.3-08 | Message quality (failure handling) | Any mutation above | Read exception | Names the vertex or edge that failed | ☐ |

**7. Verification Checklist.**
- [ ] All eight tests pass.
- [ ] Every mutation type in T1.3-02 to T1.3-05 is caught on 100 random graphs.
- [ ] `bench_dijkstra.py` runs and prints the Dijkstra work; record the value in your notes.

**8. Milestone Completion Criteria.** Checker catches 100 percent of injected mutations; oracle agreement holds on 300 graphs.

**9. Git Checkpoint.**
```
git status
git add .
git commit -m "feat(verify): shortest-path invariant checker with networkx oracle tests"
git pull --rebase origin phase-1-baseline
git push origin phase-1-baseline
git tag -a m1.3 -m "Milestone 1.3 done" && git push origin m1.3
```
Do NOT commit: `experiments/output/`, `.hypothesis/`.

**10. Rollback / Recovery.** R1 with stable tag `m1.2`.

## Phase 1 Completion Checkpoint

| Item | Record |
|---|---|
| Completed milestones | 1.1, 1.2, 1.3 |
| Tests passed | ___ / ___ |
| Known issues | ___ |
| Git commit hash | ___ |
| Overall verification | Dijkstra agrees with networkx on 300 random graphs; checker catches all mutations; scan and heap identities hold |
| **Go/No-Go for Phase 2** | **GO only if** every test is green and the counter definitions match `SPEC.md` |

```
git checkout main && git pull origin main
git merge --no-ff phase-1-baseline -m "merge: phase 1 complete"
git push origin main
git tag -a phase-1-done -m "Phase 1 complete" && git push origin phase-1-done
```

---

# Phase 2: Test Infrastructure (Generators, Updates, Differential Harness)

Branch: `phase-2-harness`

## Milestone 2.1: Graph generators, including an adversarial family

**Requires:** 1.3 (the adversarial test uses Dijkstra)

**1. Milestone Name.** Deterministic graph families for testing and later experiments.

**2. Objective.** Reproducible graphs of several shapes, plus one that forces the worst case for repair.

**3. Tasks to Complete.**
- [ ] `grid(rows, cols, seed, wmin, wmax)`: road-like, every adjacent pair joined by two directed edges with independent random weights.
- [ ] `random_sparse(n, m, seed, wmin, wmax)`.
- [ ] `hub_spoke(hubs, spokes_per_hub, seed)`.
- [ ] `comb_adversarial(n, seed)`: a chain `i → i+1` (weight 1) with back edges `i+1 → i` (weight 1) and heavy shortcut edges `0 → i` for `i >= 2` (weight `i + K` for a fixed `K > 0`).
- [ ] Every generator returns a validated `DiGraph`.

**4. Files / Modules Affected.** New: `src/graphpulse/generators.py`, `tests/test_generators.py`.

**5. Implementation Guidance.** Use `random.Random(seed)`, never the global generator, so results are identical across machines. The adversarial property to prove in a test: deleting edge `(0, 1)` changes the distance of **every** vertex `v >= 1`. This makes the affected set as large as the graph, which is what the budget controller in Phase 4 must survive.

**6. Test Cases.**

| Test Case ID | Test Scenario | Preconditions | Steps | Expected Result | Status |
|---|---|---|---|---|---|
| T2.1-01 | Determinism (positive) | Same seed | Generate twice | Identical edge sets and weights | ☐ |
| T2.1-02 | Seed sensitivity (positive) | Seeds 1 and 2 | Generate | Weights differ | ☐ |
| T2.1-03 | Grid size (validation) | `grid(5,5)` | Count | `n=25`, `m=80` | ☐ |
| T2.1-04 | Degenerate sizes (edge case) | `grid(1,1)`, `grid(1,5)` | Generate | `n=1, m=0`; `n=5, m=8` | ☐ |
| T2.1-05 | Invalid parameters (negative) | `rows=0`, `wmin=0`, `wmin>wmax` | Generate | `ValueError` | ☐ |
| T2.1-06 | Weight range (validation) | `wmin=3, wmax=9` | Check all edges | Every weight in `[3,9]` and an int | ☐ |
| T2.1-07 | Simple graph (validation) | All generators | Check | No self-loops or duplicates | ☐ |
| T2.1-08 | Adversarial property (integration) | `comb_adversarial(200)` | Dijkstra before and after deleting `(0,1)` | Distance changes for exactly 199 vertices | ☐ |
| T2.1-09 | Hub degrees (validation) | `hub_spoke(3,10)` | Check | Hubs have the expected degree | ☐ |

**7. Verification Checklist.**
- [ ] All nine tests pass; full suite green.
- [ ] T2.1-08 verified for `n` in 10, 200, 1000.

**8. Milestone Completion Criteria.** Determinism and the adversarial property proven by tests.

**9. Git Checkpoint.**
```
git checkout -b phase-2-harness
git status
git add .
git commit -m "feat(generators): graph families including adversarial comb"
git pull --rebase origin phase-2-harness
git push -u origin phase-2-harness
git tag -a m2.1 -m "Milestone 2.1 done" && git push origin m2.1
```
Do NOT commit: generated graph dumps.

**10. Rollback / Recovery.** R1 with stable tag `m1.3`.

## Milestone 2.2: Update model and update-sequence generator

**Requires:** 0.3 (2.1 is not needed, so this can run in parallel with it)

**1. Milestone Name.** Update objects and valid random update sequences.

**2. Objective.** Generate realistic sequences of deletions and increases that are always valid when applied in order.

**3. Tasks to Complete.**
- [ ] `Update` dataclass: `kind` (`"delete"` or `"increase"`), `u`, `v`, `new_w`.
- [ ] `apply_update(g, upd)` mutating the graph, raising on invalid updates.
- [ ] `random_updates(g, count, seed, mode, p_delete)` with modes `uniform`, `clustered`, `near_source`.
- [ ] Generation runs on a **copy** so the caller's graph is untouched.

**4. Files / Modules Affected.** Modified: `src/graphpulse/generators.py`. New: `tests/test_updates.py`.

**5. Implementation Guidance.** Simulate application while generating so each update is valid at its position in the sequence. `clustered` picks a random centre and samples edges whose endpoints are within `radius` hops (BFS). `near_source` samples edges within a few hops of the source. If edges run out, return the shorter list; never emit an invalid update.

**6. Test Cases.**

| Test Case ID | Test Scenario | Preconditions | Steps | Expected Result | Status |
|---|---|---|---|---|---|
| T2.2-01 | Sequential validity (positive) | Grid 10x10, 300 updates | Apply in order | No exception | ☐ |
| T2.2-02 | Determinism (positive) | Same seed and mode | Generate twice | Identical lists | ☐ |
| T2.2-03 | Input graph untouched (validation) | Graph before and after generation | Compare edge sets | Equal | ☐ |
| T2.2-04 | Exhaustion (edge case) | Graph with 5 edges, ask for 50 deletions | Generate | At most 5 returned, all valid | ☐ |
| T2.2-05 | Invalid apply (negative) | Missing edge; increase to a smaller weight | `apply_update` | Raises; graph unchanged | ☐ |
| T2.2-06 | Clustered locality (validation) | radius=2 | Check endpoints | All within 2 hops of the centre | ☐ |
| T2.2-07 | Increase strictness (validation) | 500 increases | Check | Every `new_w > old weight` | ☐ |
| T2.2-08 | Mix ratio (validation) | `p_delete=0.7`, 1000 updates | Count | Deletion share about 0.7 within tolerance | ☐ |

**7. Verification Checklist.**
- [ ] All eight tests pass.
- [ ] 1000 seeded sequences on three graph families apply without error.

**8. Milestone Completion Criteria.** No generated sequence is ever invalid.

**9. Git Checkpoint.**
```
git status
git add .
git commit -m "feat(updates): update model and valid random update sequences"
git pull --rebase origin phase-2-harness
git push origin phase-2-harness
git tag -a m2.2 -m "Milestone 2.2 done" && git push origin m2.2
```
Do NOT commit: sequence dumps.

**10. Rollback / Recovery.** R1 with stable tag `m2.1`.

## Milestone 2.3: Differential testing harness

**Requires:** 2.1 and 2.2

**1. Milestone Name.** A harness that compares any candidate maintainer against plain recomputation after every update.

**2. Objective.** One tool that will judge every repair algorithm from Phase 3 on, and that has itself been proven to catch bugs.

**3. Tasks to Complete.**
- [ ] `Maintainer` protocol: `dist()` and `apply(update) -> UpdateStats`.
- [ ] `RecomputeMaintainer`: full Dijkstra after every update (the trusted baseline).
- [ ] `run_differential(make_graph, make_candidate, updates, src)`: after each update compare candidate distances with a fresh Dijkstra and run `check_spt`-style checks where the candidate exposes parents.
- [ ] On mismatch, write a reproducer JSON (graph, updates, seed, failing index) to `tests/failures/` and raise.
- [ ] Self-test with an intentionally buggy maintainer.

**4. Files / Modules Affected.** New: `src/graphpulse/maintainer.py`, `src/graphpulse/harness.py`, `tests/test_harness.py`. Runtime folder `tests/failures/` (gitignored).

**5. Implementation Guidance.** The reference is recomputed on its **own copy** of the graph so a buggy candidate cannot corrupt it. Log the seed on every failure. Provide `BuggyMaintainer` in the test file only (for example: skips every 7th update, or adds 1 to one distance).

**6. Test Cases.**

| Test Case ID | Test Scenario | Preconditions | Steps | Expected Result | Status |
|---|---|---|---|---|---|
| T2.3-01 | Baseline vs itself (positive) | `RecomputeMaintainer` twice | 1000 updates on grid | Passes, zero mismatches | ☐ |
| T2.3-02 | Bug detection (negative) | `BuggyMaintainer` skipping every 7th update | Run | Fails at exactly the first divergent update index | ☐ |
| T2.3-03 | Reproducer replay (failure handling) | Dump from T2.3-02 | Load and replay | Reproduces the same failure deterministically | ☐ |
| T2.3-04 | Wrong-length result (validation) | Candidate returning a short `dist` | Run | Clear error naming the length | ☐ |
| T2.3-05 | Checks run every step (integration) | Spy on comparison function | 50 updates | Called exactly 50 times plus once for the initial state | ☐ |
| T2.3-06 | Unwritable dump dir (failure handling) | `tests/failures/` read-only | Trigger a failure | Loud error, never a silent pass | ☐ |
| T2.3-07 | Empty update list (edge case) | `updates=[]` | Run | Passes; only the initial state checked | ☐ |
| T2.3-08 | Graph isolation (validation) | Candidate that mutates its graph | Run | Reference graph unaffected | ☐ |

**7. Verification Checklist.**
- [ ] All eight tests pass.
- [ ] The harness catches each of three different injected bugs.
- [ ] `tests/failures/` is confirmed ignored (`git status` shows nothing from it).

**8. Milestone Completion Criteria.** The harness detects every injected bug and replays reproducers.

**9. Git Checkpoint.**
```
git status
git add .
git commit -m "feat(harness): differential testing harness with reproducer dumps"
git pull --rebase origin phase-2-harness
git push origin phase-2-harness
git tag -a m2.3 -m "Milestone 2.3 done" && git push origin m2.3
```
Do NOT commit: anything in `tests/failures/`.

**10. Rollback / Recovery.** R1 with stable tag `m2.2`.

## Phase 2 Completion Checkpoint

| Item | Record |
|---|---|
| Completed milestones | 2.1, 2.2, 2.3 |
| Tests passed | ___ / ___ |
| Known issues | ___ |
| Git commit hash | ___ |
| Overall verification | Deterministic generators; sequences always valid; harness catches injected bugs |
| **Go/No-Go for Phase 3** | **GO only if** the harness has caught all three injected bugs. Repair code must never be written before this passes. |

```
git checkout main && git pull origin main
git merge --no-ff phase-2-harness -m "merge: phase 2 complete"
git push origin main
git tag -a phase-2-done -m "Phase 2 complete" && git push origin phase-2-done
```

---

# Phase 3: Incremental Shortest-Path Repair

Branch: `phase-3-repair`

**Design summary (read before starting).** For a positive-integer-weight graph, the *tight-edge subgraph* (edges with `dist[u] + w == dist[v]`) is acyclic. Per vertex we keep `tight[v]`, the number of tight in-edges. When an update removes a tight edge:
- if `tight[v] > 1`, `v` keeps its distance (another tight edge supports it);
- if `tight[v] == 1`, `v` is affected, and so is any vertex that loses all its tight in-edges to affected vertices.
Vertices with a tight in-edge from an unaffected vertex keep their distance; that argument is proof P1 and must be written in `docs/proofs/P1_repair_correctness.md` during this phase.

## Milestone 3.1: Shortest-path-tree state with tight counters

**Requires:** 2.3

**1. Milestone Name.** `SPTState` holding `dist`, `parent`, `children`, `tight`, and the measured `F`.

**2. Objective.** The data structure repair operates on, with a from-scratch checker for it.

**3. Tasks to Complete.**
- [x] `SPTState.build(g, src, counter)`: run Dijkstra, then compute `tight` and `children` by scanning in-edges.
- [x] Record `F_ops` = total rebuild work (Dijkstra plus the in-edge scan that computes `tight`), the cost of doing this build again.
- [x] Extend `verify.py` with `check_state(g, state)` that recomputes everything from scratch and compares.

**4. Files / Modules Affected.** New: `src/graphpulse/spt.py`, `tests/test_spt.py`. Modified: `src/graphpulse/verify.py`.

**5. Implementation Guidance.** `tight[src] = 0` (the source is the root and is never affected). `parent[v]` is one tight in-neighbor (choose the smallest id for determinism). `children[x]` is a `set` of vertices whose parent is `x`. The tight test **must** guard `dist[u] != INF`.

**6. Test Cases.**

| Test Case ID | Test Scenario | Preconditions | Steps | Expected Result | Status |
|---|---|---|---|---|---|
| T3.1-01 | Diamond (positive) | g1 | Build | `tight[3]==2`, `tight[1]==tight[2]==1` | ☑ |
| T3.1-02 | Chain (positive) | g2 | Build | Every non-source `tight==1`; children form a path | ☑ |
| T3.1-03 | Unreachable (edge case) | g3 | Build | Vertex 4: `tight=0`, `parent=-1`, not in any children set | ☑ |
| T3.1-04 | INF guard (edge case) | Two unreachable vertices joined by an edge | Build | That edge is NOT counted as tight | ☑ |
| T3.1-05 | Edge into source (edge case) | Cycle back to the source | Build | `tight[src]==0` | ☑ |
| T3.1-06 | From-scratch equality (property) | Hypothesis, 300 graphs | Build then `check_state` | Passes | ☑ |
| T3.1-07 | Corruption detected (mutation) | Correct state | Change one `tight` count; then one child link | `check_state` raises each time | ☑ |
| T3.1-08 | F equals rebuild work (validation) | Random graph | Compare `F_ops` with a standalone counted Dijkstra | `F_ops == dijkstra_work + sum of in-degrees of reachable non-source vertices` | ☑ |
| T3.1-09 | Parent/children consistency (validation) | Random graphs | Check | `v in children[parent[v]]` for every reachable non-source `v` | ☑ |

**7. Verification Checklist.**
- [x] All tests pass; regression: all Phase 1 and 2 tests still pass.
- [x] `docs/proofs/P1_repair_correctness.md` started with the definition of tight edges and the DAG claim.

**8. Milestone Completion Criteria.** `check_state` accepts every built state and rejects every corruption.

**9. Git Checkpoint.**
```
git checkout -b phase-3-repair
git status
git add .
git commit -m "feat(spt): shortest-path-tree state with tight counters and state checker"
git pull --rebase origin phase-3-repair
git push -u origin phase-3-repair
git tag -a m3.1 -m "Milestone 3.1 done" && git push origin m3.1
```
Do NOT commit: `.hypothesis/`, notes outside `docs/`.

**10. Rollback / Recovery.** R1 with stable tag `m2.3`.

## Milestone 3.2: Free-update certificate and a correct-by-fallback maintainer

**Requires:** 3.1

**1. Milestone Name.** `RepairMaintainer` skeleton: zero-work certificate, alternative-support case, and full-rebuild fallback for everything else.

**2. Objective.** A maintainer that is already **correct at every commit**: cheap cases handled, unhandled cases fall back to a rebuild until 3.4 replaces the fallback.

**3. Tasks to Complete.**
- [x] `RepairMaintainer(g, src)` implementing the `Maintainer` protocol.
- [x] **Certificate 1 (non-tight):** if `dist[u] == INF` or `dist[u] + w != dist[v]` for the updated edge, distances are unchanged; charge exactly 1 SCAN and return.
- [x] **Alternative support:** edge is tight but `tight[v] > 1`. Decrement `tight[v]`; if `parent[v] == u`, scan in-edges of `v` (counted) and choose the smallest other tight in-neighbor as the new parent, updating `children`.
- [x] Otherwise call `_rebuild()` (full `SPTState.build`).
- [x] `UpdateStats` records strategy (`cert`, `alt`, `rebuild`) and work.

**4. Files / Modules Affected.** New: `src/graphpulse/repair.py`, `tests/test_cert.py`. Modified: `src/graphpulse/maintainer.py` (stats type).

**5. Implementation Guidance.** For an **increase** with a tight edge and `w' > w`, the edge is no longer tight afterwards, so `tight[v]` decrements exactly as for a deletion. Apply the update to the graph first, then read state. Deleting or increasing an edge whose head is the source is always a certificate hit (it can never be tight).

**6. Test Cases.**

| Test Case ID | Test Scenario | Preconditions | Steps | Expected Result | Status |
|---|---|---|---|---|---|
| T3.2-01 | Non-tight deletion (positive) | Diamond plus extra heavy edge | Delete the heavy edge | Strategy `cert`; state identical; work == 1 | ☑ |
| T3.2-02 | Unreachable tail (edge case) | g3 with edge among unreachable vertices | Delete it | Certificate hit | ☑ |
| T3.2-03 | Alternative support (positive) | g1 (`tight[3]=2`) | Delete `1→3` | `dist` unchanged; `tight[3]==1`; parent is 2; `check_state` passes | ☑ |
| T3.2-04 | Alternative, edge was not the parent (edge case) | g1, parent of 3 is 1 | Delete `2→3` | Parent stays 1; `tight[3]==1` | ☑ |
| T3.2-05 | Increase with alternative (positive) | g1 | Increase `1→3` | Same as T3.2-03 (edge no longer tight) | ☑ |
| T3.2-06 | Sole tight edge falls back (integration) | g2 chain | Delete `1→2` | Strategy `rebuild`; distances correct | ☑ |
| T3.2-07 | Edge into source (edge case) | Cycle to source | Delete it | Certificate hit | ☑ |
| T3.2-08 | Differential run (regression) | 3.x harness | 2000 mixed updates on grid, random_sparse, hub_spoke | Zero mismatches; `check_state` after every update | ☑ |
| T3.2-09 | Stats consistency (validation) | Same run | Sum strategy counts | Equals the number of updates | ☑ |

**7. Verification Checklist.**
- [x] All tests pass; Phase 1 and 2 tests still pass.
- [x] Report the certificate hit rate on a 30x30 grid with 1000 uniform deletions (informational, no fixed threshold): 71.30% (713/1000).

**8. Milestone Completion Criteria.** Zero harness mismatches across 3 families with 2000 updates each.

**9. Git Checkpoint.**
```
git status
git add .
git commit -m "feat(repair): zero-work certificate, alternative support and rebuild fallback"
git pull --rebase origin phase-3-repair
git push origin phase-3-repair
git tag -a m3.2 -m "Milestone 3.2 done" && git push origin m3.2
```
Do NOT commit: harness reproducer dumps.

**10. Rollback / Recovery.** R1 with stable tag `m3.1`.

## Milestone 3.3: Affected-set identification

**Requires:** 3.2

**1. Milestone Name.** `find_affected(state, g, v)`: the exact set of vertices whose distance changes.

**2. Objective.** Isolate and verify the hardest piece of logic before recomputing anything.

**3. Tasks to Complete.**
- [x] Implement propagation: start with `A = {v}` (where `tight[v] == 1` and its sole tight edge was removed). For each `x` dequeued (QUEUE op), scan out-edges `(x, z)` (SCAN). If the edge is tight under the **old** distances and `z` not in `A`, decrement a *scratch* copy of `tight[z]`; when it reaches 0, add `z` to `A` and enqueue it.
- [x] The function is **pure**: it never modifies `SPTState`.
- [x] Wire it into `RepairMaintainer` only in a test harness (the rebuild fallback still performs the actual update).

**4. Files / Modules Affected.** Modified: `src/graphpulse/repair.py`. New: `tests/test_affected.py`.

**5. Implementation Guidance.** Use a local `dict` for scratch decrements. The source never enters `A`. Because the tight subgraph is acyclic (positive weights), propagation terminates. **Oracle for the test:** `A_expected = {x : dist_old[x] != dist_new[x]}` computed with a fresh Dijkstra on the updated graph (INF counts as a change).

**6. Test Cases.**

| Test Case ID | Test Scenario | Preconditions | Steps | Expected Result | Status |
|---|---|---|---|---|---|
| T3.3-01 | Chain (positive) | g2, delete `1→2` | `find_affected` | `A == {2, 3}` | ☑ |
| T3.3-02 | Disconnection (edge case) | Delete the only in-edge of a subtree | Find | `A` = whole subtree (these become INF) | ☑ |
| T3.3-03 | Adversarial comb (integration) | `comb_adversarial(200)`, delete `(0,1)` | Find | `\|A\| == 199` | ☑ |
| T3.3-04 | Vertex with two tight parents survives (edge case) | Diamond below the deleted edge | Find | The shared vertex is **not** in `A` if a tight in-edge remains from an unaffected vertex | ☑ |
| T3.3-05 | Purity (validation) | Snapshot of state | Call `find_affected` | State deep-equals snapshot | ☑ |
| T3.3-06 | Oracle equality (property) | Hypothesis, 500 cases, deleting only edges with `tight[v]==1` | Compare `A` to `A_expected` | Equal | ☑ |
| T3.3-07 | Source never affected (edge case) | Graph with cycles through the source | Find | Source not in `A` | ☑ |
| T3.3-08 | Exact work (validation) | Any case | Read counter | `queue == 2*\|A\|` and `scan == sum(outdeg(x) for x in A)` | ☑ |
| T3.3-09 | Cyclic graphs terminate (edge case) | Random graphs with cycles | Find | Terminates; equals oracle | ☑ |

**7. Verification Checklist.**
- [x] All tests pass; earlier tests still pass.
- [x] Proof P1 part 2 written: "a vertex with a tight in-edge from an unaffected vertex keeps its distance; a vertex all of whose tight in-edges are lost has strictly larger distance."

**8. Milestone Completion Criteria.** T3.3-06 passes on 500 cases with zero disagreement.

**9. Git Checkpoint.**
```
git status
git add .
git commit -m "feat(repair): exact affected-set identification verified against oracle"
git pull --rebase origin phase-3-repair
git push origin phase-3-repair
git tag -a m3.3 -m "Milestone 3.3 done" && git push origin m3.3
```
Do NOT commit: `.hypothesis/`.

**10. Rollback / Recovery.** R1 with stable tag `m3.2`.

## Milestone 3.4: Recompute the affected region and commit (deletions)

**Requires:** 3.3

**1. Milestone Name.** Real incremental repair for deletions, replacing the rebuild fallback in the sole-tight-edge case.

**2. Objective.** Recompute distances only inside `A` and update all state consistently.

### 3. Tasks to Complete.
- [x] For each `x` in `A`: set `dist[x] = INF`, then scan in-edges `(y, x)` with `y` not in `A` and `dist[y] != INF`; the best candidate `dist[y] + w` seeds the heap (PUSH).
- [x] Run Dijkstra restricted to `A` (relax only edges into `A`).
- [x] Recompute `tight[x]` for every `x` in `A` from scratch using final distances (scan in-edges, INF-guarded) and pick a new `parent`.
- [x] Apply the scratch decrements to `tight[z]` for `z` outside `A` (edges from `A` to `z` are no longer tight, because distances in `A` strictly increased).
- [x] For each `z` outside `A` whose parent was in `A`, choose a new tight parent among in-neighbors.
- [x] Rebuild `children` links for all changed parents.
- [x] Replace the rebuild fallback for this case; keep `rebuild` only where still needed.

**4. Files / Modules Affected.** Modified: `src/graphpulse/repair.py`. New: `tests/test_repair_delete.py`.

**5. Implementation Guidance.** Correctness argument (write into P1): no edge from `A` into a non-affected vertex can become newly tight, because the head's distance is unchanged while the tail's distance only grew. Therefore non-affected `tight` counts only decrease and are fixed by the scratch decrements. Work per repair is proportional to `\|A\|` plus the edges incident to `A`, times a logarithmic heap factor; verify this with counters rather than claiming it.

**6. Test Cases.**

| Test Case ID | Test Scenario | Preconditions | Steps | Expected Result | Status |
|---|---|---|---|---|---|
| T3.4-01 | Chain repair (positive) | g2 with a detour edge `0→3` | Delete `1→2` | Distances match a fresh Dijkstra; `check_state` passes | ☑ |
| T3.4-02 | Disconnection (edge case) | Chain, delete `0→1` | Repair | Affected vertices `dist=INF`, `parent=-1`, `tight=0` | ☑ |
| T3.4-03 | Adversarial comb (integration) | `comb_adversarial(200)`, delete `(0,1)` | Repair | Correct; work is of the same order as a full Dijkstra | ☑ |
| T3.4-04 | Non-affected child re-parented (edge case) | Vertex whose parent enters `A` but keeps another tight edge | Repair | New parent chosen from a non-affected tight in-neighbor | ☑ |
| T3.4-05 | Small repair beats rebuild (validation) | Grid 30x30, delete a leaf-adjacent tight edge | Compare work | Repair work strictly less than `F` | ☑ |
| T3.4-06 | Differential run (regression) | Harness | 5000 deletions across 3 families, seeds 0 to 4 | Zero mismatches; `check_state` after every step | ☑ |
| T3.4-07 | Earlier behavior (regression) | Tests T3.2-01 to T3.2-09 | Re-run | Still pass | ☑ |
| T3.4-08 | Deleting to empty (edge case) | Repeatedly delete until no edges | Run | State remains valid at every step | ☑ |
| T3.4-09 | Nested diamonds (edge case) | Hand-built graph with chained diamonds | Delete an early edge | Matches oracle | ☑ |

**7. Verification Checklist.**
- [x] All tests pass; 5000-update differential run is clean for five seeds.
- [x] Proof P1 part 3 written (non-affected counts only decrease) and reviewed by two members other than the author.

**8. Milestone Completion Criteria.** Zero mismatches on 25,000 total deletions; proof reviewed.

**9. Git Checkpoint.**
```
git status
git add .
git commit -m "feat(repair): incremental repair for edge deletions with exact state maintenance"
git pull --rebase origin phase-3-repair
git push origin phase-3-repair
git tag -a m3.4 -m "Milestone 3.4 done" && git push origin m3.4
```
Do NOT commit: reproducer dumps, scratch proof drafts outside `docs/proofs/`.

**10. Rollback / Recovery.** R1 with stable tag `m3.3`; the maintainer at `m3.3` is still fully correct because it falls back to a rebuild.

## Milestone 3.5: Weight increases

**Requires:** 3.4

**1. Milestone Name.** Repair for edge weight increases.

**2. Objective.** Complete the agreed update model.

### 3. Tasks to Complete.
- [x] Route a tight increase with `tight[v] == 1` through the same identification and recompute as deletion, with the edge still present at its **new** weight.
- [x] The recompute step must treat `(u, v, w')` as an ordinary in-edge candidate for `v`.
- [x] After recompute, the edge may be tight again; the from-scratch `tight` recount for `A` handles that.

**4. Files / Modules Affected.** Modified: `src/graphpulse/repair.py`. New: `tests/test_repair_increase.py`.

**5. Implementation Guidance.** `u` is upstream of `v` in the tight DAG, so `u` is never in `A`. When `v` was supported only by this edge, its distance strictly increases: every other candidate is strictly larger than the old `dist[v]`, and so is the increased edge. If the increase is small and the edge remains the best route, the whole subtree below `v` is affected and shifts by exactly the same amount; a test should confirm this.

**6. Test Cases.**

| Test Case ID | Test Scenario | Preconditions | Steps | Expected Result | Status |
|---|---|---|---|---|---|
| T3.5-01 | Increase, edge stays best (positive) | Chain | Increase middle edge by 5 | All downstream distances rise by exactly 5 | ☑ |
| T3.5-02 | Increase, alternative wins (positive) | Chain with detour | Increase past the detour | Distances use the detour; matches oracle | ☑ |
| T3.5-03 | Non-tight increase (edge case) | Non-tight edge | Increase | Certificate hit, work == 1 | ☑ |
| T3.5-04 | Tight with alternative (edge case) | Diamond | Increase one branch | No distance change; `tight` decremented | ☑ |
| T3.5-05 | Edge becomes tight again (edge case) | Case from T3.5-01 | Check `tight` after | The increased edge is counted as tight for `v` | ☑ |
| T3.5-06 | Invalid increase (negative) | Edge weight 5 | `increase(...,5)` | Rejected by `apply_update`; maintainer unchanged | ☑ |
| T3.5-07 | Mixed differential run (regression) | Harness | 20,000 mixed updates, 3 families, `p_delete=0.5` | Zero mismatches | ☑ |
| T3.5-08 | Deletion tests (regression) | 3.4 tests | Re-run | Pass | ☑ |
| T3.5-09 | Huge increase (edge case) | Increase by 10^12 | Repair | Behaves like deletion; no overflow | ☑ |

**7. Verification Checklist.**
- [x] All tests pass; 20,000-update differential run clean on five seeds.
- [x] Proof P1 completed (deletions and increases) and reviewed.

**8. Milestone Completion Criteria.** Zero mismatches on 100,000 mixed updates in total.

**9. Git Checkpoint.**
```
git status
git add .
git commit -m "feat(repair): weight increases via shared affected-set repair"
git pull --rebase origin phase-3-repair
git push origin phase-3-repair
git tag -a m3.5 -m "Milestone 3.5 done" && git push origin m3.5
```
Do NOT commit: dumps, `.hypothesis/`.

**10. Rollback / Recovery.** R1 with stable tag `m3.4`.

## Phase 3 Completion Checkpoint

| Item | Record |
|---|---|
| Completed milestones | 3.1 to 3.5 |
| Tests passed | 165 / 165 |
| Known issues | None |
| Git commit hash | m3.5 |
| Overall verification | 100,000 mixed updates with zero mismatches; `check_state` clean; P1 proof reviewed |
| **Go/No-Go for Phase 4** | **GO only if** P1 is written and reviewed and the differential runs are clean. Budgets add abort logic; do not add it on top of an unproven repair. |

```
git checkout main && git pull origin main
git merge --no-ff phase-3-repair -m "merge: phase 3 complete"
git push origin main
git tag -a phase-3-done -m "Phase 3 complete" && git push origin phase-3-done
```

---

# Phase 4: Budgeted Repair Controller and Competitive Analysis

Branch: `phase-4-budget`

**Terms used in this phase (all fixed in `SPEC.md`):**
- `F` = work of a complete tree rebuild (Dijkstra plus tight recount), measured at build time.
- `r` = work of a completed repair (SCAN + PUSH + POP + QUEUE, including affected-set identification).
- Budget `B = ceil(c * F)`. A repair aborts as soon as its work exceeds `B`, so the wasted work is at most `B + 1`.
- Certificate and alternative-support work (at most `1 + indeg(v)`) is incurred by *every* strategy, so it is added equally to the online cost and to the offline optimum and cancels in the ratio analysis.

## Milestone 4.1: Abortable repair with overlay and work cap

**Requires:** 3.5

**1. Milestone Name.** Repair that can be abandoned at any operation without leaving a trace.

**2. Objective.** Make the sole-tight-edge repair (identification plus recompute) interruptible by a work cap, with abort costing nothing beyond the work already counted.

**3. Tasks to Complete.**
- [x] `Overlay` object: copy-on-write dictionaries for `dist`, `parent`, `tight`, `children` sitting on top of `SPTState`; reads check the overlay first, writes go only to the overlay.
- [x] Refactor 3.3 and 3.4 to read and write through the overlay.
- [x] `BudgetExceeded` exception; the repair checks `work_since_start > budget` after each charged operation.
- [x] `overlay.commit()` applies all entries to the base state; abort simply discards the overlay.
- [x] `repair(..., budget)` where `budget=None` means unlimited.

**4. Files / Modules Affected.** Modified: `src/graphpulse/repair.py`, `src/graphpulse/opcount.py` (`BudgetExceeded`). New: `tests/test_overlay_budget.py`.

**5. Implementation Guidance.** Copy `children[x]` sets on first write. This refactor changes a proven feature, so first run the full differential suite on the old code, then re-run it after. The graph update has already been applied when a repair aborts; abort discards only the SPT-state changes, and the caller (4.2) then rebuilds. The budget compares against the repair's own counter delta, not the global counter.

**6. Test Cases.**

| Test Case ID | Test Scenario | Preconditions | Steps | Expected Result | Status |
|---|---|---|---|---|---|
| T4.1-01 | Unlimited budget equals old behavior (regression) | Harness | 20,000 mixed updates, `budget=None` | Zero mismatches | ✅ |
| T4.1-02 | Zero budget (edge case) | Sole-tight update | `budget=0` | `BudgetExceeded`; state deep-equals snapshot | ✅ |
| T4.1-03 | Boundary: exactly enough (edge case) | Dry run gives needed work `W` | `budget=W` | Succeeds | ✅ |
| T4.1-04 | Boundary: one short (edge case) | Same case | `budget=W-1` | `BudgetExceeded`; state unchanged | ✅ |
| T4.1-05 | Abort during identification (failure handling) | Large affected set | Budget at 10 percent of `W` | Abort; state unchanged | ✅ |
| T4.1-06 | Abort during recompute (failure handling) | Same | Budget at 80 percent of `W` | Abort; state unchanged | ✅ |
| T4.1-07 | Correct after abort (integration) | After T4.1-05 | Rebuild, then `check_state` and compare with Dijkstra | Correct | ✅ |
| T4.1-08 | Overlay isolation (validation) | Mid-repair | Inspect base state | Base untouched until commit | ✅ |
| T4.1-09 | Overlay equals in-place (property) | Hypothesis, 300 cases | Repair via overlay vs previous in-place version kept as a test reference | Identical resulting state | ✅ |
| T4.1-10 | Work not inflated (validation) | Same update, budget unlimited | Compare counter to pre-refactor value | Equal or within the documented per-write constant | ✅ |

**7. Verification Checklist.**
- [x] All ten tests pass; every Phase 3 test still passes.
- [x] Abort tested at 10 different budget fractions per update on 3 families with no state leak.

**8. Milestone Completion Criteria.** Deep-equality of state after every abort; zero mismatches with unlimited budget.

**9. Git Checkpoint.**
```
git checkout -b phase-4-budget
git status
git add .
git commit -m "feat(repair): overlay-based abortable repair with operation budget"
git pull --rebase origin phase-4-budget
git push -u origin phase-4-budget
git tag -a m4.1 -m "Milestone 4.1 done" && git push origin m4.1
```
Do NOT commit: reproducer dumps, `.hypothesis/`.

**10. Rollback / Recovery.** R1 with stable tag `m3.5` (the last fully proven repair without overlays).

## Milestone 4.2: Budgeted controller

**Requires:** 4.1

**1. Milestone Name.** `BudgetedMaintainer(g, src, c, f_mode)`.

**2. Objective.** The system's decision rule: certificate first, then repair under budget, else full rebuild.

**3. Tasks to Complete.**
- [x] Order of decisions per update: certificate (3.2) → alternative support (3.2) → budgeted repair (4.1) → rebuild on `BudgetExceeded`.
- [x] `B = ceil(c * F)` where `F` is the work of the most recent full build of that tree (`f_mode="last"`, the deployable mode).
- [x] `f_mode="oracle"` (analysis only): before the update, measure the true rebuild work `F_true` on a scratch copy using a scratch counter (not charged) so the theory can be checked exactly.
- [x] After every rebuild, update `F`.
- [x] Per-update `UpdateStats`: `strategy` in {`cert`, `alt`, `repair`, `fallback`}, `repair_work`, `fallback_work`, `affected_size`, `budget`.
- [x] Internal errors other than `BudgetExceeded` must propagate (never be swallowed).
- [x] Optional `verify=True` runs `check_state` after every update (tests only).

**4. Files / Modules Affected.** New: `src/graphpulse/controller.py`, `tests/test_controller.py`.

**5. Implementation Guidance.** `f_mode="last"` is stale by design: `F` was measured on the graph before this update. That is acceptable, but the theory tests use `oracle` mode and the report shows how much the stale mode deviates. Validate `c` at construction (`c >= 0`, numeric). With `c = 0` every sole-tight repair aborts immediately, so the controller degenerates to "certificates plus rebuild"; with `c = inf` it never falls back.

**6. Test Cases.**

| Test Case ID | Test Scenario | Preconditions | Steps | Expected Result | Status |
|---|---|---|---|---|---|
| T4.2-01 | Correctness across budgets (regression) | Harness | 5000 mixed updates, 3 families, `c` in {0.25, 1, 4} | Zero mismatches | ✅ |
| T4.2-02 | `c = 0` (edge case) | Sole-tight updates | Run | Every one is `fallback`; certificates and alt still succeed | ✅ |
| T4.2-03 | `c = inf` (edge case) | Adversarial comb | Run | Never `fallback`; equals repair-always | ✅ |
| T4.2-04 | Per-update work bound (validation) | Oracle mode, adversarial comb, `c=1` | Compare | `repair_work + fallback_work <= (1 + c) * F_true + 1` (plus certificate work) | ✅ |
| T4.2-05 | Same bound on random workloads (validation) | Oracle mode, 3 families | Check every update | Bound holds for all updates | ✅ |
| T4.2-06 | F refresh (positive) | Force a fallback | Read `F` before and after | `F` equals the rebuild work just performed | ✅ |
| T4.2-07 | Invalid `c` (negative) | None | `c=-1`, `c="a"`, `c=None` | `ValueError` or `TypeError` | ✅ |
| T4.2-08 | Stats consistency (validation) | Any run | Sum strategy counts | Equals number of updates | ✅ |
| T4.2-09 | Injected internal fault (failure handling) | Repair patched to raise `RuntimeError` | Run | Error propagates; not treated as a fallback | ✅ |
| T4.2-10 | Verify mode (integration) | `verify=True` | 1000 updates | `check_state` passes after each | ✅ |
| T4.2-11 | Degenerate graph (edge case) | `n=1`, `F` small | Update attempts | No crash; budget 0 handled | ✅ |
| T4.2-12 | Regression | Phases 1 to 3 and 4.1 | Full suite | All pass | ✅ |

**7. Verification Checklist.**
- [x] All twelve tests pass.
- [x] Table of strategy shares (cert / alt / repair / fallback) recorded for 3 families at `c = 1` (informational; goes into the results section of the report).

**8. Milestone Completion Criteria.** Zero mismatches; per-update work bound holds on every update in oracle mode.

**9. Git Checkpoint.**
```
git status
git add .
git commit -m "feat(controller): budgeted repair with certificate-first decision order and fallback"
git pull --rebase origin phase-4-budget
git push origin phase-4-budget
git tag -a m4.2 -m "Milestone 4.2 done" && git push origin m4.2
```
Do NOT commit: strategy-share tables as raw CSV outputs (keep only the summarized table in `docs/`).

**10. Rollback / Recovery.** R1 with stable tag `m4.1`.

## Milestone 4.3: Competitive-ratio analysis and randomized budget

**Requires:** 4.2

**1. Milestone Name.** Proven and measured competitive ratio, plus a randomized budget.

**2. Objective.** Turn the budget rule into a theorem with matching experiments. This is the core theory contribution of the first half.

**3. Tasks to Complete.**
- [ ] `docs/proofs/P2_work_bound.md`: per-update bound under the cost model, including the abort slack of 1.
- [ ] `docs/proofs/P3_competitive_ratio.md` containing the two results below.
- [ ] `RandomizedBudget`: draw `x = ln(1 + (e - 1) * U)` with `U` uniform in `[0,1)`, and use budget `x * F` for that update, with a seeded RNG.
- [ ] `analysis.py`: `measure(make_graph, updates, c, mode)` returns total online cost and total offline optimum `sum(min(r_t, F_t))` for the same sequence (obtain `r_t` by a dry run with unlimited budget on a scratch copy).

**4. Files / Modules Affected.** New: `docs/proofs/P2_work_bound.md`, `docs/proofs/P3_competitive_ratio.md`, `src/graphpulse/analysis.py`. Modified: `src/graphpulse/controller.py`. New: `tests/test_competitive.py`.

**5. Implementation Guidance.** The two results to prove (and then test):
- *Deterministic budget `c`:* offline optimum is `min(r, F)`. If `r <= cF` the online cost is `r` (ratio 1). Otherwise it is `cF + F`. The worst case is `r` just above `cF`, giving ratio `(1 + c) / min(c, 1)`, that is `max(1 + c, (1 + c) / c)`. It is minimized at `c = 1`, where it equals 2.
- *Randomized budget:* with density `e^x / (e - 1)` on `[0,1]`, the expected online cost is `(e / (e - 1)) * min(r, F)` for **every** `r` (verify the integral in the proof), so the expected ratio is `e / (e - 1)`, about 1.582.
The ratio holds per update, hence for any sequence, with an additive slack of 1 per update. Use oracle mode for the exact check; report the stale-`F` deviation as an observation, not a pass/fail.

**6. Test Cases.**

| Test Case ID | Test Scenario | Preconditions | Steps | Expected Result | Status |
|---|---|---|---|---|---|
| T4.3-01 | Deterministic worst case (positive) | Simulated cost pairs, `r = cF + 1` | `c` in {0.25, 0.5, 1, 2, 4} | Ratio equals `max(1+c, (1+c)/c)` within 1 percent | ☐ |
| T4.3-02 | Best deterministic budget (validation) | Sweep `c` from 0.1 to 5 | Compute worst-case ratio | Minimum at `c = 1`, value 2 | ☐ |
| T4.3-03 | Sampler distribution (validation) | 200,000 samples of `x` | Mean of `x` | About `1/(e-1) = 0.582` within 0.01; all `x` in `[0,1)` | ☐ |
| T4.3-04 | Randomized expected ratio (validation) | Simulated `r/F` in {0.1, 0.5, 1, 2} | Average online over many draws | Expected ratio about 1.582 within 2 percent for each | ☐ |
| T4.3-05 | Seed reproducibility (positive) | Same seed | Two runs | Identical budget sequences | ☐ |
| T4.3-06 | Real maintainer, oracle mode (integration) | 3 families including adversarial comb | `measure` for each `c` | `online <= ratio(c) * OPT + T` (T = updates) | ☐ |
| T4.3-07 | Adversarial tightness (integration) | Comb, `c = 1` | Choose updates where `r` slightly exceeds `F` | Measured ratio close to 2 | ☐ |
| T4.3-08 | Randomized on real workloads (integration) | 3 families | Run with `RandomizedBudget` | Correctness intact (harness clean); ratio at most about 1.58 plus slack | ☐ |
| T4.3-09 | Stale-F deviation recorded (validation) | `f_mode="last"` vs `"oracle"` | Compare | Deviation reported in a table; no assertion | ☐ |
| T4.3-10 | Invalid `analysis` input (negative) | Empty or invalid update list | `measure` | Clear error or zero totals handled | ☐ |

**7. Verification Checklist.**
- [ ] All ten tests pass; every earlier test passes.
- [ ] P2 and P3 written, each read line by line by two members other than the author.
- [ ] The integral in the randomized proof was checked by hand: `∫ (1+x) e^x/(e-1) dx = e/(e-1)`.

**8. Milestone Completion Criteria.** Proofs reviewed; measured ratios never exceed the proven bounds.

**9. Git Checkpoint.**
```
git status
git add .
git commit -m "feat(analysis): proven competitive ratio and randomized budget with measurements"
git pull --rebase origin phase-4-budget
git push origin phase-4-budget
git tag -a m4.3 -m "Milestone 4.3 done" && git push origin m4.3
```
Do NOT commit: raw measurement dumps, plots generated under `experiments/output/`.

**10. Rollback / Recovery.** R1 with stable tag `m4.2`.

## Phase 4 Completion Checkpoint (this is the 50% checkpoint)

| Item | Record |
|---|---|
| Completed milestones | 4.1, 4.2, 4.3 |
| Tests passed | ___ / ___ |
| Known issues | ___ |
| Git commit hash | ___ |
| Overall verification | Zero mismatches for every budget; measured competitive ratios within proven bounds; P1, P2, P3 reviewed |
| **Go/No-Go for the second half** | **GO only if** the 50% Release Checklist below is fully ticked. The routing layer builds on these trees, so an unproven core would invalidate everything after it. |

```
git checkout main && git pull origin main
git merge --no-ff phase-4-budget -m "merge: phase 4 complete (50 percent checkpoint)"
git push origin main
git tag -a v0.5-half -m "50 percent checkpoint: budgeted single-source repair" && git push origin v0.5-half
```

---

# 50% Release Checklist

**Functionality**
- [ ] Deletions and weight increases are repaired exactly; certificate, alternative-support, repair and fallback paths all exercised.
- [ ] Budget controller works in `last` and `oracle` modes; randomized budget available.

**Testing**
- [ ] `python -m pytest -q` is fully green on a fresh clone on two machines.
- [ ] At least 100,000 mixed differential updates with zero mismatches (five seeds, three graph families).
- [ ] Every injected bug in the harness self-test is caught.

**Security**
- [ ] No secrets, `.env` or credentials anywhere in `git log -p` (`git log -p | grep -i -E "password|token|secret"` returns nothing).
- [ ] Dependencies pinned in `requirements-dev.txt`; no network calls in the code; no `pickle` or `eval`.

**Performance**
- [ ] Table of operation counts (repair versus rebuild) for a 100x100 grid and the adversarial comb saved in `docs/`.
- [ ] Repair work is strictly below `F` on small-affected-set updates and at most `(1 + c) F + 1` on adversarial ones.

**Deployment**
- [ ] `pip install -e .` works from a clean clone; tag `v0.5-half` exists on `main`.

**Documentation**
- [ ] README (install, test, layout), `SPEC.md`, and proofs P1, P2, P3 in `docs/proofs/`.
- [ ] Each milestone tag (`m0.1` to `m4.3`) exists: `git tag --list "m*"`.

**Git repository cleanliness**
- [ ] `git status` clean on `main`; no `.venv`, caches, dumps or output files tracked (`git ls-files | grep -E "\.venv|__pycache__|failures|output"` is empty).
- [ ] No file larger than 1 MB tracked; all phase branches merged into `main`.

---

# What comes in the second 50% (not covered here)

| Phase | Content | Depends on |
|---|---|---|
| 5 | Multi-terminal manager (k+1 trees), per-update touched-tree statistics, terminal distance matrix with infeasibility handling | v0.5-half |
| 6 | Held-Karp TSP, lazy re-solve certificate (skip when no used entry changed), nearest-neighbor and backtracking baselines, NP-hardness reduction write-up | Phase 5 |
| 7 | Real road-network extract loading, benchmark and ablation suite, adversarial tightness experiments | Phases 5 and 6 |
| 8 | Demo, final report, Final Release Checklist | Phase 7 |

Ask for the second-half playbook when the 50% checkpoint tag exists and the checklist above is ticked.
