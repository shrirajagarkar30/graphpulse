"""Shortest-path invariant checker (Milestone 1.3).

`check_spt` certifies that a (dist, parent) pair is a valid shortest-path
tree rooted at src in graph g, regardless of which algorithm produced it.
Raises InvariantViolation with a precise, human-readable message on any
deviation.

Four conditions checked (per SPEC.md §3):
  (a) dist[src] == 0
  (b) For every edge (u, v, w) with dist[u] != INF:
        dist[v] <= dist[u] + w            (triangle inequality / feasibility)
  (c) For every reachable v != src:
        parent[v] is a valid vertex,
        the edge (parent[v], v) exists,
        it is tight (dist[parent[v]] + w == dist[v]),
        and dist[parent[v]] < dist[v]     (no zero-weight cycles; weights > 0 guarantees this)
  (d) Every unreachable vertex has dist == INF and parent == -1.

Conditions (b) + (c) together prove optimality: feasibility shows no
path can be shorter; the parent chain shows a path achieving the distance.
"""

from __future__ import annotations

from graphpulse.dijkstra import INF
from graphpulse.graph import DiGraph


class InvariantViolation(Exception):
    """Raised by check_spt when the (dist, parent) pair is invalid."""


def check_spt(
    g: DiGraph,
    src: int,
    dist: list[float],
    parent: list[int],
) -> None:
    """Certify that (dist, parent) is a valid shortest-path tree from src in g.

    Raises
    ------
    InvariantViolation
        If any condition is violated. The message names the vertex or edge
        that caused the failure.
    ValueError
        If src is out of range, or dist/parent have wrong length.
    """
    n = g.n
    if isinstance(src, bool) or not isinstance(src, int) or not (0 <= src < n):
        raise ValueError(f"Source vertex {src!r} out of range [0, {n - 1}]")
    if len(dist) != n:
        raise ValueError(f"dist has length {len(dist)}, expected {n}")
    if len(parent) != n:
        raise ValueError(f"parent has length {len(parent)}, expected {n}")

    # (a) Source distance must be zero
    if dist[src] != 0:
        raise InvariantViolation(
            f"Condition (a) violated: dist[src={src}] = {dist[src]!r}, expected 0"
        )

    # (b) Triangle inequality: for every edge (u, v, w) with finite dist[u],
    #     dist[v] must be <= dist[u] + w.
    for u in range(n):
        if dist[u] == INF:
            continue
        for v, w in g.out_edges(u):
            if dist[v] > dist[u] + w:
                raise InvariantViolation(
                    f"Condition (b) violated: edge ({u}, {v}, w={w}) — "
                    f"dist[{v}]={dist[v]} > dist[{u}] + {w} = {dist[u] + w}"
                )

    # (c) and (d): Check every vertex
    for v in range(n):
        if v == src:
            if parent[src] != -1:
                raise InvariantViolation(
                    f"Condition (c) violated: parent[src={src}] = {parent[src]!r}, expected -1"
                )
            continue

        if dist[v] == INF:
            # Condition (d): unreachable vertex must have parent == -1
            if parent[v] != -1:
                raise InvariantViolation(
                    f"Condition (d) violated: unreachable vertex {v} has "
                    f"parent={parent[v]!r}, expected -1"
                )
        else:
            # Condition (c): reachable vertex v != src must have a valid tight parent edge
            p = parent[v]
            if p < 0 or p >= n:
                raise InvariantViolation(
                    f"Condition (c) violated: reachable vertex {v} has "
                    f"invalid parent={p!r}"
                )
            if not g.has_edge(p, v):
                raise InvariantViolation(
                    f"Condition (c) violated: reachable vertex {v} has parent={p}, "
                    f"but edge ({p}, {v}) does not exist"
                )
            w = g.weight(p, v)
            # Parent must be reachable
            if dist[p] == INF:
                raise InvariantViolation(
                    f"Condition (c) violated: vertex {v} is reachable but its "
                    f"parent {p} is unreachable (dist[{p}] = INF)"
                )
            # Edge must be tight: dist[p] + w == dist[v]
            if dist[p] + w != dist[v]:
                raise InvariantViolation(
                    f"Condition (c) violated: parent edge ({p}, {v}, w={w}) is not tight — "
                    f"dist[{p}] + {w} = {dist[p] + w} != dist[{v}] = {dist[v]}"
                )
            # dist must strictly decrease along parent (positive weights guarantee this
            # if edge is tight, but check explicitly for clarity)
            if dist[p] >= dist[v]:
                raise InvariantViolation(
                    f"Condition (c) violated: dist[parent[{v}]={p}] = {dist[p]} "
                    f">= dist[{v}] = {dist[v]}"
                )
