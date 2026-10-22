"""Milestone 6.6: executable check of the Hamiltonian-cycle -> tour reduction (T6.6-01 .. T6.6-07).

Given a digraph H on h vertices, build the complete digraph G with weight 1 on
every edge of H and weight 2 on every other ordered pair.  All h vertices are
terminals (vertex 0 is the depot).  Then a tour of cost exactly h exists iff H
has a Hamiltonian cycle (see docs/proofs/P4_np_hardness.md).
"""

from __future__ import annotations

import random
from itertools import permutations
from pathlib import Path

from graphpulse.dijkstra import dijkstra
from graphpulse.graph import DiGraph
from graphpulse.opcount import OpCounter
from graphpulse.tour import held_karp


def build_G(h: int, H_edges: set[tuple[int, int]]) -> DiGraph:
    g = DiGraph(h)
    for a in range(h):
        for b in range(h):
            if a != b:
                g.add_edge(a, b, 1 if (a, b) in H_edges else 2)
    return g


def matrix_of(g: DiGraph, h: int):
    return [[dijkstra(g, a, OpCounter())[0][b] for b in range(h)] for a in range(h)]


def has_ham_cycle(h: int, H_edges: set[tuple[int, int]]) -> bool:
    for perm in permutations(range(1, h)):
        cyc = (0,) + perm + (0,)
        if all((a, b) in H_edges for a, b in zip(cyc, cyc[1:])):
            return True
    return False


def random_H(h: int, rng: random.Random, p: float) -> set[tuple[int, int]]:
    return {(a, b) for a in range(h) for b in range(h) if a != b and rng.random() < p}


def planted(h: int, rng: random.Random, p: float) -> set[tuple[int, int]]:
    order = list(range(h))
    rng.shuffle(order)
    cyc = {(order[i], order[(i + 1) % h]) for i in range(h)}
    return cyc | random_H(h, rng, p)


def test_t66_01_yes_instances():
    rng = random.Random(1)
    for _ in range(100):
        h = rng.randint(4, 6)
        H = planted(h, rng, 0.2)
        cost, _ = held_karp(matrix_of(build_G(h, H), h))
        assert cost == h


def test_t66_02_no_instances():
    rng = random.Random(2)
    for _ in range(100):
        h = rng.randint(4, 6)
        dead = rng.randrange(h)
        H = {e for e in random_H(h, rng, 0.5) if e[0] != dead}      # vertex `dead` has out-degree 0
        cost, _ = held_karp(matrix_of(build_G(h, H), h))
        assert cost > h


def test_t66_03_iff_property():
    rng = random.Random(3)
    yes = no = 0
    for _ in range(300):
        h = rng.randint(4, 6)
        H = random_H(h, rng, rng.choice([0.2, 0.35, 0.5, 0.7]))
        cost, _ = held_karp(matrix_of(build_G(h, H), h))
        assert (cost == h) == has_ham_cycle(h, H)
        yes += cost == h
        no += cost != h
    assert yes > 0 and no > 0              # both classes are exercised


def test_t66_04_05_matrix_equals_weights_and_cost_bounds():
    rng = random.Random(4)
    for _ in range(300):
        h = rng.randint(4, 6)
        H = random_H(h, rng, 0.4)
        D = matrix_of(build_G(h, H), h)
        for a in range(h):
            for b in range(h):
                if a != b:
                    assert D[a][b] == (1 if (a, b) in H else 2)       # shortest path = direct weight
        cost, _ = held_karp(D)
        assert h <= cost <= 2 * h


def test_t66_06_proof_files_exist_with_signoff_line():
    root = Path(__file__).resolve().parent.parent / "docs" / "proofs"
    for name in ("P4_np_hardness.md", "P5_lazy_certificate.md"):
        text = (root / name).read_text(encoding="utf-8")
        assert "Reviewer sign-off:" in text.splitlines()[2] or "Reviewer sign-off:" in text[:400]
