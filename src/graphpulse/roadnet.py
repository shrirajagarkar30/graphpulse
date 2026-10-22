"""Road-network loader and preprocessing (Milestone 7.1).

Reads directed road graphs in the DIMACS `.gr` format (integer weights),
cleans them (self-loops dropped, duplicate arcs collapsed to the minimum
weight, non-positive / non-integer weights rejected), extracts the largest
strongly connected component with an *iterative* algorithm (road graphs are
deep; no recursion) and samples small strongly connected subgraphs.

DIMACS format:  `c` comment lines, one `p sp <n> <m>` header, then
`a <u> <v> <w>` arcs with 1-based vertex ids.
"""

from __future__ import annotations

import hashlib
import random
from collections import deque
from pathlib import Path

from graphpulse.graph import DiGraph


def load_gr(path: str | Path) -> DiGraph:
    """Parse a DIMACS `.gr` file into a cleaned simple DiGraph (0-based ids).

    Raises ValueError (naming the line number where applicable) on malformed
    input, a missing header, ids outside 1..n, an arc count different from the
    header, or an empty file.
    """
    n = m_decl = None
    arcs: dict[tuple[int, int], int] = {}
    arc_lines = 0
    with open(path, "r", encoding="utf-8") as f:
        for lineno, raw in enumerate(f, start=1):
            line = raw.strip()
            if not line or line[0] == "c":
                continue
            parts = line.split()
            tag = parts[0]
            if tag == "p":
                if n is not None:
                    raise ValueError(f"line {lineno}: duplicate header")
                if len(parts) != 4 or parts[1] != "sp":
                    raise ValueError(f"line {lineno}: malformed header {line!r}")
                try:
                    n, m_decl = int(parts[2]), int(parts[3])
                except ValueError:
                    raise ValueError(f"line {lineno}: non-integer header fields {line!r}") from None
                if n < 0 or m_decl < 0:
                    raise ValueError(f"line {lineno}: negative header fields")
            elif tag == "a":
                if n is None:
                    raise ValueError(f"line {lineno}: arc before header")
                if len(parts) != 4:
                    raise ValueError(f"line {lineno}: malformed arc {line!r}")
                try:
                    u, v = int(parts[1]), int(parts[2])
                except ValueError:
                    raise ValueError(f"line {lineno}: non-integer vertex id in {line!r}") from None
                try:
                    w = int(parts[3])
                except ValueError:
                    raise ValueError(f"line {lineno}: weight must be a positive integer, got {parts[3]!r}") from None
                if w <= 0:
                    raise ValueError(f"line {lineno}: weight must be a positive integer, got {w}")
                if not (1 <= u <= n and 1 <= v <= n):
                    raise ValueError(f"line {lineno}: vertex id outside 1..{n} in {line!r}")
                arc_lines += 1
                if u == v:
                    continue                                   # self-loop dropped
                key = (u - 1, v - 1)
                if key not in arcs or w < arcs[key]:
                    arcs[key] = w                              # duplicates keep the minimum
            else:
                raise ValueError(f"line {lineno}: unknown line type {tag!r}")
    if n is None:
        raise ValueError("empty or header-less .gr file")
    if arc_lines != m_decl:
        raise ValueError(f"header declares {m_decl} arcs but file has {arc_lines}")
    g = DiGraph(n)
    for (u, v), w in arcs.items():
        g.add_edge(u, v, w)
    return g


def largest_scc(g: DiGraph) -> list[int]:
    """Vertices of the largest strongly connected component (sorted).

    Iterative Tarjan.  Ties between equally large components are broken by the
    smallest vertex id, so the result is deterministic.
    """
    n = g.n
    index = [-1] * n
    low = [0] * n
    on_stack = [False] * n
    stack: list[int] = []
    counter = 0
    best: list[int] = []
    adj = [[v for v, _ in g.out_edges(u)] for u in range(n)]

    for root in range(n):
        if index[root] != -1:
            continue
        work = [(root, 0)]
        index[root] = low[root] = counter
        counter += 1
        stack.append(root)
        on_stack[root] = True
        while work:
            u, i = work[-1]
            if i < len(adj[u]):
                work[-1] = (u, i + 1)
                v = adj[u][i]
                if index[v] == -1:
                    index[v] = low[v] = counter
                    counter += 1
                    stack.append(v)
                    on_stack[v] = True
                    work.append((v, 0))
                elif on_stack[v]:
                    low[u] = min(low[u], index[v])
            else:
                work.pop()
                if work:
                    p = work[-1][0]
                    low[p] = min(low[p], low[u])
                if low[u] == index[u]:
                    comp = []
                    while True:
                        x = stack.pop()
                        on_stack[x] = False
                        comp.append(x)
                        if x == u:
                            break
                    comp.sort()
                    if len(comp) > len(best) or (len(comp) == len(best) and comp and best and comp[0] < best[0]):
                        best = comp
    return best


def induced_subgraph(g: DiGraph, vertices: list[int] | set[int]) -> tuple[DiGraph, dict[int, int]]:
    """Subgraph induced by *vertices*, relabelled 0..n'-1 in increasing old-id order.

    Returns (subgraph, mapping old_id -> new_id).  Weights are preserved.
    """
    order = sorted(set(vertices))
    for v in order:
        if not (0 <= v < g.n):
            raise ValueError(f"vertex {v} out of range [0, {g.n - 1}]")
    mapping = {old: new for new, old in enumerate(order)}
    sub = DiGraph(len(order))
    for old in order:
        for v, w in g.out_edges(old):
            if v in mapping:
                sub.add_edge(mapping[old], mapping[v], w)
    return sub, mapping


def bfs_ball(g: DiGraph, center: int, size: int) -> tuple[DiGraph, dict[int, int]]:
    """Grow a BFS ball over the undirected view until *size* vertices, keep its largest SCC.

    Returns (strongly connected subgraph with at most *size* vertices, mapping).
    """
    if not (0 <= center < g.n):
        raise ValueError(f"center {center} out of range")
    if size < 1:
        raise ValueError("size must be >= 1")
    seen = {center}
    order = [center]
    q = deque([center])
    while q and len(order) < size:
        u = q.popleft()
        nbrs = sorted({v for v, _ in g.out_edges(u)} | {v for v, _ in g.in_edges(u)})
        for v in nbrs:
            if v not in seen:
                seen.add(v)
                order.append(v)
                q.append(v)
                if len(order) >= size:
                    break
    ball, ball_map = induced_subgraph(g, order)
    comp = largest_scc(ball)
    sub, m2 = induced_subgraph(ball, comp)
    inv = {new: old for old, new in ball_map.items()}
    mapping = {inv[b]: new for b, new in m2.items()}
    return sub, mapping


def pick_terminals(g: DiGraph, k: int, seed: int) -> list[int]:
    """k+1 distinct vertices (index 0 = depot), deterministic in (n, k, seed)."""
    if k < 0 or k + 1 > g.n:
        raise ValueError(f"need 0 <= k and k+1 <= n={g.n}, got k={k}")
    return random.Random(seed).sample(range(g.n), k + 1)


def sha256_file(path: str | Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


__all__ = ["bfs_ball", "induced_subgraph", "largest_scc", "load_gr", "pick_terminals", "sha256_file"]
