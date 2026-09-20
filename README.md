# GraphPulse-R

**Certificate-Driven, Budgeted Reoptimization for Dynamic Delivery Routing**

Semester-long course project for *Design and Analysis of Algorithms (DAA)*, Computer Engineering, VIT (syllabus AY 2026-27).

---

## 1. Prerequisites

- Python 3.11 or newer (verify with `python --version`)
- Git

---

## 2. Setup & Environment

### Create and activate virtual environment

**Windows PowerShell:**
```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
```

**Linux / macOS:**
```bash
python -m venv .venv
source .venv/bin/activate
```

### Install dependencies

Install the package in editable mode alongside pinned developer dependencies:
```bash
pip install -e . -r requirements-dev.txt
```

---

## 3. Running Tests

### Quick test loop (skips slow property tests)
```bash
python -m pytest -q -m "not slow"
```

### Full test suite (required before every commit/push)
```bash
python -m pytest -q
```

### Smoke check import & version
```bash
python -c "import graphpulse; print(graphpulse.__version__)"
```

---

## 4. Repository Layout

```
graphpulse/
├── pyproject.toml             # Build configuration and tool settings
├── requirements-dev.txt       # Pinned developer dependencies (pytest, hypothesis, networkx)
├── README.md                  # Setup and execution instructions
├── .gitignore                 # Standard Python, test, and environment ignore rules
├── docs/
│   ├── AGENTS.md              # Project constitution, rules, and global conventions
│   ├── SPEC.md                # Formal model, cost model, update model
│   ├── PLAYBOOK.md            # Step-by-step milestone execution guide
│   └── proofs/                # Mathematical proofs (correctness, bounds, competitive ratio)
├── src/graphpulse/            # Core source code (src-layout)
│   └── __init__.py
├── tests/                     # Unit, property, and integration test suites
│   └── test_smoke.py
└── experiments/               # Benchmarking scripts and experimental drivers
```
