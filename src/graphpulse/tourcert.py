"""Lazy tour certificate (Milestone 6.4).

Under increase-only updates every shortest-path distance, hence every matrix
entry D[i][j], only grows.  Therefore the cost of *every* tour only grows.

* Exact keep: if no matrix entry used by the incumbent optimal tour has changed
  since the last exact solve, the tour's cost is unchanged while every other
  tour's cost has not decreased, so the tour is still optimal.
* Epsilon keep: LB (the optimum at the last exact solve) is a lower bound on
  the current optimum.  If cost'(T*) <= (1 + eps) * LB then
  cost'(T*) / optimum' <= cost'(T*) / LB <= 1 + eps.
  LB must NOT be raised when a tour is kept under epsilon (that would silently
  break the guarantee); only `rebase` after an exact solve resets it.
* Infeasible: if the stored cost is INF, entries only grow, so no tour can
  become feasible; keep.
"""

from __future__ import annotations

import math

from graphpulse.dijkstra import INF
from graphpulse.tour import tour_cost, validate_matrix
from graphpulse.verify import InvariantViolation

KEEP = "keep"
KEEP_EPS = "keep_eps"
RESOLVE = "resolve"


class TourCertificate:
    """Certificate that the incumbent tour is (approximately) still optimal."""

    def __init__(self, D: list[list[float]], order: list[int], cost: float) -> None:
        self.rebase(D, order, cost)

    # ------------------------------------------------------------------ state
    def rebase(self, D: list[list[float]], order: list[int], cost: float) -> None:
        """Reset after an exact solve: new base matrix, tour, used entries U and LB."""
        validate_matrix(D)
        k = len(D) - 1
        if math.isinf(cost):
            if order:
                raise ValueError("an infeasible certificate must have an empty order")
        elif k > 0 and tour_cost(D, order) != cost:
            raise ValueError("cost does not match tour_cost(D, order)")
        self._base: list[list[float]] = [row[:] for row in D]
        self._order: list[int] = list(order)
        self._cost: float = cost
        self._lb: float = cost
        self._used: frozenset[tuple[int, int]] = self._used_entries(order)
        self._acc: set[tuple[int, int]] = set()     # entries changed since this rebase

    @staticmethod
    def _used_entries(order: list[int]) -> frozenset[tuple[int, int]]:
        if not order:
            return frozenset()
        legs = [(0, order[0])] + list(zip(order, order[1:])) + [(order[-1], 0)]
        return frozenset(legs)

    @property
    def used(self) -> frozenset[tuple[int, int]]:
        return self._used

    @property
    def lower_bound(self) -> float:
        return self._lb

    @property
    def cost(self) -> float:
        return self._cost

    @property
    def order(self) -> list[int]:
        return list(self._order)

    def _check_monotone(self, D_new: list[list[float]]) -> None:
        if len(D_new) != len(self._base):
            raise ValueError("matrix size changed")
        for i, row in enumerate(D_new):
            for j, x in enumerate(row):
                if x < self._base[i][j]:
                    raise InvariantViolation(
                        f"Monotonicity violated: D[{i}][{j}] decreased from {self._base[i][j]} to {x}"
                    )

    # ---------------------------------------------------------------- decisions
    def decide(self, changed: set[tuple[int, int]], D_new: list[list[float]] | None = None) -> str:
        """Exact decision: KEEP if no used entry has changed since the last rebase, else RESOLVE.

        `changed` is the per-update changed set; changes are accumulated since the
        last rebase so that an earlier epsilon-keep can never make a later exact
        keep unsound.  Conservative: a changed used entry may leave the tour
        optimal, but we still RESOLVE (allowed, documented).
        """
        if D_new is not None:
            self._check_monotone(D_new)
        self._acc |= set(changed)
        if math.isinf(self._cost):
            return KEEP
        if not (self._acc & self._used):
            return KEEP
        return RESOLVE

    def decide_eps(self, D_new: list[list[float]], eps: float) -> str:
        """Epsilon decision from the new matrix; LB is never modified here."""
        if eps < 0:
            raise ValueError("eps must be non-negative")
        self._check_monotone(D_new)
        if math.isinf(self._cost):
            return KEEP_EPS
        new_cost = tour_cost(D_new, self._order) if self._order else 0
        if new_cost <= (1 + eps) * self._lb:
            return KEEP_EPS
        return RESOLVE

    def current_cost(self, D_new: list[list[float]]) -> float:
        """Cost of the incumbent tour under the matrix D_new."""
        if math.isinf(self._cost):
            return INF
        return tour_cost(D_new, self._order) if self._order else 0


__all__ = ["KEEP", "KEEP_EPS", "RESOLVE", "TourCertificate"]
