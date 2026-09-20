"""Budgeted repair controller for shortest-path maintenance (Milestone 4.2).

`BudgetedMaintainer` implements the system's decision rule under non-decreasing updates:
1. Certificate check: strategy 'cert' (1 SCAN)
2. Alternative support: strategy 'alt' (at most 1 + indeg(v) SCANs)
3. Budgeted repair: strategy 'repair' with work cap B = ceil(c * F)
4. Rebuild fallback: strategy 'fallback' if repair raises BudgetExceeded

f_mode:
- "last": uses F measured from the most recent full tree build (the deployable mode).
- "oracle": measures F_true on a scratch copy of the updated graph before repair
  (for theoretical evaluation and competitive ratio testing).
"""

from __future__ import annotations

import math

from graphpulse.dijkstra import INF
from graphpulse.generators import Update, apply_update
from graphpulse.graph import DiGraph
from graphpulse.maintainer import Maintainer, UpdateStats
from graphpulse.opcount import BudgetExceeded, OpCounter
from graphpulse.repair import repair
from graphpulse.spt import SPTState
from graphpulse.verify import check_state


class BudgetedMaintainer:
    """Dynamic shortest-path maintainer with certificate checking, budgeted repair,
    and automatic rebuild fallback on budget exhaustion.
    """

    def __init__(
        self,
        g: DiGraph,
        src: int,
        c: float = 1.0,
        f_mode: str = "last",
        verify: bool = False,
    ) -> None:
        """Initialize BudgetedMaintainer.

        Parameters
        ----------
        g      : DiGraph to maintain.
        src    : Single source vertex ID.
        c      : Competitive budget multiplier (c >= 0, float or int, inf allowed).
        f_mode : Rebuild cost estimation mode: 'last' or 'oracle'.
        verify : If True, runs check_state after every single update.
        """
        if isinstance(src, bool) or not isinstance(src, int) or not (0 <= src < g.n):
            raise ValueError(f"Source vertex {src!r} out of range [0, {g.n - 1}]")

        if isinstance(c, bool) or not isinstance(c, (int, float)):
            raise TypeError(f"Multiplier c must be a non-negative number, got {c!r}")
        if c < 0:
            raise ValueError(f"Multiplier c must be non-negative, got {c!r}")

        if f_mode not in ("last", "oracle"):
            raise ValueError(f"Unknown f_mode {f_mode!r}; expected 'last' or 'oracle'")

        self._g: DiGraph = g.copy()
        self._src: int = src
        self._c: float = float(c)
        self._f_mode: str = f_mode
        self._verify: bool = verify

        counter = OpCounter()
        self._state: SPTState = SPTState.build(self._g, self._src, counter)
        self._F: int = self._state.F
        self.last_affected: set[int] | None = None
        self._last_stats = UpdateStats(
            work=counter.work,
            scan=counter.scan,
            push=counter.push,
            pop=counter.pop,
            queue=counter.queue,
            strategy="rebuild",
            fallback_work=counter.work,
            affected_size=self._g.n,
        )

    def dist(self) -> list[float]:
        """Return a fresh copy of current shortest-path distances."""
        return list(self._state.dist)

    def parent(self) -> list[int]:
        """Return a fresh copy of current shortest-path tree parents."""
        return list(self._state.parent)

    @property
    def state(self) -> SPTState:
        """Return internal SPTState."""
        return self._state

    @property
    def graph(self) -> DiGraph:
        """Return internal DiGraph."""
        return self._g

    @property
    def src(self) -> int:
        """Return source vertex."""
        return self._src

    @property
    def F(self) -> int:
        """Return current F rebuild work value."""
        return self._F

    @property
    def c(self) -> float:
        """Return budget multiplier."""
        return self._c

    @property
    def f_mode(self) -> str:
        """Return f_mode ('last' or 'oracle')."""
        return self._f_mode

    @property
    def last_stats(self) -> UpdateStats:
        """Return stats from most recent apply() call."""
        return self._last_stats

    def _compute_f(self, update: Update) -> int:
        """Compute the F work value to use for calculating the budget."""
        if self._f_mode == "oracle":
            scratch_g = self._g.copy()
            apply_update(scratch_g, update)
            scratch_counter = OpCounter()
            SPTState.build(scratch_g, self._src, scratch_counter)
            return scratch_counter.work
        return self._F

    def _compute_budget(self, F_val: int) -> int | None:
        """Calculate the budget B = ceil(c * F)."""
        if math.isinf(self._c):
            return None
        return math.ceil(self._c * F_val)

    def apply(self, update: Update) -> UpdateStats:
        """Apply an edge deletion or weight increase in-place.

        Follows the strict decision order:
        1. Certificate check -> 'cert' (1 SCAN)
        2. Alternative support -> 'alt' (at most 1 + indeg(v) SCANs)
        3. Budgeted repair -> 'repair' (work cap B = ceil(c * F))
        4. Rebuild on BudgetExceeded -> 'fallback'
        """
        u, v = update.u, update.v
        if not self._g.has_edge(u, v):
            apply_update(self._g, update)
        old_w = self._g.weight(u, v)

        # Precompute budget using chosen f_mode before mutating main graph
        F_val = self._compute_f(update)
        budget = self._compute_budget(F_val)

        # Apply update to the maintainer's graph
        apply_update(self._g, update)

        # Decision 1: Certificate (non-tight edge or into source)
        if (
            v == self._src
            or self._state.dist[u] == INF
            or self._state.dist[u] + old_w != self._state.dist[v]
        ):
            self.last_affected = set()
            stats = UpdateStats(
                work=1,
                scan=1,
                strategy="cert",
                repair_work=0,
                fallback_work=0,
                affected_size=0,
                budget=budget,
            )
            self._last_stats = stats
            if self._verify:
                check_state(self._g, self._state)
            return stats

        # If we reach here, (u, v) was tight before update!
        dist_v = self._state.dist[v]

        # Decision 2: Alternative support (tight[v] > 1)
        if self._state.tight[v] > 1:
            self.last_affected = set()
            self._state.tight[v] -= 1

            if self._state.parent[v] != u:
                stats = UpdateStats(
                    work=1,
                    scan=1,
                    strategy="alt",
                    repair_work=0,
                    fallback_work=0,
                    affected_size=0,
                    budget=budget,
                )
                self._last_stats = stats
                if self._verify:
                    check_state(self._g, self._state)
                return stats

            # Updated edge was parent[v]: scan in-edges to find smallest replacement
            scan_count = 1
            tight_preds: list[int] = []
            for p, w in self._g.in_edges(v):
                scan_count += 1
                if self._state.dist[p] != INF and self._state.dist[p] + w == dist_v:
                    tight_preds.append(p)

            new_parent = min(tight_preds)
            self._state.children[u].remove(v)
            self._state.children[new_parent].add(v)
            self._state.parent[v] = new_parent

            stats = UpdateStats(
                work=scan_count,
                scan=scan_count,
                strategy="alt",
                repair_work=0,
                fallback_work=0,
                affected_size=0,
                budget=budget,
            )
            self._last_stats = stats
            if self._verify:
                check_state(self._g, self._state)
            return stats

        # Decision 3 & 4: Sole tight edge lost -> budgeted repair, then rebuild fallback
        aff_holder: list[set[int]] = []
        counter = OpCounter()
        try:
            repair_stats = repair(
                self._state,
                self._g,
                u,
                v,
                budget=budget,
                counter=counter,
                affected_holder=aff_holder,
            )
            affected = aff_holder[0] if aff_holder else set()
            self.last_affected = affected
            stats = UpdateStats(
                work=repair_stats.work,
                scan=repair_stats.scan,
                push=repair_stats.push,
                pop=repair_stats.pop,
                queue=repair_stats.queue,
                strategy="repair",
                repair_work=repair_stats.work,
                fallback_work=0,
                affected_size=len(affected),
                budget=budget,
            )
            self._last_stats = stats
            if self._verify:
                check_state(self._g, self._state)
            return stats

        except BudgetExceeded as exc:
            wasted_repair = exc.work if exc.work is not None else counter.work
            rebuild_counter = OpCounter()
            self._state = SPTState.build(self._g, self._src, rebuild_counter)
            self._F = self._state.F  # Update F on rebuild
            fallback_work = rebuild_counter.work
            total_work = wasted_repair + fallback_work

            self.last_affected = None
            stats = UpdateStats(
                work=total_work,
                scan=rebuild_counter.scan,
                push=rebuild_counter.push,
                pop=rebuild_counter.pop,
                queue=rebuild_counter.queue,
                strategy="fallback",
                repair_work=wasted_repair,
                fallback_work=fallback_work,
                affected_size=self._g.n,
                budget=budget,
            )
            self._last_stats = stats
            if self._verify:
                check_state(self._g, self._state)
            return stats


__all__ = ["BudgetedMaintainer"]
