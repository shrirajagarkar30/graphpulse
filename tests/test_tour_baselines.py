"""Milestone 6.3: nearest neighbour and branch-and-bound (T6.3-01 .. T6.3-08)."""

from __future__ import annotations

import math

import pytest
from hypothesis import given, settings, strategies as st

from graphpulse.dijkstra import INF
from graphpulse.tour import NodeCounter, branch_and_bound, held_karp, nearest_neighbor, tour_cost
from tests.test_heldkarp import matrices, rand_matrix
from tests.test_tour_basic import ASYM, TEXTBOOK


@settings(max_examples=300, deadline=None)
@given(matrices)
def test_t63_01_bnb_equals_held_karp(D):
    hc, _ = held_karp(D)
    bc, bo = branch_and_bound(D)
    assert bc == hc
    if bc != INF:
        assert tour_cost(D, bo) == bc


@settings(max_examples=300, deadline=None)
@given(matrices)
def test_t63_02_nn_is_upper_bound(D):
    hc, _ = held_karp(D)
    nc, no = nearest_neighbor(D)
    assert nc >= hc
    if nc != INF:
        assert tour_cost(D, no) == nc


def test_t63_03_nn_tie_break_lowest_index():
    D = [[0 if i == j else 4 for j in range(5)] for i in range(5)]
    assert nearest_neighbor(D) == (20, [1, 2, 3, 4])


def test_t63_04_stuck_nn():
    D = rand_matrix(4, 2)
    for i in range(5):
        if i != 2:
            D[i][2] = INF
    assert nearest_neighbor(D) == (INF, [])


def test_t63_05_pruning_effect():
    k = 10
    cnt = NodeCounter()
    branch_and_bound(rand_matrix(k, 9), cnt)
    full_tree = sum(math.factorial(k) // math.factorial(k - r) for r in range(1, k + 1))
    assert 0 < cnt.nodes < full_tree


def test_t63_06_infeasible():
    D = rand_matrix(5, 4)
    for i in range(6):
        if i != 4:
            D[i][4] = INF
    assert branch_and_bound(D) == (INF, [])


@pytest.mark.slow
def test_t63_07_k12_cross_check():
    for seed in range(20):
        D = rand_matrix(12, seed)
        assert branch_and_bound(D)[0] == held_karp(D)[0], seed


def test_t63_08_worked_examples():
    for D, opt in ((TEXTBOOK, 80), (ASYM, 21)):
        nc, no = nearest_neighbor(D)
        assert nc >= opt and tour_cost(D, no) == nc
        assert branch_and_bound(D)[0] == opt
