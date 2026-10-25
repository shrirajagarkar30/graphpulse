// Pune Real-Map Demo page — GraphPulse-R
// Interactive Leaflet map: click any road to close it or add congestion.
// Algorithms run on the real Pune road network served by /api/pune/*.

const TILE_URL = 'https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png';
const TILE_ATTR = '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors';
const PUNE_CENTER = [18.530, 73.860];
const ZOOM = 12;

// Strategy colour palette (matches the rest of the UI)
const STRATEGY_COLOR = {
  cert: '#22c55e',
  alt: '#f59e0b',
  repair: '#3b82f6',
  fallback: '#ef4444',
  recompute: '#8b5cf6',
};
const STRATEGY_DESC = {
  cert:      'Certificate hit — zero graph repair (1 SCAN)',
  alt:       'Alternative support — parent rewired, no Dijkstra',
  repair:    'Budgeted local Dijkstra on affected subgraph',
  fallback:  'Budget exceeded — full Dijkstra rebuild after abort',
  recompute: 'Full Dijkstra Recompute — entire shortest-path tree rebuilt from scratch',
};

// --------------------------------------------------------------------- utils
function fmtSec(s) {
  if (s == null) return '—';
  s = Math.round(s); // handle float seconds from OSRM
  if (s < 60) return `${s} s`;
  const m = Math.floor(s / 60);
  const rem = s % 60;
  return rem ? `${m}m ${rem}s` : `${m} min`;
}
function pill(strategy) {
  const c = STRATEGY_COLOR[strategy] || '#888';
  return `<span style="background:${c};color:#fff;padding:1px 7px;border-radius:9px;font-size:11px;font-weight:600">${strategy}</span>`;
}

// --------------------------------------------------------------------- main export
export default function punePage(container) {
  let selectedTarget = 'all';

  // ---- layout skeleton
  container.innerHTML = `
<div id="pune-wrap" style="display:flex;flex-direction:column;height:calc(100vh - 56px);min-height:500px">
  <div id="pune-header" style="padding:10px 16px 8px;flex-shrink:0;border-bottom:1px solid var(--border)">
    <div style="display:flex;align-items:center;gap:12px;flex-wrap:wrap">
      <div>
        <h1 style="margin:0;font-size:18px;font-weight:700">Pune Real-Map Live Routing</h1>
        <p style="margin:2px 0 0;font-size:11px;color:var(--text-2)">
          Click any road segment to close or congest it — GraphPulse-R repairs routes and highlights new detours live.
        </p>
      </div>
      <div style="margin-left:auto;display:flex;gap:8px;align-items:center;flex-wrap:wrap">
        <label style="font-size:11px;display:flex;align-items:center;gap:5px;font-weight:600">
          🎯 Target:
          <select id="pune-target-select" class="btn" style="padding:4px 8px;font-size:11px;border-radius:5px">
            <option value="all">Full Tree (All 25 nodes)</option>
            <option value="9">To: Swargate Bus Stand (Node 9)</option>
            <option value="18">To: Hinjawadi Phase-3 IT Park (Node 18)</option>
            <option value="4">To: Nal Stop / Karve Road (Node 4)</option>
            <option value="6">To: Chandani Chowk (Node 6)</option>
            <option value="14">To: Koregaon Park (Node 14)</option>
            <option value="20">To: Pune Airport Gate (Node 20)</option>
            <option value="23">To: Hadapsar Depot (Node 23)</option>
          </select>
        </label>
        <button id="pune-scenario-repair-btn" class="btn" style="font-size:11px;padding:5px 11px;background:#2563eb;color:#fff;border:none;border-radius:5px;cursor:pointer;font-weight:600" title="Scenario 1: Localized blockage on Karve Road — GraphPulse-R automatically runs Local Repair (15 ops vs 115 recompute, 87 pct saved)">
          ⚡ Scenario: Local Repair Wins
        </button>
        <button id="pune-scenario-recompute-btn" class="btn" style="font-size:11px;padding:5px 11px;background:#dc2626;color:#fff;border:none;border-radius:5px;cursor:pointer;font-weight:600" title="Scenario 2: Dual-corridor cut (Station-Swargate & FC Road) — local repair blows past budget, GraphPulse-R automatically recomputes whole Dijkstra!">
          🌊 Scenario: Whole Dijkstra Wins
        </button>
        <button id="pune-reset-btn" class="btn" style="font-size:11px;padding:5px 12px">↺ Reset all roads</button>
      </div>
    </div>
    <div style="margin-top:6px;display:flex;align-items:center;gap:14px;font-size:11px;color:var(--text-2);flex-wrap:wrap">
      <span><span style="color:#3b82f6;font-size:13px">■</span> Shortest path road</span>
      <span><span style="color:#10b981;font-size:13px">■</span> <b style="color:#10b981">Detour road (newly adopted)</b></span>
      <span><span style="color:#ef4444;font-size:13px">■</span> Closed road (blocked)</span>
      <span><span style="color:#f97316;font-size:13px">■</span> Congested road</span>
      <span id="pune-active-route-bar" style="margin-left:auto;font-weight:600;color:var(--text-1)"></span>
    </div>
  </div>

  <div id="pune-body" style="flex:1;display:flex;gap:0;overflow:hidden">
    <!-- Leaflet map -->
    <div id="pune-map" style="flex:1;min-width:0;position:relative"></div>

    <!-- Sidebar panel -->
    <div id="pune-panel" style="width:320px;flex-shrink:0;overflow-y:auto;border-left:1px solid var(--border);display:flex;flex-direction:column">
      <div style="padding:12px 14px 8px;border-bottom:1px solid var(--border)">
        <div style="font-size:12px;font-weight:600;color:var(--text-2);text-transform:uppercase;letter-spacing:.05em">Last Decision &amp; Detours</div>
        <div id="pune-last-decision" style="margin-top:8px;font-size:13px;color:var(--text-2)">
          Click any road or click the Demo button to test road closure.
        </div>
      </div>

      <div style="padding:12px 14px 6px;border-bottom:1px solid var(--border)">
        <div style="font-size:12px;font-weight:600;color:var(--text-2);text-transform:uppercase;letter-spacing:.05em">Delivery Tour (Held-Karp)</div>
        <div id="pune-tour" style="margin-top:8px;font-size:12px;color:var(--text-2)">Loading…</div>
      </div>

      <div style="padding:10px 14px 6px;border-bottom:1px solid var(--border)">
        <div style="font-size:12px;font-weight:600;color:var(--text-2);text-transform:uppercase;letter-spacing:.05em">Cumulative Operations</div>
        <div id="pune-opcounts" style="margin-top:6px;font-size:12px;color:var(--text-2)">—</div>
      </div>

      <div style="padding:10px 14px;flex:1">
        <div style="font-size:12px;font-weight:600;color:var(--text-2);text-transform:uppercase;letter-spacing:.05em">Update Log</div>
        <div id="pune-log" style="margin-top:6px;font-size:11px;display:flex;flex-direction:column;gap:6px"></div>
      </div>
    </div>
  </div>
</div>`;

  // ---- load Leaflet dynamically (CDN – no npm needed)
  let map = null;
  let graphData = null;
  let edgeGroup = null;
  let nodeGroup = null;

  function ensureLeaflet(cb) {
    if (window.L) { cb(); return; }
    const link = document.createElement('link');
    link.rel = 'stylesheet';
    link.href = 'https://unpkg.com/leaflet@1.9.4/dist/leaflet.css';
    document.head.appendChild(link);
    const script = document.createElement('script');
    script.src = 'https://unpkg.com/leaflet@1.9.4/dist/leaflet.js';
    script.onload = cb;
    document.head.appendChild(script);
  }

  function initMap() {
    map = L.map('pune-map', { zoomControl: true }).setView(PUNE_CENTER, ZOOM);
    L.tileLayer(TILE_URL, { attribution: TILE_ATTR, maxZoom: 19 }).addTo(map);
    edgeGroup = L.layerGroup().addTo(map);
    nodeGroup = L.layerGroup().addTo(map);
  }

  function renderGraph(data) {
    graphData = data;
    if (!map || !edgeGroup || !nodeGroup) return;

    edgeGroup.clearLayers();
    nodeGroup.clearLayers();

    const nodeById = {};
    data.nodes.forEach(n => { nodeById[n.id] = n; });

    // Compute active target route if specific destination is selected
    const activePathEdges = new Set();
    const pathNodes = [];
    if (selectedTarget !== 'all') {
      let curr = parseInt(selectedTarget, 10);
      const visited = new Set();
      while (curr != null && curr !== data.src && !visited.has(curr)) {
        visited.add(curr);
        const node = nodeById[curr];
        if (node && node.parent != null) {
          activePathEdges.add(`${node.parent}-${curr}`);
          pathNodes.unshift(node);
          curr = node.parent;
        } else {
          break;
        }
      }
      if (curr === data.src) {
        const srcNode = nodeById[data.src];
        if (srcNode) pathNodes.unshift(srcNode);
      }
    }

    // Check if any detour edges affect the selected target's route
    const hasDetourOnSelectedRoute = selectedTarget !== 'all' &&
      data.edges.some(e => e.is_detour && activePathEdges.has(`${e.u}-${e.v}`));
    // Also check if any detour exists globally
    const hasAnyDetour = data.edges.some(e => e.is_detour);

    // Update active route bar
    const routeBar = document.getElementById('pune-active-route-bar');
    if (routeBar) {
      if (selectedTarget === 'all') {
        if (hasAnyDetour) {
          routeBar.innerHTML = `<span style="color:#10b981;font-weight:700">🛣️ Detour roads highlighted in emerald green — new alternative paths adopted by GraphPulse-R</span>`;
        } else {
          routeBar.textContent = 'Showing all shortest paths from ⭐ Pune Railway Station';
        }
      } else {
        const destNode = nodeById[parseInt(selectedTarget, 10)];
        const destName = destNode ? destNode.name : `Node ${selectedTarget}`;
        if (pathNodes.length > 1) {
          const names = pathNodes.map(n => n.name).join(' → ');
          const totalDist = destNode.dist != null ? fmtSec(destNode.dist) : '—';
          const detourBadge = hasDetourOnSelectedRoute
            ? ` <span style="background:#10b981;color:#fff;padding:1px 6px;border-radius:8px;font-size:10px">🛣️ REROUTED</span>`
            : '';
          routeBar.innerHTML = `📍 Route to <b>${destName}</b>: <span style="color:#2563eb">${names}</span> (⏱ <b>${totalDist}</b>)${detourBadge}`;
        } else {
          routeBar.innerHTML = `<span style="color:#ef4444">⚠️ ${destName} is currently UNREACHABLE — road closure disconnected graph</span>`;
        }
      }
    }

    // Draw edges
    data.edges.forEach(edge => {
      const u = nodeById[edge.u], v = nodeById[edge.v];
      if (!u || !v) return;

      const key = `${edge.u}-${edge.v}`;
      const isTargetRoute = activePathEdges.has(key);
      const isDetour = edge.is_detour;

      let color = '#6b7280';  // default: non-tree road
      let weight = 3;
      // Detour edges are ALWAYS full opacity so they're clearly visible
      // Detour and active-route edges always at full opacity; everything else fades
      let opacity = selectedTarget === 'all' ? 0.6 : (isDetour || isTargetRoute ? 1.0 : 0.3);
      let dashArray = null;

      if (edge.is_deleted) {
        color = '#ef4444';
        weight = 3.5;
        opacity = 0.95;
        dashArray = '6,5';
      } else if (isDetour) {
        // High-contrast vibrant emerald green for newly adopted detour roads!
        color = '#10b981';
        weight = isTargetRoute ? 7 : 5.5;
        opacity = 1.0;
      } else if (isTargetRoute) {
        color = '#2563eb';
        weight = 6;
        opacity = 1.0;
      } else if (edge.is_tree) {
        color = '#3b82f6';
        weight = 4;
        opacity = selectedTarget === 'all' ? 0.92 : 0.6;
      } else if (edge.is_last_updated) {
        color = '#f97316';
        weight = 5;
        opacity = 1.0;
      }

      // Real curved road geometry or fallback to straight line
      const latlngs = (edge.geometry && edge.geometry.length > 1)
        ? edge.geometry
        : [
            [u.lat, u.lng],
            [v.lat, v.lng],
          ];

      const pl = L.polyline(latlngs, {
        color, weight, opacity,
        dashArray,
        lineJoin: 'round',
        interactive: false,
        className: isDetour ? 'pune-detour-line' : '',
      }).addTo(edgeGroup);

      const roadName = edge.label || `${u.name || ('Node ' + edge.u)} → ${v.name || ('Node ' + edge.v)}`;
      const currentW = edge.w;
      const deleted = edge.is_deleted;
      const distStr = edge.distance_m ? (edge.distance_m >= 1000 ? (edge.distance_m / 1000).toFixed(1) + ' km' : Math.round(edge.distance_m) + ' m') : '';

      // Wide invisible hit target for easy clicking and hover
      const hit = L.polyline(latlngs, {
        weight: 18,
        opacity: 0,
        lineJoin: 'round',
        interactive: !deleted,
      }).addTo(edgeGroup);

      hit.on('click', (e) => {
        if (deleted) return;
        const clickPos = e.latlng || [u.lat, u.lng];
        showEdgePopup(edge.u, edge.v, roadName, currentW, clickPos, distStr);
      });

      hit.on('mouseover', () => {
        pl.setStyle({ weight: weight + 2.5, opacity: 1.0 });
      });
      hit.on('mouseout', () => {
        pl.setStyle({ weight, opacity });
      });

      let roleText = '⏱ ' + fmtSec(edge.w);
      if (deleted) roleText = '⛔ Closed Road';
      else if (edge.is_detour) roleText = '🛣️ <b>NEW DETOUR ROAD (Adopted)</b> · ⏱ ' + fmtSec(edge.w);
      else if (isTargetRoute) roleText = '🎯 Target Active Route · ⏱ ' + fmtSec(edge.w);
      else if (edge.is_tree) roleText = '🔷 Active Shortest-Path Road · ⏱ ' + fmtSec(edge.w);

      hit.bindTooltip(
        `<b>${roadName}</b>${distStr ? ` (${distStr})` : ''}<br>${roleText}`,
        { sticky: true, className: 'pune-tip' }
      );
    });

    // Draw nodes
    data.nodes.forEach(node => {
      let fillColor = '#94a3b8';
      let radius = 5;
      let zIndex = 10;

      if (node.is_source) {
        fillColor = '#6366f1';
        radius = 10;
        zIndex = 100;
      } else if (String(node.id) === String(selectedTarget)) {
        fillColor = '#ef4444';
        radius = 9;
        zIndex = 95;
      } else if (data.tour && data.tour.stops && data.tour.stops.includes(node.id)) {
        fillColor = '#10b981';
        radius = 8;
        zIndex = 80;
      } else if (node.is_affected) {
        fillColor = '#f59e0b';
        radius = 7;
        zIndex = 60;
      } else if (!node.reachable) {
        fillColor = '#ef4444';
        radius = 5;
      }

      const m = L.circleMarker([node.lat, node.lng], {
        radius,
        fillColor,
        color: '#fff',
        weight: 2,
        fillOpacity: 0.95,
        zIndexOffset: zIndex,
      }).addTo(nodeGroup);

      m.on('click', () => {
        if (!node.is_source) {
          selectedTarget = String(node.id);
          const sel = document.getElementById('pune-target-select');
          if (sel) sel.value = selectedTarget;
          renderGraph(graphData);
        }
      });

      const distStr = node.dist != null ? fmtSec(node.dist) : 'unreachable';
      m.bindTooltip(
        `<b>${node.name}</b><br>dist from depot: ${distStr}${node.is_source ? '<br>⭐ Depot' : '<br><span style="color:#2563eb">Click to trace route</span>'}`,
        { className: 'pune-tip' }
      );
    });

    // Update panels
    renderOpcounts(data);
    renderTour(data.tour);
    renderLog(data.logs || []);
    if (data.last_update) renderLastDecision(data.last_update);
  }

  function showEdgePopup(u, v, roadName, currentW, latlng, distStr = '') {
    const incW5  = currentW + 300;   // +5 min
    const incW10 = currentW + 600;   // +10 min
    const content = `
      <div style="min-width:230px;font-family:inherit">
        <div style="font-weight:700;font-size:13px;margin-bottom:4px">${roadName || `Road ${u}→${v}`}</div>
        ${distStr ? `<div style="font-size:11px;color:#6b7280;margin-bottom:3px">🛣 Real road length: <b style="color:var(--text-1,#111)">${distStr}</b></div>` : ''}
        <div style="font-size:11px;color:#6b7280;margin-bottom:8px">Current travel time: <b style="color:var(--text-1,#111)">${fmtSec(currentW)}</b></div>
        <div style="display:flex;flex-direction:column;gap:5px">
          <button class="btn pune-action" data-kind="delete" data-u="${u}" data-v="${v}" data-w="0"
            style="background:#ef4444;border:none;color:#fff;padding:6px 8px;border-radius:6px;cursor:pointer;font-size:12px;font-weight:600">
            ⛔ Close road (delete edge)
          </button>
          <button class="btn pune-action" data-kind="increase" data-u="${u}" data-v="${v}" data-w="${incW5}"
            style="background:#f59e0b;border:none;color:#fff;padding:6px 8px;border-radius:6px;cursor:pointer;font-size:12px;font-weight:600">
            🐌 Add 5 min congestion → ${fmtSec(incW5)}
          </button>
          <button class="btn pune-action" data-kind="increase" data-u="${u}" data-v="${v}" data-w="${incW10}"
            style="background:#f97316;border:none;color:#fff;padding:6px 8px;border-radius:6px;cursor:pointer;font-size:12px;font-weight:600">
            🚗 Add 10 min jam → ${fmtSec(incW10)}
          </button>
        </div>
      </div>`;

    L.popup({ maxWidth: 290 })
      .setLatLng(latlng)
      .setContent(content)
      .openOn(map);
  }

  function renderLastDecision(upd) {
    const el = document.getElementById('pune-last-decision');
    if (!el) return;
    const isFallback = upd.strategy === 'fallback';
    const isRepair = upd.strategy === 'repair';
    const savings = upd.baseline_work - upd.work;
    const pct = upd.baseline_work > 0 ? Math.round((savings / upd.baseline_work) * 100) : 0;
    const hasDetour = upd.detour_edges && upd.detour_edges.length > 0;
    const kindIcon = upd.kind === 'delete' ? '⛔ Closed' : '🐌 Congested';

    let scenarioBanner = '';
    if (upd.scenario_title) {
      scenarioBanner = `
        <div style="margin-bottom:8px;padding:8px 10px;background:var(--ground);border:1px solid var(--border);border-left:4px solid ${isFallback ? '#ef4444' : '#2563eb'};border-radius:5px">
          <div style="font-weight:700;font-size:12px;color:var(--text-1)">${upd.scenario_title}</div>
          <div style="font-size:11px;color:var(--text-2);margin-top:2px;line-height:1.4">${upd.scenario_desc}</div>
        </div>`;
    }

    let comparisonInsight = '';
    if (isFallback) {
      comparisonInsight = `
        <div style="margin-top:6px;padding:7px 10px;background:rgba(239,68,68,0.12);border-radius:4px;font-size:11px;line-height:1.4">
          <b style="color:#ef4444">🔄 Why Recomputing Dijkstra Won:</b><br>
          Local repair on tangled subtrees blew past the competitive budget (<b>B = ${upd.budget || 170} ops</b>).
          GraphPulse-R <b>automatically aborted</b> local repair and recomputed the entire shortest path tree using Dijkstra from scratch (<b>${upd.fallback_work || 170} ops</b> across all 25 nodes)!
        </div>`;
    } else if (isRepair) {
      comparisonInsight = `
        <div style="margin-top:6px;padding:7px 10px;background:rgba(37,99,235,0.1);border-radius:4px;font-size:11px;line-height:1.4">
          <b style="color:#2563eb">⚡ Why Local Repair Won:</b><br>
          Disruption is localized to a small branch (<b>|A| = ${upd.affected_size || 1} &ll; 25</b> intersections).
          GraphPulse-R confined the Dijkstra search strictly to affected nodes, completing in only <b>${upd.work} ops</b> vs <b>${upd.baseline_work} ops</b> for full rebuild (${pct > 0 ? `<b style="color:#22c55e">-${pct}% saved</b>` : ''})!
        </div>`;
    }

    let detourSection = '';
    if (hasDetour) {
      detourSection = `
        <div style="margin-top:8px;padding:8px 10px;background:rgba(16,185,129,0.12);border-left:3px solid #10b981;border-radius:4px">
          <div style="font-size:11px;font-weight:700;color:#10b981">🛣️ Rerouted via ${upd.detour_edges.length} New Road${upd.detour_edges.length > 1 ? 's' : ''}:</div>
          <div style="font-size:11px;margin-top:4px;display:flex;flex-direction:column;gap:3px">
            ${upd.detour_edges.map(e => `<span>→ <b>${e.label}</b></span>`).join('')}
          </div>
          <div style="font-size:10px;color:var(--text-2);margin-top:4px">Highlighted in <b style="color:#10b981">emerald green</b> on the map.</div>
        </div>`;
    } else if (upd.was_tree_edge === true) {
      detourSection = `
        <div style="margin-top:8px;padding:6px 10px;background:rgba(239,68,68,0.1);border-left:3px solid #ef4444;border-radius:4px;font-size:11px">
          ⚠️ Road was on the shortest path tree — affected destinations are now <b>unreachable</b> (graph disconnected).
        </div>`;
    } else if (upd.was_tree_edge === false) {
      detourSection = `
        <div style="margin-top:8px;padding:6px 10px;background:rgba(100,116,139,0.1);border-radius:4px;font-size:11px;color:var(--text-2)">
          ℹ️ Closed road was <b>not on the active shortest path tree</b>. All routes remain optimal — Certificate hit (1 SCAN).
        </div>`;
    }

    el.innerHTML = `
      ${scenarioBanner}
      <div style="margin-bottom:4px">${pill(upd.strategy)} ${kindIcon}: <b>${upd.road_label || `${upd.u}→${upd.v}`}</b></div>
      <div style="color:var(--text-2);font-size:11px;margin-bottom:4px">${STRATEGY_DESC[upd.strategy] || ''}</div>
      <div style="font-size:11px">Operations: <b>${upd.work}</b> vs baseline <b>${upd.baseline_work}</b>
        ${pct > 0 && !isFallback ? `<span style="color:#22c55e">(-${pct}% saved)</span>` : ''}
      </div>
      ${upd.affected_size ? `<div style="font-size:11px;color:var(--text-2)">Affected intersections: ${upd.affected_size} of 25</div>` : ''}
      ${comparisonInsight}
      ${upd.route_action ? `<div style="font-size:11px;margin-top:3px">Tour: <b>${upd.route_action}</b> | Held-Karp transitions: ${upd.hk_transitions ?? '—'}</div>` : ''}
      ${detourSection}
    `;
  }

  function renderTour(tour) {
    const el = document.getElementById('pune-tour');
    if (!el || !tour) return;
    if (!tour.terminals_set) { el.textContent = 'No terminals set.'; return; }
    const stops = (tour.stops || []).map(id => {
      const nd = graphData && graphData.nodes.find(n => n.id === id);
      return nd ? nd.name : `Node ${id}`;
    });
    const depotName = (() => {
      const nd = graphData && graphData.nodes.find(n => n.id === tour.depot);
      return nd ? nd.name : `Node ${tour.depot}`;
    })();
    el.innerHTML = `
      <div style="font-size:11px;margin-bottom:4px">Depot: <b>${depotName}</b></div>
      <div style="font-size:11px;margin-bottom:4px">Stops: ${stops.join(', ')}</div>
      ${tour.tour_cost != null
        ? `<div style="font-size:13px;font-weight:700">${fmtSec(tour.tour_cost)} <span style="font-weight:400;font-size:11px;color:var(--text-2)">optimal tour</span></div>`
        : '<div style="font-size:11px;color:#ef4444">Tour infeasible (disconnected network)</div>'
      }
    `;
  }

  function renderOpcounts(data) {
    const el = document.getElementById('pune-opcounts');
    if (!el) return;
    const on = data.cumulative_online || 0;
    const rb = data.cumulative_rebuild || 0;
    const pct = rb > 0 ? Math.round((1 - on / rb) * 100) : 0;
    el.innerHTML = `
      <div style="display:grid;grid-template-columns:1fr 1fr;gap:4px 12px">
        <div>GraphPulse-R</div><div style="font-weight:700">${on.toLocaleString()}</div>
        <div>Recompute baseline</div><div style="font-weight:700">${rb.toLocaleString()}</div>
        ${rb > 0 ? `<div>Saved</div><div style="font-weight:700;color:#22c55e">${pct}%</div>` : ''}
      </div>
    `;
  }

  function renderLog(logs) {
    const el = document.getElementById('pune-log');
    if (!el) return;
    if (!logs.length) {
      el.innerHTML = '<span style="color:var(--text-2)">No updates yet.</span>';
      return;
    }
    el.innerHTML = logs.slice(0, 15).map(l => `
      <div style="padding:6px 8px;border-radius:6px;background:var(--ground);border:1px solid var(--border)">
        <div style="display:flex;align-items:center;gap:6px">
          ${pill(l.strategy)}
          <span style="font-size:10px;color:var(--text-2)">${l.time}</span>
          ${l.detour_edges && l.detour_edges.length > 0 ? `<span style="font-size:10px;background:#10b981;color:#fff;padding:1px 5px;border-radius:6px;margin-left:auto">+${l.detour_edges.length} detour</span>` : ''}
        </div>
        <div style="margin-top:3px;font-size:11px"><b>${l.road_label || `${l.u}→${l.v}`}</b></div>
        <div style="font-size:10px;color:var(--text-2)">${l.kind === 'delete' ? (l.mode === 'recompute' ? '🔄 Whole Dijkstra Recompute' : '⛔ Local Repair') : `🐌 ${fmtSec(l.old_w)} → ${fmtSec(l.new_w)}`} | ${l.work} ops</div>
      </div>`).join('');
  }

  async function fetchAndRender() {
    try {
      const res = await fetch('/api/pune/graph');
      if (!res.ok) throw new Error(`HTTP ${res.status}`);
      const data = await res.json();
      renderGraph(data);
    } catch (e) {
      console.error('Pune API error:', e);
    }
  }

  async function sendUpdate(kind, u, v, new_w) {
    const body = kind === 'delete'
      ? { kind, u, v }
      : { kind, u, v, new_w };
    const res = await fetch('/api/pune/update', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(body),
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(err.error || `HTTP ${res.status}`);
    }
    const data = await res.json();
    if (data.graph) renderGraph(data.graph);
    if (data.update) renderLastDecision(data.update);
  }

  async function runScenario(scenario) {
    const res = await fetch('/api/pune/scenario', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ scenario }),
    });
    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      throw new Error(err.error || `HTTP ${res.status}`);
    }
    const data = await res.json();
    if (data.graph) renderGraph(data.graph);
    if (data.update) renderLastDecision(data.update);
  }

  async function doReset() {
    const btn = document.getElementById('pune-reset-btn');
    if (btn) { btn.disabled = true; btn.textContent = 'Resetting…'; }
    try {
      const res = await fetch('/api/pune/reset', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: '{}' });
      const data = await res.json();
      if (data.graph) renderGraph(data.graph);
      document.getElementById('pune-last-decision').textContent = 'All roads restored. Click a road or select a scenario above.';
    } finally {
      if (btn) { btn.disabled = false; btn.textContent = '↺ Reset all roads'; }
    }
  }

  // ----- delegate popup button clicks through document (popup lives outside app root)
  function onDocClick(e) {
    const btn = e.target.closest('.pune-action');
    if (!btn || btn.disabled) return;
    const kind = btn.dataset.kind;
    const u = parseInt(btn.dataset.u, 10);
    const v = parseInt(btn.dataset.v, 10);
    const w = parseInt(btn.dataset.w, 10);
    if (map) map.closePopup();
    // Disable ALL popup buttons to prevent double-fire
    document.querySelectorAll('.pune-action').forEach(b => { b.disabled = true; });
    const origText = btn.textContent.trim();
    btn.textContent = '⏳ Updating…';
    sendUpdate(kind, u, v, w)
      .catch(err => alert(`Update failed: ${err.message}`))
      .finally(() => {
        document.querySelectorAll('.pune-action').forEach(b => { b.disabled = false; });
        btn.textContent = origText;
      });
  }

  // ----- boot sequence
  ensureLeaflet(() => {
    initMap();
    fetchAndRender();
  });

  document.addEventListener('click', onDocClick);
  document.getElementById('pune-reset-btn')?.addEventListener('click', doReset);
  const scenarioRepairBtn = document.getElementById('pune-scenario-repair-btn');
  if (scenarioRepairBtn) {
    scenarioRepairBtn.addEventListener('click', () => {
      if (scenarioRepairBtn.disabled) return;
      scenarioRepairBtn.disabled = true;
      scenarioRepairBtn.textContent = '⏳ Simulating…';
      runScenario('local_repair')
        .catch(err => alert(err.message))
        .finally(() => {
          scenarioRepairBtn.disabled = false;
          scenarioRepairBtn.textContent = '⚡ Scenario: Local Repair Wins';
        });
    });
  }

  const scenarioRecomputeBtn = document.getElementById('pune-scenario-recompute-btn');
  if (scenarioRecomputeBtn) {
    scenarioRecomputeBtn.addEventListener('click', () => {
      if (scenarioRecomputeBtn.disabled) return;
      scenarioRecomputeBtn.disabled = true;
      scenarioRecomputeBtn.textContent = '⏳ Simulating…';
      runScenario('recompute_wins')
        .catch(err => alert(err.message))
        .finally(() => {
          scenarioRecomputeBtn.disabled = false;
          scenarioRecomputeBtn.textContent = '🌊 Scenario: Whole Dijkstra Wins';
        });
    });
  }

  document.getElementById('pune-target-select')?.addEventListener('change', (e) => {
    selectedTarget = e.target.value;
    if (graphData) renderGraph(graphData);
  });

  // cleanup
  return () => {
    document.removeEventListener('click', onDocClick);
    if (map) { map.remove(); map = null; }
    style.remove();
  };
}
