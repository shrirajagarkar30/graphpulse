"""Shortest-path-tree state with tight-edge counters (Milestone 3.1).

`SPTState` holds the complete snapshot of the shortest-path tree that the
incremental repair algorithms operate on.  It is built from scratch by
`SPTState.build()` and validated by `verify.check_state()`.

Definitions (per SPEC.md §3 and proof P1)
-----------------------------------------
An edge (u, v, w) is *tight* when:
    dist[u] != INF  and  dist[u] + w == dist[v]

The *tight-edge subgraph* is a DAG (Claim 1 in P1_repair_correctness.md):
because all edge weights are strictly positive, dist[v] > dist[u] for every
tight edge, so there are no cycles.

Per-vertex invariants
---------------------
- tight[src]  == 0     (the source is the root; it has no tight predecessors)
- tight[v]    == 0     for unreachable v  (dist[v] == INF ⟹ no tight in-edges)
- tight[v]    >= 1     for every reachable v != src
- parent[v]   == min({ u : (u,v,w) tight })   (smallest-id tight in-neighbor;
                       deterministic choice)
- children[v] == { u : parent[u] == v }

F_ops record
------------
F_ops = dijkstra_work  +  sum_of_in_degrees_of_reachable_non_source_vertices

dijkstra_work = SCAN + PUSH + POP  (from the Dijkstra run)
The in-degree scan charges 1 per in-edge examined for each reachable v != src.
F_ops is the cost of re-building the SPT from scratch — the baseline the
budget controller compares repair work against.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from graphpulse.dijkstra import INF, dijkstra
from graphpulse.graph import DiGraph
from graphpulse.opcount import OpCounter


@dataclass
class SPTState:
    """Full shortest-path-tree snapshot.

    Attributes
    ----------
    src      : source vertex.
    dist     : dist[v] = shortest distance from src; INF for unreachable.
    parent   : parent[v] = smallest-id tight in-neighbor; -1 for src /
               unreachable.
    children : children[v] = {u : parent[u] == v}.
    tight    : tight[v] = number of tight in-edges of v.
    F_ops    : total rebuild work (Dijkstra + in-edge scan for tight counters).
    """
    src: int
    dist: list[float]
    parent: list[int]
    children: list[set[int]]
    tight: list[int]
    F_ops: int

    def copy(self) -> "SPTState":
        """Return a deep copy of the SPT state."""
        return SPTState(
            src=self.src,
            dist=list(self.dist),
            parent=list(self.parent),
            children=[set(c) for c in self.children],
            tight=list(self.tight),
            F_ops=self.F_ops,
        )

    @classmethod
    def build(cls, g: DiGraph, src: int, counter: OpCounter) -> "SPTState":
        """Build the SPT state from scratch.

        Runs counted Dijkstra (charges to *counter*), then scans in-edges of
        every reachable non-source vertex to compute tight counts and parents.

        The in-edge scan charges are added to *counter*.scan so that
        `counter.dijkstra_work + in_scan == F_ops` after the call.

        Parameters
        ----------
        g       : the graph (not mutated).
        src     : source vertex.
        counter : OpCounter to charge.  Must be freshly constructed or reset.

        Returns
        -------
        SPTState with all fields populated.
        """
        if not isinstance(src, int) or isinstance(src, bool) or not (0 <= src < g.n):
            raise ValueError(f"Source vertex {src!r} out of range [0, {g.n - 1}]")

        n = g.n
        # ---- Step 1: Dijkstra -------------------------------------------------
        dist, _ = dijkstra(g, src, counter)
        dijkstra_work = counter.dijkstra_work   # SCAN + PUSH + POP so far

        # ---- Step 2: Tight-edge scan to build tight, parent, children ---------
        parent: list[int] = [-1] * n
        tight: list[int] = [0] * n
        in_scan: int = 0

        for v in range(n):
            if v == src or dist[v] == INF:
                # tight[src] == 0 by definition (source has no tight predecessors).
                # tight[v] == 0 for unreachable v (INF guard: dist[u] + w != INF
                # for any finite dist[u]).
                continue

            tight_preds: list[int] = []
            for u, w in g.in_edges(v):
                in_scan += 1
                # INF guard: never test dist[u] + w when dist[u] is INF
                if dist[u] != INF and dist[u] + w == dist[v]:
                    tight_preds.append(u)

            tight[v] = len(tight_preds)
            if tight_preds:
                parent[v] = min(tight_preds)   # deterministic: smallest id

        # Charge the in-edge scan to the counter's scan field so the caller
        # can inspect counter.scan for total work.
        counter.scan += in_scan
        F_ops = dijkstra_work + in_scan

        # ---- Step 3: children from parent -------------------------------------
        children: list[set] = [set() for _ in range(n)]
        for v in range(n):
            if parent[v] != -1:
                children[parent[v]].add(v)

        return cls(
            src=src,
            dist=dist,
            parent=parent,
            children=children,
            tight=tight,
            F_ops=F_ops,
        )
