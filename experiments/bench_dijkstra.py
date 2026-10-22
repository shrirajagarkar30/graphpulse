"""Benchmark: Dijkstra work on a 100x100 directed grid (Milestone 1.3).

Run with:
    python experiments/bench_dijkstra.py

Output is NOT committed (experiments/output/ is gitignored).
"""

from __future__ import annotations

from graphpulse.dijkstra import dijkstra
from graphpulse.graph import DiGraph
from graphpulse.opcount import OpCounter
from graphpulse.verify import check_spt


def build_grid(rows: int, cols: int) -> tuple[DiGraph, int]:
    """Build a directed grid graph with right and down edges, weight=1.

    Vertex (r, c) has index r * cols + c.
    Edges: right (r,c)→(r,c+1), down (r,c)→(r+1,c).
    """
    n = rows * cols
    g = DiGraph(n)
    for r in range(rows):
        for c in range(cols):
            v = r * cols + c
            if c + 1 < cols:
                g.add_edge(v, v + 1, 1)        # right
            if r + 1 < rows:
                g.add_edge(v, v + cols, 1)     # down
    src = 0  # top-left corner
    return g, src


def main() -> None:
    rows, cols = 100, 100
    print(f"Building {rows}x{cols} directed grid ({rows * cols} vertices)...")
    g, src = build_grid(rows, cols)
    print(f"  n={g.n}, m={g.m}")

    counter = OpCounter()
    dist, parent = dijkstra(g, src, counter)
    check_spt(g, src, dist, parent)

    bottom_right = (rows - 1) * cols + (cols - 1)
    print(f"\nDijkstra results:")
    print(f"  dist[bottom-right vertex {bottom_right}] = {dist[bottom_right]}")
    print(f"  Expected shortest path length: {(rows - 1) + (cols - 1)} (Manhattan distance)")
    print(f"\nOperation counts:")
    print(f"  SCAN  = {counter.scan}")
    print(f"  PUSH  = {counter.push}")
    print(f"  POP   = {counter.pop}")
    print(f"  dijkstra_work (F) = {counter.dijkstra_work}")
    print(f"\nInvariant check: PASSED")


if __name__ == "__main__":
    main()
