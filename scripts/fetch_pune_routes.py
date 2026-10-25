import sys
from pathlib import Path
import json
import time
import urllib.request

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))
from graphpulse.pune_data import PUNE_NODES, _RAW_EDGES

out_file = Path(__file__).resolve().parent.parent / "data" / "pune_road_geometries.json"

print(f"Total directed edges to fetch: {len(_RAW_EDGES)}")
geometries = {}
if out_file.exists():
    try:
        geometries = json.loads(out_file.read_text(encoding="utf-8"))
        print(f"Loaded {len(geometries)} cached geometries from {out_file.name}")
    except Exception as e:
        print("Error reading existing cache:", e)

node_by_id = {n["id"]: n for n in PUNE_NODES}

success = 0
for i, (u, v, orig_w) in enumerate(_RAW_EDGES):
    key = f"{u}_{v}"
    if key in geometries and len(geometries[key].get("coordinates", [])) > 2:
        continue
    
    u_node = node_by_id[u]
    v_node = node_by_id[v]
    
    lng1, lat1 = u_node["lng"], u_node["lat"]
    lng2, lat2 = v_node["lng"], v_node["lat"]
    
    url = f"https://router.project-osrm.org/route/v1/driving/{lng1},{lat1};{lng2},{lat2}?overview=full&geometries=geojson"
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "GraphPulse-R/1.0 (Educational Project)"})
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read().decode())
        if data.get("code") == "Ok" and data.get("routes"):
            route = data["routes"][0]
            # geojson coordinates are [lng, lat]; Leaflet uses [lat, lng]
            # Convert to [[lat, lng], ...] for Leaflet
            leaflet_coords = [[pt[1], pt[0]] for pt in route["geometry"]["coordinates"]]
            geometries[key] = {
                "u": u,
                "v": v,
                "distance_m": round(route.get("distance", 0), 1),
                "duration_s": max(30, int(round(route.get("duration", 0)))),
                "coordinates": leaflet_coords
            }
            success += 1
            print(f"[{i+1}/{len(_RAW_EDGES)}] Edge ({u}->{v}) {u_node['name']} -> {v_node['name']}: {len(leaflet_coords)} points, {route.get('distance', 0):.0f}m")
        else:
            print(f"[{i+1}/{len(_RAW_EDGES)}] Failed code for ({u}->{v}): {data.get('code')}")
    except Exception as exc:
        print(f"[{i+1}/{len(_RAW_EDGES)}] Exception for ({u}->{v}): {exc}")
    
    time.sleep(0.3)  # Gentle rate limiting to respect OSRM public server

out_file.write_text(json.dumps(geometries, indent=2), encoding="utf-8")
print(f"Done! Successfully wrote {len(geometries)} geometries to {out_file}")
