# Claims register

The single list of statements we are willing to defend in front of a reviewer. **Type**: `proved` (a proof file), `measured` (a test or a committed seeded table), `design` (a property of the implementation, worded as such, not as a result). **Status**: `OK`, `REJECTED` (a claim found in earlier text and removed, kept here so it is not reintroduced), `PENDING` (needs an action by the team). The git hash is the commit or tag at which the source was produced.

Experiment tables were produced by `python -m experiments.run_all` at commit `fde3885` (see `docs/results/run_meta.json`); every table's SHA-256 is in `docs/results/MANIFEST.json`.

| Claim | Type | Source | Git hash | Status |
|---|---|---|---|---|
| In oracle-F mode, per-update work is at most (1+c)F + 2 | proved | `docs/proofs/P2_work_bound.md` (reviewer sign-off pending) | m4.3 | OK |
| Competitive ratio against per-update OPT = min(r,F) is max(1+c, (1+c)/c), uniquely minimised at c = 1 where it equals 2 | proved | `docs/proofs/P3_competitive_ratio.md` (reviewer sign-off pending) | m4.3 | OK |
| A randomized budget has expected ratio e/(e-1) against min(r,F) | proved | `docs/proofs/P3_competitive_ratio.md` | m4.3 | OK |
| The tight-edge subgraph is acyclic; a vertex with another tight in-edge keeps its distance | proved | `docs/proofs/P1_repair_correctness.md` | m3.1 | OK |
| The directed tour decision problem is NP-complete (reduction from directed Hamiltonian cycle) | proved | `docs/proofs/P4_np_hardness.md` (reviewer sign-off pending) | m6.6 | OK |
| If no matrix entry used by the incumbent tour changed since the last exact solve, the tour is still optimal | proved | `docs/proofs/P5_lazy_certificate.md` (reviewer sign-off pending) | m6.6 | OK |
| An epsilon-keep is (1+eps)-optimal provided the stored lower bound is never raised | proved | `docs/proofs/P5_lazy_certificate.md` | m6.6 | OK |
| The proven bounds hold for oracle F; the deployable last-F mode has no theorem | design | `docs/TECHNICAL_SOURCE_OF_TRUTH.md` | 0e02495 | OK |
| The shortest-path layer matched a recompute-from-scratch oracle, with the full structural checker after every update, on 100,000 mixed updates (4 families, 5 seeds) | measured | `tests/test_differential_scale.py` | 799c610 | OK |
| The multi-tree engine's terminal matrix and all trees matched the oracle on 60,000 updates (every update on the small grid, every 50th on large graphs) | measured | `tests/test_multitree_slow.py` | 799c610 | OK |
| Held-Karp performs exactly k(k-1)2^(k-2) recurrence transitions for k >= 2, and agrees with brute force and branch-and-bound | measured | `tests/test_heldkarp.py` | 799c610 | OK |
| The routing pipeline's tour cost equals the recompute-everything reference after every update (grid, random sparse, hub-and-spoke; exact and epsilon mode) | measured | `tests/test_pipeline.py` | 799c610 | OK |
| In the budget sweep (all rows) no deterministic budget exceeded its proven ratio plus the additive slack | measured | `docs/results/e1_budget.csv` | fde3885 | OK |
| For budgets strictly between 0 and infinity the measured ratio was far below the worst case on the swept workloads; for c = 0 it was very large | measured | `docs/results/e1_budget.md` | fde3885 | OK |
| A budget c >= 2 never triggered a fallback in the budget sweep | measured | `docs/results/e1_budget.csv` | fde3885 | OK |
| The randomized budget's measured mean ratio is close to e/(e-1) (single runs vary) | measured | `docs/results/e1_budget.csv` | fde3885 | OK |
| The adversarial sweep comes within a few percent of rho(c) at c = 0.5 and attains rho(c) at c = 1 up to the additive slack | measured | `docs/results/e4_summary.csv` | fde3885 | OK |
| The adversarial sweep does not demonstrate the bound for c = 2 (repair never exceeds about 1.75 times rebuild on this family) | measured | `docs/results/e4_adversarial.csv` | fde3885 | OK |
| On the benign grid workload repair-only used slightly fewer tree operations than the budgeted controller (a loss reported, not hidden) | measured | `docs/results/e2_ablation.csv` | fde3885 | OK |
| On the grid workload the lazy tour certificate removed most Held-Karp transitions in every variant | measured | `docs/results/e2_ablation.csv` | fde3885 | OK |
| Per-update operations of the budgeted controller grew sublinearly in n while full recomputation grew about linearly (rebuild baseline sampled on the two largest grids) | measured | `docs/results/e3_slopes.csv` | fde3885 | OK |
| End to end on synthetic graphs the pipeline saved most tree operations and most Held-Karp transitions versus recompute-everything | measured | `docs/results/e5_endtoend.csv` | fde3885 | OK |
| First-half benign-workload table: certificate hit rates and work savings for four families, one seed | measured | `docs/EMPIRICAL_EVALUATION.md` | b4fece1 | OK |
| Repair writes to an overlay, so an aborted repair leaves the state unchanged | design | `src/graphpulse/repair.py` | m4.1 | OK |
| The dashboard server binds to 127.0.0.1 by default, rejects bodies over 1 MiB, confines static files to web/, and serialises state access | design | `src/graphpulse/server.py` | fde3885 | OK |
| The dashboard passed an in-browser regression (133 checks) across all pages in the light and dark themes, after one bug was fixed | measured | `tests/ui/smoke.js` | fde3885 | OK |
| The algorithms use only the standard library | design | `pyproject.toml` | 0e02495 | OK |
| "(c+1)-competitive" (work bound confused with competitive ratio) | design | `docs/SPEC.md` | 42f9258 | REJECTED |
| "70% to 94% certificate hit rate" and "65% to 92% operation savings" as universal claims | measured | `docs/EMPIRICAL_EVALUATION.md` | 2606a8c | REJECTED |
| "GraphPulse-R eliminates over 95-99% of operations" (universal) | measured | `docs/EMPIRICAL_EVALUATION.md` | 2606a8c | REJECTED |
| Any result on real road networks | measured | `data/README.md` | fde3885 | REJECTED |
| A claim of a new algorithm (beyond integration, competitive analysis and certificates) | design | `docs/RELATED_WORK.md` | fde3885 | REJECTED |
| Literature check: budgeted repair with rebuild fallback and the lazy tour certificate are not already published | design | `docs/RELATED_WORK.md` | fde3885 | PENDING |
| Independent reviewer sign-off of proofs P1-P5 by two team members | proved | `docs/proofs/P5_lazy_certificate.md` | m6.6 | PENDING |
