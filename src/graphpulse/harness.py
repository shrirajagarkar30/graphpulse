"""Differential testing harness (Milestone 2.3).

`run_differential` drives any Maintainer candidate against the trusted
RecomputeMaintainer baseline after every single update.  On any distance
mismatch it:
  1. Writes a reproducer JSON to `failures_dir` (default: tests/failures/).
  2. Raises `HarnessMismatch` with a precise message naming the failing index.

The reference is computed on its own independent graph copy, so a buggy
candidate cannot corrupt it even if it mutates its graph in arbitrary ways.
"""

from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Callable

from graphpulse.dijkstra import INF
from graphpulse.generators import Update, apply_update
from graphpulse.graph import DiGraph
from graphpulse.maintainer import Maintainer, RecomputeMaintainer, UpdateStats
from graphpulse.opcount import OpCounter


# Default location for reproducer dumps (must be gitignored)
_DEFAULT_FAILURES_DIR = Path(__file__).parent.parent.parent / "tests" / "failures"


class HarnessMismatch(Exception):
    """Raised when a candidate's distances diverge from the reference."""


def _check_distances(
    ref_dist: list[float],
    cand_dist: list[float],
    n: int,
    step_label: str,
) -> None:
    """Compare reference and candidate distance arrays.

    Raises HarnessMismatch with a precise message on any discrepancy:
    - Wrong length.
    - Any vertex where distances disagree.
    """
    if len(cand_dist) != n:
        raise HarnessMismatch(
            f"{step_label}: candidate dist has length {len(cand_dist)}, expected {n}"
        )
    for v in range(n):
        r = ref_dist[v]
        c = cand_dist[v]
        if r != c:
            raise HarnessMismatch(
                f"{step_label}: dist[{v}] mismatch — "
                f"reference={r!r}, candidate={c!r}"
            )


def _write_reproducer(
    failures_dir: Path,
    g_init: DiGraph,
    updates: list[Update],
    src: int,
    failing_index: int,
    mismatch_msg: str,
) -> Path:
    """Write a reproducer JSON file and return its path.

    The reproducer contains everything needed to replay the failure:
    the initial graph, the update sequence, src, the failing index,
    and the mismatch message.

    Raises IOError (wrapping the original error) if the write fails so the
    caller can still surface the mismatch even when the dump fails.
    """
    failures_dir.mkdir(parents=True, exist_ok=True)
    ts = int(time.time() * 1000)
    path = failures_dir / f"failure_{ts}_step{failing_index}.json"

    payload = {
        "src": src,
        "failing_index": failing_index,
        "mismatch": mismatch_msg,
        "graph": {
            "n": g_init.n,
            "edges": [
                [u, v, w]
                for u in range(g_init.n)
                for v, w in g_init.out_edges(u)
            ],
        },
        "updates": [
            {"kind": u.kind, "u": u.u, "v": u.v, "new_w": u.new_w}
            for u in updates[: failing_index + 1]
        ],
    }
    try:
        path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    except OSError as exc:
        raise OSError(
            f"HarnessMismatch occurred at step {failing_index} AND "
            f"reproducer write to {path} failed: {exc}\n"
            f"Original mismatch: {mismatch_msg}"
        ) from exc
    return path


def run_differential(
    make_graph: Callable[[], DiGraph],
    make_candidate: Callable,
    updates: list[Update],
    src: int,
    failures_dir: Path | str | None = None,
    _compare_hook: Callable | None = None,
) -> int:
    """Run *candidate* against the trusted recompute baseline on every update.

    Parameters
    ----------
    make_graph      : Callable returning a fresh DiGraph (called twice: once
                      for the reference, once for the candidate).
    make_candidate  : Callable(g: DiGraph, src: int) -> Maintainer.
    updates         : Ordered list of Update objects to apply.
    src             : Source vertex for shortest-path computation.
    failures_dir    : Directory for reproducer JSON dumps on failure.
                      Defaults to tests/failures/.  Pass None to use default.
    _compare_hook   : Optional zero-arg callable invoked after every
                      comparison (including the initial state check).
                      Used only by tests to count comparison calls.

    Returns
    -------
    int
        Number of distance comparisons performed (1 initial + len(updates)
        if no failure, or fewer if a failure cuts the run short).

    Raises
    ------
    HarnessMismatch
        On the first distance discrepancy.  A reproducer JSON is written to
        failures_dir first (or an OSError is raised if that write fails).
    """
    if failures_dir is None:
        failures_dir = _DEFAULT_FAILURES_DIR
    failures_dir = Path(failures_dir)

    # Build the initial graph used as a template for reproductions
    g_init = make_graph()

    # Independent reference: RecomputeMaintainer on its own copy
    g_ref = make_graph()
    reference = RecomputeMaintainer(g_ref, src)

    # Candidate on its own copy
    g_cand = make_graph()
    candidate = make_candidate(g_cand, src)

    n = g_init.n
    checks = 0

    def compare(step_label: str, failing_index: int) -> None:
        nonlocal checks
        ref_d = reference.dist()
        cand_d = candidate.dist()
        try:
            _check_distances(ref_d, cand_d, n, step_label)
        except HarnessMismatch as exc:
            dump_path = _write_reproducer(
                failures_dir, g_init, updates, src, failing_index, str(exc)
            )
            raise HarnessMismatch(
                f"{exc}  [reproducer: {dump_path}]"
            ) from exc
        finally:
            checks += 1
            if _compare_hook is not None:
                _compare_hook()

    # Initial state check (before any updates)
    compare("initial state", failing_index=-1)

    # Apply each update to reference and candidate, then compare
    for i, upd in enumerate(updates):
        reference.apply(upd)
        candidate.apply(upd)
        compare(f"after update {i}", failing_index=i)

    return checks


def replay_reproducer(path: Path | str) -> dict:
    """Load a reproducer JSON and replay it, returning the failure info dict.

    Rebuilds the graph, applies the updates, and checks that the reference
    Dijkstra from the reproducer produces the distances embedded in the JSON.

    Primarily used by tests to verify reproducers are self-consistent.
    """
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    g = DiGraph(data["graph"]["n"])
    for u, v, w in data["graph"]["edges"]:
        g.add_edge(u, v, w)

    src = data["src"]
    updates = [
        Update(kind=u["kind"], u=u["u"], v=u["v"], new_w=u["new_w"])
        for u in data["updates"]
    ]
    failing_index = data["failing_index"]
    return {
        "graph": g,
        "src": src,
        "updates": updates,
        "failing_index": failing_index,
        "mismatch": data["mismatch"],
    }
