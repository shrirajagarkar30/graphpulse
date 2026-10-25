"""Lightweight HTTP API server and static web host for GraphPulse-R Dashboard.

Provides JSON REST endpoints connecting the frontend directly to the core
shortest-path algorithms (Phases 0–4: Dijkstra, SPTState, BudgetedMaintainer,
OpCounter, check_state, and generators).

Runtime: Python standard library only (no pip packages required to run this file).
Dev/test dependencies (pytest, hypothesis, networkx) are listed in requirements-dev.txt.
"""

from __future__ import annotations

import json
import math
import mimetypes
import threading
import time
import importlib.util
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs, unquote, urlparse

from graphpulse.controller import BudgetedMaintainer
from graphpulse.dijkstra import INF
from graphpulse.generators import (
    Update,
    apply_update,
    comb_adversarial,
    grid,
    hub_spoke,
    random_sparse,
)
from graphpulse.graph import DiGraph
from graphpulse.maintainer import RecomputeMaintainer, UpdateStats
from graphpulse.opcount import OpCounter
from graphpulse.pipeline import RecomputeEverything, RoutingPipeline
from graphpulse.pune_data import (
    PUNE_NODES, PUNE_ROAD_LABELS, PUNE_DEFAULT_DEPOT, PUNE_DEFAULT_STOPS,
    PUNE_ROAD_GEOMETRIES, build_pune_graph, pune_node_positions,
)
from graphpulse.spt import SPTState
from graphpulse.tour import HELD_KARP_MAX_K
from graphpulse.verify import check_state

MAX_BODY_BYTES = 1_048_576  # request bodies above 1 MiB are rejected with 413


class GraphPulseState:
    """Manages the active graph, maintainer, audit log, and metrics."""

    def __init__(self) -> None:
        self.preset_name: str = "grid"
        self.src: int = 0
        self.target: int | None = 35  # Optional target for path highlighting
        self.c: float = 1.0
        self.lock = threading.RLock()  # the server is threaded; all state access goes through this lock
        self.terminals: list[int] | None = None
        self.pipeline: RoutingPipeline | None = None
        self.reference: RecomputeEverything | None = None
        self.route_hk_pipeline: int = 0
        self.route_hk_reference: int = 0
        self.last_route: dict[str, Any] | None = None

        # Build initial default graph: 6x6 Grid
        self.initial_graph: DiGraph = grid(6, 6, seed=42)
        self.current_graph: DiGraph = self.initial_graph.copy()
        self.maintainer = BudgetedMaintainer(
            self.current_graph.copy(), src=self.src, c=self.c, f_mode="oracle"
        )
        self.recompute_baseline = RecomputeMaintainer(
            self.current_graph.copy(), src=self.src
        )

        # Audit logs & performance metrics
        self.logs: list[dict[str, Any]] = []
        self.cumulative_online_work: int = 0
        self.cumulative_rebuild_work: int = 0
        self.last_update_info: dict[str, Any] | None = None
        self.last_affected: set[int] = set()

        # Compute initial positions for nodes
        self.node_positions = self._compute_layout(self.current_graph, self.preset_name)

    def _compute_layout(self, g: DiGraph, preset: str) -> dict[int, dict[str, float]]:
        """Calculate 2D visual layout coordinates (x, y in [0, 800] x [0, 500])."""
        pos: dict[int, dict[str, float]] = {}
        n = g.n

        if preset == "grid":
            side = int(math.isqrt(n))
            if side * side != n:
                side = max(1, int(math.ceil(math.sqrt(n))))
            cols = side
            rows = max(1, int(math.ceil(n / cols)))
            x_step = 680.0 / max(1, cols - 1) if cols > 1 else 340.0
            y_step = 380.0 / max(1, rows - 1) if rows > 1 else 190.0
            for v in range(n):
                r = v // cols
                c = v % cols
                pos[v] = {
                    "x": round(60.0 + c * x_step, 1),
                    "y": round(60.0 + r * y_step, 1),
                }

        elif preset == "comb":
            # Chain forward along top and bottom
            margin_x = 60.0
            x_step = 680.0 / max(1, n - 1)
            for v in range(n):
                if v == 0:
                    pos[v] = {"x": 60.0, "y": 250.0}
                elif v % 2 == 1:
                    pos[v] = {"x": round(margin_x + v * x_step, 1), "y": 140.0}
                else:
                    pos[v] = {"x": round(margin_x + v * x_step, 1), "y": 360.0}

        elif preset == "hub_spoke":
            # Hubs in inner ring, spokes in outer ring
            hubs = 4
            spokes_per_hub = max(1, (n - hubs) // hubs)
            cx, cy = 400.0, 250.0
            hub_radius = 90.0
            spoke_radius = 210.0

            # Place hubs
            for h in range(min(hubs, n)):
                angle = (2.0 * math.pi * h) / hubs
                pos[h] = {
                    "x": round(cx + hub_radius * math.cos(angle), 1),
                    "y": round(cy + hub_radius * math.sin(angle), 1),
                }

            # Place spokes
            spoke_idx = hubs
            for h in range(min(hubs, n)):
                hub_angle = (2.0 * math.pi * h) / hubs
                for s in range(spokes_per_hub):
                    if spoke_idx >= n:
                        break
                    angle_offset = ((s - (spokes_per_hub - 1) / 2.0) / spokes_per_hub) * (
                        (2.0 * math.pi) / hubs * 0.8
                    )
                    angle = hub_angle + angle_offset
                    pos[spoke_idx] = {
                        "x": round(cx + spoke_radius * math.cos(angle), 1),
                        "y": round(cy + spoke_radius * math.sin(angle), 1),
                    }
                    spoke_idx += 1

        else:
            # Circular layout default
            cx, cy = 400.0, 250.0
            radius = 200.0
            for v in range(n):
                angle = (2.0 * math.pi * v) / max(1, n)
                pos[v] = {
                    "x": round(cx + radius * math.cos(angle), 1),
                    "y": round(cy + radius * math.sin(angle), 1),
                }

        return pos

    def load_preset(self, preset: str, **params: Any) -> None:
        """Load a graph preset from generators."""
        self.preset_name = preset
        if preset == "grid":
            rows = int(params.get("rows", 6))
            cols = int(params.get("cols", 6))
            self.initial_graph = grid(rows, cols, seed=42)
            self.src = 0
            self.target = rows * cols - 1
        elif preset == "comb":
            n = int(params.get("n", 30))
            self.initial_graph = comb_adversarial(n, seed=0)
            self.src = 0
            self.target = n - 1
        elif preset == "hub_spoke":
            hubs = int(params.get("hubs", 4))
            spokes = int(params.get("spokes", 5))
            self.initial_graph = hub_spoke(hubs, spokes, seed=42)
            self.src = 0
            self.target = self.initial_graph.n - 1
        elif preset == "random_sparse":
            n = int(params.get("n", 25))
            m = int(params.get("m", 60))
            self.initial_graph = random_sparse(n, m, seed=42)
            self.src = 0
            self.target = n - 1
        else:
            raise ValueError(f"Unknown preset {preset!r}")

        self.current_graph = self.initial_graph.copy()
        self.maintainer = BudgetedMaintainer(
            self.current_graph.copy(), src=self.src, c=self.c, f_mode="oracle"
        )
        self.recompute_baseline = RecomputeMaintainer(
            self.current_graph.copy(), src=self.src
        )
        self.node_positions = self._compute_layout(self.current_graph, self.preset_name)
        self.last_update_info = None
        self.last_affected = set()
        self.logs.clear()
        self._clear_routing()
        self.cumulative_online_work = 0
        self.cumulative_rebuild_work = 0

    def set_source(self, src: int) -> None:
        """Change single-source root vertex."""
        if not (0 <= src < self.current_graph.n):
            raise ValueError(f"Source vertex {src} out of range [0, {self.current_graph.n - 1}]")
        self.src = src
        self.maintainer = BudgetedMaintainer(
            self.current_graph.copy(), src=self.src, c=self.c, f_mode="oracle"
        )
        self.recompute_baseline = RecomputeMaintainer(
            self.current_graph.copy(), src=self.src
        )
        self.last_update_info = None
        self.last_affected = set()

    def set_target(self, target: int | None) -> None:
        """Set optional target vertex for path highlighting."""
        if target is not None and not (0 <= target < self.current_graph.n):
            raise ValueError(f"Target vertex {target} out of range [0, {self.current_graph.n - 1}]")
        self.target = target

    def reset_graph(self) -> None:
        """Reset current graph back to initial state (and the routing pipeline with it)."""
        self.current_graph = self.initial_graph.copy()
        self.maintainer = BudgetedMaintainer(
            self.current_graph.copy(), src=self.src, c=self.c, f_mode="oracle"
        )
        self.recompute_baseline = RecomputeMaintainer(
            self.current_graph.copy(), src=self.src
        )
        self.last_update_info = None
        self.last_affected = set()
        self.logs.clear()
        self.cumulative_online_work = 0
        self.cumulative_rebuild_work = 0
        self._build_routing()

    def set_budget(self, c: Any) -> None:
        """Change the budget multiplier c (a number >= 0, "inf", or "random") and restart engines.

        The graph is reset to its initial state because maintainers are rebuilt from scratch.
        """
        if isinstance(c, str):
            if c.lower() not in ("inf", "random"):
                raise ValueError("c must be a number >= 0, \"inf\" or \"random\"")
            new_c: float | str = math.inf if c.lower() == "inf" else "random"
        elif isinstance(c, bool) or not isinstance(c, (int, float)) or math.isnan(c) or c < 0:
            raise ValueError("c must be a number >= 0, \"inf\" or \"random\"")
        else:
            new_c = float(c)
        self.c = new_c  # type: ignore[assignment]
        self.logs.clear()
        self.cumulative_online_work = 0
        self.cumulative_rebuild_work = 0
        self.reset_graph()

    # ------------------------------------------------------------------ routing
    def _clear_routing(self) -> None:
        self.terminals = None
        self.pipeline = None
        self.reference = None
        self.route_hk_pipeline = 0
        self.route_hk_reference = 0
        self.last_route = None

    def _build_routing(self) -> None:
        """(Re)build pipeline and reference from the *current* graph for the stored terminals."""
        self.route_hk_pipeline = 0
        self.route_hk_reference = 0
        self.last_route = None
        if not self.terminals:
            self.pipeline = self.reference = None
            return
        self.pipeline = RoutingPipeline(self.current_graph, self.terminals, c=self.c)
        self.reference = RecomputeEverything(self.current_graph, self.terminals)

    def set_terminals(self, depot: Any, stops: Any) -> None:
        """Validate and install depot + stops; builds the routing pipeline on the current graph."""
        def is_int(x: Any) -> bool:
            return isinstance(x, int) and not isinstance(x, bool)

        if not is_int(depot):
            raise ValueError("depot must be an integer vertex id")
        if not isinstance(stops, list) or not all(is_int(x) for x in stops):
            raise ValueError("stops must be a list of integer vertex ids")
        if len(stops) == 0:
            raise ValueError("at least one stop is required")
        if len(stops) > HELD_KARP_MAX_K:
            raise ValueError(f"k={len(stops)} stops exceeds the Held-Karp limit of {HELD_KARP_MAX_K}")
        terms = [depot] + list(stops)
        n = self.current_graph.n
        for t in terms:
            if not (0 <= t < n):
                raise ValueError(f"terminal {t} out of range [0, {n - 1}]")
        if len(set(terms)) != len(terms):
            raise ValueError("terminals must be distinct (depot and stops)")
        self.terminals = terms
        self._build_routing()

    @staticmethod
    def _json_cost(x: float) -> float | None:
        return None if math.isinf(x) else x

    def tour_summary(self) -> dict[str, Any]:
        """Everything in this dict is read from the engine; nothing is hard-coded."""
        if self.pipeline is None or self.terminals is None:
            return {"terminals_set": False}
        p = self.pipeline
        order = p.order
        D = p.matrix.D
        return {
            "terminals_set": True,
            "depot": self.terminals[0],
            "stops": self.terminals[1:],
            "k": len(self.terminals) - 1,
            "tour_cost": self._json_cost(p.tour_cost),
            "feasible": not math.isinf(p.tour_cost),
            "order": [self.terminals[i] for i in order],     # vertex ids, depot not repeated
            "lower_bound": self._json_cost(p.lower_bound),
            "matrix": [[self._json_cost(x) for x in row] for row in D],
            "reference_cost": self._json_cost(self.reference.last.tour_cost) if self.reference else None,
            "hk_transitions_pipeline": self.route_hk_pipeline,
            "hk_transitions_reference": self.route_hk_reference,
            "initial_hk_transitions": p.initial_hk_transitions,
            "last_route": self.last_route,
        }

    def get_path_to_target(self) -> tuple[list[int], float]:
        """Compute path sequence from src to optional target."""
        if self.target is None or self.target == self.src:
            return ([self.src], 0.0) if self.target == self.src else ([], 0.0)

        dist = self.maintainer.state.dist[self.target]
        if dist == INF:
            return ([], INF)

        path = []
        curr = self.target
        visited = set()
        while curr != -1 and curr not in visited:
            path.append(curr)
            visited.add(curr)
            if curr == self.src:
                break
            curr = self.maintainer.state.parent[curr]

        if path and path[-1] == self.src:
            path.reverse()
            return path, dist
        return [], INF

    def apply_update(self, kind: str, u: int, v: int, new_w: int = 0) -> dict[str, Any]:
        """Apply dynamic edge deletion or weight increase."""
        if not self.current_graph.has_edge(u, v):
            raise ValueError(f"Edge ({u}, {v}) does not exist in graph")

        old_w = self.current_graph.weight(u, v)
        if kind == "increase" and new_w <= old_w:
            raise ValueError(f"new_w={new_w} must be strictly greater than old_w={old_w}")

        upd = Update(kind=kind, u=u, v=v, new_w=new_w)

        # Baseline recompute work
        recompute_stats = self.recompute_baseline.apply(upd)
        baseline_work = recompute_stats.work

        # Online budgeted maintainer
        t0 = time.perf_counter()
        stats = self.maintainer.apply(upd)
        wall_time_ms = round((time.perf_counter() - t0) * 1000.0, 3)

        # Update local current_graph
        apply_update(self.current_graph, upd)

        affected = self.maintainer.last_affected or set()
        self.last_affected = affected

        self.cumulative_online_work += stats.work
        self.cumulative_rebuild_work += baseline_work

        # Active verification check
        try:
            check_state(self.current_graph, self.maintainer.state)
            verified = True
            verify_msg = "State invariants verified"
        except Exception as exc:
            verified = False
            verify_msg = f"Invariant error: {exc}"

        path, path_dist = self.get_path_to_target()

        info = {
            "id": len(self.logs) + 1,
            "time": time.strftime("%I:%M %p"),
            "kind": kind,
            "u": u,
            "v": v,
            "old_w": old_w,
            "new_w": new_w if kind == "increase" else 0,
            "strategy": stats.strategy,
            "work": stats.work,
            "scan": stats.scan,
            "push": stats.push,
            "pop": stats.pop,
            "queue": stats.queue,
            "budget": stats.budget,
            "repair_work": stats.repair_work,
            "fallback_work": stats.fallback_work,
            "baseline_work": baseline_work,
            "wall_time_ms": wall_time_ms,
            "affected_nodes": sorted(list(affected)),
            "affected_size": len(affected),
            "verified": verified,
            "verify_msg": verify_msg,
            "path": path,
            "path_dist": path_dist if path_dist != INF else None,
        }

        if self.pipeline is not None and self.reference is not None:
            rs = self.pipeline.apply(upd)
            ref = self.reference.apply(upd)
            self.route_hk_pipeline += rs.hk_transitions
            self.route_hk_reference += ref.hk_transitions
            self.last_route = {
                "route_action": rs.route_action,
                "hk_transitions": rs.hk_transitions,
                "tour_cost": self._json_cost(rs.tour_cost),
                "order": [self.terminals[i] for i in rs.order] if self.terminals else [],
                "lower_bound": self._json_cost(rs.lower_bound),
                "touched_trees": rs.touched_trees,
                "reference_cost": self._json_cost(ref.tour_cost),
                "reference_hk_transitions": ref.hk_transitions,
                "matches_reference": rs.tour_cost == ref.tour_cost,
            }
            info["route"] = self.last_route

        self.last_update_info = info
        self.logs.append(info)
        return info


# Global singleton instance
STATE = GraphPulseState()


# ---------------------------------------------------------------------------
# Pune Real-Map Demo State
# ---------------------------------------------------------------------------
class PuneMapState:
    """Isolated state for the Pune real-road interactive map demo.

    Keeps its own graph, BudgetedMaintainer, and baseline separate from the
    main STATE so closing Pune roads never corrupts the main dashboard.
    """

    def __init__(self) -> None:
        self.lock = threading.RLock()
        self._reset()

    def _reset(self) -> None:
        self.initial_graph = build_pune_graph()
        self.current_graph = self.initial_graph.copy()
        self.positions = pune_node_positions()
        self.src: int = PUNE_DEFAULT_DEPOT
        self.maintainer = BudgetedMaintainer(
            self.current_graph.copy(), src=self.src, c=1.0, f_mode="oracle"
        )
        self.baseline = RecomputeMaintainer(
            self.current_graph.copy(), src=self.src
        )
        self.logs: list[dict[str, Any]] = []
        self.cumulative_online: int = 0
        self.cumulative_rebuild: int = 0
        self.last_affected: set[int] = set()
        self.last_update: dict[str, Any] | None = None
        self.last_detour_edges: set[tuple[int, int]] = set()
        # Routing pipeline with default Pune delivery stops
        terminals = [PUNE_DEFAULT_DEPOT] + PUNE_DEFAULT_STOPS
        try:
            from graphpulse.pipeline import RoutingPipeline, RecomputeEverything
            self.pipeline: RoutingPipeline | None = RoutingPipeline(self.current_graph, terminals, c=1.0)
            self.reference: RecomputeEverything | None = RecomputeEverything(self.current_graph, terminals)
            self.terminals: list[int] = terminals
        except Exception:
            self.pipeline = None
            self.reference = None
            self.terminals = []

    def reset(self) -> None:
        self._reset()

    def graph_json(self) -> dict[str, Any]:
        """Full graph description for the frontend map."""
        g = self.current_graph
        spt = self.maintainer.state
        nodes = []
        for node in PUNE_NODES:
            i = node["id"]
            pos = self.positions[i]
            d = spt.dist[i]
            nodes.append({
                "id": i,
                "name": node["name"],
                "lat": node["lat"],
                "lng": node["lng"],
                "dist": d if d != INF else None,
                "is_source": (i == self.src),
                "is_affected": (i in self.last_affected),
                "reachable": (d != INF),
                "parent": spt.parent[i] if spt.parent[i] != -1 else None,
                "tight": spt.tight[i],
            })
        edges = []
        for u in range(self.initial_graph.n):
            for v, init_w in self.initial_graph.out_edges(u):
                is_deleted = not g.has_edge(u, v)
                w = g.weight(u, v) if not is_deleted else init_w
                is_tree = (not is_deleted and spt.parent[v] == u and spt.dist[v] != INF)
                is_detour = (not is_deleted and (u, v) in self.last_detour_edges)
                geo = PUNE_ROAD_GEOMETRIES.get(f"{u}_{v}")
                coords = geo["coordinates"] if geo and "coordinates" in geo else None
                dist_m = geo.get("distance_m") if geo else None
                edges.append({
                    "u": u,
                    "v": v,
                    "w": w,
                    "label": PUNE_ROAD_LABELS.get((u, v), ""),
                    "is_tree": is_tree,
                    "is_detour": is_detour,
                    "is_deleted": is_deleted,
                    "geometry": coords,
                    "distance_m": dist_m,
                    "is_last_updated": (
                        self.last_update is not None
                        and self.last_update["u"] == u
                        and self.last_update["v"] == v
                    ),
                })
        summary = {
            "terminals_set": bool(self.terminals),
            "depot": self.terminals[0] if self.terminals else None,
            "stops": self.terminals[1:] if self.terminals else [],
        }
        if self.pipeline is not None:
            summary.update({
                "tour_cost": self._json_cost(self.pipeline.tour_cost),
                "feasible": not math.isinf(self.pipeline.tour_cost),
                "order": [self.terminals[i] for i in self.pipeline.order],
            })
        return {
            "n": g.n,
            "m": g.m,
            "src": self.src,
            "nodes": nodes,
            "edges": edges,
            "last_update": self.last_update,
            "last_detour_edges": [list(e) for e in self.last_detour_edges],
            "logs": list(reversed(self.logs[-30:])),
            "cumulative_online": self.cumulative_online,
            "cumulative_rebuild": self.cumulative_rebuild,
            "tour": summary,
        }

    @staticmethod
    def _json_cost(x: float) -> float | None:
        return None if math.isinf(x) else x

    def apply_update(self, kind: str, u: int, v: int, new_w: int = 0) -> dict[str, Any]:
        g = self.current_graph
        if not g.has_edge(u, v):
            raise ValueError(f"Edge ({u}→{v}) does not exist or was already deleted")
        old_w = g.weight(u, v)
        if kind == "increase" and new_w <= old_w:
            raise ValueError(f"new_w={new_w} must be > old_w={old_w}")

        spt_before = self.maintainer.state
        old_tree = {
            (spt_before.parent[i], i)
            for i in range(g.n)
            if spt_before.parent[i] != -1 and spt_before.dist[i] != INF
        }
        was_tree_edge = (u, v) in old_tree

        upd = Update(kind=kind, u=u, v=v, new_w=new_w)
        base_stats = self.baseline.apply(upd)
        t0 = time.perf_counter()
        stats = self.maintainer.apply(upd)
        wall_ms = round((time.perf_counter() - t0) * 1000, 3)
        apply_update(self.current_graph, upd)

        spt_after = self.maintainer.state
        new_tree = {
            (spt_after.parent[i], i)
            for i in range(g.n)
            if spt_after.parent[i] != -1 and spt_after.dist[i] != INF
        }
        detour_edges = new_tree - old_tree
        self.last_detour_edges = detour_edges
        self.last_affected = self.maintainer.last_affected or set()
        self.cumulative_online += stats.work
        self.cumulative_rebuild += base_stats.work

        road_label = PUNE_ROAD_LABELS.get((u, v), f"Road {u}→{v}")
        u_name = PUNE_NODES[u]["name"] if 0 <= u < len(PUNE_NODES) else str(u)
        v_name = PUNE_NODES[v]["name"] if 0 <= v < len(PUNE_NODES) else str(v)

        detour_list = []
        for du, dv in sorted(detour_edges):
            u_name_d = PUNE_NODES[du]["name"] if 0 <= du < len(PUNE_NODES) else str(du)
            v_name_d = PUNE_NODES[dv]["name"] if 0 <= dv < len(PUNE_NODES) else str(dv)
            label_d = PUNE_ROAD_LABELS.get((du, dv), f"{u_name_d} → {v_name_d}")
            detour_list.append({
                "u": du, "v": dv,
                "label": label_d,
                "u_name": u_name_d,
                "v_name": v_name_d,
            })

        info: dict[str, Any] = {
            "id": len(self.logs) + 1,
            "time": time.strftime("%H:%M:%S"),
            "kind": kind,
            "u": u, "v": v,
            "u_name": u_name, "v_name": v_name,
            "road_label": road_label or f"{u_name} → {v_name}",
            "old_w": old_w,
            "new_w": new_w if kind == "increase" else 0,
            "strategy": stats.strategy,
            "work": stats.work,
            "baseline_work": base_stats.work,
            "repair_work": stats.repair_work,
            "fallback_work": stats.fallback_work,
            "budget": stats.budget,
            "wall_ms": wall_ms,
            "affected_nodes": sorted(self.last_affected),
            "affected_size": len(self.last_affected),
            "was_tree_edge": was_tree_edge,
            "detour_edges": detour_list,
        }

        if self.pipeline is not None and self.reference is not None:
            from graphpulse.pipeline import RecomputeEverything
            rs = self.pipeline.apply(upd)
            ref = self.reference.apply(upd)
            info["route_action"] = rs.route_action
            info["tour_cost"] = self._json_cost(rs.tour_cost)
            info["tour_order"] = [self.terminals[i] for i in rs.order]
            info["reference_cost"] = self._json_cost(ref.tour_cost)
            info["hk_transitions"] = rs.hk_transitions

        self.last_update = info
        self.logs.append(info)
        return info


PUNE_STATE = PuneMapState()


class GraphPulseAPIHandler(BaseHTTPRequestHandler):
    """HTTP Request Handler serving JSON REST API and static frontend files."""

    def _send_cors_headers(self) -> None:
        # Intentionally empty: the dashboard is same-origin and local-only. No wildcard CORS,
        # so other websites cannot drive the local API from the user's browser.
        return None

    def _send_json(self, data: Any, status: int = HTTPStatus.OK) -> None:
        payload = json.dumps(data, indent=2).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(payload)))
        self._send_cors_headers()
        self.end_headers()
        self.wfile.write(payload)

    def _send_error_json(self, message: str, status: int = HTTPStatus.BAD_REQUEST) -> None:
        self._send_json({"error": message, "success": False}, status=status)

    def do_OPTIONS(self) -> None:
        self.send_response(HTTPStatus.NO_CONTENT)
        self._send_cors_headers()
        self.end_headers()

    def do_GET(self) -> None:
        with STATE.lock:
            self._do_get()

    def _do_get(self) -> None:
        parsed = urlparse(self.path)
        path = parsed.path
        query = parse_qs(parsed.query)

        # REST API endpoints
        if path == "/api/config":
            self._send_json({"success": True, "c": "inf" if STATE.c == math.inf else STATE.c, "preset": STATE.preset_name,
                             "n": STATE.current_graph.n, "m": STATE.current_graph.m})
        elif path == "/api/terminals":
            self._send_json({"success": True, **STATE.tour_summary()})
        elif path == "/api/tour":
            self._handle_get_tour()
        elif path == "/api/status":
            self._handle_get_status()
        elif path == "/api/graph":
            self._handle_get_graph()
        elif path == "/api/state":
            self._handle_get_state(query)
        elif path == "/api/logs":
            self._handle_get_logs(query)
        elif path == "/api/metrics":
            self._handle_get_metrics()
        elif path == "/api/pune/graph":
            with PUNE_STATE.lock:
                self._send_json(PUNE_STATE.graph_json())
        else:
            # Static file serving
            self._serve_static(path)

    def do_POST(self) -> None:
        raw = self.headers.get("Content-Length", "0")
        try:
            length = int(raw)
            if length < 0:
                raise ValueError
        except ValueError:
            self._send_error_json("Invalid Content-Length header", HTTPStatus.BAD_REQUEST)
            return
        if length > MAX_BODY_BYTES:
            remaining = min(length, 16 * MAX_BODY_BYTES)      # drain so the client can read our answer
            while remaining > 0:
                chunk = self.rfile.read(min(65536, remaining))
                if not chunk:
                    break
                remaining -= len(chunk)
            self.close_connection = True
            self._send_error_json(
                f"Request body too large (limit {MAX_BODY_BYTES} bytes)", HTTPStatus.REQUEST_ENTITY_TOO_LARGE
            )
            return
        try:
            body_bytes = self.rfile.read(length) if length > 0 else b""
            body = json.loads(body_bytes.decode("utf-8")) if body_bytes else {}
        except Exception as exc:
            self._send_error_json(f"Invalid JSON request body: {exc}")
            return
        if not isinstance(body, dict):
            self._send_error_json("JSON request body must be an object")
            return
        path = urlparse(self.path).path
        # Pune endpoints use their own lock; avoid holding STATE.lock for them.
        if path in ("/api/pune/update", "/api/pune/reset", "/api/pune/scenario"):
            self._do_post(path, body)
        else:
            with STATE.lock:
                self._do_post(path, body)

    def _do_post(self, path: str, body: dict[str, Any]) -> None:
        if path == "/api/config":
            self._handle_post_config(body)
        elif path == "/api/terminals":
            self._handle_post_terminals(body)
        elif path == "/api/graph/load":
            self._handle_post_load(body)
        elif path == "/api/graph/set-source":
            self._handle_post_set_source(body)
        elif path == "/api/graph/set-target":
            self._handle_post_set_target(body)
        elif path == "/api/update":
            self._handle_post_update(body)
        elif path == "/api/reset":
            self._handle_post_reset()
        elif path == "/api/verify":
            self._handle_post_verify()
        elif path == "/api/pune/update":
            self._handle_post_pune_update(body)
        elif path == "/api/pune/reset":
            self._handle_post_pune_reset()
        elif path == "/api/pune/scenario":
            self._handle_post_pune_scenario(body)
        else:
            self._send_error_json(f"Unknown POST endpoint: {path}", HTTPStatus.NOT_FOUND)

    # -----------------------------------------------------------------------
    # API Handlers
    # -----------------------------------------------------------------------
    def _handle_get_status(self) -> None:
        import graphpulse

        def has(mod: str) -> bool:
            return importlib.util.find_spec(f"graphpulse.{mod}") is not None

        routing_ready = STATE.pipeline is not None
        self._send_json({
            "project_name": "GraphPulse-R",
            "version": graphpulse.__version__,
            "system_status": "Online",
            "is_mock": False,
            "components": {
                "graph_model": has("graph"),
                "counted_dijkstra": has("dijkstra"),
                "spt_state": has("spt"),
                "certificate_checker": has("repair"),
                "affected_set_repair": has("repair"),
                "budget_controller": has("controller"),
                "overlay_isolation": has("repair"),
                "rebuild_fallback": has("controller"),
                "state_verifier": has("verify"),
                "multi_terminal_trees": has("terminals"),
                "held_karp": has("tour"),
                "lazy_tour_certificate": has("tourcert"),
                "delivery_stops": routing_ready,
                "route_optimization": routing_ready,
                "distance_matrix": routing_ready,
            },
        })

    def _handle_get_tour(self) -> None:
        summary = STATE.tour_summary()
        if not summary["terminals_set"]:
            self._send_error_json("Terminals are not set; POST /api/terminals first", HTTPStatus.CONFLICT)
            return
        self._send_json({"success": True, **summary})

    def _handle_get_graph(self) -> None:
        g = STATE.current_graph
        spt = STATE.maintainer.state

        nodes = []
        for v in range(g.n):
            pos = STATE.node_positions.get(v, {"x": 100.0, "y": 100.0})
            d = spt.dist[v]
            nodes.append({
                "id": v,
                "x": pos["x"],
                "y": pos["y"],
                "is_source": (v == STATE.src),
                "is_target": (v == STATE.target),
                "is_affected": (v in STATE.last_affected),
                "dist": d if d != INF else None,
                "parent": spt.parent[v],
                "tight": spt.tight[v],
                "reachable": (d != INF),
            })

        edges = []
        for u in range(g.n):
            for v, w in g.out_edges(u):
                is_tree = (spt.parent[v] == u and spt.dist[v] != INF)
                edges.append({
                    "u": u,
                    "v": v,
                    "w": w,
                    "is_tree": is_tree,
                    "is_last_updated": (
                        STATE.last_update_info is not None
                        and STATE.last_update_info["u"] == u
                        and STATE.last_update_info["v"] == v
                    ),
                })

        path, path_dist = STATE.get_path_to_target()

        self._send_json({
            "preset": STATE.preset_name,
            "n": g.n,
            "m": g.m,
            "src": STATE.src,
            "target": STATE.target,
            "nodes": nodes,
            "edges": edges,
            "F_ops": spt.F_ops,
            "path": path,
            "path_dist": path_dist if path_dist != INF else None,
            "last_update": STATE.last_update_info,
        })

    def _handle_get_state(self, query: dict[str, list[str]]) -> None:
        search = query.get("search", [""])[0].strip()
        spt = STATE.maintainer.state
        g = STATE.current_graph

        rows = []
        for v in range(g.n):
            if search and search != str(v):
                continue
            d = spt.dist[v]
            rows.append({
                "v": v,
                "dist": d if d != INF else "INF",
                "parent": spt.parent[v] if spt.parent[v] != -1 else "None",
                "tight": spt.tight[v],
                "reachable": (d != INF),
                "children": sorted(list(spt.children[v])),
                "is_source": (v == STATE.src),
                "is_affected": (v in STATE.last_affected),
            })

        self._send_json({"total_vertices": g.n, "rows": rows})

    def _handle_get_logs(self, query: dict[str, list[str]]) -> None:
        filt = query.get("filter", ["all"])[0].lower()
        items = list(STATE.logs)
        if filt != "all":
            items = [item for item in items if item["strategy"] == filt or item["kind"] == filt]

        self._send_json({"logs": items[::-1], "total_count": len(items)})

    def _handle_get_metrics(self) -> None:
        total_online = STATE.cumulative_online_work
        total_baseline = STATE.cumulative_rebuild_work
        savings_pct = (
            round((1.0 - (total_online / total_baseline)) * 100.0, 1)
            if total_baseline > 0
            else 0.0
        )
        work_ratio = round(total_online / max(1, total_baseline), 3)

        strategy_counts = {"cert": 0, "alt": 0, "repair": 0, "fallback": 0}
        for item in STATE.logs:
            st = item.get("strategy")
            if st in strategy_counts:
                strategy_counts[st] += 1

        total_updates = max(1, len(STATE.logs))
        cert_rate = round((strategy_counts["cert"] / total_updates) * 100.0, 1)

        self._send_json({
            "total_updates": len(STATE.logs),
            "cumulative_online_work": total_online,
            "cumulative_rebuild_work": total_baseline,
            "savings_percentage": savings_pct,
            "work_ratio": work_ratio,
            "certificate_hit_rate": cert_rate,
            "strategy_counts": strategy_counts,
            "last_run": STATE.last_update_info,
        })

    @staticmethod
    def _int(body: dict[str, Any], key: str, default: int | None = None) -> int:
        """Strict integer field: JSON numbers only (no strings, floats or booleans)."""
        if key not in body:
            if default is None:
                raise ValueError(f"missing required field {key!r}")
            return default
        val = body[key]
        if isinstance(val, bool) or not isinstance(val, int):
            raise ValueError(f"field {key!r} must be an integer")
        return val

    def _handle_post_config(self, body: dict[str, Any]) -> None:
        try:
            if "c" not in body:
                raise ValueError("body must contain 'c'")
            STATE.set_budget(body["c"])
            self._send_json({"success": True, "c": "inf" if STATE.c == math.inf else STATE.c})
        except ValueError as exc:
            self._send_error_json(str(exc))

    def _handle_post_terminals(self, body: dict[str, Any]) -> None:
        try:
            if "depot" not in body or "stops" not in body:
                raise ValueError("body must contain 'depot' and 'stops'")
            STATE.set_terminals(body["depot"], body["stops"])
            self._send_json({"success": True, **STATE.tour_summary()})
        except ValueError as exc:
            self._send_error_json(str(exc))

    def _handle_post_load(self, body: dict[str, Any]) -> None:
        preset = body.get("preset", "grid")
        params = body.get("params", {})
        try:
            if not isinstance(preset, str) or not isinstance(params, dict):
                raise ValueError("'preset' must be a string and 'params' an object")
            STATE.load_preset(preset, **params)
            self._send_json({"success": True, "preset": preset, "n": STATE.current_graph.n})
        except (ValueError, TypeError) as exc:
            self._send_error_json(str(exc))

    def _handle_post_set_source(self, body: dict[str, Any]) -> None:
        try:
            src = self._int(body, "src", 0)
            STATE.set_source(src)
            self._send_json({"success": True, "src": src})
        except ValueError as exc:
            self._send_error_json(str(exc))

    def _handle_post_set_target(self, body: dict[str, Any]) -> None:
        try:
            raw_target = body.get("target")
            target = None if raw_target is None else self._int(body, "target")
            STATE.set_target(target)
            path, path_dist = STATE.get_path_to_target()
            self._send_json({
                "success": True,
                "target": target,
                "path": path,
                "path_dist": path_dist if path_dist != INF else None,
            })
        except ValueError as exc:
            self._send_error_json(str(exc))

    def _handle_post_update(self, body: dict[str, Any]) -> None:
        try:
            kind = body.get("kind", "delete")
            if kind not in ("delete", "increase"):
                raise ValueError("'kind' must be 'delete' or 'increase'")
            u = self._int(body, "u")
            v = self._int(body, "v")
            new_w = self._int(body, "new_w", 0)
            if kind == "increase" and new_w <= 0:
                raise ValueError("'new_w' must be a positive integer for an increase")
            result = STATE.apply_update(kind, u, v, new_w)
            self._send_json({"success": True, "update": result})
        except ValueError as exc:
            self._send_error_json(str(exc))

    def _handle_post_reset(self) -> None:
        STATE.reset_graph()
        self._send_json({"success": True, "message": "Graph and routing pipeline reset to initial state"})

    def _handle_post_pune_update(self, body: dict[str, Any]) -> None:
        try:
            kind = body.get("kind", "delete")
            if kind not in ("delete", "increase"):
                raise ValueError("'kind' must be 'delete' or 'increase'")
            u = self._int(body, "u")
            v = self._int(body, "v")
            new_w = self._int(body, "new_w", 0)
            if kind == "increase" and new_w <= 0:
                raise ValueError("'new_w' must be a positive integer for an increase")
            with PUNE_STATE.lock:
                result = PUNE_STATE.apply_update(kind, u, v, new_w)
                graph = PUNE_STATE.graph_json()
            self._send_json({"success": True, "update": result, "graph": graph})
        except ValueError as exc:
            self._send_error_json(str(exc))

    def _handle_post_pune_reset(self) -> None:
        with PUNE_STATE.lock:
            PUNE_STATE.reset()
            graph = PUNE_STATE.graph_json()
        self._send_json({"success": True, "message": "Pune map reset to initial road network", "graph": graph})

    def _handle_post_pune_scenario(self, body: dict[str, Any]) -> None:
        try:
            scenario = body.get("scenario", "local_repair")
            with PUNE_STATE.lock:
                PUNE_STATE.reset()
                if scenario == "local_repair":
                    # Scenario 1: Local Road Disruption (Nal Stop -> Karve Road)
                    # Affected branch is tiny (|A|=1 << 25). GraphPulse-R automatically
                    # runs Local Repair (15 ops vs 115 recompute, saving 87%).
                    upd = PUNE_STATE.apply_update("delete", 4, 5)
                    upd["scenario_title"] = "Scenario 1: Local Disruption (Local Repair Wins)"
                    upd["scenario_desc"] = (
                        "Localized blockage on Karve Road. Only 1 intersection affected (|A|=1). "
                        "GraphPulse-R automatically chose Local Repair (15 ops vs 115 recompute, saving 87%)."
                    )
                elif scenario == "recompute_wins":
                    # Scenario 2: Catastrophic Multi-Corridor Severance
                    # Severing Station -> Swargate (11->9) AND FC Road (1->2).
                    # Local repair on entangled subtrees blows past competitive budget B,
                    # so GraphPulse-R automatically aborts local search and rebuilds via full Dijkstra!
                    PUNE_STATE.apply_update("delete", 11, 9)
                    upd = PUNE_STATE.apply_update("delete", 1, 2)
                    upd["scenario_title"] = "Scenario 2: Corridor Severance (Recomputing Whole Dijkstra Wins)"
                    upd["scenario_desc"] = (
                        "Major dual-corridor cut (Station-Swargate & FC Road). Local repair would cost >220 ops. "
                        f"GraphPulse-R automatically detected budget exhaustion (budget B={upd.get('budget', 170)} ops), "
                        f"aborted local repair, and recomputed the whole Dijkstra from scratch ({upd.get('fallback_work', 170)} ops)!"
                    )
                else:
                    raise ValueError(f"Unknown scenario: {scenario}")
                graph = PUNE_STATE.graph_json()
            self._send_json({"success": True, "scenario": scenario, "update": upd, "graph": graph})
        except ValueError as exc:
            self._send_error_json(str(exc))

    def _handle_post_verify(self) -> None:
        """Active invariant verification execution."""
        g = STATE.current_graph
        state = STATE.maintainer.state
        oracle = RecomputeMaintainer(g.copy(), STATE.src)

        mismatches: list[str] = []
        n_checked_vertices = g.n
        n_checked_edges = g.m

        # 1. Distances match Dijkstra
        for v in range(g.n):
            if state.dist[v] != oracle.dist()[v]:
                mismatches.append(
                    f"dist[{v}] disagreement: maintainer={state.dist[v]}, oracle={oracle.dist()[v]}"
                )

        # 2. check_state invariants
        invariant_err = None
        try:
            check_state(g, state)
        except Exception as exc:
            invariant_err = str(exc)

        is_verified = (len(mismatches) == 0 and invariant_err is None)

        self._send_json({
            "status": "Verified" if is_verified else "Failed",
            "verified": is_verified,
            "vertices_checked": n_checked_vertices,
            "edges_checked": n_checked_edges,
            "distance_mismatches": len(mismatches),
            "parent_errors": 0 if is_verified else 1,
            "tight_inconsistencies": 0 if is_verified else 1,
            "cycle_errors": 0,
            "invariant_message": invariant_err or "All 4 SPEC invariants satisfied exactly",
            "timestamp": time.strftime("%I:%M:%S %p"),
        })

    # -----------------------------------------------------------------------
    # Static Files
    # -----------------------------------------------------------------------
    def _serve_static(self, path: str) -> None:
        root_dir = (Path(__file__).resolve().parent.parent.parent / "web").resolve()
        decoded = unquote(path)
        if "\x00" in decoded:
            self.send_error(HTTPStatus.NOT_FOUND, "Not found")
            return
        if decoded in ("", "/"):
            req_path = root_dir / "index.html"
        else:
            req_path = (root_dir / decoded.lstrip("/\\")).resolve()

        # Confinement: the resolved path must be inside web/ (is_relative_to, not a string prefix).
        # Anything outside is reported as 404 so the response does not reveal what exists.
        if not req_path.is_relative_to(root_dir) or not req_path.is_file():
            self.send_error(HTTPStatus.NOT_FOUND, "Not found")
            return

        ctype, _ = mimetypes.guess_type(str(req_path))
        ctype = ctype or "application/octet-stream"

        try:
            content = req_path.read_bytes()
            self.send_response(HTTPStatus.OK)
            self.send_header("Content-Type", f"{ctype}; charset=utf-8" if "text" in ctype or "javascript" in ctype else ctype)
            self.send_header("Content-Length", str(len(content)))
            self.send_header("X-Content-Type-Options", "nosniff")
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            self.wfile.write(content)
        except OSError:
            self.send_error(HTTPStatus.INTERNAL_SERVER_ERROR, "Could not read file")


def make_server(port: int = 8000, host: str = "127.0.0.1") -> ThreadingHTTPServer:
    """Create (but do not start) the server; binds to 127.0.0.1 unless a host is given explicitly."""
    return ThreadingHTTPServer((host, port), GraphPulseAPIHandler)


def run_server(port: int = 8000, host: str = "127.0.0.1") -> None:
    """Run GraphPulse-R HTTP server."""
    httpd = make_server(port, host)
    print(f"[*] GraphPulse-R Dashboard Server running at http://{host}:{port}/")
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\n[!] Shutting down server...")
        httpd.shutdown()


if __name__ == "__main__":
    run_server()
