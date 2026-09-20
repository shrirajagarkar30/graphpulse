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


class StateViolation(InvariantViolation):
    """Raised by check_state when SPTState does not match the graph."""


def check_state(g: DiGraph, state: Any) -> None:
    """Certify that *state* (an SPTState) is valid for graph *g*.

    Verifies:
    1. Valid source and attribute shapes (dist, parent, children, tight, F_ops).
    2. SPT conditions (a)-(d) via check_spt (optimality, triangle inequality, feasibility).
    3. tight[src] == 0 and tight[v] == 0 for all unreachable v.
    4. For all reachable v != src: tight[v] equals the exact count of tight in-edges,
       and parent[v] is one of those tight in-neighbors.
    5. Bidirectional parent <-> children consistency:
       - Every c in children[u] has parent[c] == u.
       - Every reachable non-source v has v in children[parent[v]].
       - Unreachable vertices and src are not in any children set.
       - Unreachable vertices have empty children sets.
    6. F_ops is a non-negative integer.

    Raises
    ------
    StateViolation
        If any invariant or structural check fails.
    ValueError
        If inputs have invalid types or lengths.
    """
    n = g.n
    src = getattr(state, "src", None)
    if isinstance(src, bool) or not isinstance(src, int) or not (0 <= src < n):
        raise ValueError(f"Source vertex {src!r} out of range [0, {n - 1}]")

    dist = getattr(state, "dist", None)
    parent = getattr(state, "parent", None)
    tight = getattr(state, "tight", None)
    children = getattr(state, "children", None)
    F_ops = getattr(state, "F_ops", None)

    if dist is None or len(dist) != n:
        raise ValueError(f"state.dist must have length {n}")
    if parent is None or len(parent) != n:
        raise ValueError(f"state.parent must have length {n}")
    if tight is None or len(tight) != n:
        raise ValueError(f"state.tight must have length {n}")
    if children is None or len(children) != n:
        raise ValueError(f"state.children must have length {n}")
    if not isinstance(F_ops, int) or isinstance(F_ops, bool) or F_ops < 0:
        raise StateViolation(f"state.F_ops must be a non-negative int, got {F_ops!r}")

    # (1) Check SPT invariants (optimality, triangle inequality, feasibility)
    try:
        check_spt(g, src, dist, parent)
    except InvariantViolation as exc:
        raise StateViolation(str(exc)) from exc

    # (2) Source tight count must be 0
    if tight[src] != 0:
        raise StateViolation(f"tight[src={src}] = {tight[src]}, expected 0")

    # (3) Verify tight counts and parent tight-in-neighbor property
    for v in range(n):
        if v == src:
            continue
        if dist[v] == INF:
            if tight[v] != 0:
                raise StateViolation(
                    f"Unreachable vertex {v} has tight={tight[v]}, expected 0"
                )
        else:
            # Count incoming tight edges from scratch (with INF guard)
            tight_preds: list[int] = []
            for u, w in g.in_edges(v):
                if dist[u] != INF and dist[u] + w == dist[v]:
                    tight_preds.append(u)

            if tight[v] != len(tight_preds):
                raise StateViolation(
                    f"tight[{v}] = {tight[v]}, expected {len(tight_preds)} "
                    f"(tight in-neighbors: {tight_preds})"
                )
            if parent[v] not in tight_preds:
                raise StateViolation(
                    f"parent[{v}] = {parent[v]} is not a tight in-neighbor of {v} "
                    f"(tight in-neighbors: {tight_preds})"
                )

    # (4) Bidirectional parent <-> children consistency
    for u in range(n):
        c_set = children[u]
        if not isinstance(c_set, (set, frozenset)):
            raise StateViolation(f"children[{u}] is {type(c_set)}, expected set")
        if dist[u] == INF and len(c_set) > 0:
            raise StateViolation(
                f"Unreachable vertex {u} has non-empty children set: {c_set}"
            )
        for c in c_set:
            if not isinstance(c, int) or isinstance(c, bool) or not (0 <= c < n):
                raise StateViolation(f"children[{u}] contains invalid vertex {c!r}")
            if parent[c] != u:
                raise StateViolation(
                    f"Inconsistent child link: {c} is in children[{u}], "
                    f"but parent[{c}] = {parent[c]}"
                )

    for v in range(n):
        p = parent[v]
        if p != -1:
            if v not in children[p]:
                raise StateViolation(
                    f"Inconsistent parent link: parent[{v}] = {p}, "
                    f"but {v} is not in children[{p}]"
                )
