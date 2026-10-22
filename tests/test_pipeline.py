"""Milestone 6.5: RoutingPipeline end-to-end (T6.5-01 .. T6.5-10)."""

from __future__ import annotations

import random

import pytest

from graphpulse.dijkstra import INF
from graphpulse.generators import Update, grid, hub_spoke, random_sparse, random_updates
from graphpulse.graph import DiGraph
from graphpulse.pipeline import (
    INFEASIBLE, KEPT, KEPT_EPS, RESOLVED, RecomputeEverything, RoutingPipeline, run_differential,
)


def terms(g, k, seed=0):
    return [0] + random.Random(seed).sample(range(1, g.n), k)


def ups(g, n, p, seed):
    u = random_updates(g, n, seed=seed, p_delete=p)
    assert len(u) == n
    return u


def test_t65_01_exact_grid():
    g = grid(12, 12, seed=1)
    out = run_differential(g, terms(g, 8), ups(g, 2000, 0.02, 1))
    assert out["updates"] == 2000


@pytest.mark.parametrize("make,p", [
    (lambda: random_sparse(120, 700, seed=2), 0.05),
    (lambda: hub_spoke(6, 20, seed=2), 0.02),
])
def test_t65_02_other_families(make, p):
    g = make()
    out = run_differential(g, terms(g, 8), ups(g, 2000, p, 2))
    assert out["updates"] == 2000


def test_t65_03_skips_happen():
    g = grid(12, 12, seed=1)
    out = run_differential(g, terms(g, 8), ups(g, 2000, 0.02, 1))
    assert out[KEPT] > 0
    assert out["pipe_hk"] < out["ref_hk"]


def _cycle():
    g = DiGraph(4)
    for a, b in ((0, 1), (1, 2), (2, 3), (3, 0)):
        g.add_edge(a, b, 1)
    g.add_edge(0, 2, 9)
    return g


def test_t65_04_disconnection_then_infeasible_forever():
    g = _cycle()
    p = RoutingPipeline(g, [0, 1, 2, 3])
    assert p.tour_cost == 4
    s = p.apply(Update(kind="delete", u=0, v=1))      # only road into stop 1
    assert s.route_action == INFEASIBLE and s.tour_cost == INF and s.order == []
    s2 = p.apply(Update(kind="increase", u=1, v=2, new_w=5))
    s3 = p.apply(Update(kind="delete", u=3, v=0))
    assert s2.route_action == s3.route_action == INFEASIBLE
    assert s2.hk_transitions == s3.hk_transitions == 0


def test_t65_05_epsilon_mode():
    g = grid(12, 12, seed=3)
    out = run_differential(g, terms(g, 8), ups(g, 2000, 0.02, 3), eps=0.1)
    assert out["updates"] == 2000
    assert out["pipe_hk"] <= out["ref_hk"]


@pytest.mark.parametrize("k", [0, 1])
def test_t65_06_k0_k1(k):
    g = grid(8, 8, seed=4)
    t = [0] if k == 0 else [0, 37]
    out = run_differential(g, t, ups(g, 500, 0.02, 4))
    assert out["updates"] == 500


def test_t65_07_invalid_update_modifies_nothing():
    g = grid(5, 5, seed=1)
    p = RoutingPipeline(g, [0, 6, 12, 18])
    before = (p.tour_cost, p.order, p.matrix.snapshot(), [list(t.dist()) for t in p.manager.trees],
              [p.graph.out_edges(u) for u in range(p.graph.n)])
    with pytest.raises(ValueError):
        p.apply(Update(kind="delete", u=0, v=24))
    after = (p.tour_cost, p.order, p.matrix.snapshot(), [list(t.dist()) for t in p.manager.trees],
             [p.graph.out_edges(u) for u in range(p.graph.n)])
    assert before == after


def test_t65_08_reference_isolation():
    g = grid(5, 5, seed=1)
    p = RoutingPipeline(g, [0, 6, 12])
    ref = RecomputeEverything(g, [0, 6, 12])
    assert ref.graph is not p.graph
    ref.graph.remove_edge(0, 1)
    assert p.graph.has_edge(0, 1) and g.has_edge(0, 1)


def test_t65_09_action_totals():
    g = grid(10, 10, seed=5)
    out = run_differential(g, terms(g, 6), ups(g, 800, 0.03, 5))
    assert sum(out[a] for a in (KEPT, KEPT_EPS, RESOLVED, INFEASIBLE)) == out["updates"] == 800


def test_t65_invalid_eps():
    for bad in (-0.1, float("inf"), True):
        with pytest.raises(ValueError):
            RoutingPipeline(grid(4, 4, seed=1), [0, 5], eps=bad)


@pytest.mark.slow
def test_t65_slow_20000_updates_k6():
    g = grid(12, 12, seed=7)
    out = run_differential(g, terms(g, 6), ups(g, 20_000, 0.005, 7))
    assert out["updates"] == 20_000
    print(f"\n[pipeline k=6] actions: { {k: v for k, v in out.items()} }")
