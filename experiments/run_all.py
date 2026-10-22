"""Run every experiment in dependency order, then the figures, then write MANIFEST.json (Milestone 7.6).

    python -m experiments.run_all --quick     # tiny configs (used by tests); writes to --out
    python -m experiments.run_all             # full run; writes docs/results and docs/figures

Stops on the first failure (including any cross-variant correctness failure) and
writes NO manifest in that case.  The manifest lists every output with its
SHA-256 and the git hash, so any later edit of a table is detectable
(`--verify` re-checks an existing manifest).
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
import time
from pathlib import Path

from experiments import e1_budget, e2_stages, e3_scaling, e4_adversarial, e5_endtoend, make_figures
from experiments.common import RESULTS, ROOT
from experiments.runner import git_short_hash, write_meta

STEPS = [("E1", e1_budget.run), ("E2", e2_stages.run), ("E3", e3_scaling.run), ("E4", e4_adversarial.run),
         ("E5", e5_endtoend.run)]


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def run_all(quick: bool, results: Path, figures: Path, log=print) -> Path:
    outputs: list[Path] = []
    timings: dict[str, float] = {}
    for name, fn in STEPS:
        t0 = time.perf_counter()
        log(f"[run_all] {name} ...")
        outputs += fn(quick=quick, out_dir=results)
        timings[name] = round(time.perf_counter() - t0, 1)
        log(f"[run_all] {name} done in {timings[name]} s")
    t0 = time.perf_counter()
    outputs += make_figures.run(results, figures)
    timings["figures"] = round(time.perf_counter() - t0, 1)
    log(f"[run_all] figures done in {timings['figures']} s")

    base = results.parent if results.name == "results" else results
    manifest = {
        "git_hash": git_short_hash(),
        "mode": "quick" if quick else "full",
        "files": {str(p.relative_to(base)).replace("\\", "/"): sha256(p) for p in sorted(set(outputs))
                  if p.suffix in (".csv", ".md")},
        "figures": {str(p.relative_to(base)).replace("\\", "/"): sha256(p) for p in sorted(set(outputs))
                    if p.suffix in (".png", ".pdf")},
    }
    path = results / "MANIFEST.json"
    path.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    # timings / environment are kept OUT of the hashed manifest so it stays reproducible
    write_meta(results / "run_meta.json", [0, 1, 2, 5], {"mode": manifest["mode"], "step_seconds": timings})
    log(f"[run_all] wrote {path}")
    return path


def verify_manifest(manifest_path: Path) -> list[str]:
    """Return a list of problems (empty when every listed file matches its recorded hash)."""
    m = json.loads(manifest_path.read_text(encoding="utf-8"))
    base = manifest_path.parent.parent if manifest_path.parent.name == "results" else manifest_path.parent
    problems = []
    for group in ("files", "figures"):
        for rel, digest in m[group].items():
            p = base / rel
            if not p.exists():
                problems.append(f"missing: {rel}")
            elif group == "files" and sha256(p) != digest:
                problems.append(f"hash mismatch: {rel}")
    return problems


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--quick", action="store_true")
    ap.add_argument("--out", type=Path, default=None, help="output root (quick mode default: experiments/output/quick)")
    ap.add_argument("--verify", action="store_true", help="only verify docs/results/MANIFEST.json")
    a = ap.parse_args(argv)
    if a.verify:
        probs = verify_manifest(RESULTS / "MANIFEST.json")
        print("\n".join(probs) or "manifest OK")
        return 1 if probs else 0
    if a.quick:
        root = a.out or (ROOT / "experiments" / "output" / "quick")
        results, figures = root / "results", root / "figures"
    else:
        results, figures = (a.out / "results", a.out / "figures") if a.out else (RESULTS, make_figures.FIGURES)
    try:
        run_all(a.quick, results, figures)
    except Exception as exc:                        # fail loudly, no manifest
        print(f"[run_all] FAILED: {type(exc).__name__}: {exc}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
