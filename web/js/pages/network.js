// Network: the working screen. Pick a road, apply a closure or slowdown, read the decision.
import { Api } from '../api.js';
import { Store } from '../store.js';
import { Settings } from '../theme.js';
import { GraphView } from '../graph_view.js';
import { icon } from '../icons.js';
import { esc, fmt, DASH, strategyPill, strategyText, toast, withBusy, confirmDialog, errorNotice } from '../ui.js';

const PRESETS = {
  grid: { label: 'Grid', params: [['rows', 'Rows', 6, 2, 30], ['cols', 'Columns', 6, 2, 30]] },
  comb: { label: 'Comb (worst case for repair)', params: [['n', 'Vertices', 30, 4, 400]] },
  hub_spoke: { label: 'Hub and spoke', params: [['hubs', 'Hubs', 4, 1, 12], ['spokes', 'Spokes per hub', 5, 1, 30]] },
  random_sparse: { label: 'Random sparse', params: [['n', 'Vertices', 25, 5, 400], ['m', 'Roads', 60, 5, 2000]] },
};

export default function network(view, ctx) {
  view.innerHTML = `
    <header class="page-head"><div><h1 class="page-title">Network</h1><p class="page-sub" id="net-sub">Close or slow a road and see which decision the engine takes.</p></div>
      <div class="page-actions"><button class="btn" type="button" id="net-sim" data-busy="Simulating">${icon('dice')}Simulate 10 updates</button>
      <button class="btn" type="button" id="net-reset">${icon('refresh')}Reset workspace</button></div></header>
    <div id="net-error"></div>
    <div class="split-network">
      <div class="panel graph-card">
        <div class="graph-toolbar">
          <div class="row-wrap">
            <button class="btn btn-sm" type="button" id="tg-weights" aria-pressed="true">Road weights</button>
            <button class="btn btn-sm" type="button" id="tg-tree" aria-pressed="false">Tree only</button>
          </div>
          <div class="row-wrap">
            <button class="btn btn-ghost btn-icon btn-sm" type="button" id="z-in" aria-label="Zoom in">${icon('zoomin')}</button>
            <button class="btn btn-ghost btn-icon btn-sm" type="button" id="z-out" aria-label="Zoom out">${icon('zoomout')}</button>
            <button class="btn btn-ghost btn-icon btn-sm" type="button" id="z-fit" aria-label="Fit to view">${icon('fit')}</button>
          </div>
        </div>
        <div class="graph-stage"><canvas id="net-canvas" aria-label="Road network. Click a road to select it, a vertex to set the target."></canvas><div class="stage-msg" id="net-msg" hidden></div></div>
        <div class="graph-legend">
          <span class="legend-item"><span class="swatch" style="background:var(--cv-source)"></span>Source</span>
          <span class="legend-item"><span class="swatch" style="background:var(--cv-target)"></span>Target</span>
          <span class="legend-item"><span class="swatch-line" style="background:var(--cv-path)"></span>Shortest path</span>
          <span class="legend-item"><span class="swatch-line" style="background:var(--cv-edge-tree)"></span>Shortest-path tree</span>
          <span class="legend-item"><span class="swatch" style="background:var(--cv-affected)"></span>Affected by the last update</span>
          <span class="legend-item">Drag to pan, Ctrl and scroll to zoom</span>
        </div>
      </div>
      <div class="stack">
        <form class="panel panel-pad stack" id="upd-form" novalidate>
          <h2 class="panel-title">Apply update</h2>
          <div class="segmented" role="group" aria-label="Update type"><button type="button" data-kind="delete" aria-pressed="true">Close road</button><button type="button" data-kind="increase" aria-pressed="false">Slow road</button></div>
          <div class="input-row">
            <div class="field"><label for="u-from">From vertex</label><input class="input num" id="u-from" inputmode="numeric" autocomplete="off"></div>
            <div class="field"><label for="u-to">To vertex</label><input class="input num" id="u-to" inputmode="numeric" autocomplete="off"></div>
          </div>
          <div class="field" id="w-field" hidden><label for="u-w">New weight</label><input class="input num" id="u-w" inputmode="numeric" autocomplete="off"><span class="hint" id="w-hint">Must be greater than the current weight.</span></div>
          <p class="error-text" id="upd-err" role="alert" hidden></p>
          <button class="btn btn-primary" type="submit" data-busy="Applying">Apply update</button>
          <p class="hint muted small">Tip: click a road on the map to fill in its ends.</p>
        </form>
        <div class="panel" id="decision"></div>
        <div class="panel panel-pad stack" id="path-panel"></div>
      </div>
    </div>
    <form class="panel panel-pad section" id="graph-form" style="margin-top:var(--gap)"><div class="graph-form-row">
      <div><h2 class="panel-title">Graph</h2><p class="panel-sub">Load a different road network. This restarts the engines.</p></div>
      <div class="field"><label for="g-preset">Preset</label><div class="select-wrap"><select class="select" id="g-preset">${Object.entries(PRESETS).map(([k, v]) => `<option value="${k}">${esc(v.label)}</option>`).join('')}</select></div></div>
      <div class="input-row" id="g-params"></div>
      <button class="btn" type="submit" data-busy="Loading" style="align-self:end">Load graph</button></div>
      <p class="error-text" id="g-err" role="alert" hidden></p></form>`;

  const q = (s) => view.querySelector(s);
  let kind = 'delete';
  let gv = null;
  let lastGraphKey = '';

  gv = new GraphView(q('#net-canvas'), {
    onNode: async (n) => { try { await Api.setTarget(n.id); await Store.refresh(); } catch (e) { toast(e.message, 'error'); } },
    onEdge: (e) => { q('#u-from').value = e.u; q('#u-to').value = e.v; q('#u-w').value = e.w + 1; q('#w-hint').textContent = `Current weight is ${e.w}. The new weight must be greater.`; q('#upd-err').hidden = true; q('#u-w').focus(); },
  });
  const s = Settings.get();
  gv.setOptions({ showWeights: s.showWeights, showTree: s.showTree });
  q('#tg-weights').setAttribute('aria-pressed', String(s.showWeights));
  q('#tg-tree').setAttribute('aria-pressed', String(s.showTree));

  // ---- toolbar ------------------------------------------------------------------------------
  const toggle = (id, key, apply) => q(id).addEventListener('click', (ev) => {
    const on = ev.currentTarget.getAttribute('aria-pressed') !== 'true';
    ev.currentTarget.setAttribute('aria-pressed', String(on)); apply(on);
  });
  toggle('#tg-weights', 'showWeights', (on) => gv.setOptions({ showWeights: on }));
  toggle('#tg-tree', 'showTree', (on) => gv.setOptions({ showTree: on }));
  q('#z-in').addEventListener('click', () => gv.zoomBy(1.25));
  q('#z-out').addEventListener('click', () => gv.zoomBy(0.8));
  q('#z-fit').addEventListener('click', () => gv.fit());

  // ---- update form ----------------------------------------------------------------------------
  view.querySelectorAll('[data-kind]').forEach((b) => b.addEventListener('click', () => {
    kind = b.dataset.kind;
    view.querySelectorAll('[data-kind]').forEach((x) => x.setAttribute('aria-pressed', String(x === b)));
    q('#w-field').hidden = kind !== 'increase';
  }));
  const showErr = (el, msg) => { el.textContent = msg; el.hidden = !msg; };
  q('#upd-form').addEventListener('submit', async (ev) => {
    ev.preventDefault();
    const u = Number(q('#u-from').value), v = Number(q('#u-to').value), w = Number(q('#u-w').value);
    const isInt = (x, raw) => raw.trim() !== '' && Number.isInteger(x);
    if (!isInt(u, q('#u-from').value) || !isInt(v, q('#u-to').value)) return showErr(q('#upd-err'), 'Enter both road ends as whole numbers.');
    if (kind === 'increase' && (!isInt(w, q('#u-w').value) || w <= 0)) return showErr(q('#upd-err'), 'Enter a positive whole number for the new weight.');
    showErr(q('#upd-err'), '');
    await withBusy(ev.submitter || q('#upd-form button[type=submit]'), async () => {
      try { await Api.update(kind, u, v, w); await Store.refresh(); toast(kind === 'delete' ? `Closed road ${u} to ${v}` : `Slowed road ${u} to ${v}`); }
      catch (e) { showErr(q('#upd-err'), e.message); }
    });
  });

  // ---- simulate, reset ------------------------------------------------------------------------
  q('#net-sim').addEventListener('click', async (ev) => {
    await withBusy(ev.currentTarget, async () => {
      try {
        for (let i = 0; i < 10; i++) {
          const g = Store.state.graph;
          if (!g || !g.edges.length) break;
          const e = g.edges[Math.floor(Math.random() * g.edges.length)];
          const del = Math.random() < 0.15;
          await Api.update(del ? 'delete' : 'increase', e.u, e.v, e.w + 1 + Math.floor(Math.random() * 9));
          await Store.refresh();
        }
        toast('Simulated 10 random updates');
      } catch (e) { toast(e.message, 'error'); }
    });
  });
  q('#net-reset').addEventListener('click', async () => {
    const ok = await confirmDialog({ title: 'Reset workspace?', body: 'This restores the initial graph and clears the activity log and routing counters.', confirm: 'Reset', danger: true });
    if (!ok) return;
    try { await Api.reset(); await Store.refresh(); toast('Workspace reset'); } catch (e) { toast(e.message, 'error'); }
  });

  // ---- graph form -------------------------------------------------------------------------------
  const paramsEl = q('#g-params');
  const drawParams = () => {
    const p = PRESETS[q('#g-preset').value];
    paramsEl.innerHTML = p.params.map(([k, label, def, min, max]) => `<div class="field"><label for="gp-${k}">${esc(label)}</label><input class="input num" id="gp-${k}" data-key="${k}" type="number" min="${min}" max="${max}" value="${def}"></div>`).join('');
  };
  q('#g-preset').addEventListener('change', drawParams);
  drawParams();
  q('#graph-form').addEventListener('submit', async (ev) => {
    ev.preventDefault();
    const params = {};
    paramsEl.querySelectorAll('input').forEach((i) => { params[i.dataset.key] = Number(i.value); });
    await withBusy(q('#graph-form button[type=submit]'), async () => {
      try { await Api.loadGraph(q('#g-preset').value, params); showErr(q('#g-err'), ''); lastGraphKey = ''; await Store.refresh(); toast('Graph loaded'); }
      catch (e) { showErr(q('#g-err'), e.message); }
    });
  });

  // ---- render from the store ----------------------------------------------------------------------
  const update = () => {
    const st = Store.state; const g = st.graph;
    q('#net-error').innerHTML = st.error && !st.online ? errorNotice(st.error) : '';
    q('#net-error [data-retry]')?.addEventListener('click', () => Store.refresh());
    const msg = q('#net-msg');
    if (!g) { msg.hidden = false; msg.textContent = st.error ? 'The engine is not reachable.' : 'Loading the graph…'; return; }
    msg.hidden = true;
    q('#net-sub').textContent = `${g.n} vertices and ${g.m} roads. Source ${g.src}${g.target !== null ? `, target ${g.target}` : ''}.`;
    const key = `${g.preset}:${g.n}`;
    gv.setData(g, { fit: key !== lastGraphKey }); lastGraphKey = key;
    // decision
    const lu = g.last_update;
    q('#decision').innerHTML = lu ? `<div class="decision">${icon('check')}<div><strong>${strategyPill(lu.strategy)} <span class="small muted">${esc(lu.kind === 'delete' ? `Closed ${lu.u} to ${lu.v}` : `Slowed ${lu.u} to ${lu.v}`)}</span></strong>
        <p>${esc(strategyText(lu.strategy))}</p>
        <p class="small" style="margin-top:6px">${fmt(lu.work)} operations; recomputing would have used ${fmt(lu.baseline_work)}. ${lu.affected_size ? `${fmt(lu.affected_size)} vertices changed distance.` : 'No distances changed.'}</p></div></div>`
      : `<div class="decision">${icon('info')}<div><strong>No decision yet</strong><p>Apply an update to see which of the four decisions the engine takes, and what it cost.</p></div></div>`;
    // path
    const path = g.path || [];
    q('#path-panel').innerHTML = `<h2 class="panel-title">Shortest path</h2>
      <dl class="facts"><dt>Source</dt><dd>${g.src}</dd><dt>Target</dt><dd>${g.target === null ? DASH : g.target}</dd><dt>Distance</dt><dd>${g.path_dist === null ? DASH : fmt(g.path_dist)}</dd></dl>
      ${path.length ? `<div class="path-line">${path.map((v, i) => `${i ? `<span class="sep">${icon('chevron')}</span>` : ''}<span class="chip">${v}</span>`).join('')}</div>` : `<p class="muted small">${g.target === null ? 'Click a vertex to set the target.' : 'The target is unreachable.'}</p>`}`;
    if (g.preset && PRESETS[g.preset] && q('#g-preset').value !== g.preset && !q('#g-preset').matches(':focus')) { q('#g-preset').value = g.preset; drawParams(); }
  };
  const unsub = Store.subscribe(update);
  update();
  Store.refresh();
  return () => { unsub(); gv.destroy(); };
}
