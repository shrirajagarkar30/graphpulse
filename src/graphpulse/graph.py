"""Validated directed graph with forward and reverse adjacency (Milestone 0.3)."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Iterator, Union


class DiGraph:
    """A simple directed graph with positive integer edge weights.

    Maintains dual adjacency mappings:
    - forward adjacency: out_edges for out-neighborhood scans
    - reverse adjacency: in_edges for in-neighborhood / tight-counter updates

    Strictly validates vertices (0 <= v < n), weights (positive integers),
    and prohibits self-loops or parallel edges.
    """

    __slots__ = ("_n", "_m", "_out", "_inn")

    def __init__(self, n: int) -> None:
        if isinstance(n, bool) or not isinstance(n, int) or n < 0:
            raise ValueError(f"Vertex count n must be a non-negative integer, got {n!r}")
        self._n: int = n
        self._m: int = 0
        self._out: list[dict[int, int]] = [{} for _ in range(n)]
        self._inn: list[dict[int, int]] = [{} for _ in range(n)]

    @property
    def n(self) -> int:
        """Number of vertices in the graph."""
        return self._n

    @property
    def m(self) -> int:
        """Number of directed edges in the graph."""
        return self._m

    def _validate_vertex(self, v: int, name: str = "vertex") -> None:
        if isinstance(v, bool) or not isinstance(v, int) or not (0 <= v < self._n):
            raise ValueError(f"{name} {v!r} out of range [0, {self._n - 1}]")

    def _validate_weight(self, w: int) -> None:
        if isinstance(w, bool) or not isinstance(w, int) or w <= 0:
            raise ValueError(f"Edge weight must be a strictly positive integer, got {w!r}")

    def add_edge(self, u: int, v: int, w: int) -> None:
        """Add directed edge (u, v) with weight w."""
        self._validate_vertex(u, "Source vertex")
        self._validate_vertex(v, "Target vertex")
        if u == v:
            raise ValueError(f"Self-loop detected: edge ({u}, {v}) is not allowed")
        self._validate_weight(w)

        if v in self._out[u]:
            raise ValueError(f"Duplicate edge detected: edge ({u}, {v}) already exists")

        self._out[u][v] = w
        self._inn[v][u] = w
        self._m += 1

    def remove_edge(self, u: int, v: int) -> None:
        """Remove directed edge (u, v). Raises KeyError if edge is absent."""
        self._validate_vertex(u, "Source vertex")
        self._validate_vertex(v, "Target vertex")

        if v not in self._out[u]:
            raise KeyError(f"Edge ({u}, {v}) does not exist in graph")

        del self._out[u][v]
        del self._inn[v][u]
        self._m -= 1

    def increase_weight(self, u: int, v: int, new_w: int) -> None:
        """Increase weight of directed edge (u, v) to new_w > current weight."""
        self._validate_vertex(u, "Source vertex")
        self._validate_vertex(v, "Target vertex")

        if v not in self._out[u]:
            raise KeyError(f"Edge ({u}, {v}) does not exist in graph")

        self._validate_weight(new_w)
        old_w = self._out[u][v]
        if new_w <= old_w:
            raise ValueError(
                f"New weight {new_w} must be strictly greater than existing weight {old_w}"
            )

        self._out[u][v] = new_w
        self._inn[v][u] = new_w

    def has_edge(self, u: int, v: int) -> bool:
        """Check if directed edge (u, v) exists."""
        if isinstance(u, bool) or not isinstance(u, int) or not (0 <= u < self._n):
            return False
        if isinstance(v, bool) or not isinstance(v, int) or not (0 <= v < self._n):
            return False
        return v in self._out[u]

    def weight(self, u: int, v: int) -> int:
        """Return the weight of directed edge (u, v). Raises KeyError if missing."""
        self._validate_vertex(u, "Source vertex")
        self._validate_vertex(v, "Target vertex")
        if v not in self._out[u]:
            raise KeyError(f"Edge ({u}, {v}) does not exist in graph")
        return self._out[u][v]

    def out_edges(self, u: int) -> list[tuple[int, int]]:
        """Return list of (v, weight) for all outgoing edges from u."""
        self._validate_vertex(u, "Source vertex")
        return list(self._out[u].items())

    def in_edges(self, v: int) -> list[tuple[int, int]]:
        """Return list of (u, weight) for all incoming edges to v."""
        self._validate_vertex(v, "Target vertex")
        return list(self._inn[v].items())

    def out_degree(self, u: int) -> int:
        """Return the number of outgoing edges from vertex u."""
        self._validate_vertex(u, "Source vertex")
        return len(self._out[u])

    def in_degree(self, v: int) -> int:
        """Return the number of incoming edges to vertex v."""
        self._validate_vertex(v, "Target vertex")
        return len(self._inn[v])

    def copy(self) -> DiGraph:
        """Create a deep copy of the graph with independent adjacency mappings."""
        new_graph = DiGraph(self._n)
        for u in range(self._n):
            new_graph._out[u] = dict(self._out[u])
            new_graph._inn[u] = dict(self._inn[u])
        new_graph._m = self._m
        return new_graph

    @classmethod
    def from_json(cls, path: Union[str, Path]) -> DiGraph:
        """Instantiate DiGraph from a JSON file path containing 'n' and 'edges'."""
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        n = data["n"]
        graph = cls(n)
        for edge in data["edges"]:
            u, v, w = edge[0], edge[1], edge[2]
            graph.add_edge(u, v, w)
        return graph

    def __repr__(self) -> str:
        return f"DiGraph(n={self._n}, m={self._m})"

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, DiGraph):
            return False
        return self._n == other._n and self._m == other._m and self._out == other._out
