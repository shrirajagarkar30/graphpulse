"""Maintainer protocol and the trusted recompute baseline (Milestone 2.3).

Every repair algorithm in Phase 3 must implement the `Maintainer` protocol.
The harness uses `RecomputeMaintainer` as the ground truth to validate any
candidate implementation.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Protocol, runtime_checkable

from graphpulse.dijkstra import dijkstra
from graphpulse.generators import Update, apply_update
from graphpulse.graph import DiGraph
from graphpulse.opcount import OpCounter


@dataclass
class UpdateStats:
    """Operation counts returned by a Maintainer after each apply() call.

    Repair algorithms fill these from their OpCounter; the recompute baseline
    runs a full Dijkstra and reports its op counts.
    """
    work: int = 0      # total op-count (scan + push + pop + queue)
    scan: int = 0
    push: int = 0
    pop: int = 0
    queue: int = 0


@runtime_checkable
class Maintainer(Protocol):
    """Protocol that every shortest-path maintainer must satisfy.

    dist()  -- current distance array (must be a fresh list, not a view).
    apply() -- apply one update in-place, return op-count stats.
    """

    def dist(self) -> list[float]:
        ...

    def apply(self, update: Update) -> UpdateStats:
        ...


class RecomputeMaintainer:
    """Trusted baseline: full Dijkstra after every single update.

    Keeps its own internal copy of the graph so it is never contaminated by
    a buggy candidate or by external graph mutations.
    """

    def __init__(self, g: DiGraph, src: int) -> None:
        if not isinstance(src, int) or isinstance(src, bool) or not (0 <= src < g.n):
            raise ValueError(f"Source vertex {src!r} out of range [0, {g.n - 1}]")
        self._g = g.copy()
        self._src = src
        counter = OpCounter()
        self._dist, self._parent = dijkstra(self._g, src, counter)
        self._last_stats = UpdateStats(
            work=counter.work,
            scan=counter.scan,
            push=counter.push,
            pop=counter.pop,
        )

    def dist(self) -> list[float]:
        """Return a fresh copy of the current distance array."""
        return list(self._dist)

    def parent(self) -> list[int]:
        """Return the current parent array (convenience accessor)."""
        return list(self._parent)

    def apply(self, update: Update) -> UpdateStats:
        """Apply *update* then run full Dijkstra; return op counts."""
        apply_update(self._g, update)
        counter = OpCounter()
        self._dist, self._parent = dijkstra(self._g, self._src, counter)
        self._last_stats = UpdateStats(
            work=counter.work,
            scan=counter.scan,
            push=counter.push,
            pop=counter.pop,
        )
        return self._last_stats
