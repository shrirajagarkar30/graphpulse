"""Milestone 5.3: TerminalMatrix (T5.3-01 .. T5.3-10; T5.3-10 is the full suite)."""

from __future__ import annotations

import pytest
from hypothesis import given, settings, strategies as st

from graphpulse.dijkstra import INF, dijkstra
from graphpulse.generators import Update, grid, hub_spoke, random_sparse, random_updates
from graphpulse.graph import DiGraph
from graphpulse.opcount import OpCounter
from graphpulse.terminals import MultiTreeManager, TerminalMatrix
from graphpulse.verify import InvariantViolation


def oracle(g, terms):
    return [[dijkstra(g, a, OpCounter())[0][b] for b in terms] for a in terms]


def test_t53_01_initial_matrix():
    g = grid(6, 6, seed=2)
    terms = [0, 7, 14, 21, 35]
    mat = TerminalMatrix(MultiTreeManager(g, terms))
    assert mat.D == oracle(g, terms)
    assert all(mat.D[i][i] == 0 for i in range(5))


def test_t53_02_03_changed_set_matches_oracle_diff():
    g = grid(8, 8, seed=5)
    terms = [0, 9, 27, 45, 63]
    mgr = MultiTreeManager(g, terms)
    mat = TerminalMatrix(mgr)
    prev = oracle(g, terms)
    seen_empty = seen_nonempty = False
    for u in random_updates(g, 600, seed=4, p_delete=0.05):
        mgr.apply(u)
        cur = oracle(mgr.graph, terms)
        expect = {(i, j) for i in range(5) for j in range(5) if prev[i][j] != cur[i][j]}
        got = mat.refresh()
        assert got == expect
        seen_empty |= not got
        seen_nonempty |= bool(got)
        prev = cur
    assert seen_empty and seen_nonempty


def _chain():
    g = DiGraph(3)
    g.add_edge(0, 1, 1)
    g.add_edge(1, 2, 1)
    g.add_edge(2, 0, 1)
    return g


def test_t53_04_05_disconnection_and_inf_stays_inf():
    mgr = MultiTreeManager(_chain(), [0, 1, 2])
    mat = TerminalMatrix(mgr)
    assert mat.is_complete()
    mgr.apply(Update(kind="delete", u=1, v=2))
    changed = mat.refresh()
    assert mat.D[0][2] == INF and mat.D[1][2] == INF and (0, 2) in changed
    assert not mat.is_complete()
    mgr.apply(Update(kind="increase", u=0, v=1, new_w=7))
    mat.refresh()                                  # INF stays INF, no exception
    assert mat.D[0][2] == INF and mat.D[0][1] == 7


def test_t53_06_monotonicity_guard_fires_on_injected_decrease():
    g = grid(5, 5, seed=1)
    mgr = MultiTreeManager(g, [0, 6, 12])
    mat = TerminalMatrix(mgr)
    before = mat.snapshot()
    mgr.trees[1].state.dist[12] -= 1               # injected bug: a distance decreases
    with pytest.raises(InvariantViolation):
        mat.refresh()
    assert mat.snapshot() == before                # stored matrix untouched


def test_t53_07_snapshot_immutable():
    g = grid(6, 6, seed=3)
    mgr = MultiTreeManager(g, [0, 7, 20])
    mat = TerminalMatrix(mgr)
    snap = mat.snapshot()
    for u in random_updates(g, 50, seed=2, p_delete=0.05):
        mgr.apply(u)
    mat.refresh()
    assert snap == tuple(tuple(r) for r in oracle(g, [0, 7, 20]))
    assert snap != mat.snapshot()
    with pytest.raises(TypeError):
        snap[0][0] = 5  # type: ignore[index]


@settings(max_examples=300, deadline=None)
@given(n=st.integers(6, 14), seed=st.integers(0, 10_000), k=st.integers(1, 4))
def test_t53_08_oracle_equality_property(n, seed, k):
    g = random_sparse(n, min(n * (n - 1), 3 * n), seed=seed)
    terms = list(range(k + 1))
    mgr = MultiTreeManager(g, terms)
    mat = TerminalMatrix(mgr)
    for u in random_updates(g, 25, seed=seed, p_delete=0.3):
        mgr.apply(u)
        mat.refresh()
        assert mat.D == oracle(mgr.graph, terms)


def test_t53_09_adjacent_terminals():
    g = DiGraph(3)
    g.add_edge(0, 1, 2)
    g.add_edge(1, 0, 2)
    g.add_edge(1, 2, 5)
    mgr = MultiTreeManager(g, [0, 1])
    mat = TerminalMatrix(mgr)
    assert mat.D == [[0, 2], [2, 0]]
    mgr.apply(Update(kind="increase", u=0, v=1, new_w=9))
    assert mat.refresh() == {(0, 1)}
    assert mat.D == [[0, 9], [2, 0]]


def test_t53_matrix_cells_counted_separately():
    mgr = MultiTreeManager(grid(4, 4, seed=1), [0, 5, 10])
    mat = TerminalMatrix(mgr)
    mat.refresh()
    mat.refresh()
    assert mat.matrix_cells == 2 * 9


@pytest.mark.slow
@pytest.mark.parametrize("make,p", [
    (lambda: grid(10, 10, seed=5), 0.02),
    (lambda: random_sparse(80, 700, seed=5), 0.02),
])
def test_t53_oracle_after_5000_updates(make, p):
    g = make()
    terms = [0, 11, 33, 55, 77]
    mgr = MultiTreeManager(g, terms)
    mat = TerminalMatrix(mgr)
    ups = random_updates(g, 5000, seed=8, p_delete=p)
    assert len(ups) == 5000
    for u in ups:
        mgr.apply(u)
        mat.refresh()
        assert mat.D == oracle(mgr.graph, terms)
