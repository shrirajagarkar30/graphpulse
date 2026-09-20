"""Deterministic graph generators for testing and experiments (Milestone 2.1).

All generators use `random.Random(seed)` — never the global random state —
so results are bit-identical across machines and Python versions given the
same seed.

Every generator validates its parameters and returns a fully validated DiGraph.

Generator catalogue
-------------------
grid(rows, cols, seed, wmin, wmax)
    Road-like grid: every adjacent (horizontal and vertical) pair of cells is
    connected by *two independent directed edges* (one in each direction),
    each with an independently drawn integer weight in [wmin, wmax].

random_sparse(n, m, seed, wmin, wmax)
    Simple directed graph with exactly n vertices and m edges, chosen uniformly
    at random from all valid non-self-loop, non-duplicate directed pairs.

hub_spoke(hubs, spokes_per_hub, seed, wmin=1, wmax=10)
    Hub-and-spoke topology: hub vertices 0..hubs-1, each with spokes_per_hub
    dedicated spoke vertices.  Edges: hub→spoke and spoke→hub, with
    independently drawn weights.

comb_adversarial(n, seed=0, K=None)
    Worst-case repair family.  For vertices 0..n-1:
    - Chain forward : i → i+1, weight 1, for i in 0..n-2.
    - Chain back    : i+1 → i, weight 1, for i in 0..n-2.
    - Shortcuts     : 0 → i, weight i+K, for i >= 2.
    Default K = n (any K > 0 suffices; K = n makes shortcuts clearly heavier).

    Adversarial property: before deleting (0,1), dist[i] = i for all i>=1
    (the chain is shortest).  After deleting (0,1), all distances increase
    (dist[i] = i+K for i>=2, dist[1] = K+3).  The affected set is exactly
    {1, 2, ..., n-1}, i.e. every non-source vertex.
"""

from __future__ import annotations

import random as _random

from graphpulse.graph import DiGraph


def _validate_weight_range(wmin: int, wmax: int) -> None:
    if not isinstance(wmin, int) or isinstance(wmin, bool) or wmin <= 0:
        raise ValueError(f"wmin must be a positive integer, got {wmin!r}")
    if not isinstance(wmax, int) or isinstance(wmax, bool) or wmax <= 0:
        raise ValueError(f"wmax must be a positive integer, got {wmax!r}")
    if wmin > wmax:
        raise ValueError(f"wmin={wmin} must be <= wmax={wmax}")


def grid(
    rows: int,
    cols: int,
    seed: int = 0,
    wmin: int = 1,
    wmax: int = 10,
) -> DiGraph:
    """Generate a road-like directed grid with bidirectional edges.

    Each adjacent cell pair (horizontal and vertical) is connected by two
    independent directed edges with independently sampled integer weights.

    Parameters
    ----------
    rows, cols : positive integers (each >= 1).
    seed       : RNG seed for reproducibility.
    wmin, wmax : inclusive weight range (positive integers).

    Vertex numbering: vertex(r, c) = r * cols + c.

    Edge count for rows >= 1, cols >= 1:
        horizontal pairs : rows * (cols - 1)  -> * 2 directed edges
        vertical pairs   : (rows - 1) * cols  -> * 2 directed edges
        total m = 2 * [rows*(cols-1) + (rows-1)*cols]
    """
    if not isinstance(rows, int) or isinstance(rows, bool) or rows <= 0:
        raise ValueError(f"rows must be a positive integer, got {rows!r}")
    if not isinstance(cols, int) or isinstance(cols, bool) or cols <= 0:
        raise ValueError(f"cols must be a positive integer, got {cols!r}")
    _validate_weight_range(wmin, wmax)

    rng = _random.Random(seed)
    n = rows * cols
    g = DiGraph(n)

    def v(r: int, c: int) -> int:
        return r * cols + c

    for r in range(rows):
        for c in range(cols):
            u = v(r, c)
            # Horizontal: right neighbor
            if c + 1 < cols:
                vr = v(r, c + 1)
                g.add_edge(u, vr, rng.randint(wmin, wmax))
                g.add_edge(vr, u, rng.randint(wmin, wmax))
            # Vertical: down neighbor
            if r + 1 < rows:
                vd = v(r + 1, c)
                g.add_edge(u, vd, rng.randint(wmin, wmax))
                g.add_edge(vd, u, rng.randint(wmin, wmax))

    return g


def random_sparse(
    n: int,
    m: int,
    seed: int = 0,
    wmin: int = 1,
    wmax: int = 10,
) -> DiGraph:
    """Generate a simple directed graph with exactly n vertices and m edges.

    Edges are sampled uniformly at random (without replacement) from all
    n*(n-1) valid directed pairs, then assigned random weights.

    Parameters
    ----------
    n    : number of vertices (>= 1).
    m    : number of directed edges; must satisfy 0 <= m <= n*(n-1).
    seed : RNG seed.
    """
    if not isinstance(n, int) or isinstance(n, bool) or n <= 0:
        raise ValueError(f"n must be a positive integer, got {n!r}")
    if not isinstance(m, int) or isinstance(m, bool) or m < 0:
        raise ValueError(f"m must be a non-negative integer, got {m!r}")
    max_edges = n * (n - 1)
    if m > max_edges:
        raise ValueError(f"m={m} exceeds maximum {max_edges} edges for n={n}")
    _validate_weight_range(wmin, wmax)

    rng = _random.Random(seed)
    all_pairs = [(u, v) for u in range(n) for v in range(n) if u != v]
    chosen = rng.sample(all_pairs, m)
    g = DiGraph(n)
    for u, v in chosen:
        g.add_edge(u, v, rng.randint(wmin, wmax))
    return g


def hub_spoke(
    hubs: int,
    spokes_per_hub: int,
    seed: int = 0,
    wmin: int = 1,
    wmax: int = 10,
) -> DiGraph:
    """Generate a hub-and-spoke graph.

    Vertex layout:
    - Hubs      : 0 .. hubs - 1
    - Spokes    : hubs .. hubs + hubs*spokes_per_hub - 1
      Hub i owns spokes: hubs + i*spokes_per_hub .. hubs + (i+1)*spokes_per_hub - 1

    Edges (bidirectional, independent weights):
    - hub → spoke  (weight drawn from [wmin, wmax])
    - spoke → hub  (weight drawn independently from [wmin, wmax])

    Parameters
    ----------
    hubs           : number of hub vertices (>= 1).
    spokes_per_hub : number of spoke vertices per hub (>= 1).
    seed           : RNG seed.
    """
    if not isinstance(hubs, int) or isinstance(hubs, bool) or hubs <= 0:
        raise ValueError(f"hubs must be a positive integer, got {hubs!r}")
    if not isinstance(spokes_per_hub, int) or isinstance(spokes_per_hub, bool) or spokes_per_hub <= 0:
        raise ValueError(f"spokes_per_hub must be a positive integer, got {spokes_per_hub!r}")
    _validate_weight_range(wmin, wmax)

    rng = _random.Random(seed)
    n = hubs + hubs * spokes_per_hub
    g = DiGraph(n)

    for h in range(hubs):
        hub_v = h
        for s_idx in range(spokes_per_hub):
            spoke_v = hubs + h * spokes_per_hub + s_idx
            g.add_edge(hub_v, spoke_v, rng.randint(wmin, wmax))
            g.add_edge(spoke_v, hub_v, rng.randint(wmin, wmax))

    return g


def comb_adversarial(
    n: int,
    seed: int = 0,
    K: int | None = None,
) -> DiGraph:
    """Generate the worst-case adversarial graph for incremental repair.

    For n vertices (0..n-1):
    - Chain forward : i → i+1, weight 1       for i in 0..n-2
    - Chain back    : i+1 → i, weight 1       for i in 0..n-2
    - Shortcuts     : 0 → i,   weight i+K     for i in 2..n-1

    With K = n (default), every shortcut is heavier than the chain path,
    so Dijkstra from source 0 sets dist[i] = i via the chain.

    After deleting edge (0, 1):
    - dist[i] = i + K for i >= 2  (shortcut is now the only direct path)
    - dist[1] = (2 + K) + 1 = K + 3  (via shortcut 0→2 then back 2→1)

    All n-1 non-source vertices change distance → affected set = {1,..,n-1}.

    Parameters
    ----------
    n    : number of vertices (>= 2).
    seed : unused (graph is deterministic regardless), kept for API uniformity.
    K    : shortcut cost offset. Default: n. Must be > 0.
    """
    if not isinstance(n, int) or isinstance(n, bool) or n <= 0:
        raise ValueError(f"n must be a positive integer, got {n!r}")
    if n < 2:
        raise ValueError(f"comb_adversarial requires n >= 2, got n={n}")
    if K is None:
        K = n
    if not isinstance(K, int) or isinstance(K, bool) or K <= 0:
        raise ValueError(f"K must be a positive integer, got {K!r}")

    g = DiGraph(n)
    for i in range(n - 1):
        g.add_edge(i, i + 1, 1)       # chain forward
        g.add_edge(i + 1, i, 1)       # chain back
    for i in range(2, n):
        g.add_edge(0, i, i + K)       # heavy shortcut

    return g
