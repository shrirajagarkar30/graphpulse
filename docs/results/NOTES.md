# Notes on the committed results

Every table in this directory is produced by `python -m experiments.run_all` (seeded; see `run_meta.json` for the seeds and the per-step runtimes of the run that produced these files, and `MANIFEST.json` for SHA-256 of every table). Nothing here is edited by hand.

## What was run (deviations from the playbook, stated up front)

| Item | Playbook | Run here | Why |
|---|---|---|---|
| E1 uniform updates | T = 5,000 | T = 2,000 | oracle-F measurement rebuilds the tree several times per sole-tight update; counts are recorded per row (`T_actual`) |
| E1 families | includes a road subgraph | grid, random_sparse, hub_spoke, comb only | **no real road data was used** (`data/README.md`) |
| E3 rebuild baseline | every update | first `T_rebuild` updates for 80x80 and 160x160 grids (100 and 20) | rebuilding nine trees on 25,600 vertices after each of 1,000 updates is very slow in pure Python; the per-update mean is a sampled estimate |
| E5 | 2,000 updates, grid + road subgraph | 1,000 updates, grid + random_sparse | time; no road data |
| Update counts | "N updates" | `T_actual` column | the update generator exhausts its edge pool under deletion-heavy settings (e.g. deletion share 0.8, or near-source updates), so some rows have fewer updates than requested |

## Results that are unfavourable or limiting (reported, not hidden)

1. **Repair-only beats the budgeted controller on benign workloads.** In `e2_ablation.csv` (grid, uniform updates, k=8, exact tours) `repair_always` (c = inf) used fewer tree operations than `gp` (c = 1), because `gp` occasionally aborts a repair and then rebuilds, paying for both. The budget buys a worst-case guarantee, not an average-case gain on these inputs.
2. **`cert_only` (c = 0) is far worse** than any repairing variant (many fallbacks); its measured ratio in E1 is unbounded in theory and was very large in practice.
3. **The adversarial sweep does not demonstrate the bound for c = 2.** On `partial_comb` the repair cost never exceeded about 1.75 times the rebuild cost (`r_over_F` in `e4_adversarial.csv`), so the trigger condition r > 2F is never met; the maximum measured ratio for c = 2 stays well below rho(2). Tightness *is* demonstrated for c = 0.5 (within a few percent of rho) and c = 1 (equal to rho up to the additive slack).
4. **Near-source updates disconnect the depot's neighbourhood** (many `infeasible` rows in `e2_skip.csv`, and short update sequences), so the skip rate for that mode excludes infeasible updates and is not comparable with the other modes.
5. **E3's rebuild baseline is sampled** for the two largest grids (see above).
6. **Synthetic graphs only.** No claim about real road networks is supported.

## How to read the tables

* Work is SCAN + PUSH + POP + QUEUE operations; Held-Karp is reported separately as DP transitions (`hk_transitions`).
* `rebuild_always` rebuilds every tree with the full tight-counter build (cost F), which is what the maintained variants must also keep consistent.
* All variants in a row group processed the identical update sequence (`updates_sha`) and produced identical terminal matrices (`matrix_sha`); in epsilon mode tour costs are within the stated factor of the exact reference.
