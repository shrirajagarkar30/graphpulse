"""Exact and baseline tour solvers on a terminal distance matrix (Milestones 6.1-6.3).

Conventions: `D` is a list of lists, D[i][j] is a non-negative int or INF,
index 0 is the depot, indices 1..k are the stops, entries are directed
(asymmetric allowed) and the diagonal is 0.  A *tour* is a list `order` that
is a permutation of 1..k; its cost is
    D[0][order[0]] + sum D[order[r]][order[r+1]] + D[order[-1]][0].
An infeasible instance (no finite tour) is reported as `(INF, [])`.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from itertools import permutations

from graphpulse.dijkstra import INF
from graphpulse.opcount import OpCounter

BRUTE_FORCE_MAX_K = 8
HELD_KARP_MAX_K = 18


def validate_matrix(D: list[list[float]]) -> None:
    """Raise ValueError unless D is square, has a zero diagonal and non-negative int/INF entries."""
    n = len(D)
    if n == 0:
        raise ValueError("matrix must contain at least the depot")
    for i, row in enumerate(D):
        if len(row) != n:
            raise ValueError(f"matrix is not square: row {i} has {len(row)} entries, expected {n}")
        for j, x in enumerate(row):
            if isinstance(x, bool):
                raise ValueError(f"D[{i}][{j}] must be a non-negative int or INF, got {x!r}")
            if x == INF:
                continue
            if not isinstance(x, int) or x < 0:
                raise ValueError(f"D[{i}][{j}] must be a non-negative int or INF, got {x!r}")
        if row[i] != 0:
            raise ValueError(f"diagonal D[{i}][{i}] must be 0, got {row[i]!r}")


def _check_order(D: list[list[float]], order: list[int]) -> None:
    k = len(D) - 1
    if sorted(order) != list(range(1, k + 1)):
        raise ValueError(f"order {order!r} is not a permutation of 1..{k}")


def tour_cost(D: list[list[float]], order: list[int]) -> float:
    """Cost of the closed tour depot -> order -> depot (INF if any leg is INF)."""
    _check_order(D, order)
    if not order:
        return 0
    cost = D[0][order[0]]
    for a, b in zip(order, order[1:]):
        cost += D[a][b]
    return cost + D[order[-1]][0]


def brute_force_tour(D: list[list[float]]) -> tuple[float, list[int]]:
    """Exact solver over all permutations (k <= 8); ties -> lexicographically smallest order."""
    validate_matrix(D)
    k = len(D) - 1
    if k > BRUTE_FORCE_MAX_K:
        raise ValueError(f"brute force supports k <= {BRUTE_FORCE_MAX_K}, got k={k}")
    if k == 0:
        return 0, []
    best: float = INF
    best_order: list[int] = []
    for perm in permutations(range(1, k + 1)):       # lexicographic order
        c = tour_cost(D, list(perm))
        if c < best:                                  # strict: keeps the lexicographically first
            best, best_order = c, list(perm)
    return (best, best_order) if not math.isinf(best) else (INF, [])


def held_karp(D: list[list[float]], counter: OpCounter | None = None) -> tuple[float, list[int]]:
    """Exact Held-Karp DP, k <= 18.  Stops 1..k map to bits 0..k-1.

    H[S][j] = cheapest path depot -> (all of S) ending at j.  Exactly
    k(k-1)2^(k-2) recurrence transitions are performed (k >= 2) and added to
    `counter.dp`.  Ties: smallest predecessor / smallest last stop.
    """
    validate_matrix(D)
    k = len(D) - 1
    if k > HELD_KARP_MAX_K:
        raise ValueError(f"Held-Karp supports k <= {HELD_KARP_MAX_K}, got k={k}")
    if k == 0:
        return 0, []
    if k == 1:
        cost = D[0][1] + D[1][0]
        return (INF, []) if math.isinf(cost) else (cost, [1])

    full = (1 << k) - 1
    H: list[list[float] | None] = [None] * (full + 1)
    P: list[list[int] | None] = [None] * (full + 1)
    transitions = 0
    for mask in range(1, full + 1):
        row = [INF] * k
        par = [-1] * k
        bits = [b for b in range(k) if mask >> b & 1]
        if len(bits) == 1:
            j = bits[0]
            row[j] = D[0][j + 1]
        else:
            for j in bits:
                prev = mask ^ (1 << j)
                hp = H[prev]
                best, bp = INF, -1
                for i in bits:
                    if i == j:
                        continue
                    transitions += 1
                    cand = hp[i] + D[i + 1][j + 1]
                    if cand < best:
                        best, bp = cand, i
                row[j], par[j] = best, bp
        H[mask], P[mask] = row, par

    if counter is not None:
        counter.dp += transitions

    best, last = INF, -1
    for j in range(k):
        cand = H[full][j] + D[j + 1][0]
        if cand < best:
            best, last = cand, j
    if math.isinf(best):
        return INF, []
    order: list[int] = []
    mask, j = full, last
    while j != -1:
        order.append(j + 1)
        pj = P[mask][j]
        mask ^= 1 << j
        j = pj
    order.reverse()
    return best, order


def nearest_neighbor(D: list[list[float]]) -> tuple[float, list[int]]:
    """Greedy heuristic; ties -> lowest index; (INF, []) if it gets stuck."""
    validate_matrix(D)
    k = len(D) - 1
    if k == 0:
        return 0, []
    cur, left, order = 0, set(range(1, k + 1)), []
    while left:
        j = min(left, key=lambda x: (D[cur][x], x))
        if math.isinf(D[cur][j]):
            return INF, []
        order.append(j)
        left.discard(j)
        cur = j
    cost = tour_cost(D, order)
    return (cost, order) if not math.isinf(cost) else (INF, [])


@dataclass
class NodeCounter:
    """Counts expanded search nodes in `branch_and_bound`."""

    nodes: int = 0


def branch_and_bound(D: list[list[float]], node_counter: NodeCounter | None = None) -> tuple[float, list[int]]:
    """Exact depth-first search, pruning when partial cost >= best known.

    Safe because all entries are non-negative: a partial tour whose cost already
    reaches the best known cost cannot lead to a strictly cheaper tour.  The
    initial bound is the nearest-neighbour cost.
    """
    validate_matrix(D)
    k = len(D) - 1
    if k == 0:
        return 0, []
    best, best_order = nearest_neighbor(D)
    nodes = 0

    def dfs(cur: int, partial: float, left: list[int], path: list[int]) -> None:
        nonlocal best, best_order, nodes
        if not left:
            total = partial + D[cur][0]
            if total < best:
                best, best_order = total, list(path)
            return
        for j in left:
            nodes += 1
            np_ = partial + D[cur][j]
            if np_ >= best:
                continue
            path.append(j)
            dfs(j, np_, [x for x in left if x != j], path)
            path.pop()

    dfs(0, 0, list(range(1, k + 1)), [])
    if node_counter is not None:
        node_counter.nodes += nodes
    return (best, best_order) if not math.isinf(best) else (INF, [])


__all__ = [
    "BRUTE_FORCE_MAX_K", "HELD_KARP_MAX_K", "NodeCounter", "branch_and_bound", "brute_force_tour",
    "held_karp", "nearest_neighbor", "tour_cost", "validate_matrix",
]
