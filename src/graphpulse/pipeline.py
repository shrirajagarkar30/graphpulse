"""End-to-end routing pipeline (Milestone 6.5).

Per update: multi-tree repair -> terminal matrix refresh -> lazy tour
certificate -> Held-Karp only when the certificate cannot keep the tour.

`RecomputeEverything` is the reference: fresh Dijkstra from every terminal and
a full Held-Karp solve after every update, on its own graph copy that shares no
object with the pipeline.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

from graphpulse.dijkstra import INF, dijkstra
from graphpulse.generators import Update, apply_update
from graphpulse.graph import DiGraph
from graphpulse.opcount import OpCounter
from graphpulse.terminals import MultiStats, MultiTreeManager, TerminalMatrix
from graphpulse.tour import held_karp
from graphpulse.tourcert import KEEP, KEEP_EPS, TourCertificate

KEPT, KEPT_EPS, RESOLVED, INFEASIBLE = "kept", "kept_eps", "resolved", "infeasible"


@dataclass
class RouteStats(MultiStats):
    """MultiStats plus the routing decision for one update."""

    route_action: str = KEPT
    hk_transitions: int = 0
    tour_cost: float = 0
    order: list[int] | None = None
    lower_bound: float = 0
    matrix_changed: int = 0


class RoutingPipeline:
    def __init__(
        self,
        g: DiGraph,
        terminals: list[int],
        c: float | str = 1.0,
        eps: float = 0.0,
        f_mode: str = "last",
        verify: bool = False,
        seed: int | None = None,
        lazy_tour: bool = True,
    ) -> None:
        if isinstance(eps, bool) or not isinstance(eps, (int, float)) or eps < 0 or math.isinf(eps):
            raise ValueError(f"eps must be a finite non-negative number, got {eps!r}")
        self._mgr = MultiTreeManager(g, terminals, c=c, f_mode=f_mode, verify=verify, seed=seed)
        self._mat = TerminalMatrix(self._mgr)
        self._eps = float(eps)
        self._lazy = bool(lazy_tour)
        cnt = OpCounter()
        cost, order = held_karp(self._mat.D, cnt)          # initial solve: not part of per-update accounting
        self._cert = TourCertificate(self._mat.D, order, cost)
        self._cost: float = cost
        self._order: list[int] = order
        self.initial_hk_transitions: int = cnt.dp
        self.last_stats: RouteStats | None = None

    # ---------------------------------------------------------------- accessors
    @property
    def manager(self) -> MultiTreeManager:
        return self._mgr

    @property
    def matrix(self) -> TerminalMatrix:
        return self._mat

    @property
    def graph(self) -> DiGraph:
        return self._mgr.graph

    @property
    def tour_cost(self) -> float:
        return self._cost

    @property
    def order(self) -> list[int]:
        return list(self._order)

    @property
    def lower_bound(self) -> float:
        return self._cert.lower_bound

    # -------------------------------------------------------------------- update
    def apply(self, update: Update) -> RouteStats:
        """Apply one update.  Raises ValueError (nothing modified) if invalid."""
        multi = self._mgr.apply(update)
        changed = self._mat.refresh()
        D = self._mat.D
        hk = 0

        if self._lazy and math.isinf(self._cert.cost):
            action = INFEASIBLE                       # entries only grow: stays infeasible, 0 transitions
        elif not self._lazy:
            cnt = OpCounter()                         # lazy_tour off: exact re-solve after every update
            cost, order = held_karp(D, cnt)
            hk = cnt.dp
            self._cert.rebase(D, order, cost)
            self._cost, self._order = cost, order
            action = INFEASIBLE if math.isinf(cost) else RESOLVED
        elif not changed:
            action = KEPT                             # skip even the certificate lookup
        elif self._cert.decide(changed, D) == KEEP:
            action = KEPT
        elif self._eps > 0 and self._cert.decide_eps(D, self._eps) == KEEP_EPS:
            action = KEPT_EPS
            self._cost = self._cert.current_cost(D)
        else:
            cnt = OpCounter()
            cost, order = held_karp(D, cnt)
            hk = cnt.dp
            self._cert.rebase(D, order, cost)
            self._cost, self._order = cost, order
            action = INFEASIBLE if math.isinf(cost) else RESOLVED

        stats = RouteStats(
            per_tree=multi.per_tree,
            touched_trees=multi.touched_trees,
            dist_changed_trees=multi.dist_changed_trees,
            total_work=multi.total_work,
            strategy_counts=multi.strategy_counts,
            route_action=action,
            hk_transitions=hk,
            tour_cost=self._cost,
            order=list(self._order),
            lower_bound=self._cert.lower_bound,
            matrix_changed=len(changed),
        )
        self.last_stats = stats
        return stats


@dataclass
class RefStats:
    tour_cost: float
    order: list[int]
    hk_transitions: int
    dijkstra_work: int


class RecomputeEverything:
    """Reference: fresh Dijkstra from each terminal + Held-Karp after every update."""

    def __init__(self, g: DiGraph, terminals: list[int]) -> None:
        self._g = g.copy()                              # shares nothing with the pipeline
        self._terms = list(terminals)
        self.last = self._solve()

    @property
    def graph(self) -> DiGraph:
        return self._g

    def _solve(self) -> RefStats:
        work = 0
        D = []
        for a in self._terms:
            c = OpCounter()
            dist, _ = dijkstra(self._g, a, c)
            work += c.work
            D.append([dist[b] for b in self._terms])
        cnt = OpCounter()
        cost, order = held_karp(D, cnt)
        return RefStats(cost, order, cnt.dp, work)

    def apply(self, update: Update) -> RefStats:
        apply_update(self._g, update)
        self.last = self._solve()
        return self.last


def run_differential(
    g: DiGraph,
    terminals: list[int],
    updates: list[Update],
    c: float | str = 1.0,
    eps: float = 0.0,
    f_mode: str = "last",
) -> dict[str, int]:
    """Run pipeline and reference side by side; raise AssertionError on any cost mismatch.

    Exact mode (eps = 0): pipeline cost == reference cost after every update.
    Epsilon mode: reference <= pipeline cost <= (1 + eps) * reference and lower_bound <= reference.
    Returns action counts plus total Held-Karp transitions for both sides.
    """
    pipe = RoutingPipeline(g, terminals, c=c, eps=eps, f_mode=f_mode)
    ref = RecomputeEverything(g, terminals)
    assert pipe.tour_cost == ref.last.tour_cost, "initial tour cost mismatch"
    out = {KEPT: 0, KEPT_EPS: 0, RESOLVED: 0, INFEASIBLE: 0, "pipe_hk": 0, "ref_hk": 0, "updates": 0}
    for i, upd in enumerate(updates):
        s = pipe.apply(upd)
        r = ref.apply(upd)
        if eps == 0:
            assert s.tour_cost == r.tour_cost, f"update {i}: pipeline {s.tour_cost} != reference {r.tour_cost}"
        else:
            assert r.tour_cost <= s.tour_cost <= (1 + eps) * r.tour_cost or (
                math.isinf(r.tour_cost) and math.isinf(s.tour_cost)
            ), f"update {i}: pipeline {s.tour_cost} vs reference {r.tour_cost}"
            assert s.lower_bound <= r.tour_cost or math.isinf(r.tour_cost)
        out[s.route_action] += 1
        out["pipe_hk"] += s.hk_transitions
        out["ref_hk"] += r.hk_transitions
        out["updates"] += 1
    return out


__all__ = [
    "INFEASIBLE", "KEPT", "KEPT_EPS", "RESOLVED", "RecomputeEverything", "RefStats",
    "RouteStats", "RoutingPipeline", "run_differential",
]
