"""Milestone 5.4: multi-tree integration hardening (T5.4-01 .. T5.4-07)."""

from __future__ import annotations

import math
import random
import subprocess
import sys
from pathlib import Path

import pytest

from graphpulse.dijkstra import INF, dijkstra
from graphpulse.generators import Update, comb_adversarial, grid, random_sparse, random_updates
from graphpulse.opcount import OpCounter
from graphpulse.spt import SPTState
from graphpulse.terminals import MultiTreeManager, TerminalMatrix
from graphpulse.verify import check_state


def _terms(g, k, seed=0):
    return [0] + random.Random(seed).sample(range(1, g.n), k)


def _run(g, k, count, p_delete, every, seed, check_trees):
    """Run `count` updates; compare the matrix with the oracle every `every`-th update."""
    terms = _terms(g, k, seed)
    mgr = MultiTreeManager(g, terms)
    mat = TerminalMatrix(mgr)
    ups = random_updates(g, count, seed=seed, p_delete=p_delete)
    assert len(ups) == count, f"only {len(ups)} updates generated"
    for i, u in enumerate(ups):
        st = mgr.apply(u)
        mat.refresh()
        assert 0 <= st.touched_trees <= k + 1                      # T5.4-05
        if i % every == 0:
            oracle = [[dijkstra(mgr.graph, a, OpCounter())[0][b] for b in terms] for a in terms]
            assert mat.D == oracle, f"matrix mismatch at update {i}"
            if check_trees:
                for tree in mgr.trees:
                    check_state(mgr.graph, tree.state)
    return count


@pytest.mark.slow
def test_t54_01_small_exhaustive():
    """10x10 grid, k=5, 20,000 updates, matrix + all trees checked after EVERY update."""
    assert _run(grid(10, 10, seed=1), 5, 20_000, 0.01, 1, 1, True) == 20_000


@pytest.mark.slow
def test_t54_02_medium_grid_sampled():
    """30x30 grid, k=8, 20,000 updates, checked every 50th (the small run above checks every update)."""
    assert _run(grid(30, 30, seed=2), 8, 20_000, 0.01, 50, 2, True) == 20_000


@pytest.mark.slow
def test_t54_03_random_sparse_sampled():
    assert _run(random_sparse(900, 4500, seed=3), 8, 20_000, 0.05, 50, 3, True) == 20_000


@pytest.mark.parametrize("c", [0.5, 1.0, 2.0])
def test_t54_04_work_bound_per_tree(c):
    """Oracle mode: every tree's per-update work <= (1+c)*F_true + 2 (P2)."""
    g = grid(8, 8, seed=6)
    mgr = MultiTreeManager(g, [0, 9, 27, 63], c=c, f_mode="oracle")
    ups = random_updates(g, 400, seed=5, p_delete=0.1)
    assert len(ups) == 400
    for u in ups:
        st = mgr.apply(u)
        for tree, s in zip(mgr.trees, st.per_tree):
            f_true = SPTState.build(mgr.graph, tree.src, OpCounter()).F
            assert s.work <= (1 + c) * f_true + 2, (s, f_true)


def test_t54_06_comb_adversarial():
    g = comb_adversarial(200)
    c = 1.0
    mgr = MultiTreeManager(g, [0, 50, 100, 150], c=c, f_mode="oracle")
    st = mgr.apply(Update(kind="delete", u=0, v=1))
    root = st.per_tree[0]
    assert root.strategy in ("repair", "fallback")
    f_true = SPTState.build(mgr.graph, 0, OpCounter()).F
    assert root.work <= (1 + c) * f_true + 2
    assert [s.strategy for s in st.per_tree[1:]] == ["cert"] * 3
    for tree in mgr.trees:
        check_state(mgr.graph, tree.state)


def test_t54_07_script_runs():
    script = Path(__file__).resolve().parent.parent / "experiments" / "touched_trees.py"
    r = subprocess.run([sys.executable, str(script), "--small", "--updates", "60", "--k", "4"],
                       capture_output=True, text=True, timeout=300)
    assert r.returncode == 0, r.stderr
    assert "grid" in r.stdout and "comb" in r.stdout and "histogram" in r.stdout
