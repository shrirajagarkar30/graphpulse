"""Incremental shortest-path repair maintainer and abortable overlay (Milestones 3.2-4.1).

`RepairMaintainer` maintains an SPTState dynamically under non-decreasing
updates (edge deletions and weight increases).

Updates are resolved in order:
- Strategy 'cert': The updated edge was not tight (or pointed into source).
  Distances and tree structure are guaranteed invariant.  Cost: exactly 1 SCAN.
- Strategy 'alt': The updated edge was tight, but the target vertex has
  alternative tight in-edges (tight[v] > 1).  tight[v] is decremented.
  If the edge was parent[v], in-edges of v are scanned to select the
  smallest-id tight in-neighbor as the new parent.
- Strategy 'repair': Incremental repair using an `Overlay` copy-on-write wrapper
  over `SPTState`. If a budget is specified and the operations performed exceed
  the budget, `BudgetExceeded` is raised and the base state is untouched.
  On completion, `overlay.commit()` writes changes into the base state.
"""

from __future__ import annotations

from collections import deque
from typing import Generic, TypeVar

from graphpulse.dijkstra import INF
from graphpulse.generators import Update, apply_update
from graphpulse.graph import DiGraph
from graphpulse.maintainer import Maintainer, UpdateStats
from graphpulse.opcount import BudgetExceeded, CountedHeap, OpCounter
from graphpulse.spt import SPTState

T = TypeVar("T")


class DictOverlay(Generic[T]):
    """Copy-on-write mapping over a base list."""

    __slots__ = ("_base", "_dirty")

    def __init__(self, base: list[T]) -> None:
        self._base = base
        self._dirty: dict[int, T] = {}

    def __getitem__(self, idx: int) -> T:
        if idx in self._dirty:
            return self._dirty[idx]
        return self._base[idx]

    def __setitem__(self, idx: int, val: T) -> None:
        self._dirty[idx] = val

    def get(self, idx: int, default: T | None = None) -> T:
        if idx in self._dirty:
            return self._dirty[idx]
        if 0 <= idx < len(self._base):
            return self._base[idx]
        return default

    def __contains__(self, idx: object) -> bool:
        if isinstance(idx, int) and 0 <= idx < len(self._base):
            return True
        return False

    def __len__(self) -> int:
        return len(self._base)

    def commit(self) -> None:
        """Apply all dirty modifications back to the base list."""
        for idx, val in self._dirty.items():
            self._base[idx] = val


class ChildSetProxy:
    """Proxy for a children set of a specific vertex with copy-on-write semantics."""

    __slots__ = ("_overlay", "_u")

    def __init__(self, overlay: ChildrenOverlay, u: int) -> None:
        self._overlay = overlay
        self._u = u

    def _ensure_copy(self) -> set[int]:
        if self._u not in self._overlay._dirty:
            self._overlay._dirty[self._u] = set(self._overlay._base[self._u])
        return self._overlay._dirty[self._u]

    def add(self, v: int) -> None:
        self._ensure_copy().add(v)

    def discard(self, v: int) -> None:
        self._ensure_copy().discard(v)

    def remove(self, v: int) -> None:
        self._ensure_copy().remove(v)

    def __iter__(self):
        if self._u in self._overlay._dirty:
            return iter(self._overlay._dirty[self._u])
        return iter(self._overlay._base[self._u])

    def __contains__(self, v: object) -> bool:
        if self._u in self._overlay._dirty:
            return v in self._overlay._dirty[self._u]
        return v in self._overlay._base[self._u]

    def __len__(self) -> int:
        if self._u in self._overlay._dirty:
            return len(self._overlay._dirty[self._u])
        return len(self._overlay._base[self._u])

    def copy(self) -> set[int]:
        if self._u in self._overlay._dirty:
            return set(self._overlay._dirty[self._u])
        return set(self._overlay._base[self._u])


class ChildrenOverlay:
    """Copy-on-write mapping for children adjacency sets."""

    __slots__ = ("_base", "_dirty")

    def __init__(self, base: list[set[int]]) -> None:
        self._base = base
        self._dirty: dict[int, set[int]] = {}

    def __getitem__(self, u: int) -> ChildSetProxy:
        return ChildSetProxy(self, u)

    def __setitem__(self, u: int, new_set: set[int]) -> None:
        self._dirty[u] = set(new_set)

    def __len__(self) -> int:
        return len(self._base)

    def commit(self) -> None:
        """Apply all modified child sets back to the base list."""
        for u, s in self._dirty.items():
            self._base[u] = s


class Overlay:
    """Copy-on-write overlay sitting on top of SPTState.

    Reads check the overlay first, falling back to base SPTState.
    Writes go strictly to the overlay's dirty dictionaries.
    Calling commit() applies all dirty entries to the base state.
    Discarding the overlay leaves base state completely untouched.
    """

    __slots__ = ("_base", "dist", "parent", "tight", "children")

    def __init__(self, base: SPTState) -> None:
        self._base = base
        self.dist = DictOverlay(base.dist)
        self.parent = DictOverlay(base.parent)
        self.tight = DictOverlay(base.tight)
        self.children = ChildrenOverlay(base.children)

    @property
    def base(self) -> SPTState:
        """Reference to the underlying base SPTState."""
        return self._base

    @property
    def src(self) -> int:
        """Source vertex."""
        return self._base.src

    @property
    def F(self) -> int:
        """Work of full rebuild."""
        return self._base.F

    def commit(self) -> None:
        """Apply all overlaid modifications to the underlying SPTState."""
        self.dist.commit()
        self.parent.commit()
        self.tight.commit()
        self.children.commit()

    @property
    def has_changes(self) -> bool:
        """Return True if any entry has been written to the overlay."""
        return bool(
            self.dist._dirty
            or self.parent._dirty
            or self.tight._dirty
            or self.children._dirty
        )


def find_affected(
    state: SPTState | Overlay,
    g: DiGraph,
    v: int,
    counter: OpCounter | None = None,
    return_scratch: bool = False,
) -> set[int] | tuple[set[int], dict[int, int]]:
    """Identify the exact set of vertices whose shortest-path distance changes.

    This function is pure with respect to *state* and *g*.

    Parameters
    ----------
    state          : SPTState or Overlay before the update.
    g              : DiGraph after the edge removal/increase.
    v              : Head of the updated edge that lost its sole tight in-edge.
    counter        : Optional OpCounter charging QUEUE (enqueue + dequeue) and SCAN
                     (out-edge examination).
    return_scratch : If True, returns (A, scratch_tight). Otherwise returns A.

    Returns
    -------
    set[int] or tuple[set[int], dict[int, int]]
        The exact set of affected vertices A, optionally with scratch tight counts.
    """
    if counter is None:
        counter = OpCounter()

    if v == state.src or state.dist[v] == INF:
        return (set(), {}) if return_scratch else set()

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

    if return_scratch:
        return A, scratch_tight
    return A


def repair(
    state: SPTState,
    g: DiGraph,
    u: int,
    v: int,
    budget: int | None = None,
    counter: OpCounter | None = None,
    affected_holder: list[set[int]] | None = None,
) -> UpdateStats:
    """Incrementally repair the SPT after deletion or weight increase of
    tight edge (u, v) where v has sole tight in-edge (tight[v] <= 1).

    If budget is not None and the repair work exceeds budget, BudgetExceeded
    is raised and *state* is left completely unmodified.
    On success, changes are committed to *state*.
    """
    if counter is None:
        counter = OpCounter()

    # Configure budget on counter (delta from current work)
    counter.budget = budget
    counter.start_work = counter.work

    # Certificate test examined the edge (u, v): charge 1 SCAN
    counter.scan += 1

    overlay = Overlay(state)

    # Step 1: Identify affected set A and scratch decrements
    A, scratch_tight = find_affected(
        overlay, g, v, counter=counter, return_scratch=True
    )
    if affected_holder is not None:
        affected_holder.append(A)

    if not A:
        overlay.commit()
        return UpdateStats(
            work=counter.work,
            scan=counter.scan,
            push=counter.push,
            pop=counter.pop,
            queue=counter.queue,
            strategy="repair",
        )

    # Step 2: Identify boundary nodes and record old parents
    boundary_nodes = list({c for x in A for c in overlay.children[x] if c not in A})
    old_parents: dict[int, int] = {x: overlay.parent[x] for x in A}
    for z in boundary_nodes:
        old_parents[z] = overlay.parent[z]

    # Step 3: Initialize local Dijkstra for A
    for x in A:
        overlay.dist[x] = INF
        overlay.parent[x] = -1

    heap: CountedHeap[tuple[float, int]] = CountedHeap(counter)
    for x in A:
        best_cand: float = INF
        for y, w in g.in_edges(x):
            counter.scan += 1
            if y not in A and overlay.dist[y] != INF:
                cand_d = overlay.dist[y] + w
                if cand_d < best_cand:
                    best_cand = cand_d
        if best_cand != INF:
            overlay.dist[x] = best_cand
            heap.push((best_cand, x))

    # Step 4: Run Dijkstra restricted to A
    while heap:
        d, curr = heap.pop()
        if d > overlay.dist[curr]:
            continue  # Stale entry

        for z, w in g.out_edges(curr):
            counter.scan += 1
            if z not in A:
                continue
            new_d = overlay.dist[curr] + w
            if new_d < overlay.dist[z]:
                overlay.dist[z] = new_d
                heap.push((new_d, z))

    # Step 5: Recompute tight[x] and pick parent for every x in A
    for x in A:
        if overlay.dist[x] == INF:
            overlay.tight[x] = 0
            overlay.parent[x] = -1
        else:
            tight_preds: list[int] = []
            for y, w in g.in_edges(x):
                counter.scan += 1
                if overlay.dist[y] != INF and overlay.dist[y] + w == overlay.dist[x]:
                    tight_preds.append(y)
            overlay.tight[x] = len(tight_preds)
            overlay.parent[x] = min(tight_preds) if tight_preds else -1

    # Step 6: Apply scratch decrements to tight[z] for z outside A
    for z, remaining_tight in scratch_tight.items():
        if z not in A:
            overlay.tight[z] = remaining_tight

    # Step 7: For each z outside A whose parent was in A, choose a new tight parent
    for z in boundary_nodes:
        tight_preds = []
        for y, w in g.in_edges(z):
            counter.scan += 1
            if overlay.dist[y] != INF and overlay.dist[y] + w == overlay.dist[z]:
                tight_preds.append(y)
        overlay.parent[z] = min(tight_preds) if tight_preds else -1

    # Step 8: Rebuild children links for all changed parents
    for node, old_p in old_parents.items():
        new_p = overlay.parent[node]
        if old_p != new_p:
            if old_p != -1:
                overlay.children[old_p].discard(node)
            if new_p != -1:
                overlay.children[new_p].add(node)

    # Commit all changes to the underlying state
    overlay.commit()

    return UpdateStats(
        work=counter.work,
        scan=counter.scan,
        push=counter.push,
        pop=counter.pop,
        queue=counter.queue,
        strategy="repair",
    )


class RepairMaintainer:
    """Dynamic shortest-path maintainer with zero-work certificate, alternative
    support, and abortable budgeted repair.
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

    def apply(self, update: Update, budget: int | None = None) -> UpdateStats:
        """Apply an edge deletion or weight increase in-place.

        Parameters
        ----------
        update : Update
            Edge deletion or weight increase.
        budget : int | None
            Maximum allowed work for repair if update requires repair.
            If exceeded, BudgetExceeded is raised and state is unchanged.

        Returns
        -------
        UpdateStats
            Operation counts and strategy ('cert', 'alt', or 'repair').
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

        # Non-tight edge: unreachable u or dist[u] + old_w != dist_v
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

        # Sole tight edge lost (tight[v] <= 1):
        return self._repair(u, v, budget=budget)

    def _repair_delete(self, u: int, v: int, budget: int | None = None) -> UpdateStats:
        """Backward-compatible alias for _repair."""
        return self._repair(u, v, budget=budget)

    def _repair(self, u: int, v: int, budget: int | None = None) -> UpdateStats:
        """Incrementally repair the SPT after deletion or weight increase of
        tight edge (u, v) where v has sole tight in-edge (tight[v] <= 1).
        """
        aff_holder: list[set[int]] = []
        counter = OpCounter()
        stats = repair(
            self._state,
            self._g,
            u,
            v,
            budget=budget,
            counter=counter,
            affected_holder=aff_holder,
        )
        self.last_affected = aff_holder[0] if aff_holder else set()
        self._last_stats = stats
        return stats

    def repair(self, u: int, v: int, budget: int | None = None) -> UpdateStats:
        """Public alias for _repair."""
        return self._repair(u, v, budget=budget)


__all__ = [
    "BudgetExceeded",
    "DictOverlay",
    "ChildSetProxy",
    "ChildrenOverlay",
    "Overlay",
    "find_affected",
    "repair",
    "RepairMaintainer",
]
