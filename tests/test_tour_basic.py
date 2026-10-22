"""Milestone 6.1: tour cost and brute-force oracle (T6.1-01 .. T6.1-08)."""

from __future__ import annotations

import pytest

from graphpulse.dijkstra import INF
from graphpulse.tour import brute_force_tour, tour_cost, validate_matrix

TEXTBOOK = [[0, 10, 15, 20], [10, 0, 35, 25], [15, 35, 0, 30], [20, 25, 30, 0]]
ASYM = [[0, 2, 9, 10], [1, 0, 6, 4], [15, 7, 0, 8], [6, 3, 12, 0]]


def test_t61_01_symmetric_textbook():
    # cost 80 is reached by both [1,3,2] and [2,3,1]; lexicographically smallest wins
    assert brute_force_tour(TEXTBOOK) == (80, [1, 3, 2])
    assert tour_cost(TEXTBOOK, [2, 3, 1]) == 80


def test_t61_02_asymmetric():
    assert brute_force_tour(ASYM) == (21, [2, 3, 1])


def test_t61_03_k0_k1():
    assert brute_force_tour([[0]]) == (0, [])
    assert brute_force_tour([[0, 4], [7, 0]]) == (11, [1])


def test_t61_04_inf_entries():
    D = [[0, INF, 3], [1, 0, 1], [1, 1, 0]]       # stop 1 unreachable from anywhere
    D[2][1] = INF
    D[0][1] = INF
    assert brute_force_tour(D) == (INF, [])
    assert tour_cost(D, [1, 2]) == INF


@pytest.mark.parametrize("order", [[1, 1, 2], [1, 2], [0, 1, 2], [1, 2, 3, 4]])
def test_t61_05_bad_order(order):
    D = [[0, 1, 1, 1], [1, 0, 1, 1], [1, 1, 0, 1], [1, 1, 1, 0]]
    with pytest.raises(ValueError):
        tour_cost(D, order)


@pytest.mark.parametrize("bad", [
    [[0, 1], [1, 0], [1, 1]],          # non-square
    [[0, -1], [1, 0]],                 # negative entry
    [[1, 1], [1, 0]],                  # nonzero diagonal
    [[0, 1.5], [1, 0]],                # non-integer
    [[0, True], [1, 0]],               # bool
    [],
])
def test_t61_06_bad_matrix(bad):
    with pytest.raises(ValueError):
        validate_matrix(bad)


def test_t61_07_k_above_limit():
    n = 10                                  # k = 9
    D = [[0 if i == j else 1 for j in range(n)] for i in range(n)]
    with pytest.raises(ValueError, match="8"):
        brute_force_tour(D)


def test_t61_08_determinism():
    assert brute_force_tour(TEXTBOOK) == brute_force_tour(TEXTBOOK)
    ties = [[0 if i == j else 5 for j in range(5)] for i in range(5)]
    assert brute_force_tour(ties) == brute_force_tour(ties) == (25, [1, 2, 3, 4])
