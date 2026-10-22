"""Milestone 8.1: routing API, input validation and server hardening (T8.1-01 .. T8.1-12)."""

from __future__ import annotations

import ast
import http.client
import inspect
import json
import textwrap
import threading

import pytest

import graphpulse.server as server
from graphpulse.dijkstra import dijkstra
from graphpulse.opcount import OpCounter
from graphpulse.tour import brute_force_tour


@pytest.fixture()
def api():
    server.STATE = server.GraphPulseState()
    httpd = server.make_server(0)
    t = threading.Thread(target=httpd.serve_forever, daemon=True)
    t.start()
    port = httpd.server_address[1]

    def call(method, path, body=None, raw=None, headers=None):
        conn = http.client.HTTPConnection("127.0.0.1", port, timeout=30)
        data = raw if raw is not None else (json.dumps(body).encode() if body is not None else None)
        h = {"Content-Type": "application/json", **(headers or {})}
        conn.request(method, path, body=data, headers=h)
        r = conn.getresponse()
        payload = r.read()
        conn.close()
        try:
            js = json.loads(payload)
        except Exception:
            js = None
        return r.status, js, payload

    call.httpd = httpd
    yield call
    httpd.shutdown()
    httpd.server_close()


def true_matrix(terms):
    g = server.STATE.current_graph
    return [[dijkstra(g, a, OpCounter())[0][b] for b in terms] for a in terms]


def test_t81_01_set_terminals_and_get_tour(api):
    st, js, _ = api("POST", "/api/terminals", {"depot": 0, "stops": [5, 12, 20, 35]})
    assert st == 200 and js["success"] and js["k"] == 4
    st, tour, _ = api("GET", "/api/tour")
    assert st == 200 and tour["feasible"]
    terms = [0, 5, 12, 20, 35]
    bf_cost, _ = brute_force_tour(true_matrix(terms))
    assert tour["tour_cost"] == bf_cost
    assert sorted(tour["order"]) == [5, 12, 20, 35]


def test_t81_02_update_returns_routing_stats(api):
    api("POST", "/api/terminals", {"depot": 0, "stops": [5, 12, 20, 35]})
    st, js, _ = api("POST", "/api/update", {"kind": "increase", "u": 0, "v": 1, "new_w": 50})
    assert st == 200
    route = js["update"]["route"]
    assert set(route) >= {"route_action", "hk_transitions", "tour_cost", "order", "lower_bound",
                          "touched_trees", "reference_cost", "matches_reference"}
    assert route["matches_reference"] is True and route["tour_cost"] == route["reference_cost"]
    st, tour, _ = api("GET", "/api/tour")
    assert tour["tour_cost"] == brute_force_tour(true_matrix([0, 5, 12, 20, 35]))[0]


@pytest.mark.parametrize("body", [
    {"depot": 0, "stops": [3, 3]},          # duplicate stops
    {"depot": 3, "stops": [3, 4]},          # depot equals a stop
    {"depot": 0, "stops": [99]},            # out of range
    {"depot": 0, "stops": [-1]},
    {"depot": 0, "stops": []},
])
def test_t81_03_bad_terminals_leave_pipeline_unchanged(api, body):
    api("POST", "/api/terminals", {"depot": 0, "stops": [5, 6]})
    st0, before, _ = api("GET", "/api/tour")
    st, js, _ = api("POST", "/api/terminals", body)
    assert st == 400 and js["success"] is False and js["error"]
    st1, after, _ = api("GET", "/api/tour")
    assert before["stops"] == after["stops"] and before["tour_cost"] == after["tour_cost"]


def test_t81_04_too_many_stops(api):
    st, js, _ = api("POST", "/api/terminals", {"depot": 0, "stops": list(range(1, 20))})
    assert st == 400 and "18" in js["error"]


@pytest.mark.parametrize("path,raw,body", [
    ("/api/terminals", b"{not json", None),
    ("/api/terminals", None, {"depot": "0", "stops": [1]}),
    ("/api/terminals", None, {"depot": 0, "stops": "12"}),
    ("/api/terminals", None, [1, 2]),
    ("/api/update", None, {"kind": "delete", "u": "0", "v": 1}),
    ("/api/update", None, {"kind": "delete", "u": 0, "v": 1.5}),
    ("/api/update", None, {"kind": "delete", "u": True, "v": 1}),
    ("/api/update", None, {"kind": "explode", "u": 0, "v": 1}),
    ("/api/graph/set-source", None, {"src": "0"}),
])
def test_t81_05_malformed_and_wrong_types(api, path, raw, body):
    st, js, _ = api("POST", path, body, raw=raw)
    assert st == 400 and js["success"] is False


def test_t81_06_oversized_body(api):
    st, js, _ = api("POST", "/api/terminals", raw=b"x" * (2 * 1024 * 1024))
    assert st == 413


@pytest.mark.parametrize("path", ["/../AGENTS.md", "/%2e%2e/AGENTS.md", "/web/../pyproject.toml",
                                  "/..%2fpyproject.toml", "/%2e%2e/%2e%2e/pyproject.toml", "/css/../../pyproject.toml"])
def test_t81_07_path_traversal(api, path):
    st, js, body = api("GET", path)
    assert st == 404
    assert b"build-system" not in body and b"setuptools" not in body and b"AGENTS" not in body


def test_t81_07b_static_files_still_served(api):
    st, _, body = api("GET", "/")
    assert st == 200 and b"<html" in body.lower()


def test_t81_08_local_only_binding(api):
    assert api.httpd.server_address[0] == "127.0.0.1"
    assert inspect.signature(server.make_server).parameters["host"].default == "127.0.0.1"
    assert inspect.signature(server.run_server).parameters["host"].default == "127.0.0.1"


def test_t81_09_disconnection_shows_infeasible(api):
    api("POST", "/api/graph/load", {"preset": "hub_spoke", "params": {"hubs": 1, "spokes": 3}})
    st, js, _ = api("POST", "/api/terminals", {"depot": 0, "stops": [1, 2]})
    assert st == 200 and js["feasible"]
    st, js, _ = api("POST", "/api/update", {"kind": "delete", "u": 0, "v": 1})   # only road into stop 1
    assert st == 200 and js["update"]["route"]["route_action"] == "infeasible"
    assert js["update"]["route"]["tour_cost"] is None
    st, tour, _ = api("GET", "/api/tour")
    assert tour["feasible"] is False and tour["tour_cost"] is None


def test_t81_10_concurrent_updates(api):
    api("POST", "/api/terminals", {"depot": 0, "stops": [5, 12, 20, 35]})
    g = server.STATE.current_graph
    edges = [(u, v) for u in range(g.n) for v, _ in g.out_edges(u)][:20]
    results, errors = [], []

    def worker(e):
        try:
            results.append(api("POST", "/api/update", {"kind": "increase", "u": e[0], "v": e[1], "new_w": 1000})[0])
        except Exception as exc:                       # pragma: no cover
            errors.append(exc)

    threads = [threading.Thread(target=worker, args=(e,)) for e in edges]
    [t.start() for t in threads]
    [t.join() for t in threads]
    assert not errors and results == [200] * 20
    st, ver, _ = api("POST", "/api/verify")
    assert ver["verified"] is True
    st, tour, _ = api("GET", "/api/tour")
    assert tour["tour_cost"] == tour["reference_cost"]


def test_t81_11_no_hard_coded_telemetry():
    src = inspect.getsource(server)
    assert "project_progress" not in src
    for fn in (server.GraphPulseAPIHandler._handle_get_status, server.GraphPulseState.tour_summary,
               server.GraphPulseAPIHandler._handle_get_tour):
        tree = ast.parse(textwrap.dedent(inspect.getsource(fn)))
        nums = [n.value for n in ast.walk(tree) if isinstance(n, ast.Constant)
                and isinstance(n.value, (int, float)) and not isinstance(n.value, bool)]
        # 0 and 1 are list indices / "k = len - 1", never reported values
        assert [x for x in nums if x not in (0, 1)] == [], f"{fn.__name__} contains numeric literals {nums}"


def test_t81_12_regression_existing_endpoints_and_reset(api):
    st, js, _ = api("GET", "/api/status")
    assert st == 200 and js["components"]["budget_controller"] is True
    assert js["components"]["route_optimization"] is False          # computed: no terminals yet
    api("POST", "/api/terminals", {"depot": 0, "stops": [5, 12]})
    st, js, _ = api("GET", "/api/status")
    assert js["components"]["route_optimization"] is True
    st, g, _ = api("GET", "/api/graph")
    assert st == 200 and g["n"] == 36
    st, before, _ = api("GET", "/api/tour")
    api("POST", "/api/update", {"kind": "delete", "u": 0, "v": 1})
    st, js, _ = api("POST", "/api/reset")
    assert st == 200
    st, after, _ = api("GET", "/api/tour")
    assert after["tour_cost"] == before["tour_cost"]
    assert after["hk_transitions_pipeline"] == 0 and after["last_route"] is None
    st, js, _ = api("POST", "/api/update", {"kind": "delete", "u": 0, "v": 1})   # still works without terminals? (they remain)
    assert st == 200
