"""Tests for exact affected-set identification (Milestone 3.3).

Covers test cases T3.3-01 through T3.3-09 per PLAYBOOK.md §Milestone 3.3.
"""

from __future__ import annotations

import json
from pathlib import Path
import pytest
from hypothesis import assume, given, settings, strategies as st

from graphpulse.dijkstra import INF, dijkstra
from graphpulse.generators import comb_adversarial, random_sparse
from graphpulse.graph import DiGraph
from graphpulse.opcount import OpCounter
from graphpulse.repair import find_affected
from graphpulse.spt import SPTState

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
# T3.3-01: Chain (positive)
# ---------------------------------------------------------------------------

def test_t33_01_chain():
    """T3.3-01: Chain g2: deleting 1->2 yields A == {2, 3}."""
    data = load_golden("g2_chain.json")
    g = graph_from_golden(data)
    state = SPTState.build(g, src=0, counter=OpCounter())

    # Delete 1 -> 2
    g_prime = g.copy()
    g_prime.remove_edge(1, 2)

    A = find_affected(state, g_prime, v=2)
    assert A == {2, 3}


# ---------------------------------------------------------------------------
# T3.3-02: Disconnection (edge case)
# ---------------------------------------------------------------------------

def test_t33_02_disconnection():
    """T3.3-02: Deleting sole in-edge of a subtree marks whole subtree affected."""
    # Graph: 0 -> 1 -> 2, 1 -> 3, 2 -> 4, 3 -> 4
    g = DiGraph(5)
    g.add_edge(0, 1, 1)
    g.add_edge(1, 2, 1)
    g.add_edge(1, 3, 1)
    g.add_edge(2, 4, 1)
    g.add_edge(3, 4, 1)

    state = SPTState.build(g, src=0, counter=OpCounter())

    # Cut edge 0 -> 1; whole subtree {1, 2, 3, 4} becomes unreachable
    g_prime = g.copy()
    g_prime.remove_edge(0, 1)

    A = find_affected(state, g_prime, v=1)
    assert A == {1, 2, 3, 4}

    # Verify via fresh Dijkstra oracle: all become INF
    dist_new, _ = dijkstra(g_prime, src=0, counter=OpCounter())
    for x in A:
        assert dist_new[x] == INF


# ---------------------------------------------------------------------------
# T3.3-03: Adversarial comb (integration)
# ---------------------------------------------------------------------------

def test_t33_03_adversarial_comb():
    """T3.3-03: comb_adversarial(200), delete (0,1) -> |A| == 199 (all non-source)."""
    n = 200
    g = comb_adversarial(n=n, seed=0)
    state = SPTState.build(g, src=0, counter=OpCounter())

    # In comb_adversarial, before deletion dist[i] = i via the chain.
    # Deleting (0, 1) affects every single non-source vertex.
    g_prime = g.copy()
    g_prime.remove_edge(0, 1)

    A = find_affected(state, g_prime, v=1)
    assert len(A) == n - 1
    assert A == set(range(1, n))


# ---------------------------------------------------------------------------
# T3.3-04: Vertex with two tight parents survives (edge case)
# ---------------------------------------------------------------------------

def test_t33_04_vertex_with_two_tight_parents_survives():
    """T3.3-04: Shared vertex with alternative tight support from unaffected is not in A."""
    # Graph:
    # 0 -> 1 (w=1, dist=1)
    # 0 -> 2 (w=2, dist=2)
    # 1 -> 3 (w=1, dist=2)
    # 2 -> 4 (w=1, dist=3) -- tight!
    # 3 -> 4 (w=1, dist=3) -- tight!
    g = DiGraph(5)
    g.add_edge(0, 1, 1)
    g.add_edge(0, 2, 2)
    g.add_edge(1, 3, 1)
    g.add_edge(2, 4, 1)
    g.add_edge(3, 4, 1)

    state = SPTState.build(g, src=0, counter=OpCounter())
    assert state.tight[4] == 2

    # Delete 0 -> 1 (sole tight edge to 1)
    g_prime = g.copy()
    g_prime.remove_edge(0, 1)

    A = find_affected(state, g_prime, v=1)

    # 1 and 3 are affected, but 4 is supported by unaffected vertex 2 via 2->4!
    assert A == {1, 3}
    assert 4 not in A
    assert 2 not in A

    # Verify against Dijkstra oracle
    dist_new, _ = dijkstra(g_prime, src=0, counter=OpCounter())
    assert dist_new[4] == state.dist[4] == 3
    assert dist_new[1] != state.dist[1]
    assert dist_new[3] != state.dist[3]


# ---------------------------------------------------------------------------
# T3.3-05: Purity (validation)
# ---------------------------------------------------------------------------

def test_t33_05_purity():
    """T3.3-05: find_affected never modifies state or graph."""
    data = load_golden("g1_diamond.json")
    g = graph_from_golden(data)
    state = SPTState.build(g, src=0, counter=OpCounter())

    # Deep snapshot before call
    state_snap = state.copy()
    g_snap = g.copy()

    g_prime = g.copy()
    g_prime.remove_edge(0, 1)

    _ = find_affected(state, g_prime, v=1)

    # Assert deep equality
    assert state.src == state_snap.src
    assert state.dist == state_snap.dist
    assert state.parent == state_snap.parent
    assert state.children == state_snap.children
    assert state.tight == state_snap.tight
    assert state.F_ops == state_snap.F_ops
    assert g == g_snap


# ---------------------------------------------------------------------------
# T3.3-06: Oracle equality (property test on 500 cases)
# ---------------------------------------------------------------------------

@settings(max_examples=500, deadline=None)
@given(st.integers(min_value=2, max_value=9), st.data())
def test_t33_06_oracle_equality(n, data):
    """T3.3-06: Property test over 500 cases: find_affected == Dijkstra oracle."""
    g = DiGraph(n)
    all_pairs = [(u, v) for u in range(n) for v in range(n) if u != v]
    num_edges = data.draw(st.integers(min_value=1, max_value=min(len(all_pairs), 20)))
    added: set[tuple[int, int]] = set()

    for _ in range(num_edges):
        candidates = [p for p in all_pairs if p not in added]
        if not candidates:
            break
        u, v = data.draw(st.sampled_from(candidates))
        w = data.draw(st.integers(min_value=1, max_value=30))
        g.add_edge(u, v, w)
        added.add((u, v))

    src = data.draw(st.integers(min_value=0, max_value=n - 1))
    state = SPTState.build(g, src, OpCounter())

    # Filter tight edges (u, v) where tight[v] == 1 and v != src
    candidates = []
    for u in range(n):
        if state.dist[u] == INF:
            continue
        for v, w in g.out_edges(u):
            if v != src and state.dist[u] + w == state.dist[v] and state.tight[v] == 1:
                candidates.append((u, v))

    assume(len(candidates) > 0)
    u_del, v_del = data.draw(st.sampled_from(candidates))

    # Perform deletion on copy
    g_prime = g.copy()
    g_prime.remove_edge(u_del, v_del)

    # Dijkstra ground-truth oracle
    dist_new, _ = dijkstra(g_prime, src, OpCounter())
    expected_A = {x for x in range(n) if state.dist[x] != dist_new[x]}

    computed_A = find_affected(state, g_prime, v_del)
    assert computed_A == expected_A, (
        f"Mismatch on edge ({u_del}, {v_del}): expected {expected_A}, got {computed_A}"
    )


# ---------------------------------------------------------------------------
# T3.3-07: Source never affected (edge case)
# ---------------------------------------------------------------------------

def test_t33_07_source_never_affected():
    """T3.3-07: Graph with cycles through source: source never enters A."""
    # Directed cycle: 0 -> 1 -> 2 -> 0, plus 1 -> 3
    g = DiGraph(4)
    g.add_edge(0, 1, 1)
    g.add_edge(1, 2, 1)
    g.add_edge(2, 0, 1)
    g.add_edge(1, 3, 1)

    state = SPTState.build(g, src=0, counter=OpCounter())
    assert state.tight[1] == 1

    g_prime = g.copy()
    g_prime.remove_edge(0, 1)

    A = find_affected(state, g_prime, v=1)
    assert 0 not in A
    assert state.src not in A
    assert A == {1, 2, 3}


# ---------------------------------------------------------------------------
# T3.3-08: Exact work (validation)
# ---------------------------------------------------------------------------

def test_t33_08_exact_work():
    """T3.3-08: Work satisfies queue == 2*|A| and scan == sum(outdeg(x) for x in A)."""
    # Build a tree: 0 -> 1 -> 2 -> 3, with 2 -> 4 and 1 -> 5
    g = DiGraph(6)
    g.add_edge(0, 1, 2)
    g.add_edge(1, 2, 3)
    g.add_edge(2, 3, 4)
    g.add_edge(2, 4, 1)
    g.add_edge(1, 5, 2)

    state = SPTState.build(g, src=0, counter=OpCounter())

    # Cut 0 -> 1; all nodes {1, 2, 3, 4, 5} are affected
    g_prime = g.copy()
    g_prime.remove_edge(0, 1)

    counter = OpCounter()
    A = find_affected(state, g_prime, v=1, counter=counter)

    assert A == {1, 2, 3, 4, 5}
    assert counter.queue == 2 * len(A)
    assert counter.scan == sum(g_prime.out_degree(x) for x in A)
    assert counter.push == 0
    assert counter.pop == 0
    assert counter.work == counter.queue + counter.scan


# ---------------------------------------------------------------------------
# T3.3-09: Cyclic graphs terminate (edge case)
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("seed", [10, 25, 99, 137, 2026])
def test_t33_09_cyclic_graphs_terminate(seed):
    """T3.3-09: Cycles in graph do not cause infinite loops; propagation terminates."""
    # Generate sparse graph with bidirected edges (cycles everywhere)
    g = random_sparse(n=20, m=50, seed=seed, wmin=1, wmax=10)
    src = 0
    state = SPTState.build(g, src=src, counter=OpCounter())

    # Find a tight edge into a node with tight[v] == 1
    tight_singletons = []
    for u in range(g.n):
        if state.dist[u] == INF:
            continue
        for v, w in g.out_edges(u):
            if v != src and state.dist[u] + w == state.dist[v] and state.tight[v] == 1:
                tight_singletons.append((u, v))

    if not tight_singletons:
        pytest.skip("No tight singleton edge found for this seed")

    u_del, v_del = tight_singletons[0]
    g_prime = g.copy()
    g_prime.remove_edge(u_del, v_del)

    # Call find_affected: MUST terminate without recursion or loop errors
    A = find_affected(state, g_prime, v_del)

    # Compare with Dijkstra oracle
    dist_new, _ = dijkstra(g_prime, src, OpCounter())
    expected_A = {x for x in range(g.n) if state.dist[x] != dist_new[x]}
    assert A == expected_A
