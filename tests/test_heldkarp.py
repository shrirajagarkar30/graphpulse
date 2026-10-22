"""Milestone 6.2: Held-Karp with exact work counting (T6.2-01 .. T6.2-10)."""

from __future__ import annotations

import random

import pytest
from hypothesis import given, settings, strategies as st

from graphpulse.dijkstra import INF
from graphpulse.opcount import OpCounter
from graphpulse.tour import brute_force_tour, held_karp, tour_cost
from tests.test_tour_basic import ASYM, TEXTBOOK


def rand_matrix(k, seed, lo=1, hi=30, p_inf=0.0):
    rng = random.Random(seed)
    D = [[0 if i == j else (INF if rng.random() < p_inf else rng.randint(lo, hi)) for j in range(k + 1)]
         for i in range(k + 1)]
    return D


matrices = st.builds(rand_matrix, st.integers(1, 8), st.integers(0, 10**6), st.just(1), st.just(30),
                     st.sampled_from([0.0, 0.0, 0.2]))


def test_t62_01_textbook():
    c, o = held_karp(TEXTBOOK)
    assert c == 80 and tour_cost(TEXTBOOK, o) == 80
    c, o = held_karp(ASYM)
    assert c == 21 and tour_cost(ASYM, o) == 21


@settings(max_examples=300, deadline=None)
@given(matrices)
def test_t62_02_agrees_with_brute_force(D):
    bc, _ = brute_force_tour(D)
    hc, ho = held_karp(D)
    assert hc == bc
    if hc != INF:
        assert tour_cost(D, ho) == hc
    else:
        assert ho == []


@pytest.mark.parametrize("k", range(2, 11))
def test_t62_03_transition_formula(k):
    c = OpCounter()
    held_karp(rand_matrix(k, k), c)
    assert c.dp == k * (k - 1) * 2 ** (k - 2)
    assert c.dijkstra_work == 0 and c.work == 0      # dp is excluded from the work metrics


def test_t62_04_k0_k1():
    c = OpCounter()
    assert held_karp([[0]], c) == (0, [])
    assert held_karp([[0, 3], [4, 0]], c) == (7, [1])
    assert c.dp == 0


def test_t62_05_infeasible():
    D = rand_matrix(4, 1)
    for i in range(5):
        if i != 3:
            D[i][3] = INF                  # nothing can enter stop 3
    assert held_karp(D) == (INF, [])


def test_t62_06_guard_before_allocation():
    n = 20                                  # k = 19
    D = [[0 if i == j else 1 for j in range(n)] for i in range(n)]
    with pytest.raises(ValueError, match="18"):
        held_karp(D)


def test_t62_07_determinism_with_ties():
    D = [[0 if i == j else 5 for j in range(8)] for i in range(8)]
    assert held_karp(D) == held_karp(D)


def test_t62_08_large_weights():
    D = rand_matrix(6, 3, lo=10**12, hi=2 * 10**12)
    c, o = held_karp(D)
    assert isinstance(c, int) and c == brute_force_tour(D)[0] == tour_cost(D, o)


def test_t62_09_k12_valid_permutation():
    D = rand_matrix(12, 5)
    c, o = held_karp(D)
    assert sorted(o) == list(range(1, 13)) and tour_cost(D, o) == c


@pytest.mark.slow
def test_t62_k16_runs_and_formula():
    k = 16
    cnt = OpCounter()
    c, o = held_karp(rand_matrix(k, 1), cnt)
    assert cnt.dp == k * (k - 1) * 2 ** (k - 2) and tour_cost(rand_matrix(k, 1), o) == c
