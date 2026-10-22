# GraphPulse-R dashboard API

Local-only JSON API served by `src/graphpulse/server.py` (Python standard library, `ThreadingHTTPServer`).

* **Binding:** `127.0.0.1` unless `--host` is passed explicitly to `run_ui.py`.
* **Same-origin only:** no CORS headers are sent (other websites cannot drive the local API from the user's browser).
* **Concurrency:** all state access is guarded by one re-entrant lock; requests are serialised.
* **Content type:** request and response bodies are `application/json; charset=utf-8`. A request body must be a JSON **object**.
* **Integers:** every integer field must be a JSON number that is an integer; strings, floats and booleans are rejected with `400`.
* **Request size:** bodies above **1 MiB** are rejected with `413`.
* **Static files:** served only from `web/`; anything outside (including percent-encoded `..`) returns `404`.
* **Values:** every number in a response is computed by the engine. `INF` (unreachable / infeasible) is encoded as `null`.

All error responses have the shape `{"success": false, "error": "<message>"}`.

| Status | Meaning |
|---|---|
| 200 | OK |
| 400 | malformed JSON, wrong types, invalid ids / terminals, update not applicable (missing edge, non-increasing weight), `k > 18` |
| 404 | unknown endpoint or file |
| 409 | `GET /api/tour` before terminals were set |
| 413 | request body larger than 1 MiB |

## Routing endpoints (Milestone 8.1)

### `POST /api/terminals`
Set the depot and delivery stops; builds the `RoutingPipeline` (and an independent `RecomputeEverything` reference) on the **current** graph.

Request: `{"depot": int, "stops": [int, ...]}` — terminals must be distinct and in `[0, n-1]`; `1 ≤ len(stops) ≤ 18` (Held–Karp limit).

Response (200): `{"success": true, ...tour summary...}` (see `GET /api/tour`).
On any `400` the existing pipeline is left unchanged.

### `GET /api/tour`
Response (200):

| Field | Type | Meaning |
|---|---|---|
| `terminals_set` | bool | always `true` here |
| `depot`, `stops`, `k` | int, [int], int | current terminals |
| `tour_cost` | int \| null | optimal tour cost; `null` when infeasible |
| `feasible` | bool | a finite tour exists |
| `order` | [int] | stops in visiting order (vertex ids; the depot is not repeated); `[]` if infeasible |
| `lower_bound` | int \| null | lower bound stored by the lazy certificate (equals `tour_cost` in exact mode) |
| `matrix` | [[int \| null]] | terminal distance matrix, index 0 = depot |
| `reference_cost` | int \| null | cost from the independent recompute-everything reference |
| `hk_transitions_pipeline`, `hk_transitions_reference` | int | cumulative Held–Karp transitions since terminals were set / last reset |
| `initial_hk_transitions` | int | transitions of the initial solve (not counted above) |
| `last_route` | object \| null | routing stats of the most recent update (below) |

`409` if terminals are not set.

### `POST /api/update` (extended)
Request: `{"kind": "delete" | "increase", "u": int, "v": int, "new_w": int}` (`new_w` required and positive for `increase`).
Response (200): `{"success": true, "update": {...}}` where `update` has the existing shortest-path fields (`strategy`, `work`, `scan`, `push`, `pop`, `queue`, `budget`, `repair_work`, `fallback_work`, `baseline_work`, `affected_nodes`, `verified`, `path`, ...) and, **when terminals are set**, a `route` object:

| `route` field | Type | Meaning |
|---|---|---|
| `route_action` | `"kept"` \| `"kept_eps"` \| `"resolved"` \| `"infeasible"` | what the lazy certificate decided |
| `hk_transitions` | int | Held–Karp transitions this update (0 when kept) |
| `tour_cost`, `lower_bound` | int \| null | |
| `order` | [int] | visiting order after the update |
| `touched_trees` | int | trees whose strategy was not `cert` |
| `reference_cost`, `reference_hk_transitions` | int \| null, int | recompute-everything reference |
| `matches_reference` | bool | pipeline cost equals the reference cost |

### `POST /api/reset`
Resets the graph **and** the routing pipeline (terminals are kept; counters cleared) to the initial state. Response: `{"success": true, "message": "..."}`.

## Shortest-path endpoints (unchanged semantics)

| Endpoint | Request | Response |
|---|---|---|
| `GET /api/status` | — | `{project_name, version, system_status, is_mock, components{...}}`; every component flag is computed (module availability, terminals set) |
| `GET /api/graph` | — | nodes (`id, x, y, dist, parent, tight, is_source, is_target, is_affected`), edges, `F_ops`, `path`, `last_update` |
| `POST /api/graph/load` | `{"preset": "grid"\|"comb"\|"hub_spoke"\|"random_sparse", "params": {...}}` | `{success, preset, n}`; clears terminals |
| `POST /api/graph/set-source` | `{"src": int}` | `{success, src}` |
| `POST /api/graph/set-target` | `{"target": int \| null}` | `{success, target, path, path_dist}` |
| `GET /api/state?search=<id>` | — | per-vertex table |
| `GET /api/logs?filter=all\|cert\|alt\|repair\|fallback\|delete\|increase` | — | `{logs, total_count}` |
| `GET /api/metrics` | — | cumulative online vs rebuild work, strategy counts |
| `POST /api/verify` | — | invariant verification of the live state against a Dijkstra oracle |
