"""Tests for counted Dijkstra baseline (Milestone 1.2)."""

from __future__ import annotations

import json
from pathlib import Path
import pytest
from hypothesis import given, settings, strategies as st

from graphpulse.dijkstra import dijkstra, INF
from graphpulse.graph import DiGraph
from graphpulse.opcount import OpCounter

GOLDEN_DIR = Path(__file__).parent / "golden"


def load_golden(name: str) -> dict:
    with open(GOLDEN_DIR / name, encoding="utf-8") as f:
        return json.load(f)


def graph_from_golden(data: dict) -> DiGraph:
    g = DiGraph(data["n"])
    for u, v, w in data["edges"]:
        g.add_edge(u, v, w)
    return g


# ---------------------------------------------------------------------------
# T1.2-01: Golden graphs
# ---------------------------------------------------------------------------

def test_t12_01_golden_g1_diamond():
    """T1.2-01: Dijkstra on g1 (diamond) matches golden distances."""
    data = load_golden("g1_diamond.json")
    g = graph_from_golden(data)
    counter = OpCounter()
    dist, parent = dijkstra(g, data["source"], counter)

    expected = [d if d is not None else INF for d in data["dist"]]
    assert dist == expected
    # dist[3] must be 2 via some path
    assert dist[3] == 2


def test_t12_01_golden_g2_chain():
    """T1.2-01: Dijkstra on g2 (chain) matches golden distances."""
    data = load_golden("g2_chain.json")
    g = graph_from_golden(data)
    counter = OpCounter()
    dist, parent = dijkstra(g, data["source"], counter)

    expected = [d if d is not None else INF for d in data["dist"]]
    assert dist == expected


def test_t12_01_golden_g3_unreachable():
    """T1.2-01: Dijkstra on g3 yields INF for vertex 4."""
    data = load_golden("g3_unreachable.json")
    g = graph_from_golden(data)
    counter = OpCounter()
    dist, parent = dijkstra(g, data["source"], counter)

    assert dist[4] == INF
    assert parent[4] == -1
    expected_reachable = [0, 2, 5, 9]
    for i, d in enumerate(expected_reachable):
        assert dist[i] == d


# ---------------------------------------------------------------------------
# T1.2-02: Single vertex
# ---------------------------------------------------------------------------

def test_t12_02_single_vertex():
    """T1.2-02: Dijkstra on a single-vertex graph returns dist=[0]."""
    g = DiGraph(1)
    counter = OpCounter()
    dist, parent = dijkstra(g, 0, counter)

    assert dist == [0]
    assert parent == [-1]
    assert counter.scan == 0
    assert counter.push == 1
    assert counter.pop == 1


# ---------------------------------------------------------------------------
# T1.2-03: Isolated source
# ---------------------------------------------------------------------------

def test_t12_03_isolated_source():
    """T1.2-03: All non-source vertices are INF when source has no out-edges."""
    g = DiGraph(4)
    g.add_edge(1, 2, 3)
    g.add_edge(2, 3, 7)
    counter = OpCounter()
    # src=0 has no outgoing edges
    dist, parent = dijkstra(g, 0, counter)

    assert dist[0] == 0
    assert all(dist[v] == INF for v in range(1, 4))
    assert all(parent[v] == -1 for v in range(1, 4))
    assert counter.scan == 0  # no out-edges from source


# ---------------------------------------------------------------------------
# T1.2-04: Equal-cost paths
# ---------------------------------------------------------------------------

def test_t12_04_equal_cost_paths():
    """T1.2-04: dist[3]=2 for diamond graph regardless of parent chosen."""
    data = load_golden("g1_diamond.json")
    g = graph_from_golden(data)
    counter = OpCounter()
    dist, parent = dijkstra(g, 0, counter)

    assert dist[3] == 2
    # parent[3] must be either 1 or 2 (both are valid shortest-path predecessors)
    assert parent[3] in (1, 2)


# ---------------------------------------------------------------------------
# T1.2-05: Very large weights (no overflow since Python ints are arbitrary)
# ---------------------------------------------------------------------------

def test_t12_05_very_large_weights():
    """T1.2-05: Dijkstra handles very large integer weights correctly."""
    g = DiGraph(4)
    W = 10 ** 12
    g.add_edge(0, 1, W)
    g.add_edge(1, 2, W)
    g.add_edge(2, 3, W)
    counter = OpCounter()
    dist, parent = dijkstra(g, 0, counter)

    assert dist[0] == 0
    assert dist[1] == W
    assert dist[2] == 2 * W
    assert dist[3] == 3 * W
    assert parent == [-1, 0, 1, 2]


# ---------------------------------------------------------------------------
# T1.2-06: Bad source
# ---------------------------------------------------------------------------

def test_t12_06_bad_source():
    """T1.2-06: Out-of-range source raises ValueError."""
    g = DiGraph(4)
    with pytest.raises(ValueError, match="out of range"):
        dijkstra(g, 4, OpCounter())
    with pytest.raises(ValueError, match="out of range"):
        dijkstra(g, -1, OpCounter())


# ---------------------------------------------------------------------------
# T1.2-07: Exact scan count
# ---------------------------------------------------------------------------

@settings(max_examples=100)
@given(
    st.integers(min_value=1, max_value=6),
    st.data(),
)
def test_t12_07_exact_scan_count(n, data):
    """T1.2-07: scan == sum of out-degrees of settled (reachable) vertices."""
    g = DiGraph(n)
    all_pairs = [(u, v) for u in range(n) for v in range(n) if u != v]
    num_edges = data.draw(st.integers(min_value=0, max_value=min(len(all_pairs), 12)))
    added = set()
    for _ in range(num_edges):
        candidates = [p for p in all_pairs if p not in added]
        if not candidates:
            break
        u, v = data.draw(st.sampled_from(candidates))
        w = data.draw(st.integers(min_value=1, max_value=100))
        g.add_edge(u, v, w)
        added.add((u, v))

    src = data.draw(st.integers(min_value=0, max_value=n - 1))
    counter = OpCounter()
    dist, parent = dijkstra(g, src, counter)

    # Expected scan = sum of out-degrees of settled vertices
    expected_scan = sum(
        len(g.out_edges(v))
        for v in range(n)
        if dist[v] != INF
    )
    assert counter.scan == expected_scan


# ---------------------------------------------------------------------------
# T1.2-08: Heap balance (push == pop, push <= 1 + scan)
# ---------------------------------------------------------------------------

@settings(max_examples=100)
@given(
    st.integers(min_value=1, max_value=6),
    st.data(),
)
def test_t12_08_heap_balance(n, data):
    """T1.2-08: push == pop at termination; push <= 1 + scan."""
    g = DiGraph(n)
    all_pairs = [(u, v) for u in range(n) for v in range(n) if u != v]
    num_edges = data.draw(st.integers(min_value=0, max_value=min(len(all_pairs), 12)))
    added = set()
    for _ in range(num_edges):
        candidates = [p for p in all_pairs if p not in added]
        if not candidates:
            break
        u, v = data.draw(st.sampled_from(candidates))
        w = data.draw(st.integers(min_value=1, max_value=100))
        g.add_edge(u, v, w)
        added.add((u, v))

    src = data.draw(st.integers(min_value=0, max_value=n - 1))
    counter = OpCounter()
    dist, parent = dijkstra(g, src, counter)

    assert counter.push == counter.pop, "push must equal pop at termination"
    assert counter.push <= 1 + counter.scan, "push cannot exceed 1 + scan"


# ---------------------------------------------------------------------------
# T1.2-09: Parents form a tree (integration)
# ---------------------------------------------------------------------------

@settings(max_examples=100)
@given(
    st.integers(min_value=2, max_value=6),
    st.data(),
)
def test_t12_09_parents_form_a_tree(n, data):
    """T1.2-09: Every reachable vertex can reach src via parent chain; dist[parent[v]] < dist[v]."""
    g = DiGraph(n)
    all_pairs = [(u, v) for u in range(n) for v in range(n) if u != v]
    num_edges = data.draw(st.integers(min_value=1, max_value=min(len(all_pairs), 12)))
    added = set()
    for _ in range(num_edges):
        candidates = [p for p in all_pairs if p not in added]
        if not candidates:
            break
        u, v = data.draw(st.sampled_from(candidates))
        w = data.draw(st.integers(min_value=1, max_value=100))
        g.add_edge(u, v, w)
        added.add((u, v))

    src = data.draw(st.integers(min_value=0, max_value=n - 1))
    counter = OpCounter()
    dist, parent = dijkstra(g, src, counter)

    for v in range(n):
        if v == src:
            assert dist[v] == 0
            assert parent[v] == -1
        elif dist[v] == INF:
            assert parent[v] == -1
        else:
            # dist must be strictly less along parent edge
            p = parent[v]
            assert p >= 0, f"Reachable vertex {v} has parent=-1"
            assert dist[p] < dist[v], f"dist[parent[{v}]] >= dist[{v}]"

            # Follow chain to src — must terminate at src without cycles
            visited = set()
            cur = v
            while cur != src:
                assert cur not in visited, f"Cycle detected in parent chain at vertex {cur}"
                visited.add(cur)
                cur = parent[cur]
                assert cur >= 0, f"Parent chain broke at {cur}"
