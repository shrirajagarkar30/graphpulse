"""Milestone 5.2: MultiTreeManager (T5.2-01 .. T5.2-11; T5.2-11 is the full suite)."""

from __future__ import annotations

import math

import pytest

import graphpulse.terminals as terminals_mod
from graphpulse.controller import BudgetedMaintainer
from graphpulse.dijkstra import dijkstra
from graphpulse.generators import Update, grid, hub_spoke, random_sparse, random_updates
from graphpulse.graph import DiGraph
from graphpulse.opcount import OpCounter
from graphpulse.terminals import MultiTreeManager
from graphpulse.verify import check_state


def _snap(m: BudgetedMaintainer):
    s = m.state
    return (list(s.dist), list(s.parent), list(s.tight), [set(c) for c in s.children], m.F)


def test_t52_01_construction():
    g = grid(6, 6, seed=2)
    mgr = MultiTreeManager(g, [0, 7, 20, 35])
    assert len(mgr.trees) == 4 and mgr.k == 3
    for t, tree in zip(mgr.terminals, mgr.trees):
        assert tree.dist() == dijkstra(g, t, OpCounter())[0]


@pytest.mark.parametrize("bad", [[0, 5, 5], [], [99, 0], [0, True], [0, -1], [0.5]])
def test_t52_02_03_invalid_terminals(bad):
    with pytest.raises(ValueError):
        MultiTreeManager(grid(6, 6, seed=2), bad)


def test_t52_04_single_terminal_matches_standalone():
    g = grid(6, 6, seed=4)
    ups = random_updates(g, 500, seed=9)
    mgr = MultiTreeManager(g, [0])
    solo = BudgetedMaintainer(g, 0)
    for u in ups:
        ms, ss = mgr.apply(u), solo.apply(u)
        assert ms.per_tree[0] == ss
        assert _snap(mgr.trees[0]) == _snap(solo)


def test_t52_05_certificate_only_update():
    g = grid(5, 5, seed=1)
    mgr = MultiTreeManager(g, [0, 6, 12, 24])
    target = None
    for u in range(g.n):
        for v, w in g.out_edges(u):
            if all(t.state.dist[u] == math.inf or t.state.dist[u] + w != t.state.dist[v] or v == t.src for t in mgr.trees):
                target = (u, v)
                break
        if target:
            break
    assert target is not None
    st = mgr.apply(Update(kind="delete", u=target[0], v=target[1]))
    assert st.touched_trees == 0 and st.dist_changed_trees == 0
    assert st.total_work == mgr.k + 1


def test_t52_06_touched_count_hand_built():
    g = DiGraph(5)
    g.add_edge(0, 1, 1)
    g.add_edge(3, 1, 1)
    g.add_edge(1, 2, 1)
    g.add_edge(4, 2, 10)
    mgr = MultiTreeManager(g, [0, 3, 4])
    st = mgr.apply(Update(kind="increase", u=1, v=2, new_w=5))
    assert st.touched_trees == 2 and st.dist_changed_trees == 2
    assert [s.strategy for s in st.per_tree][2] == "cert"


def test_t52_07_graph_mutated_once(monkeypatch):
    calls = []
    real = terminals_mod.apply_update

    def spy(g, upd):
        calls.append(1)
        return real(g, upd)

    monkeypatch.setattr(terminals_mod, "apply_update", spy)
    g = grid(6, 6, seed=5)
    mgr = MultiTreeManager(g, [0, 7, 20, 35])
    for u in random_updates(g, 100, seed=2):
        mgr.apply(u)
    assert len(calls) == 100


@pytest.mark.parametrize("make,p_delete,full", [
    (lambda: grid(6, 6, seed=7), 0.02, True),
    (lambda: random_sparse(40, 200, seed=7), 0.05, True),
    (lambda: hub_spoke(3, 8, seed=7), 0.02, True),
    (lambda: grid(6, 6, seed=7), 0.5, False),          # deletion-heavy: pool exhausts early
    (lambda: random_sparse(40, 200, seed=7), 0.5, False),
    (lambda: hub_spoke(3, 8, seed=7), 0.5, False),
])
def test_t52_08_differential_vs_oracle(make, p_delete, full):
    g = make()
    terms = [0, 5, 11, 17]
    mgr = MultiTreeManager(g, terms)
    ups = random_updates(g, 2000, seed=21, p_delete=p_delete)
    assert (len(ups) == 2000) if full else (len(ups) > 50)
    for i, u in enumerate(ups):
        mgr.apply(u)
        for t, tree in zip(terms, mgr.trees):
            assert tree.dist() == dijkstra(mgr.graph, t, OpCounter())[0], f"update {i}, terminal {t}"


def test_t52_09_independent_budgets():
    g = grid(6, 6, seed=3)
    c = 0.5
    mgr = MultiTreeManager(g, [0, 7, 20, 35], c=c)
    assert len({t.F for t in mgr.trees}) > 1          # different F per tree
    for u in random_updates(g, 300, seed=6):
        before = [t.F for t in mgr.trees]
        st = mgr.apply(u)
        for F_i, s in zip(before, st.per_tree):
            assert s.budget == math.ceil(c * F_i)


def test_t52_10_invalid_update_modifies_nothing():
    g = grid(4, 4, seed=1)
    mgr = MultiTreeManager(g, [0, 5, 10])
    before = [_snap(t) for t in mgr.trees]
    edges = [[mgr.graph.out_edges(u)] for u in range(mgr.graph.n)]
    with pytest.raises(ValueError):
        mgr.apply(Update(kind="delete", u=0, v=15))
    assert [_snap(t) for t in mgr.trees] == before
    assert [[mgr.graph.out_edges(u)] for u in range(mgr.graph.n)] == edges


def test_t52_verify_mode_1000_updates():
    g = grid(6, 6, seed=8)
    mgr = MultiTreeManager(g, [0, 7, 20, 35], verify=True)
    for u in random_updates(g, 1000, seed=13):
        mgr.apply(u)
    for tree in mgr.trees:
        check_state(mgr.graph, tree.state)


def test_t52_random_budget_streams_independent():
    mgr = MultiTreeManager(grid(5, 5, seed=1), [0, 6, 12], c="random", seed=3)
    seeds = [t.random_budget.seed for t in mgr.trees]
    assert len(set(seeds)) == 3
