// Routing: depot and stops, the exact tour, and the lazy certificate's decisions.
import { Api } from '../api.js';
import { Store } from '../store.js';
import { Settings } from '../theme.js';
import { GraphView } from '../graph_view.js';
import { icon } from '../icons.js';
import { esc, fmt, fmtCost, DASH, routePill, routeText, toast, withBusy, errorNotice } from '../ui.js';

export default function routing(view, ctx) {
  view.innerHTML = `
    <header class="page-head"><div><h1 class="page-title">Routing</h1><p class="page-sub" id="rt-sub">Keep an exact delivery tour correct as roads change.</p></div></header>
    <div id="rt-error"></div>
    <div class="split-network">
      <div class="stack">
        <div class="panel graph-card"><div class="graph-toolbar"><span class="muted small">Click vertices to build the stop list: the first click sets the depot.</span>
          <div class="row-wrap"><button class="btn btn-ghost btn-icon btn-sm" type="button" id="rz-in" aria-label="Zoom in">${icon('zoomin')}</button><button class="btn btn-ghost btn-icon btn-sm" type="button" id="rz-out" aria-label="Zoom out">${icon('zoomout')}</button><button class="btn btn-ghost btn-icon btn-sm" type="button" id="rz-fit" aria-label="Fit to view">${icon('fit')}</button></div></div>
          <div class="graph-stage graph-stage-small"><canvas id="rt-canvas" aria-label="Road network with the delivery tour drawn between depot and stops"></canvas></div></div>
        <div id="rt-results" class="stack"></div>
      </div>
      <div class="stack">
        <form class="panel panel-pad stack" id="term-form" novalidate>
          <h2 class="panel-title">Depot and stops</h2>
          <div class="field"><label for="t-depot">Depot vertex</label><input class="input num" id="t-depot" inputmode="numeric" autocomplete="off"></div>
          <div class="field"><label for="t-stops">Stops</label><input class="input num" id="t-stops" placeholder="for example 5, 12, 20" autocomplete="off"><span class="hint">Vertex numbers separated by commas. At most eighteen stops; they must differ from each other and from the depot.</span></div>
          <div class="row-wrap"><div class="field" style="width:96px"><label for="t-k">Random stops</label><input class="input num" id="t-k" type="number" min="1" max="18" value="4"></div>
            <button class="btn" type="button" id="t-random" style="align-self:end">${icon('dice')}Pick random</button></div>
          <p class="error-text" id="t-err" role="alert" hidden></p>
          <button class="btn btn-primary" type="submit" data-busy="Setting up">Set stops</button>
        </form>
        <div id="rt-cert" class="panel panel-pad stack"></div>
      </div>
    </div>`;

  const q = (s) => view.querySelector(s);
  const gv = new GraphView(q('#rt-canvas'), {
    onNode: (n) => {
      const depot = q('#t-depot'), stops = q('#t-stops');
      const list = parse(stops.value);
      if (depot.value.trim() === '') { depot.value = n.id; return; }
      if (String(n.id) === depot.value.trim()) { depot.value = ''; return; }
      const i = list.indexOf(n.id);
      if (i >= 0) list.splice(i, 1); else if (list.length < 18) list.push(n.id);
      stops.value = list.join(', ');
    },
  });
  gv.setOptions({ showWeights: false, showTree: false });
  q('#rz-in').addEventListener('click', () => gv.zoomBy(1.25));
  q('#rz-out').addEventListener('click', () => gv.zoomBy(0.8));
  q('#rz-fit').addEventListener('click', () => gv.fit());

  function parse(text) { return text.split(/[\s,;]+/).filter(Boolean).map(Number).filter((x) => Number.isInteger(x)); }
  const showErr = (m) => { const e = q('#t-err'); e.textContent = m; e.hidden = !m; };

  q('#t-random').addEventListener('click', () => {
    const g = Store.state.graph; if (!g) return;
    const k = Math.max(1, Math.min(18, Number(q('#t-k').value) || 4));
    const ids = g.nodes.map((n) => n.id).sort(() => Math.random() - 0.5).slice(0, Math.min(k + 1, g.nodes.length));
    q('#t-depot').value = ids[0]; q('#t-stops').value = ids.slice(1).join(', ');
  });
  q('#term-form').addEventListener('submit', async (ev) => {
    ev.preventDefault();
    const raw = q('#t-depot').value.trim();
    if (raw === '' || !Number.isInteger(Number(raw))) return showErr('Enter the depot as a whole number.');
    const stops = parse(q('#t-stops').value);
    if (!stops.length) return showErr('Enter at least one stop.');
    await withBusy(q('#term-form button[type=submit]'), async () => {
      try { await Api.setTerminals(Number(raw), stops); showErr(''); await Store.refresh(); toast('Stops set'); }
      catch (e) { showErr(e.message); }
    });
  });

  const update = () => {
    const st = Store.state, t = st.tour, g = st.graph;
    q('#rt-error').innerHTML = st.error && !st.online ? errorNotice(st.error) : '';
    q('#rt-error [data-retry]')?.addEventListener('click', () => Store.refresh());
    if (g) gv.setData(g, { fit: !gv._fitted });
    if (t && t.terminals_set) {
      gv.setOverlay({ terminals: [t.depot, ...t.stops], order: t.order });
      q('#rt-sub').textContent = `Depot ${t.depot} and ${t.k} stop${t.k === 1 ? '' : 's'}.`;
    } else { gv.setOverlay(null); q('#rt-sub').textContent = 'Keep an exact delivery tour correct as roads change.'; }
    renderResults(q('#rt-results'), t);
    renderCert(q('#rt-cert'), t);
  };
  const unsub = Store.subscribe(update);
  update(); Store.refresh();
  return () => { unsub(); gv.destroy(); };
}

function renderResults(el, t) {
  if (!t || !t.terminals_set) {
    el.innerHTML = `<div class="empty"><div><strong>No tour yet</strong><p>Set a depot and stops. The tour is solved exactly and then kept up to date as roads close.</p></div></div>`;
    return;
  }
  const terms = [t.depot, ...t.stops];
  const last = t.last_route;
  const changedNote = last ? `Last update: ${last.touched_trees} of ${terms.length} shortest-path trees did real work.` : 'No updates applied since the stops were set.';
  el.innerHTML = `
    <div class="kpis" style="--cols:3">
      <div class="kpi"><div class="kpi-label">Tour cost</div><div class="kpi-value">${t.feasible ? fmtCost(t.tour_cost) : DASH}</div><div class="kpi-note">${t.feasible ? 'exact optimum' : 'no feasible tour'}</div></div>
      <div class="kpi"><div class="kpi-label">Exact-solver steps</div><div class="kpi-value ${t.hk_transitions_pipeline === 0 ? 'is-zero' : ''}">${fmt(t.hk_transitions_pipeline)}</div><div class="kpi-note">recompute-everything: ${fmt(t.hk_transitions_reference)}</div></div>
      <div class="kpi"><div class="kpi-label">Reference tour cost</div><div class="kpi-value">${fmtCost(t.reference_cost)}</div><div class="kpi-note">${t.tour_cost === t.reference_cost ? 'matches the pipeline' : 'differs from the pipeline'}</div></div>
    </div>
    <div class="panel panel-pad"><h2 class="panel-title" style="margin-bottom:12px">Visiting order</h2>
      ${t.order.length ? `<div class="path-line"><span class="chip chip-depot">${t.depot}</span>${t.order.map((v) => `<span class="sep">${icon('chevron')}</span><span class="chip">${v}</span>`).join('')}<span class="sep">${icon('chevron')}</span><span class="chip chip-depot">${t.depot}</span></div>`
        : '<p class="muted">No finite tour exists: some stop cannot be reached.</p>'}
      <p class="small muted" style="margin-top:12px">${esc(changedNote)}</p></div>
    <div class="panel"><div class="panel-head"><div><h2 class="panel-title">Terminal distances</h2><p class="panel-sub">Shortest-path distance from the row vertex to the column vertex</p></div></div>
      <div class="table-wrap panel-body" style="padding-left:0;padding-right:0"><table class="table matrix"><thead><tr><th>From \\ to</th>${terms.map((v, i) => `<th class="num">${v}${i === 0 ? ' (depot)' : ''}</th>`).join('')}</tr></thead><tbody>
      ${t.matrix.map((row, i) => `<tr><td>${terms[i]}${i === 0 ? ' (depot)' : ''}</td>${row.map((x, j) => `<td class="num ${i === j ? 'diag' : ''}">${i === j ? DASH : x === null ? '<span class="pill pill-negative">unreachable</span>' : fmt(x)}</td>`).join('')}</tr>`).join('')}</tbody></table></div></div>`;
}

function renderCert(el, t) {
  const lr = t && t.last_route;
  el.innerHTML = `<h2 class="panel-title">Certificate decision</h2>
    ${lr ? `<div>${routePill(lr.route_action)}</div><p class="muted">${esc(routeText(lr.route_action))}</p>
      <dl class="facts"><dt>Stops</dt><dd>${fmt(t.k)}</dd><dt>Distances the tour depends on</dt><dd>${fmt(t.k + 1)}</dd><dt>Exact-solver steps this update</dt><dd>${fmt(lr.hk_transitions)}</dd><dt>Recompute-everything would use</dt><dd>${fmt(lr.reference_hk_transitions)}</dd>
      <dt>Lower bound on the tour</dt><dd>${fmtCost(lr.lower_bound)}</dd><dt>Matches the reference</dt><dd>${lr.matches_reference ? '<span class="pill pill-positive">Yes</span>' : '<span class="pill pill-negative">No</span>'}</dd></dl>`
      : '<p class="muted">After each update the engine asks whether any road the current tour uses got worse. If not, the tour is kept and the exact solver is skipped. Decisions appear here.</p>'}`;
}
