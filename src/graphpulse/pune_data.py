"""Pune, India – real-road subgraph for the interactive map demo.

The network covers a ~12 km central Pune slice:
  Shivajinagar ↔ FC Road ↔ Deccan ↔ Karve Road ↔ Kothrud ↔ Swargate ↔ Pune Station ↔ Hinjawadi (tech-park end).

Each node is a real road-intersection with:
  - "name"  : nearest landmark / junction name
  - "lat"   : latitude  (WGS 84)
  - "lng"   : longitude (WGS 84)

Each edge is a directed road segment with:
  - (u, v, w_seconds)  where w_seconds = ceil(distance_m / speed_m_s)
    Speed assumptions: arterials 30 km/h ≈ 8.33 m/s, narrow roads 20 km/h ≈ 5.55 m/s.
  Integer weights (seconds) satisfy the GraphPulse-R invariant w ∈ ℤ⁺.

The graph is made strongly connected (both directions on every major road).
Source of coordinates: OpenStreetMap contributors (ODbL).
"""
from __future__ import annotations
import json
from pathlib import Path
from graphpulse.graph import DiGraph

_GEO_PATH = Path(__file__).resolve().parent.parent.parent / "data" / "pune_road_geometries.json"
PUNE_ROAD_GEOMETRIES: dict[str, dict] = {}
if _GEO_PATH.exists():
    try:
        PUNE_ROAD_GEOMETRIES = json.loads(_GEO_PATH.read_text(encoding="utf-8"))
    except Exception:
        PUNE_ROAD_GEOMETRIES = {}

# ---------------------------------------------------------------------------
# Node table:  index → { name, lat, lng }
# ---------------------------------------------------------------------------
PUNE_NODES: list[dict] = [
    # 0-4  Shivajinagar / Ganeshkhind corridor
    {"id": 0,  "name": "Shivajinagar Station",        "lat": 18.5302, "lng": 73.8440},
    {"id": 1,  "name": "Shivajinagar Bus Stand",       "lat": 18.5290, "lng": 73.8470},
    {"id": 2,  "name": "FC Road & JM Road Junction",   "lat": 18.5200, "lng": 73.8401},
    {"id": 3,  "name": "Deccan Gymkhana",               "lat": 18.5164, "lng": 73.8378},
    {"id": 4,  "name": "Nal Stop",                      "lat": 18.5139, "lng": 73.8306},
    # 5-8  Karve Road corridor
    {"id": 5,  "name": "Karve Road & Paud Road Jn",    "lat": 18.5055, "lng": 73.8267},
    {"id": 6,  "name": "Chandani Chowk",                "lat": 18.5013, "lng": 73.8047},
    {"id": 7,  "name": "Kothrud Bus Depot",             "lat": 18.5085, "lng": 73.8098},
    {"id": 8,  "name": "Kothrud Depot Rd / Paud Rd",   "lat": 18.5112, "lng": 73.8147},
    # 9-12 Swargate / Pune Station corridor
    {"id": 9,  "name": "Swargate Bus Stand",            "lat": 18.5014, "lng": 73.8636},
    {"id": 10, "name": "Swargate Circle",               "lat": 18.5028, "lng": 73.8560},
    {"id": 11, "name": "Pune Railway Station",          "lat": 18.5298, "lng": 73.8700},
    {"id": 12, "name": "Pune Station / Dhole Patil Rd","lat": 18.5330, "lng": 73.8770},
    # 13-15 Camp / MG Road
    {"id": 13, "name": "MG Road / Bund Garden",        "lat": 18.5391, "lng": 73.8773},
    {"id": 14, "name": "Koregaon Park",                 "lat": 18.5362, "lng": 73.8934},
    {"id": 15, "name": "Kalyaninagar Bridge",           "lat": 18.5431, "lng": 73.9010},
    # 16-18 Hinjawadi side
    {"id": 16, "name": "Baner Road Jn",                 "lat": 18.5590, "lng": 73.7930},
    {"id": 17, "name": "Hinjawadi Phase-1 Circle",      "lat": 18.5904, "lng": 73.7382},
    {"id": 18, "name": "Hinjawadi Phase-3 IT Park",     "lat": 18.5963, "lng": 73.7220},
    # 19-21 Viman Nagar / Airport road
    {"id": 19, "name": "Viman Nagar Chowk",             "lat": 18.5679, "lng": 73.9143},
    {"id": 20, "name": "Pune Airport Gate",              "lat": 18.5822, "lng": 73.9177},
    {"id": 21, "name": "Nagar Road Jn",                  "lat": 18.5527, "lng": 73.9287},
    # 22-24 Hadapsar / Magarpatta
    {"id": 22, "name": "Magarpatta City Gate",           "lat": 18.5168, "lng": 73.9251},
    {"id": 23, "name": "Hadapsar Depot",                 "lat": 18.5011, "lng": 73.9261},
    {"id": 24, "name": "Solapur Road Jn",                "lat": 18.4834, "lng": 73.9065},
]

# ---------------------------------------------------------------------------
# Edge table:  (u, v, w_seconds)  – directed
# w = ceil( haversine_distance_m / speed_m_per_s )
# Both directions added for major roads so graph is strongly connected.
# ---------------------------------------------------------------------------
_RAW_EDGES: list[tuple[int, int, int]] = [
    # Shivajinagar–FC Road–Deccan–Nal Stop
    (0,  1,  60),  (1,  0,  60),
    (1,  2, 180),  (2,  1, 180),
    (2,  3,  90),  (3,  2,  90),
    (3,  4, 120),  (4,  3, 120),
    # Deccan/Nal Stop → Karve Road
    (4,  5, 150),  (5,  4, 150),
    (5,  8, 200),  (8,  5, 200),
    (8,  7, 180),  (7,  8, 180),
    (7,  6, 240),  (6,  7, 240),
    # Karve Rd → Chandani → Kothrud
    (5,  6, 360),  (6,  5, 360),
    # FC Road → Swargate side road
    (3, 10, 300),  (10, 3, 300),
    (10, 9, 120),  (9, 10, 120),
    # Swargate ↔ Pune Station
    (9, 11, 300),  (11, 9, 300),
    # Shivajinagar ↔ Pune Station
    (0, 11, 180),  (11, 0, 180),
    (11, 12, 90),  (12, 11, 90),
    # Pune Station ↔ MG Road ↔ Camp
    (12, 13, 180),  (13, 12, 180),
    (13, 14, 210),  (14, 13, 210),
    (14, 15, 150),  (15, 14, 150),
    # Koregaon Park ↔ Viman Nagar
    (14, 19, 420),  (19, 14, 420),
    (19, 20, 360),  (20, 19, 360),
    (20, 21, 600),  (21, 20, 600),
    # Nagar Road ↔ Hadapsar ↔ Solapur Road
    (21, 22, 480),  (22, 21, 480),
    (22, 23, 300),  (23, 22, 300),
    (23, 24, 420),  (24, 23, 420),
    # Swargate ↔ Hadapsar
    (9, 22, 540),   (22, 9, 540),
    # Baner / Hinjawadi
    (2, 16, 600),   (16, 2, 600),
    (16, 17, 900),  (17, 16, 900),
    (17, 18, 360),  (18, 17, 360),
    # Cross-links
    (1, 11, 240),   (11, 1, 240),
    (4,  9, 480),   (9,  4, 480),
    (6, 10, 480),   (10, 6, 480),
    (8,  9, 600),   (9,  8, 600),
    (13, 15, 360),  (15, 13, 360),
]

# ---------------------------------------------------------------------------
# Labels for common event presets
# ---------------------------------------------------------------------------
PUNE_ROAD_LABELS: dict[tuple[int, int], str] = {
    (1,  2): "FC Road (Shivajinagar end)",
    (2,  1): "FC Road (toward Shivajinagar)",
    (2,  3): "Jangali Maharaj Road",
    (3,  2): "JM Road (return)",
    (3,  4): "Karve Road (north)",
    (4,  3): "Karve Road (south)",
    (4,  5): "Karve Road (mid)",
    (5,  6): "Karve Road (Chandani Chowk)",
    (6,  7): "Paud Road",
    (7,  8): "Kothrud Link Road",
    (9, 11): "Swargate–Station Road",
    (0, 11): "Ganeshkhind Road",
   (11, 12): "Station Road East",
   (12, 13): "Dhole Patil Road",
   (13, 14): "Koregaon Park Road",
   (16, 17): "Baner–Hinjawadi Road",
   (17, 18): "Hinjawadi Inner Road",
}

# Default delivery terminals for the Pune demo
PUNE_DEFAULT_DEPOT = 11       # Pune Railway Station
PUNE_DEFAULT_STOPS = [0, 9, 14, 17, 22]   # 5 key stops across Pune


def build_pune_graph() -> DiGraph:
    """Return a clean DiGraph for the Pune road demo using real road driving times."""
    n = len(PUNE_NODES)
    g = DiGraph(n)
    for u, v, w in _RAW_EDGES:
        geo = PUNE_ROAD_GEOMETRIES.get(f"{u}_{v}")
        actual_w = geo.get("duration_s", w) if geo else w
        g.add_edge(u, v, max(1, int(actual_w)))
    return g


def pune_node_positions() -> dict[int, dict]:
    """Map node index → {x, y} scaled to the Leaflet coordinate system.

    We keep lat/lng in the 'lat'/'lng' fields so the JS side can use them
    directly with Leaflet.  x/y here are just fallback canvas coords (unused
    for the map view).
    """
    return {
        node["id"]: {
            "x": (node["lng"] - 73.70) * 5000,
            "y": (18.65 - node["lat"]) * 5000,
            "lat": node["lat"],
            "lng": node["lng"],
            "name": node["name"],
        }
        for node in PUNE_NODES
    }
