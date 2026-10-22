"""Tests for graph generators (Milestone 2.1)."""

from __future__ import annotations

import pytest

from graphpulse.dijkstra import INF, dijkstra
from graphpulse.generators import comb_adversarial, grid, hub_spoke, random_sparse
from graphpulse.graph import DiGraph
from graphpulse.opcount import OpCounter
from graphpulse.verify import check_spt


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def assert_simple_graph(g: DiGraph) -> None:
    """Assert no self-loops and no duplicate edges in g."""
    for u in range(g.n):
        assert u not in {v for v, _ in g.out_edges(u)}, f"Self-loop at vertex {u}"
    # Duplicate detection is guaranteed by DiGraph.add_edge, but double-check m
    edge_set = {(u, v) for u in range(g.n) for v, _ in g.out_edges(u)}
    assert len(edge_set) == g.m, "Duplicate directed edges detected"


def assert_weight_range(g: DiGraph, wmin: int, wmax: int) -> None:
    """Assert every edge weight is an integer in [wmin, wmax]."""
    for u in range(g.n):
        for v, w in g.out_edges(u):
            assert isinstance(w, int) and not isinstance(w, bool), \
                f"Weight of ({u},{v}) is not int: {w!r}"
            assert wmin <= w <= wmax, \
                f"Weight {w} of ({u},{v}) outside [{wmin},{wmax}]"


# ---------------------------------------------------------------------------
# T2.1-01: Determinism
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("generator_call", [
    lambda s: grid(5, 5, seed=s),
    lambda s: random_sparse(20, 40, seed=s),
    lambda s: hub_spoke(3, 5, seed=s),
    lambda s: comb_adversarial(20, seed=s),
])
def test_t21_01_determinism(generator_call):
    """T2.1-01: Same seed produces identical edge sets and weights."""
    g1 = generator_call(42)
    g2 = generator_call(42)
    assert g1.n == g2.n
    assert g1.m == g2.m
    for u in range(g1.n):
        assert sorted(g1.out_edges(u)) == sorted(g2.out_edges(u))


# ---------------------------------------------------------------------------
# T2.1-02: Seed sensitivity
# ---------------------------------------------------------------------------

def test_t21_02_seed_sensitivity():
    """T2.1-02: Different seeds produce different weight assignments."""
    g1 = grid(5, 5, seed=1)
    g2 = grid(5, 5, seed=2)
    # Same topology (grids are deterministic in structure) but weights differ
    weights1 = sorted(w for u in range(g1.n) for _, w in g1.out_edges(u))
    weights2 = sorted(w for u in range(g2.n) for _, w in g2.out_edges(u))
    assert weights1 != weights2, "Different seeds produced identical weights"

    r1 = random_sparse(20, 40, seed=1)
    r2 = random_sparse(20, 40, seed=2)
    edges1 = sorted((u, v) for u in range(r1.n) for v, _ in r1.out_edges(u))
    edges2 = sorted((u, v) for u in range(r2.n) for v, _ in r2.out_edges(u))
    assert edges1 != edges2, "Different seeds produced identical edge sets"


# ---------------------------------------------------------------------------
# T2.1-03: Grid size
# ---------------------------------------------------------------------------

def test_t21_03_grid_size():
    """T2.1-03: grid(5,5) has n=25, m=80."""
    g = grid(5, 5, seed=0)
    assert g.n == 25
    # Horizontal pairs: 5 * 4 = 20 → 40 directed edges
    # Vertical pairs: 4 * 5 = 20 → 40 directed edges
    assert g.m == 80


# ---------------------------------------------------------------------------
# T2.1-04: Degenerate sizes
# ---------------------------------------------------------------------------

def test_t21_04_degenerate_grid_1x1():
    """T2.1-04: grid(1,1) → n=1, m=0."""
    g = grid(1, 1, seed=0)
    assert g.n == 1
    assert g.m == 0


def test_t21_04_degenerate_grid_1x5():
    """T2.1-04: grid(1,5) → n=5, m=8."""
    g = grid(1, 5, seed=0)
    assert g.n == 5
    # 4 horizontal pairs × 2 directed edges = 8
    assert g.m == 8


# ---------------------------------------------------------------------------
# T2.1-05: Invalid parameters
# ---------------------------------------------------------------------------

def test_t21_05_invalid_grid_rows():
    """T2.1-05: rows=0 raises ValueError."""
    with pytest.raises(ValueError, match="rows"):
        grid(0, 5, seed=0)


def test_t21_05_invalid_wmin_zero():
    """T2.1-05: wmin=0 raises ValueError."""
    with pytest.raises(ValueError, match="wmin"):
        grid(3, 3, seed=0, wmin=0)


def test_t21_05_invalid_wmin_greater_than_wmax():
    """T2.1-05: wmin > wmax raises ValueError."""
    with pytest.raises(ValueError, match="wmin"):
        grid(3, 3, seed=0, wmin=9, wmax=3)


def test_t21_05_invalid_random_sparse_m_too_large():
    """T2.1-05: m > n*(n-1) raises ValueError."""
    with pytest.raises(ValueError, match="exceeds maximum"):
        random_sparse(3, 10, seed=0)  # max is 3*2=6


def test_t21_05_invalid_comb_n_less_than_2():
    """T2.1-05: comb_adversarial(n=1) raises ValueError."""
    with pytest.raises(ValueError, match="n >= 2"):
        comb_adversarial(1)


# ---------------------------------------------------------------------------
# T2.1-06: Weight range
# ---------------------------------------------------------------------------

def test_t21_06_weight_range_grid():
    """T2.1-06: All grid edge weights in [3, 9] and are ints."""
    g = grid(6, 6, seed=7, wmin=3, wmax=9)
    assert_weight_range(g, 3, 9)


def test_t21_06_weight_range_random_sparse():
    """T2.1-06: All random_sparse edge weights in [5, 15] and are ints."""
    g = random_sparse(15, 30, seed=3, wmin=5, wmax=15)
    assert_weight_range(g, 5, 15)


def test_t21_06_weight_range_hub_spoke():
    """T2.1-06: All hub_spoke edge weights in [2, 8] and are ints."""
    g = hub_spoke(4, 5, seed=1, wmin=2, wmax=8)
    assert_weight_range(g, 2, 8)


# ---------------------------------------------------------------------------
# T2.1-07: Simple graph validation
# ---------------------------------------------------------------------------

def test_t21_07_simple_graph_all_generators():
    """T2.1-07: All generators produce simple graphs (no self-loops, no duplicates)."""
    assert_simple_graph(grid(5, 5, seed=0))
    assert_simple_graph(random_sparse(20, 50, seed=0))
    assert_simple_graph(hub_spoke(4, 5, seed=0))
    assert_simple_graph(comb_adversarial(20, seed=0))


# ---------------------------------------------------------------------------
# T2.1-08: Adversarial property
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("n", [10, 200, 1000])
def test_t21_08_adversarial_property(n):
    """T2.1-08: Deleting (0,1) changes exactly n-1 distances in comb_adversarial(n)."""
    g = comb_adversarial(n, seed=0)
    K = n  # default K

    # Before deletion: dist[i] = i for all i (chain is cheapest)
    c_before = OpCounter()
    dist_before, parent_before = dijkstra(g, 0, c_before)
    check_spt(g, 0, dist_before, parent_before)

    for i in range(n):
        assert dist_before[i] == i, (
            f"n={n}: expected dist[{i}]={i}, got {dist_before[i]}"
        )

    # Delete edge (0, 1)
    g.remove_edge(0, 1)

    # After deletion
    c_after = OpCounter()
    dist_after, parent_after = dijkstra(g, 0, c_after)
    check_spt(g, 0, dist_after, parent_after)

    # Count how many distances changed
    changed = sum(1 for i in range(n) if dist_before[i] != dist_after[i])
    assert changed == n - 1, (
        f"n={n}: expected {n-1} distances to change, got {changed}"
    )

    # Specifically: vertex 0 unchanged, all others changed
    assert dist_after[0] == 0
    for i in range(1, n):
        assert dist_after[i] != dist_before[i], f"n={n}: dist[{i}] did not change"

    # Verify expected new distances
    # dist[i] = i + K for i >= 2
    for i in range(2, n):
        assert dist_after[i] == i + K, (
            f"n={n}: expected dist[{i}]={i+K} after deletion, got {dist_after[i]}"
        )
    # dist[1] = (2 + K) + 1 = K + 3 (shortcut 0→2, then back 2→1)
    assert dist_after[1] == K + 3, (
        f"n={n}: expected dist[1]={K+3}, got {dist_after[1]}"
    )


# ---------------------------------------------------------------------------
# T2.1-09: Hub degrees
# ---------------------------------------------------------------------------

def test_t21_09_hub_degrees():
    """T2.1-09: Each hub has exactly spokes_per_hub outgoing edges to its spokes."""
    hubs_count = 3
    spokes = 10
    g = hub_spoke(hubs_count, spokes, seed=0)

    assert g.n == hubs_count + hubs_count * spokes  # 3 + 30 = 33

    for h in range(hubs_count):
        out = g.out_edges(h)
        assert len(out) == spokes, (
            f"Hub {h} has {len(out)} out-edges, expected {spokes}"
        )
        # Each hub's out-neighbors must be its dedicated spokes
        expected_spokes = set(
            range(hubs_count + h * spokes, hubs_count + (h + 1) * spokes)
        )
        actual_neighbors = {v for v, _ in out}
        assert actual_neighbors == expected_spokes, (
            f"Hub {h} connects to wrong spokes: {actual_neighbors}"
        )

        # Each hub has exactly spokes_per_hub in-edges (from its spokes)
        inn = g.in_edges(h)
        assert len(inn) == spokes, (
            f"Hub {h} has {len(inn)} in-edges, expected {spokes}"
        )
