"""Milestone 5.1: shared-graph update entry point (T5.1-02 .. T5.1-08).

T5.1-01 (full regression) is the rest of the suite.
"""

from __future__ import annotations

import pytest

from graphpulse.controller import BudgetedMaintainer
from graphpulse.generators import Update, apply_update, grid, random_updates
from graphpulse.graph import DiGraph
from graphpulse.verify import check_state


def _snapshot(m: BudgetedMaintainer):
    s = m.state
    return (list(s.dist), list(s.parent), list(s.tight), [set(c) for c in s.children], s.F_ops, m.F)


def test_t51_02_apply_update_returns_old_weight():
    g = DiGraph(2)
    g.add_edge(0, 1, 5)
    assert apply_update(g, Update(kind="increase", u=0, v=1, new_w=9)) == 5
    assert g.weight(0, 1) == 9
    assert apply_update(g, Update(kind="delete", u=0, v=1)) == 9
    assert not g.has_edge(0, 1)


@pytest.mark.parametrize("c,p_delete,expected", [(1.0, 0.1, 2000), (0.5, 0.1, 2000), (1.0, 0.5, None)])
def test_t51_03_04_shared_equals_separate(c, p_delete, expected):
    g0 = grid(8, 8, seed=3)
    updates = random_updates(g0, 2000, seed=11, p_delete=p_delete)
    # p_delete=0.5 exhausts the 224-edge pool early; the count is asserted, not assumed.
    assert len(updates) == expected if expected else len(updates) > 100
    shared_g = g0.copy()
    shared = [BudgetedMaintainer(shared_g, s, c=c, own_graph=False) for s in (0, 40)]
    sep = [BudgetedMaintainer(g0, s, c=c) for s in (0, 40)]
    for upd in updates:
        old_w = apply_update(shared_g, upd)
        for a, b in zip(shared, sep):
            sa = a.handle_applied(upd, old_w)
            sb = b.apply(upd)
            assert _snapshot(a) == _snapshot(b)
            assert (sa.strategy, sa.work, sa.scan, sa.push, sa.pop, sa.queue, sa.budget) == (
                sb.strategy, sb.work, sb.scan, sb.push, sb.pop, sb.queue, sb.budget)
    for a in shared:
        check_state(shared_g, a.state)
    assert shared[0].graph is shared_g


def test_t51_05_handled_before_applied():
    g = grid(3, 3, seed=1)
    m = BudgetedMaintainer(g, 0, own_graph=True)
    before = _snapshot(m)
    u, v = 0, 1
    with pytest.raises(RuntimeError):
        m.handle_applied(Update(kind="delete", u=u, v=v), 1)
    w = m.graph.weight(u, v)
    with pytest.raises(RuntimeError):
        m.handle_applied(Update(kind="increase", u=u, v=v, new_w=w + 5), w)
    assert _snapshot(m) == before


def test_t51_06_old_weight_used_for_tightness():
    g = DiGraph(3)
    g.add_edge(0, 1, 2)
    g.add_edge(1, 2, 3)
    upd = Update(kind="increase", u=1, v=2, new_w=10)

    m = BudgetedMaintainer(g, 0, own_graph=False)
    old_w = apply_update(g, upd)
    assert m.handle_applied(upd, old_w).strategy != "cert"   # was tight under old_w=3
    assert m.dist() == [0, 2, 12]

    g2 = DiGraph(3)
    g2.add_edge(0, 1, 2)
    g2.add_edge(1, 2, 3)
    m2 = BudgetedMaintainer(g2, 0, own_graph=False)
    apply_update(g2, upd)
    # A (wrong) old weight that makes the edge look non-tight is treated as a certificate:
    assert m2.handle_applied(upd, 4).strategy == "cert"


def test_t51_07_invalid_update_leaves_everything_untouched():
    g = grid(3, 3, seed=1)
    m = BudgetedMaintainer(g, 0)
    before, gsnap = _snapshot(m), [m.graph.out_edges(u) for u in range(m.graph.n)]
    with pytest.raises(ValueError):
        m.apply(Update(kind="delete", u=0, v=8))          # no such edge
    with pytest.raises(ValueError):
        m.apply(Update(kind="increase", u=0, v=1, new_w=1))  # not an increase
    assert _snapshot(m) == before
    assert [m.graph.out_edges(u) for u in range(m.graph.n)] == gsnap


def test_t51_08_deletion_of_non_tight_edge_is_certificate():
    g = DiGraph(3)
    g.add_edge(0, 1, 1)
    g.add_edge(0, 2, 1)
    g.add_edge(1, 2, 5)   # non-tight
    m = BudgetedMaintainer(g, 0)
    s = m.apply(Update(kind="delete", u=1, v=2))
    assert (s.strategy, s.work) == ("cert", 1)
