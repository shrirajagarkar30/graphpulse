# Reproducing every table, figure and test result

Reproduction means **identical operation counts and tables**. Wall-clock values differ between machines and are secondary everywhere.

## 1. Environment

* Python ≥ 3.11 (developed and tested on **3.14.7**, Windows 11).
* Algorithms use the standard library only. Dev dependencies are pinned in `requirements-dev.txt`
  (`pytest`, `hypothesis`, `networkx` for tests; `pandas`, `matplotlib` for result tables and figures).

```bash
git clone https://github.com/shrirajagarkar30/graphpulse.git
cd graphpulse
python -m venv .venv
# Windows PowerShell: .venv\Scripts\Activate.ps1      Linux/macOS: source .venv/bin/activate
pip install -e . -r requirements-dev.txt
```

(`pip install -e .` is required: tests import the installed package.)

## 2. Tests

```bash
python -m pytest -q -m "not slow"     # fast loop
python -m pytest -q -m slow           # long differential runs (about 30 minutes on the reference machine)
python -m pytest -q                   # everything (run before every push)
```

Do not rely on hard-coded test counts in documents; run the commands above.

## 3. Experiments and figures

```bash
python -m experiments.run_all --quick     # tiny configs (~15 s); writes to experiments/output/quick (git-ignored)
python -m experiments.run_all             # full run; writes docs/results/*.csv|md and docs/figures/*
python -m experiments.run_all --verify    # re-check docs/results/MANIFEST.json (SHA-256 of every table)
```

Individual experiments: `python -m experiments.e1_budget`, `e2_stages`, `e3_scaling`, `e4_adversarial`, `e5_endtoend`, then `python -m experiments.make_figures`.

All runs are seeded (seeds listed in `docs/results/run_meta.json`). Every variant of every experiment runs on the identical update sequence and is cross-checked against an exact recompute-everything reference after every update; a disagreement aborts the run and no manifest is written.

### Recorded runtimes (reference machine: Windows 11, Intel i5-12450H, 15.7 GB RAM)

See `docs/results/run_meta.json` (`step_seconds`) for the full run; the quick run takes about 13 s.

## 4. Seeded benchmark of the first half

```bash
python experiments/bench_empirical_claims.py   # regenerates docs/EMPIRICAL_EVALUATION.md; `git diff` must be empty
```

## 5. Dashboard and demo

The dashboard UI regression (`tests/ui/smoke.js`) needs a browser; its header explains how to run it against a running dashboard.

```bash
python demo.py                    # console demo
python run_ui.py --port 8000      # dashboard on http://127.0.0.1:8000
```

## 6. Data

No real road dataset is used (see `data/README.md`). `tests/data/tiny.gr` is the only committed `.gr` file.

## 7. Known deviations from the playbook (all recorded in `docs/PROJECT_LOGBOOK.md`)

* E1 uses T = 2,000 uniform updates (playbook: 5,000) and T = 500 tree-edge updates, because the oracle-F measurement rebuilds the tree several times per sole-tight update; counts are recorded in the CSV.
* E3 measures `rebuild_always` on a prefix of the updates for the largest grids (column `T_rebuild`).
* E5 uses T = 1,000 updates and synthetic families only.
