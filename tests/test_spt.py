"""Tests for SPTState with tight counters (Milestone 3.1).

Covers test cases T3.1-01 through T3.1-09 per PLAYBOOK.md §Milestone 3.1.
"""

from __future__ import annotations

import json
from pathlib import Path
import pytest
from hypothesis import given, settings, strategies as st

from graphpulse.dijkstra import INF, dijkstra
from graphpulse.graph import DiGraph
from graphpulse.opcount import OpCounter
from graphpulse.spt import SPTState
from graphpulse.verify import StateViolation, check_state, check_spt

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
# T3.1-01: Diamond (positive)
# ---------------------------------------------------------------------------

def test_t31_01_diamond():
    """T3.1-01: Diamond graph has tight[3]==2, tight[1]==tight[2]==1, tight[0]==0."""
    data = load_golden("g1_diamond.json")
    g = graph_from_golden(data)
    counter = OpCounter()
    state = SPTState.build(g, data["source"], counter)

    assert state.src == 0
    assert state.dist == [0, 1, 1, 2]
    assert state.tight[0] == 0
    assert state.tight[1] == 1
    assert state.tight[2] == 1
    assert state.tight[3] == 2

    # Deterministic tie-breaking selects smallest-id in-neighbor: min(1, 2) = 1
    assert state.parent[3] == 1
    assert state.parent[1] == 0
    assert state.parent[2] == 0
    assert state.parent[0] == -1

    # check_state passes
    check_state(g, state)


# ---------------------------------------------------------------------------
# T3.1-02: Chain (positive)
# ---------------------------------------------------------------------------

def test_t31_02_chain():
    """T3.1-02: Chain graph: every non-source tight==1; children form a path."""
    data = load_golden("g2_chain.json")
    g = graph_from_golden(data)
    counter = OpCounter()
    state = SPTState.build(g, data["source"], counter)

    assert state.tight[0] == 0
    assert state.tight[1] == 1
    assert state.tight[2] == 1
    assert state.tight[3] == 1

    assert state.parent == [-1, 0, 1, 2]
    assert state.children == [{1}, {2}, {3}, set()]

    check_state(g, state)


# ---------------------------------------------------------------------------
# T3.1-03: Unreachable (edge case)
# ---------------------------------------------------------------------------

def test_t31_03_unreachable():
    """T3.1-03: Unreachable vertex 4 in g3: tight=0, parent=-1, not in children."""
    data = load_golden("g3_unreachable.json")
    g = graph_from_golden(data)
    counter = OpCounter()
    state = SPTState.build(g, data["source"], counter)

    assert state.dist[4] == INF
    assert state.tight[4] == 0
    assert state.parent[4] == -1
    assert state.children[4] == set()

    for u in range(g.n):
        assert 4 not in state.children[u]

    check_state(g, state)


# ---------------------------------------------------------------------------
# T3.1-04: INF guard (edge case)
# ---------------------------------------------------------------------------

def test_t31_04_inf_guard():
    """T3.1-04: Two unreachable vertices joined by an edge are NOT counted tight."""
    # Graph: 0 -> 1 (w=2); vertices 2 and 3 are unreachable with edge 2 -> 3 (w=4)
    g = DiGraph(4)
    g.add_edge(0, 1, 2)
    g.add_edge(2, 3, 4)

    counter = OpCounter()
    state = SPTState.build(g, 0, counter)

    assert state.dist[2] == INF
    assert state.dist[3] == INF
    # The edge 2 -> 3 must NOT be counted as tight because dist[2] is INF
    assert state.tight[2] == 0
    assert state.tight[3] == 0
    assert state.parent[2] == -1
    assert state.parent[3] == -1
    assert state.children[2] == set()
    assert state.children[3] == set()

    check_state(g, state)


# ---------------------------------------------------------------------------
# T3.1-05: Edge into source (edge case)
# ---------------------------------------------------------------------------

def test_t31_05_edge_into_source():
    """T3.1-05: In-edge or cycle back to the source: tight[src]==0, parent[src]==-1."""
    # Cycle 0 -> 1 -> 2 -> 0
    g = DiGraph(3)
    g.add_edge(0, 1, 1)
    g.add_edge(1, 2, 1)
    g.add_edge(2, 0, 1)

    counter = OpCounter()
    state = SPTState.build(g, 0, counter)

    assert state.src == 0
    assert state.dist[0] == 0
    assert state.tight[0] == 0
    assert state.parent[0] == -1
    assert 0 not in state.children[2]

    check_state(g, state)


# ---------------------------------------------------------------------------
# T3.1-06: From-scratch equality (property)
# ---------------------------------------------------------------------------

@settings(max_examples=300)
@given(
    st.integers(min_value=1, max_value=8),
    st.data(),
)
def test_t31_06_from_scratch_equality_hypothesis(n, data):
    """T3.1-06: Property test across 300 random graphs — build then check_state."""
    g = DiGraph(n)
    all_pairs = [(u, v) for u in range(n) for v in range(n) if u != v]
    num_edges = data.draw(st.integers(min_value=0, max_value=min(len(all_pairs), 18)))
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
    counter = OpCounter()
    state = SPTState.build(g, src, counter)

    # Must pass check_state certification
    check_state(g, state)


# ---------------------------------------------------------------------------
# T3.1-07: Corruption detected (mutation)
# ---------------------------------------------------------------------------

def test_t31_07_corruption_detected():
    """T3.1-07: check_state raises StateViolation on any mutated field."""
    data = load_golden("g1_diamond.json")
    g = graph_from_golden(data)
    state = SPTState.build(g, 0, OpCounter())
    check_state(g, state)  # baseline passes

    # 1. Mutate tight count
    mutated = state.copy()
    mutated.tight[3] += 1
    with pytest.raises(StateViolation):
        check_state(g, mutated)

    mutated = state.copy()
    mutated.tight[3] = 1
    with pytest.raises(StateViolation):
        check_state(g, mutated)

    mutated = state.copy()
    mutated.tight[0] = 1
    with pytest.raises(StateViolation):
        check_state(g, mutated)

    # 2. Mutate child link (break bidirectional consistency)
    mutated = state.copy()
    # parent of 3 is 1; remove 3 from children[1]
    mutated.children[1].remove(3)
    with pytest.raises(StateViolation):
        check_state(g, mutated)

    mutated = state.copy()
    # Add spurious child to vertex 2
    mutated.children[2].add(1)
    with pytest.raises(StateViolation):
        check_state(g, mutated)

    # 3. Mutate dist
    mutated = state.copy()
    mutated.dist[3] += 1
    with pytest.raises(StateViolation):
        check_state(g, mutated)

    # 4. Mutate parent
    mutated = state.copy()
    mutated.parent[1] = 2  # 2 is not an in-neighbor of 1
    with pytest.raises(StateViolation):
        check_state(g, mutated)

    # 5. Mutate F_ops
    mutated = state.copy()
    mutated.F_ops = -1
    with pytest.raises(StateViolation):
        check_state(g, mutated)


# ---------------------------------------------------------------------------
# T3.1-08: F equals rebuild work (validation)
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("seed", [1, 7, 42, 99, 123])
def test_t31_08_f_equals_rebuild_work(seed):
    """T3.1-08: F_ops == dijkstra_work + sum of in-degrees of reachable non-source."""
    from graphpulse.generators import random_sparse

    g = random_sparse(n=20, m=50, seed=seed, wmin=1, wmax=20)
    src = 0

    # Standalone Dijkstra
    dijkstra_counter = OpCounter()
    dist, _ = dijkstra(g, src, dijkstra_counter)
    dijkstra_work = dijkstra_counter.dijkstra_work

    # Expected in-degree scan
    in_deg_sum = sum(
        g.in_degree(v) for v in range(g.n)
        if v != src and dist[v] != INF
    )

    expected_F = dijkstra_work + in_deg_sum

    # Counted build
    build_counter = OpCounter()
    state = SPTState.build(g, src, build_counter)

    assert state.F_ops == expected_F
    assert build_counter.scan == dijkstra_counter.scan + in_deg_sum
    assert build_counter.work == expected_F
    assert state.F_ops == build_counter.dijkstra_work


# ---------------------------------------------------------------------------
# T3.1-09: Parent/children consistency (validation)
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("seed", [2, 13, 77, 101, 2024])
def test_t31_09_parent_children_consistency(seed):
    """T3.1-09: v in children[parent[v]] for reachable non-source; unreachable isolated."""
    from graphpulse.generators import random_sparse

    g = random_sparse(n=25, m=40, seed=seed, wmin=1, wmax=15)
    src = 3
    state = SPTState.build(g, src, OpCounter())

    for v in range(g.n):
        if v == src:
            assert state.parent[v] == -1
            assert state.tight[v] == 0
        elif state.dist[v] != INF:
            # Reachable non-source
            p = state.parent[v]
            assert p != -1
            assert v in state.children[p]
            assert state.tight[v] >= 1
        else:
            # Unreachable
            assert state.parent[v] == -1
            assert state.tight[v] == 0
            assert len(state.children[v]) == 0
            for u in range(g.n):
                assert v not in state.children[u]

    check_state(g, state)


# ---------------------------------------------------------------------------
# Additional validation: Input validation & copy()
# ---------------------------------------------------------------------------

def test_spt_input_validation():
    """Verify ValueError on invalid src or malformed state inputs."""
    g = DiGraph(3)
    counter = OpCounter()

    with pytest.raises(ValueError, match="Source vertex"):
        SPTState.build(g, -1, counter)

    with pytest.raises(ValueError, match="Source vertex"):
        SPTState.build(g, 3, counter)

    with pytest.raises(ValueError, match="Source vertex"):
        SPTState.build(g, True, counter)


def test_spt_state_copy():
    """Verify that SPTState.copy() creates a deep, independent copy."""
    data = load_golden("g1_diamond.json")
    g = graph_from_golden(data)
    state = SPTState.build(g, 0, OpCounter())

    cloned = state.copy()
    assert cloned.src == state.src
    assert cloned.dist == state.dist
    assert cloned.parent == state.parent
    assert cloned.children == state.children
    assert cloned.tight == state.tight
    assert cloned.F_ops == state.F_ops

    # Modifying clone must not mutate original
    cloned.dist[1] = 999
    assert state.dist[1] == 1

    cloned.children[0].add(99)
    assert 99 not in state.children[0]
