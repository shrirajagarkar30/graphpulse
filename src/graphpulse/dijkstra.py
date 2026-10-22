"""Counted heap-based Dijkstra baseline (Milestone 1.2).

Implements a standard lazy-deletion Dijkstra algorithm that charges
SCAN, PUSH, and POP operations to an explicit OpCounter.

Cost model (per SPEC.md):
- SCAN : each adjacency entry examined for a *settled* vertex.
- PUSH : each heap push (only on strict distance improvement).
- POP  : each heap pop, including stale entries.

Because pushes happen only on strict improvement, at termination:
    pop == push

And scan equals exactly the sum of out-degrees of all settled vertices.
"""

from __future__ import annotations

INF = float("inf")

from graphpulse.graph import DiGraph
from graphpulse.opcount import CountedHeap, OpCounter


def dijkstra(
    g: DiGraph,
    src: int,
    counter: OpCounter,
) -> tuple[list[float], list[int]]:
    """Run counted heap-based Dijkstra from *src* on graph *g*.

    Returns
    -------
    dist   : list of length n.  dist[v] = shortest distance from src.
             INF = float("inf") for unreachable vertices.
    parent : list of length n.  parent[v] = predecessor of v on the
             shortest path from src, or -1 if v == src or v is unreachable.

    Charges to *counter*:
    - PUSH for each heap push (strict improvement only).
    - POP  for each heap pop, including stale entries.
    - SCAN for each out-edge examined of a settled vertex.
    """
    n = g.n
    # Validate source vertex using the same rules as DiGraph
    if isinstance(src, bool) or not isinstance(src, int) or not (0 <= src < n):
        raise ValueError(f"Source vertex {src!r} out of range [0, {n - 1}]")

    dist: list[float] = [INF] * n
    parent: list[int] = [-1] * n
    dist[src] = 0

    heap: CountedHeap[tuple[float, int]] = CountedHeap(counter)
    heap.push((0, src))          # PUSH charged

    while heap:
        d, u = heap.pop()        # POP charged

        # Lazy deletion: skip stale entries
        if d > dist[u]:
            continue

        # u is now settled — scan all outgoing edges
        for v, w in g.out_edges(u):
            counter.scan += 1    # SCAN charged per adjacency entry

            new_dist = dist[u] + w
            if new_dist < dist[v]:
                dist[v] = new_dist
                parent[v] = u
                heap.push((new_dist, v))  # PUSH charged

    return dist, parent
