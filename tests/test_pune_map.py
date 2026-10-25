"""Tests for Pune real-road interactive map backend (pune_data.py and server.py)."""

import pytest
from graphpulse.pune_data import (
    PUNE_NODES,
    PUNE_ROAD_GEOMETRIES,
    PUNE_ROAD_LABELS,
    PUNE_DEFAULT_DEPOT,
    build_pune_graph,
    pune_node_positions,
)
from graphpulse.server import PuneMapState


def test_pune_nodes_and_positions():
    """Verify Pune intersections and coordinate metadata."""
    assert len(PUNE_NODES) == 25
    positions = pune_node_positions()
    assert len(positions) == 25
    for node in PUNE_NODES:
        nid = node["id"]
        assert 0 <= nid < 25
        assert "name" in node and len(node["name"]) > 0
        # Pune latitude ~ 18.4 to 18.7, longitude ~ 73.7 to 74.0
        assert 18.4 <= node["lat"] <= 18.7
        assert 73.7 <= node["lng"] <= 74.0
        assert nid in positions


def test_pune_graph_build():
    """Verify road graph connectivity and positive integer edge weights."""
    g = build_pune_graph()
    assert g.n == 25
    assert g.m >= 50
    # Every edge must have weight >= 1
    for u in range(g.n):
        for v, w in g.out_edges(u):
            assert w >= 1


def test_pune_road_geometries():
    """Verify that curved road geometries are present and valid."""
    assert len(PUNE_ROAD_GEOMETRIES) > 0
    # Check that geometries have coordinates
    for key, geo in PUNE_ROAD_GEOMETRIES.items():
        coords = geo.get("coordinates")
        assert isinstance(coords, list)
        assert len(coords) >= 2
        for pt in coords:
            assert len(pt) == 2
            # Leaflet expects [lat, lng]
            assert 18.4 <= pt[0] <= 18.7
            assert 73.7 <= pt[1] <= 74.0


def test_pune_map_state_detour_and_reset():
    """Verify PuneMapState computes detours when a road closes and resets cleanly."""
    state = PuneMapState()
    initial_json = state.graph_json()
    assert len(initial_json["nodes"]) == 25
    assert len(initial_json["edges"]) >= 50
    assert initial_json["src"] == PUNE_DEFAULT_DEPOT

    # Delete road (11 -> 9: Pune Station -> Swargate)
    res = state.apply_update(kind="delete", u=11, v=9)
    assert res["u"] == 11 and res["v"] == 9
    assert res["was_tree_edge"] is True
    # When primary tree edge is cut, alternate detour edges must be adopted
    assert len(res["detour_edges"]) > 0

    # Verify is_detour is reflected in serialized graph edges
    graph_after = state.graph_json()
    detour_edges = [e for e in graph_after["edges"] if e.get("is_detour")]
    assert len(detour_edges) == len(res["detour_edges"])

    # Reset
    state.reset()
    graph_reset = state.graph_json()
    assert len([e for e in graph_reset["edges"] if e.get("is_detour")]) == 0
    assert len([e for e in graph_reset["edges"] if e.get("is_deleted")]) == 0


def test_pune_map_automatic_scenarios():
    """Verify scenarios where local repair is optimal vs where full Dijkstra recompute is optimal."""
    state = PuneMapState()

    # Scenario 1: Localized Road Disruption (Karve Road)
    # GraphPulse-R automatically detects that disruption is localized (|A|=1 << 25),
    # so local repair is vastly superior to full rebuild (15 ops vs 115 baseline, 87% saved).
    res_local = state.apply_update(kind="delete", u=4, v=5)
    assert res_local["strategy"] == "repair"
    assert res_local["affected_size"] == 1
    assert res_local["work"] < res_local["baseline_work"]
    assert len(res_local["detour_edges"]) > 0

    state.reset()

    # Scenario 2: Multi-Corridor Cut (Station-Swargate + FC Road)
    # GraphPulse-R automatically detects that local repair work exceeds competitive budget B,
    # aborts local repair, and executes a full Dijkstra rebuild from scratch (strategy = fallback).
    state.apply_update(kind="delete", u=11, v=9)
    res_corridor = state.apply_update(kind="delete", u=1, v=2)
    assert res_corridor["strategy"] == "fallback"
    assert res_corridor["fallback_work"] is not None
    assert res_corridor["budget"] is not None
    assert len(res_corridor["detour_edges"]) > 0
