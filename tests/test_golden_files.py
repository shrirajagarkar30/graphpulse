"""Tests and schema validation for hand-computed golden files (Milestone 0.2)."""

import copy
import json
from pathlib import Path
import pytest

GOLDEN_DIR = Path(__file__).parent / "golden"
GOLDEN_FILES = ["g1_diamond.json", "g2_chain.json", "g3_unreachable.json"]


def validate_golden_data(data: dict) -> None:
    """Validate golden graph dictionary schema and shortest-path consistency."""
    required_keys = {"n", "source", "edges", "dist", "tight"}
    missing = required_keys - set(data.keys())
    if missing:
        raise ValueError(f"Missing required keys in golden file: {missing}")

    n = data["n"]
    if not isinstance(n, int) or isinstance(n, bool) or n <= 0:
        raise ValueError(f"Invalid vertex count n: {n}")

    source = data["source"]
    if not isinstance(source, int) or isinstance(source, bool) or not (0 <= source < n):
        raise ValueError(f"Invalid source vertex: {source}")

    dist = data["dist"]
    if not isinstance(dist, list) or len(dist) != n:
        raise ValueError(f"dist must be a list of length {n}")

    tight = data["tight"]
    if not isinstance(tight, list) or len(tight) != n:
        raise ValueError(f"tight must be a list of length {n}")

    for i, d in enumerate(dist):
        if d is not None:
            if not isinstance(d, int) or isinstance(d, bool) or d < 0:
                raise ValueError(f"dist[{i}] must be non-negative integer or null: got {d}")
        if not isinstance(tight[i], int) or isinstance(tight[i], bool) or tight[i] < 0:
            raise ValueError(f"tight[{i}] must be non-negative integer: got {tight[i]}")

    if dist[source] != 0:
        raise ValueError(f"dist[source] must be 0, got {dist[source]}")

    seen_edges = set()
    in_edges: dict[int, list[tuple[int, int]]] = {i: [] for i in range(n)}

    for edge in data["edges"]:
        if not isinstance(edge, (list, tuple)) or len(edge) != 3:
            raise ValueError(f"Edge must be a triplet [u, v, w], got {edge}")
        u, v, w = edge
        if not isinstance(u, int) or isinstance(u, bool) or not (0 <= u < n):
            raise ValueError(f"Invalid source vertex in edge: {u}")
        if not isinstance(v, int) or isinstance(v, bool) or not (0 <= v < n):
            raise ValueError(f"Invalid target vertex in edge: {v}")
        if u == v:
            raise ValueError(f"Self-loop detected on vertex {u}")
        if not isinstance(w, int) or isinstance(w, bool) or w <= 0:
            raise ValueError(f"Edge weight must be strictly positive integer, got {w}")

        edge_pair = (u, v)
        if edge_pair in seen_edges:
            raise ValueError(f"Duplicate edge detected: {edge_pair}")
        seen_edges.add(edge_pair)
        in_edges[v].append((u, w))

    # Triangle inequality and tight count consistency check
    for v in range(n):
        computed_tight = 0
        for u, w in in_edges[v]:
            # INF guard: if dist[u] is INF (None), edge cannot be tight
            if dist[u] is not None:
                if dist[v] is not None and dist[v] > dist[u] + w:
                    raise ValueError(f"Triangle inequality violated: dist[{v}] > dist[{u}] + {w}")
                if dist[v] is not None and dist[u] + w == dist[v]:
                    computed_tight += 1
        if dist[v] is None:
            if tight[v] != 0:
                raise ValueError(f"Unreachable vertex {v} must have tight=0, got {tight[v]}")
        else:
            if tight[v] != computed_tight:
                raise ValueError(
                    f"tight[{v}] mismatch: file specifies {tight[v]}, hand-computed {computed_tight}"
                )


def load_golden_json(filename: str) -> dict:
    file_path = GOLDEN_DIR / filename
    with open(file_path, "r", encoding="utf-8") as f:
        return json.load(f)


def test_t02_01_all_golden_files_load():
    """T0.2-01: All golden files load and contain required keys."""
    for filename in GOLDEN_FILES:
        data = load_golden_json(filename)
        validate_golden_data(data)
        for key in ("n", "edges", "source", "dist", "tight"):
            assert key in data


def test_t02_02_non_positive_weight_rejected():
    """T0.2-02: Non-positive weight is rejected by schema validator."""
    data = load_golden_json("g1_diamond.json")
    bad_data = copy.deepcopy(data)
    bad_data["edges"][0][2] = 0
    with pytest.raises(ValueError, match="strictly positive integer"):
        validate_golden_data(bad_data)

    bad_data_neg = copy.deepcopy(data)
    bad_data_neg["edges"][0][2] = -2
    with pytest.raises(ValueError, match="strictly positive integer"):
        validate_golden_data(bad_data_neg)


def test_t02_03_duplicate_edge_rejected():
    """T0.2-03: Duplicate edge is rejected by schema validator."""
    data = load_golden_json("g1_diamond.json")
    bad_data = copy.deepcopy(data)
    bad_data["edges"].append([0, 1, 1])
    with pytest.raises(ValueError, match="Duplicate edge"):
        validate_golden_data(bad_data)


def test_t02_04_inf_encoding():
    """T0.2-04: INF encoding: dist[4] in g3_unreachable is null (None in Python)."""
    data = load_golden_json("g3_unreachable.json")
    assert data["dist"][4] is None
    assert data["tight"][4] == 0


def test_t02_05_hand_check_independent_of_code():
    """T0.2-05: Hand-check independent of code matches expected values."""
    # g1 diamond
    g1 = load_golden_json("g1_diamond.json")
    assert g1["dist"] == [0, 1, 1, 2]
    assert g1["tight"] == [0, 1, 1, 2]

    # g2 chain
    g2 = load_golden_json("g2_chain.json")
    assert g2["dist"] == [0, 2, 5, 9]
    assert g2["tight"] == [0, 1, 1, 1]

    # g3 unreachable
    g3 = load_golden_json("g3_unreachable.json")
    assert g3["dist"] == [0, 2, 5, 9, None]
    assert g3["tight"] == [0, 1, 1, 1, 0]
