# GraphPulse-R

**Certificate-driven, budgeted reoptimization for dynamic delivery routing**

When roads close or slow down, GraphPulse-R keeps exact shortest-path distances, the terminal distance matrix and a minimum-cost delivery tour correct by *repairing* the previous solution instead of recomputing everything. It decides repair-versus-recompute with a provable work budget, and skips the exact tour solve when a certificate proves the old tour is still optimal. Cost is measured in machine-independent operation counts.

> Honest claim: every ingredient has prior art. The contribution is the integration, the competitive analysis and the certificates, evaluated end to end. See `docs/TECHNICAL_SOURCE_OF_TRUTH.md` for what is proved, validated and measured, and `docs/CLAIMS.md` for the claims register.

Course project for *Design and Analysis of Algorithms* (VIT, AY 2026-27).

## Install

Python 3.11 or newer.

```bash
python -m venv .venv
# Windows PowerShell: .venv\Scripts\Activate.ps1      Linux/macOS: source .venv/bin/activate
pip install -e . -r requirements-dev.txt
```

The algorithms use only the standard library. `requirements-dev.txt` (all pinned) adds `pytest`, `hypothesis`, `networkx` for tests and `pandas`, `matplotlib` for result tables and figures.

## Run

```bash
python -m pytest -q -m "not slow"          # fast tests
python -m pytest -q                        # everything (includes long differential runs)
python demo.py                             # console demo
python run_ui.py --port 8000               # dashboard at http://127.0.0.1:8000 (local-only by default)
python -m experiments.run_all --quick      # tiny experiment run (seconds)
python -m experiments.run_all              # full experiments -> docs/results, docs/figures
python -m experiments.run_all --verify     # check docs/results/MANIFEST.json
```

Full instructions and expected runtimes: `docs/REPRODUCE.md`.

## What is implemented

| Layer | Modules | Notes |
|---|---|---|
| Shortest-path trees | `graph`, `dijkstra`, `spt`, `repair`, `controller` | certificate, alternative support, budgeted repair with free abort, rebuild fallback, randomized budget |
| Multi-terminal | `terminals` | one tree per terminal on a shared graph; terminal matrix with monotonicity guard |
| Routing | `tour`, `tourcert`, `pipeline` | brute force, Held-Karp (k <= 18), nearest neighbour, branch-and-bound; lazy tour certificate (+ epsilon mode); end-to-end `RoutingPipeline` |
| Data | `roadnet` | DIMACS `.gr` loader, SCC extraction, subgraph sampling (no real dataset is bundled or used; see `data/README.md`) |
| Experiments | `experiments/` | seeded runner with cross-variant checks, experiments E1-E5, figures, one-command `run_all` |
| Dashboard | `server`, `web/` | local HTTP API (`docs/API.md`) and web UI |

## Repository map

```
src/graphpulse/      core library (standard library only)
tests/               unit, property, differential and integration tests
experiments/         runner, E1-E5, figures, run_all, table generators
docs/                SPEC, proofs (P1-P5), technical source of truth, logbook, claims, API, reproduction
docs/results/        committed result tables + MANIFEST.json (SHA-256)
docs/figures/        generated figures
paper/               IEEE paper source (tables generated from docs/results)
web/                 dashboard frontend
data/README.md       how to add a real road network (none is used)
```

## Status and limits

* Proofs P1-P5 are drafted; **independent reviewer sign-off is pending** (each proof file says so).
* The work bound and competitive ratio are proved for an oracle estimate of F; the deployable mode that reuses the last F has no theorem.
* Updates are increase-only (deletions and weight increases). Pure Python, small graphs, k <= 18, synthetic data only.
* The paper source is in `paper/`; it has not been compiled in this environment (no LaTeX installed) and its bibliography details still need verification.

## License

MIT, see `LICENSE` (choose differently if your course policy requires it).
