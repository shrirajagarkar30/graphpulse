"""Milestone 7.1: road-network loader (T7.1-01 .. T7.1-11)."""

from __future__ import annotations

from pathlib import Path

import networkx as nx
import pytest
from hypothesis import given, settings, strategies as st

from graphpulse.generators import grid
from graphpulse.graph import DiGraph
from graphpulse.roadnet import (
    bfs_ball, induced_subgraph, largest_scc, load_gr, pick_terminals, sha256_file,
)

TINY = Path(__file__).parent / "data" / "tiny.gr"


def write(tmp_path, text, name="x.gr"):
    p = tmp_path / name
    p.write_text(text, encoding="utf-8")
    return p


def test_t71_01_parse_tiny():
    g = load_gr(TINY)
    # raw: 9 arcs; after dropping the self-loop and collapsing the duplicate: 7
    assert (g.n, g.m) == (6, 7)
    assert g.weight(0, 1) == 4                      # duplicate kept the minimum
    assert not g.has_edge(1, 1)
    assert largest_scc(g) == [0, 1, 2, 3]           # vertices 5 and 6 are one-way


def test_t71_02_malformed_line(tmp_path):
    p = write(tmp_path, "p sp 3 2\na 1 2 5\na 2 oops 4\n")
    with pytest.raises(ValueError, match="line 3"):
        load_gr(p)


@pytest.mark.parametrize("w", ["0", "-2", "2.5", "abc"])
def test_t71_03_bad_weight(tmp_path, w):
    with pytest.raises(ValueError, match="line 2"):
        load_gr(write(tmp_path, f"p sp 2 1\na 1 2 {w}\n"))


def test_t71_04_duplicate_arcs(tmp_path):
    g = load_gr(write(tmp_path, "p sp 2 2\na 1 2 7\na 1 2 3\n"))
    assert g.m == 1 and g.weight(0, 1) == 3


digraphs = st.integers(1, 12).flatmap(
    lambda n: st.tuples(st.just(n), st.sets(st.tuples(st.integers(0, n - 1), st.integers(0, n - 1)), max_size=40))
)


@settings(max_examples=300, deadline=None)
@given(digraphs)
def test_t71_05_scc_matches_networkx(data):
    n, edges = data
    g = DiGraph(n)
    nxg = nx.DiGraph()
    nxg.add_nodes_from(range(n))
    for u, v in edges:
        if u != v:
            g.add_edge(u, v, 1)
            nxg.add_edge(u, v)
    ref = max((sorted(c) for c in nx.strongly_connected_components(nxg)), key=lambda c: (len(c), [-x for x in c]))
    got = largest_scc(g)
    assert len(got) == len(ref)
    assert set(map(frozenset, [got])) <= set(frozenset(c) for c in nx.strongly_connected_components(nxg))


def test_t71_06_deep_graph_no_recursion_error():
    n = 200_000
    g = DiGraph(n)
    for i in range(n - 1):
        g.add_edge(i, i + 1, 1)
    g.add_edge(n - 1, 0, 1)                         # one giant cycle
    assert len(largest_scc(g)) == n


def test_t71_07_relabelling():
    g = grid(5, 5, seed=1)
    keep = [3, 4, 8, 9, 13]
    sub, mp = induced_subgraph(g, keep)
    assert mp == {3: 0, 4: 1, 8: 2, 9: 3, 13: 4}
    for old_u in keep:
        for old_v, w in g.out_edges(old_u):
            if old_v in mp:
                assert sub.weight(mp[old_u], mp[old_v]) == w
    assert sub.m == sum(1 for u in keep for v, _ in g.out_edges(u) if v in mp)


def test_t71_08_ball_is_strongly_connected():
    g = grid(15, 15, seed=2)
    sub, mp = bfs_ball(g, 112, 100)
    assert 0 < sub.n <= 100
    assert len(largest_scc(sub)) == sub.n
    assert len(mp) == sub.n


def test_t71_09_terminals_deterministic_and_distinct():
    g = grid(8, 8, seed=1)
    a, b = pick_terminals(g, 8, seed=5), pick_terminals(g, 8, seed=5)
    assert a == b and len(set(a)) == 9
    assert pick_terminals(g, 8, seed=6) != a
    with pytest.raises(ValueError):
        pick_terminals(g, 64, seed=1)


@pytest.mark.parametrize("text", [
    "p sp 5 1\na 6 1 3\n",                 # vertex id above n
    "p sp 5 2\na 1 2 3\n",                 # arc count mismatch
    "a 1 2 3\n",                           # arc before header
    "p sp 2 0\np sp 2 0\n",                # duplicate header
    "p sp 2 0\nz what\n",                  # unknown line type
])
def test_t71_10_header_mismatch(tmp_path, text):
    with pytest.raises(ValueError):
        load_gr(write(tmp_path, text))


def test_t71_11_empty_file(tmp_path):
    with pytest.raises(ValueError):
        load_gr(write(tmp_path, ""))
    with pytest.raises(ValueError):
        load_gr(write(tmp_path, "c only comments\n"))


def test_sha256_is_stable(tmp_path):
    p = write(tmp_path, "abc")
    assert sha256_file(p) == "ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad"
