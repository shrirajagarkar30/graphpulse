"""Incremental shortest-path repair maintainer (Milestone 3.2).

`RepairMaintainer` maintains an SPTState dynamically under non-decreasing
updates (edge deletions and weight increases).

In Milestone 3.2, cheap updates are resolved immediately:
- Strategy 'cert': The updated edge was not tight (or pointed into source).
  Distances and tree structure are guaranteed invariant.  Cost: exactly 1 SCAN.
- Strategy 'alt': The updated edge was tight, but the target vertex has
  alternative tight in-edges (tight[v] > 1).  tight[v] is decremented.
  If the edge was parent[v], in-edges of v are scanned to select the
  smallest-id tight in-neighbor as the new parent.
- Strategy 'rebuild': Unhandled cases (sole tight edge lost) fall back to a
  full from-scratch build using SPTState.build until Milestone 3.4 replaces
  the fallback with bounded repair.
"""

from __future__ import annotations

from collections import deque

from graphpulse.dijkstra import INF
from graphpulse.generators import Update, apply_update
from graphpulse.graph import DiGraph
from graphpulse.maintainer import Maintainer, UpdateStats
from graphpulse.opcount import OpCounter
from graphpulse.spt import SPTState


def find_affected(
    state: SPTState,
    g: DiGraph,
    v: int,
    counter: OpCounter | None = None,
) -> set[int]:
    """Identify the exact set of vertices whose shortest-path distance changes.

    This function is pure: it never mutates *state* or *g*.

    Parameters
    ----------
    state   : SPTState before the update.
    g       : DiGraph after the edge removal/increase.
    v       : Head of the updated edge that lost its sole tight in-edge.
    counter : Optional OpCounter charging QUEUE (enqueue + dequeue) and SCAN
              (out-edge examination).

    Returns
    -------
    set[int]
        The exact set of affected vertices A.
    """
    if counter is None:
        counter = OpCounter()

    if v == state.src or state.dist[v] == INF:
        return set()

    A: set[int] = {v}
    queue: deque[int] = deque([v])
    counter.queue += 1  # Enqueue v

    scratch_tight: dict[int, int] = {}

    while queue:
        x = queue.popleft()
        counter.queue += 1  # Dequeue x
        dist_x = state.dist[x]

        for z, w in g.out_edges(x):
            counter.scan += 1

            if z == state.src or z in A:
                continue

            dist_z = state.dist[z]
            # Edge must be tight under the OLD distances
            if dist_x != INF and dist_x + w == dist_z:
                current_tight = scratch_tight.get(z, state.tight[z]) - 1
                scratch_tight[z] = current_tight
                if current_tight == 0:
                    A.add(z)
                    queue.append(z)
                    counter.queue += 1  # Enqueue z

    return A


class RepairMaintainer:
    """Dynamic shortest-path maintainer with zero-work certificate, alternative
    support, and fallback rebuild.
    """

    def __init__(self, g: DiGraph, src: int) -> None:
        """Initialize maintainer with graph g and source vertex src."""
        if isinstance(src, bool) or not isinstance(src, int) or not (0 <= src < g.n):
            raise ValueError(f"Source vertex {src!r} out of range [0, {g.n - 1}]")
        self._g = g.copy()
        self._src = src
        self.last_affected: set[int] | None = None
        counter = OpCounter()
        self._state = SPTState.build(self._g, self._src, counter)
        self._last_stats = UpdateStats(
            work=counter.work,
            scan=counter.scan,
            push=counter.push,
            pop=counter.pop,
            queue=counter.queue,
            strategy="rebuild",
        )

    def dist(self) -> list[float]:
        """Return a fresh copy of current shortest-path distances."""
        return list(self._state.dist)

    def parent(self) -> list[int]:
        """Return a fresh copy of current shortest-path tree parents."""
        return list(self._state.parent)

    @property
    def state(self) -> SPTState:
        """Return the internal SPTState."""
        return self._state

    @property
    def graph(self) -> DiGraph:
        """Return the internal DiGraph."""
        return self._g

    @property
    def last_stats(self) -> UpdateStats:
        """Return the UpdateStats produced by the most recent apply() call."""
        return self._last_stats

    def _rebuild(self) -> UpdateStats:
        """Execute a full rebuild from scratch using SPTState.build."""
        counter = OpCounter()
        self._state = SPTState.build(self._g, self._src, counter)
        stats = UpdateStats(
            work=counter.work,
            scan=counter.scan,
            push=counter.push,
            pop=counter.pop,
            queue=counter.queue,
            strategy="rebuild",
        )
        self._last_stats = stats
        return stats

    def apply(self, update: Update) -> UpdateStats:
        """Apply an edge deletion or weight increase in-place.

        Returns
        -------
        UpdateStats
            Operation counts and strategy ('cert', 'alt', or 'rebuild').
        """
        u, v = update.u, update.v
        # Precondition check & extract old weight before mutation
        old_w = self._g.weight(u, v)

        # Apply update to the graph first
        apply_update(self._g, update)

        # Certificate 1: Edge into source or non-tight edge
        # An edge into source is never tight (dist[src] == 0 and weights >= 1).
        if v == self._src:
            self.last_affected = set()
            stats = UpdateStats(work=1, scan=1, strategy="cert")
            self._last_stats = stats
            return stats

        dist_u = self._state.dist[u]
        dist_v = self._state.dist[v]

        # Non-tight edge: unreachable u or dist[u] + old_w != dist[v]
        if dist_u == INF or dist_u + old_w != dist_v:
            self.last_affected = set()
            stats = UpdateStats(work=1, scan=1, strategy="cert")
            self._last_stats = stats
            return stats

        # If we reach here, (u, v) was tight before the update!
        # The certificate check examined the edge: 1 SCAN.
        # Now (u, v) is no longer tight (deleted, or increased so dist[u] + new_w > dist[v]).
        if self._state.tight[v] > 1:
            # Alternative support case: v has at least one other tight in-edge
            self.last_affected = set()
            self._state.tight[v] -= 1

            if self._state.parent[v] != u:
                # The updated edge was not the SPT tree parent of v; tree unchanged
                stats = UpdateStats(work=1, scan=1, strategy="alt")
                self._last_stats = stats
                return stats

            # The updated edge WAS the SPT parent of v: scan in-edges to find replacement
            scan_count = 1  # 1 scan for the initial certificate check
            tight_preds: list[int] = []
            for p, w in self._g.in_edges(v):
                scan_count += 1
                if self._state.dist[p] != INF and self._state.dist[p] + w == dist_v:
                    tight_preds.append(p)

            new_parent = min(tight_preds)
            self._state.children[u].remove(v)
            self._state.children[new_parent].add(v)
            self._state.parent[v] = new_parent

            stats = UpdateStats(work=scan_count, scan=scan_count, strategy="alt")
            self._last_stats = stats
            return stats

        # Sole tight edge lost (tight[v] <= 1): compute affected set for inspection
        self.last_affected = find_affected(self._state, self._g, v)
        return self._rebuild()
