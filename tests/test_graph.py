"""Tests for DiGraph implementation (Milestone 0.3)."""

from pathlib import Path
import pytest
from hypothesis import given, settings, strategies as st

from graphpulse.graph import DiGraph

GOLDEN_DIR = Path(__file__).parent / "golden"


def test_t03_01_add_and_query_edges():
    """T0.3-01: Add and query edges in an empty graph (n=4)."""
    g = DiGraph(4)
    assert g.n == 4
    assert g.m == 0

    g.add_edge(0, 1, 10)
    g.add_edge(1, 2, 20)
    g.add_edge(0, 3, 30)

    assert g.m == 3
    assert g.has_edge(0, 1)
    assert g.has_edge(1, 2)
    assert g.has_edge(0, 3)
    assert not g.has_edge(1, 0)
    assert not g.has_edge(2, 3)

    assert g.weight(0, 1) == 10
    assert g.weight(1, 2) == 20
    assert g.weight(0, 3) == 30

    assert sorted(g.out_edges(0)) == [(1, 10), (3, 30)]
    assert g.out_edges(1) == [(2, 20)]
    assert g.out_edges(2) == []

    assert g.in_edges(0) == []
    assert g.in_edges(1) == [(0, 10)]
    assert g.in_edges(2) == [(1, 20)]
    assert g.in_edges(3) == [(0, 30)]


def test_t03_02_remove_edge():
    """T0.3-02: Remove an edge and ensure both out and inn are updated, and m decrements."""
    g = DiGraph(4)
    g.add_edge(0, 1, 10)
    g.add_edge(1, 2, 20)
    assert g.m == 2

    g.remove_edge(0, 1)
    assert g.m == 1
    assert not g.has_edge(0, 1)
    assert g.out_edges(0) == []
    assert g.in_edges(1) == []
    assert g.has_edge(1, 2)
    assert g.weight(1, 2) == 20


def test_t03_03_duplicate_edge():
    """T0.3-03: Attempting to add duplicate edge raises ValueError."""
    g = DiGraph(3)
    g.add_edge(0, 1, 5)
    with pytest.raises(ValueError, match="Duplicate edge"):
        g.add_edge(0, 1, 10)
    assert g.m == 1
    assert g.weight(0, 1) == 5


def test_t03_04_self_loop():
    """T0.3-04: Adding a self-loop (u, u) raises ValueError."""
    g = DiGraph(3)
    with pytest.raises(ValueError, match="Self-loop"):
        g.add_edge(2, 2, 1)
    assert g.m == 0


def test_t03_05_bad_weights():
    """T0.3-05: Non-positive, non-integer, and boolean weights are rejected."""
    g = DiGraph(3)
    for bad_w in [0, -3, 2.5, True, False, "10", None]:
        with pytest.raises(ValueError, match="strictly positive integer"):
            g.add_edge(0, 1, bad_w)  # type: ignore


def test_t03_06_vertex_out_of_range():
    """T0.3-06: Vertices outside [0, n-1] raise ValueError."""
    g = DiGraph(4)
    with pytest.raises(ValueError, match="out of range"):
        g.add_edge(0, 4, 1)
    with pytest.raises(ValueError, match="out of range"):
        g.add_edge(-1, 2, 1)
    with pytest.raises(ValueError, match="out of range"):
        g.out_edges(5)
    with pytest.raises(ValueError, match="out of range"):
        g.in_edges(-2)


def test_t03_07_missing_edge_operations():
    """T0.3-07: Missing edge operations raise KeyError and leave graph unchanged."""
    g = DiGraph(3)
    g.add_edge(0, 1, 5)
    m_before = g.m

    with pytest.raises(KeyError, match="does not exist"):
        g.remove_edge(1, 2)

    with pytest.raises(KeyError, match="does not exist"):
        g.increase_weight(1, 2, 10)

    with pytest.raises(KeyError, match="does not exist"):
        g.weight(1, 2)

    assert g.m == m_before
    assert g.weight(0, 1) == 5


def test_t03_08_increase_rules():
    """T0.3-08: increase_weight requires strictly greater positive integer."""
    g = DiGraph(3)
    g.add_edge(0, 1, 5)

    # Equal weight -> error
    with pytest.raises(ValueError, match="strictly greater"):
        g.increase_weight(0, 1, 5)

    # Decreased weight -> error
    with pytest.raises(ValueError, match="strictly greater"):
        g.increase_weight(0, 1, 3)

    # Strictly greater weight -> succeeds in both maps
    g.increase_weight(0, 1, 9)
    assert g.weight(0, 1) == 9
    assert g.out_edges(0) == [(1, 9)]
    assert g.in_edges(1) == [(0, 9)]


def test_t03_09_copy_independence():
    """T0.3-09: Mutating a copy does not affect the original."""
    g1 = DiGraph(3)
    g1.add_edge(0, 1, 5)
    g1.add_edge(1, 2, 7)

    g2 = g1.copy()
    assert g2 == g1

    g2.add_edge(0, 2, 10)
    g2.remove_edge(0, 1)
    g2.increase_weight(1, 2, 15)

    assert g1.m == 2
    assert g1.has_edge(0, 1)
    assert g1.weight(0, 1) == 5
    assert not g1.has_edge(0, 2)
    assert g1.weight(1, 2) == 7

    assert g2.m == 2
    assert not g2.has_edge(0, 1)
    assert g2.has_edge(0, 2)
    assert g2.weight(1, 2) == 15


@settings(max_examples=200)
@given(
    st.data(),
    st.integers(min_value=2, max_value=8),
)
def test_t03_10_adjacency_consistency(data, n):
    """T0.3-10: Adjacency consistency across arbitrary valid operations."""
    g = DiGraph(n)
    all_pairs = [(u, v) for u in range(n) for v in range(n) if u != v]

    num_ops = data.draw(st.integers(min_value=1, max_value=30))
    for _ in range(num_ops):
        op_type = data.draw(st.sampled_from(["add", "remove", "increase"]))
        if op_type == "add":
            candidates = [pair for pair in all_pairs if not g.has_edge(pair[0], pair[1])]
            if candidates:
                u, v = data.draw(st.sampled_from(candidates))
                w = data.draw(st.integers(min_value=1, max_value=100))
                g.add_edge(u, v, w)
        elif op_type == "remove":
            existing = [pair for pair in all_pairs if g.has_edge(pair[0], pair[1])]
            if existing:
                u, v = data.draw(st.sampled_from(existing))
                g.remove_edge(u, v)
        elif op_type == "increase":
            existing = [pair for pair in all_pairs if g.has_edge(pair[0], pair[1])]
            if existing:
                u, v = data.draw(st.sampled_from(existing))
                old_w = g.weight(u, v)
                new_w = data.draw(st.integers(min_value=old_w + 1, max_value=old_w + 50))
                g.increase_weight(u, v, new_w)

        # Invariant check: out and inn describe the exact same directed edges and weights
        forward_edges = set()
        for u in range(n):
            for v, w in g.out_edges(u):
                forward_edges.add((u, v, w))

        reverse_edges = set()
        for v in range(n):
            for u, w in g.in_edges(v):
                reverse_edges.add((u, v, w))

        assert forward_edges == reverse_edges
        assert len(forward_edges) == g.m


def test_t03_11_boundary_sizes():
    """T0.3-11: Boundary graph sizes: n=0, n=1, and large n=100,000 with 200,000 edges."""
    g0 = DiGraph(0)
    assert g0.n == 0
    assert g0.m == 0

    g1 = DiGraph(1)
    assert g1.n == 1
    assert g1.m == 0
    assert g1.out_edges(0) == []
    assert g1.in_edges(0) == []

    # Large graph
    n = 100_000
    g_large = DiGraph(n)
    # Add 200,000 edges along a circular chain and jumps
    for i in range(100_000):
        g_large.add_edge(i, (i + 1) % n, 1)
        g_large.add_edge(i, (i + 2) % n, 2)
    assert g_large.n == 100_000
    assert g_large.m == 200_000
    assert g_large.weight(42, 43) == 1
    assert g_large.weight(42, 44) == 2


def test_t03_12_golden_integration():
    """T0.3-12: Load DiGraph from all golden JSON files and verify n and m."""
    g1 = DiGraph.from_json(GOLDEN_DIR / "g1_diamond.json")
    assert g1.n == 4
    assert g1.m == 4
    assert g1.weight(0, 1) == 1
    assert g1.weight(0, 2) == 1
    assert g1.weight(1, 3) == 1
    assert g1.weight(2, 3) == 1

    g2 = DiGraph.from_json(GOLDEN_DIR / "g2_chain.json")
    assert g2.n == 4
    assert g2.m == 3
    assert g2.weight(0, 1) == 2
    assert g2.weight(1, 2) == 3
    assert g2.weight(2, 3) == 4

    g3 = DiGraph.from_json(GOLDEN_DIR / "g3_unreachable.json")
    assert g3.n == 5
    assert g3.m == 3
    assert not g3.has_edge(0, 4)
    assert g3.in_edges(4) == []
    assert g3.out_edges(4) == []
