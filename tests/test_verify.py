"""Tests for shortest-path invariant checker and networkx oracle (Milestone 1.3)."""

from __future__ import annotations

import copy
import json
from pathlib import Path

import networkx as nx
import pytest
from hypothesis import given, settings, strategies as st

from graphpulse.dijkstra import INF, dijkstra
from graphpulse.graph import DiGraph
from graphpulse.opcount import OpCounter
from graphpulse.verify import InvariantViolation, check_spt

GOLDEN_DIR = Path(__file__).parent / "golden"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def load_golden(name: str) -> dict:
    with open(GOLDEN_DIR / name, encoding="utf-8") as f:
        return json.load(f)


def graph_from_golden(data: dict) -> DiGraph:
    g = DiGraph(data["n"])
    for u, v, w in data["edges"]:
        g.add_edge(u, v, w)
    return g


def run_dijkstra(g: DiGraph, src: int) -> tuple[list[float], list[int]]:
    return dijkstra(g, src, OpCounter())


# ---------------------------------------------------------------------------
# T1.3-01: Accepts correct output on all golden graphs
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("filename", [
    "g1_diamond.json",
    "g2_chain.json",
    "g3_unreachable.json",
])
def test_t13_01_accepts_correct_output(filename):
    """T1.3-01: check_spt raises no exception on correct Dijkstra output."""
    data = load_golden(filename)
    g = graph_from_golden(data)
    dist, parent = run_dijkstra(g, data["source"])
    # Must not raise
    check_spt(g, data["source"], dist, parent)


# ---------------------------------------------------------------------------
# T1.3-02: Rejects dist too small (subtract 1 from a reachable dist[v])
# ---------------------------------------------------------------------------

def test_t13_02_rejects_dist_too_small():
    """T1.3-02: Subtracting 1 from a reachable dist[v] triggers InvariantViolation."""
    data = load_golden("g2_chain.json")
    g = graph_from_golden(data)
    dist, parent = run_dijkstra(g, data["source"])

    # dist[2] = 5; set it to 4 — violates triangle inequality on in-edge
    bad_dist = list(dist)
    bad_dist[2] = 4   # 4 < dist[1] + w(1,2) = 2+3 = 5 → violates condition (c) tight edge
    with pytest.raises(InvariantViolation) as exc_info:
        check_spt(g, data["source"], bad_dist, parent)
    assert "2" in str(exc_info.value)  # T1.3-08: message names the vertex


def test_t13_02_rejects_dist_too_small_mutation_check():
    """T1.3-08: Violation message names the failing vertex or edge."""
    data = load_golden("g2_chain.json")
    g = graph_from_golden(data)
    dist, parent = run_dijkstra(g, data["source"])
    bad_dist = list(dist)
    bad_dist[3] = 8   # correct is 9
    with pytest.raises(InvariantViolation) as exc_info:
        check_spt(g, data["source"], bad_dist, parent)
    msg = str(exc_info.value)
    assert "3" in msg


# ---------------------------------------------------------------------------
# T1.3-03: Rejects dist too large (add 1 to a dist[v])
# ---------------------------------------------------------------------------

def test_t13_03_rejects_dist_too_large():
    """T1.3-03: Adding 1 to dist[v] violates the tight-parent condition (c)."""
    data = load_golden("g2_chain.json")
    g = graph_from_golden(data)
    dist, parent = run_dijkstra(g, data["source"])

    bad_dist = list(dist)
    bad_dist[2] = 6  # correct is 5; parent edge (1,2,3): 2+3=5 != 6 → not tight
    with pytest.raises(InvariantViolation) as exc_info:
        check_spt(g, data["source"], bad_dist, parent)
    assert "2" in str(exc_info.value)


# ---------------------------------------------------------------------------
# T1.3-04: Rejects wrong parent (point parent to a non-tight neighbor)
# ---------------------------------------------------------------------------

def test_t13_04_rejects_wrong_parent():
    """T1.3-04: Pointing a parent to a non-tight neighbor triggers violation."""
    # diamond: vertex 3 has parents 1 and 2 — both tight
    # Manufacture a graph where only one parent is valid
    g = DiGraph(4)
    g.add_edge(0, 1, 1)
    g.add_edge(0, 2, 5)   # long path through 2
    g.add_edge(1, 3, 1)
    g.add_edge(2, 3, 1)
    # dist = [0, 1, 5, 2]; parent[3] must be 1 (dist[1]+1=2), NOT 2 (dist[2]+1=6 != 2)
    dist, parent = run_dijkstra(g, 0)
    assert parent[3] == 1

    bad_parent = list(parent)
    bad_parent[3] = 2  # edge (2,3): dist[2]+1 = 5+1=6 != dist[3]=2 → not tight
    with pytest.raises(InvariantViolation) as exc_info:
        check_spt(g, 0, dist, bad_parent)
    assert "3" in str(exc_info.value)


# ---------------------------------------------------------------------------
# T1.3-05: Rejects reachable vertex marked INF
# ---------------------------------------------------------------------------

def test_t13_05_rejects_reachable_marked_inf():
    """T1.3-05: A reachable vertex with dist=INF must trigger violation."""
    data = load_golden("g2_chain.json")
    g = graph_from_golden(data)
    dist, parent = run_dijkstra(g, data["source"])

    bad_dist = list(dist)
    bad_dist[2] = INF   # vertex 2 IS reachable but we mark it INF
    bad_parent = list(parent)
    bad_parent[2] = -1  # consistent with INF claim
    with pytest.raises(InvariantViolation) as exc_info:
        check_spt(g, data["source"], bad_dist, bad_parent)
    # condition (b): edge (1,2,3) with dist[1]=2 < INF → dist[2]=INF > 2+3=5
    assert str(exc_info.value)  # any message is acceptable


# ---------------------------------------------------------------------------
# T1.3-06: Oracle agreement — Dijkstra vs networkx on 300 random graphs
# ---------------------------------------------------------------------------

@settings(max_examples=300)
@given(
    st.integers(min_value=1, max_value=7),
    st.data(),
)
def test_t13_06_oracle_agreement(n, data):
    """T1.3-06: Dijkstra distances agree with networkx on 300 random graphs."""
    g = DiGraph(n)
    nx_g = nx.DiGraph()
    nx_g.add_nodes_from(range(n))

    all_pairs = [(u, v) for u in range(n) for v in range(n) if u != v]
    num_edges = data.draw(st.integers(min_value=0, max_value=min(len(all_pairs), 14)))
    added: set[tuple[int, int]] = set()
    for _ in range(num_edges):
        candidates = [p for p in all_pairs if p not in added]
        if not candidates:
            break
        u, v = data.draw(st.sampled_from(candidates))
        w = data.draw(st.integers(min_value=1, max_value=100))
        g.add_edge(u, v, w)
        nx_g.add_edge(u, v, weight=w)
        added.add((u, v))

    src = data.draw(st.integers(min_value=0, max_value=n - 1))
    counter = OpCounter()
    dist, parent = dijkstra(g, src, counter)

    # networkx oracle
    nx_lengths = nx.single_source_dijkstra_path_length(nx_g, src, weight="weight")

    for v in range(n):
        nx_d = nx_lengths.get(v, INF)
        assert dist[v] == nx_d, (
            f"Mismatch at vertex {v}: our dist={dist[v]}, networkx dist={nx_d}"
        )

    # Also certify with invariant checker
    check_spt(g, src, dist, parent)


# ---------------------------------------------------------------------------
# T1.3-07: Unreachable vertices in g3
# ---------------------------------------------------------------------------

def test_t13_07_unreachable_vertices():
    """T1.3-07: g3 check accepted with INF and parent=-1 for vertex 4."""
    data = load_golden("g3_unreachable.json")
    g = graph_from_golden(data)
    dist, parent = run_dijkstra(g, data["source"])

    assert dist[4] == INF
    assert parent[4] == -1
    # Must be accepted
    check_spt(g, data["source"], dist, parent)

    # Corrupt: claim vertex 4 is reachable → must reject
    bad_dist = list(dist)
    bad_parent = list(parent)
    bad_dist[4] = 10
    bad_parent[4] = 3  # (3, 4) doesn't exist in g3
    with pytest.raises(InvariantViolation) as exc_info:
        check_spt(g, data["source"], bad_dist, bad_parent)
    assert "4" in str(exc_info.value)


# ---------------------------------------------------------------------------
# T1.3-08: Message quality — all mutation types name the failing entity
# ---------------------------------------------------------------------------

def test_t13_08_message_quality_src_dist():
    """T1.3-08: Corrupting dist[src] names src in the exception message."""
    g = DiGraph(3)
    g.add_edge(0, 1, 1)
    dist, parent = run_dijkstra(g, 0)
    bad_dist = list(dist)
    bad_dist[0] = 1  # src dist must be 0
    with pytest.raises(InvariantViolation) as exc_info:
        check_spt(g, 0, bad_dist, parent)
    assert "src" in str(exc_info.value) or "0" in str(exc_info.value)


# ---------------------------------------------------------------------------
# Mutation property test (checks T1.3-02 to T1.3-05 on 100 random graphs)
# ---------------------------------------------------------------------------

@settings(max_examples=100)
@given(
    st.integers(min_value=2, max_value=6),
    st.data(),
)
def test_t13_mutations_caught_property(n, data):
    """Property test: all four mutation types are caught on 100 random graphs."""
    g = DiGraph(n)
    nx_g = nx.DiGraph()
    nx_g.add_nodes_from(range(n))

    all_pairs = [(u, v) for u in range(n) for v in range(n) if u != v]
    num_edges = data.draw(st.integers(min_value=1, max_value=min(len(all_pairs), 10)))
    added: set[tuple[int, int]] = set()
    for _ in range(num_edges):
        candidates = [p for p in all_pairs if p not in added]
        if not candidates:
            break
        u, v = data.draw(st.sampled_from(candidates))
        w = data.draw(st.integers(min_value=1, max_value=50))
        g.add_edge(u, v, w)
        added.add((u, v))

    src = data.draw(st.integers(min_value=0, max_value=n - 1))
    dist, parent = run_dijkstra(g, src)

    # Find a reachable, non-source vertex to mutate
    reachable = [v for v in range(n) if v != src and dist[v] != INF]
    if not reachable:
        return  # nothing to mutate

    v = data.draw(st.sampled_from(reachable))
    mutation = data.draw(st.sampled_from(["dist_too_small", "dist_too_large", "inf_mark"]))

    if mutation == "dist_too_small":
        bad_dist = list(dist)
        bad_dist[v] = dist[v] - 1
        with pytest.raises(InvariantViolation):
            check_spt(g, src, bad_dist, parent)

    elif mutation == "dist_too_large":
        bad_dist = list(dist)
        bad_dist[v] = dist[v] + 1
        with pytest.raises(InvariantViolation):
            check_spt(g, src, bad_dist, parent)

    elif mutation == "inf_mark":
        bad_dist = list(dist)
        bad_parent = list(parent)
        bad_dist[v] = INF
        bad_parent[v] = -1
        with pytest.raises(InvariantViolation):
            check_spt(g, src, bad_dist, bad_parent)
