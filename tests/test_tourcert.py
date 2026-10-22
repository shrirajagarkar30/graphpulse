"""Milestone 6.4: lazy tour certificate (T6.4-01 .. T6.4-10)."""

from __future__ import annotations

import random

import pytest
from hypothesis import given, settings, strategies as st

from graphpulse.dijkstra import INF
from graphpulse.tour import held_karp, tour_cost
from graphpulse.tourcert import KEEP, KEEP_EPS, RESOLVE, TourCertificate
from graphpulse.verify import InvariantViolation
from tests.test_heldkarp import rand_matrix


def grow(D, seed, n_changes):
    """Return (D', changed): random entry increases (some to INF)."""
    rng = random.Random(seed)
    D2 = [r[:] for r in D]
    n = len(D)
    changed = set()
    for _ in range(n_changes):
        i, j = rng.randrange(n), rng.randrange(n)
        if i == j:
            continue
        D2[i][j] = INF if rng.random() < 0.1 else D2[i][j] + rng.randint(1, 25)
        changed.add((i, j))
    changed = {e for e in changed if D2[e[0]][e[1]] != D[e[0]][e[1]]}
    return D2, changed


def make(k, seed):
    D = rand_matrix(k, seed)
    c, o = held_karp(D)
    return D, TourCertificate(D, o, c)


def test_t64_01_untouched_tour_kept():
    D, cert = make(5, 1)
    unused = next((i, j) for i in range(6) for j in range(6) if i != j and (i, j) not in cert.used)
    D2 = [r[:] for r in D]
    D2[unused[0]][unused[1]] += 5
    assert cert.decide({unused}, D2) == KEEP


def test_t64_02_touched_tour_resolves():
    D, cert = make(5, 1)
    e = next(iter(cert.used))
    D2 = [r[:] for r in D]
    D2[e[0]][e[1]] += 1
    assert cert.decide({e}, D2) == RESOLVE


@settings(max_examples=500, deadline=None)
@given(st.integers(1, 7), st.integers(0, 10**6), st.integers(1, 6))
def test_t64_03_soundness(k, seed, n_changes):
    D, cert = make(k, seed)
    D2, changed = grow(D, seed + 1, n_changes)
    if cert.decide(changed, D2) == KEEP:
        assert held_karp(D2)[0] == cert.current_cost(D2) == cert.cost


def test_t64_04_conservative_resolve():
    # [1,2] and [2,1] both cost 3.  Raising a leg used only by the incumbent leaves the
    # optimum at 3 (via the other tour) - yet the certificate conservatively says RESOLVE.
    D = [[0, 1, 1], [1, 0, 1], [1, 1, 0]]
    c, o = held_karp(D)
    cert = TourCertificate(D, o, c)
    e = (o[0], o[1])
    D2 = [r[:] for r in D]
    D2[e[0]][e[1]] = 2
    assert held_karp(D2)[0] == c            # still optimal-cost: a re-solve was not strictly needed
    assert cert.decide({e}, D2) == RESOLVE


def test_t64_05_infeasible_stays_infeasible():
    D = rand_matrix(4, 3)
    for i in range(5):
        if i != 2:
            D[i][2] = INF
    c, o = held_karp(D)
    assert (c, o) == (INF, [])
    cert = TourCertificate(D, o, c)
    D2 = [r[:] for r in D]
    D2[1][3] += 4
    assert cert.decide({(1, 3)}, D2) == KEEP


@settings(max_examples=500, deadline=None)
@given(st.integers(1, 7), st.integers(0, 10**6), st.integers(1, 6), st.sampled_from([0.05, 0.2]))
def test_t64_06_epsilon_guarantee(k, seed, n_changes, eps):
    D, cert = make(k, seed)
    D2, _ = grow(D, seed + 1, n_changes)
    if cert.decide_eps(D2, eps) == KEEP_EPS:
        exact = held_karp(D2)[0]
        cur = cert.current_cost(D2)
        assert cur <= (1 + eps) * exact


def test_t64_07_lb_not_ratcheted():
    D, cert = make(5, 2)
    lb0 = cert.lower_bound
    D1 = [r[:] for r in D]
    e = next(iter(cert.used))
    D1[e[0]][e[1]] += 1
    assert cert.decide_eps(D1, 0.5) == KEEP_EPS
    D2 = [r[:] for r in D1]
    D2[e[0]][e[1]] += 1
    cert.decide_eps(D2, 0.5)
    assert cert.lower_bound == lb0


def test_t64_08_monotonicity_guard():
    D, cert = make(4, 1)
    D2 = [r[:] for r in D]
    D2[1][2] = max(0, D[1][2] - 1)
    with pytest.raises(InvariantViolation):
        cert.decide(set(), D2)
    with pytest.raises(InvariantViolation):
        cert.decide_eps(D2, 0.1)


def test_t64_09_rebase():
    D, cert = make(5, 4)
    e = next(iter(cert.used))
    D2 = [r[:] for r in D]
    D2[e[0]][e[1]] += 30
    assert cert.decide({e}, D2) == RESOLVE
    c2, o2 = held_karp(D2)
    cert.rebase(D2, o2, c2)
    assert cert.lower_bound == c2 and cert.cost == c2 and cert.order == o2
    assert cert.decide(set(), D2) == KEEP
    new_unused = next((i, j) for i in range(6) for j in range(6) if i != j and (i, j) not in cert.used)
    D3 = [r[:] for r in D2]
    D3[new_unused[0]][new_unused[1]] += 3
    assert cert.decide({new_unused}, D3) == KEEP


def test_t64_10_k0():
    cert = TourCertificate([[0]], [], 0)
    assert cert.decide(set(), [[0]]) == KEEP
    assert cert.decide_eps([[0]], 0.1) == KEEP_EPS
    assert cert.used == frozenset()


def test_t64_accumulated_changes_after_eps_keep():
    """An epsilon keep must never make a later *exact* keep unsound."""
    D, cert = make(5, 7)
    e = next(iter(cert.used))
    D1 = [r[:] for r in D]
    D1[e[0]][e[1]] += 1
    assert cert.decide({e}, D1) == RESOLVE       # used entry changed (accumulated)
    assert cert.decide(set(), D1) == RESOLVE     # empty per-update change must not forget it
