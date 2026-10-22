// Overview: did repairs save work, and is the tour still right?
import { Store } from '../store.js';
import { icon } from '../icons.js';
import { lineChart, barList } from '../charts.js';
import { esc, fmt, fmtCost, DASH, strategyPill, routePill, routeText, skeletonKpis, emptyState, errorNotice } from '../ui.js';

export default function overview(view, ctx) {
  let stamp = null;
  const draw = () => {
    const st = Store.state;
    const m = st.metrics;
    const logs = st.logs || [];
    const h = [];
    const updates = m ? m.total_updates : 0;
    let sub = 'Operation counts for every update applied in this workspace.';
    if (m && updates > 0) {
      sub = `${fmt(m.cumulative_online_work)} operations were used; recomputing after every update would have used ${fmt(m.cumulative_rebuild_work)}.`;
    } else if (m) sub = 'No updates applied yet. Close or slow a road to see how the engine responds.';

    h.push(`<header class="page-head"><div><h1 class="page-title">Overview</h1><p class="page-sub">${esc(sub)}</p></div>
      <div class="page-actions"><span class="stamp" id="ov-stamp">${stamp ? `Updated ${esc(stamp)}` : ''}</span>
      <button class="btn" type="button" id="ov-refresh">${icon('refresh')}Refresh</button>
      <a class="btn btn-primary" href="#/network">Apply an update</a></div></header>`);

    if (st.error && !st.online) h.push(errorNotice(st.error));
    if (!st.loaded && !st.error) {
      h.push(skeletonKpis(4));
    } else if (st.loaded) {
      const saved = m && m.cumulative_rebuild_work > 0 ? m.savings_percentage : null;
      h.push(`<div class="kpis" style="--cols:4">
        ${kpi('Updates applied', fmt(updates), '', updates === 0)}
        ${kpi('Operations used', fmt(m.cumulative_online_work), '', m.cumulative_online_work === 0)}
        ${kpi('Recompute baseline', fmt(m.cumulative_rebuild_work), 'Dijkstra after every update', m.cumulative_rebuild_work === 0)}
        ${kpi('Operations saved', saved === null ? DASH : `${fmt(saved, 1)}<span class="unit">%</span>`, saved === null ? 'No baseline yet' : 'against the recompute baseline', saved === null)}
      </div>`);

      const online = [], base = [];
      let a = 0, b = 0;
      [...logs].reverse().forEach((l) => { a += l.work; b += l.baseline_work; online.push(a); base.push(b); });
      const mix = m.strategy_counts;
      h.push(`<section class="section"><div class="split">
        <div class="panel"><div class="panel-head"><div><h2 class="panel-title">Cumulative operations</h2><p class="panel-sub">Online engine against recomputing after every update</p></div></div>
          <div class="panel-body">${updates === 0 ? emptyChartNote() : ''}${lineChart({ series: [{ name: 'GraphPulse-R', values: online, cls: 'series-main' }, { name: 'Recompute baseline', values: base, cls: 'series-ref' }] })}</div></div>
        <div class="panel"><div class="panel-head"><div><h2 class="panel-title">How updates were resolved</h2><p class="panel-sub">Single-source engine, by decision</p></div></div>
          <div class="panel-body">${barList([
            { label: 'Certificate', value: mix.cert }, { label: 'Alternative support', value: mix.alt },
            { label: 'Repair', value: mix.repair }, { label: 'Rebuild after abort', value: mix.fallback }], { unit: 'updates' })}
          <p class="small muted" style="margin-top:12px">Certificate hit rate: ${updates === 0 ? DASH : `${fmt(m.certificate_hit_rate, 1)}<span class="muted">%</span>`}</p></div></div>
      </div></section>`);

      h.push(`<section class="section"><div class="section-head"><h2 class="section-title">Delivery tour</h2><a class="link-btn" href="#/routing">Open routing</a></div>${tourPanel(st.tour)}</section>`);

      const rows = logs.slice(0, 5);
      h.push(`<section class="section"><div class="section-head"><h2 class="section-title">Recent updates</h2>${logs.length ? `<a class="link-btn" href="#/activity">View all ${fmt(logs.length)}</a>` : ''}</div>
        ${rows.length ? `<div class="panel table-wrap"><table class="table"><thead><tr><th>Update</th><th>Resolved by</th><th class="num">Operations</th><th class="num hide-sm">Baseline</th></tr></thead><tbody>
          ${rows.map((l) => `<tr class="row-link" data-id="${l.id}"><td>${l.kind === 'delete' ? 'Closed' : 'Slowed'} road <span class="num">${l.u} to ${l.v}</span><span class="sub">${esc(l.time)}${l.kind === 'increase' ? `, weight ${l.old_w} to ${l.new_w}` : ''}</span></td>
          <td>${strategyPill(l.strategy)}</td><td class="num">${fmt(l.work)}</td><td class="num hide-sm">${fmt(l.baseline_work)}</td></tr>`).join('')}</tbody></table></div>`
          : emptyState('Nothing to show yet', 'Applied updates appear here with the decision the engine made.', '<a class="btn btn-primary btn-sm" href="#/network">Apply an update</a>')}</section>`);
    }
    view.innerHTML = h.join('');
    view.querySelector('#ov-refresh')?.addEventListener('click', async () => { await Store.refresh(); stamp = new Date().toLocaleTimeString(); draw(); });
    view.querySelector('[data-retry]')?.addEventListener('click', () => Store.refresh());
    view.querySelectorAll('tr.row-link').forEach((tr) => tr.addEventListener('click', () => { location.hash = '#/activity'; }));
  };
  const unsub = Store.subscribe(draw);
  draw();
  if (!Store.state.loaded) Store.refresh().then(() => { stamp = new Date().toLocaleTimeString(); });
  return unsub;
}

const kpi = (label, value, note = '', zero = false) =>
  `<div class="kpi"><div class="kpi-label">${esc(label)}</div><div class="kpi-value ${zero ? 'is-zero' : ''}">${value}</div>${note ? `<div class="kpi-note">${esc(note)}</div>` : ''}</div>`;
const emptyChartNote = () => '<p class="small muted" style="margin-bottom:8px">No updates yet. The chart will fill as updates are applied.</p>';

export function tourPanel(t) {
  if (!t || !t.terminals_set) {
    return emptyState('No stops set', 'Choose a depot and delivery stops to keep an exact tour correct as roads change.', '<a class="btn btn-primary btn-sm" href="#/routing">Set up stops</a>');
  }
  const lr = t.last_route;
  return `<div class="panel panel-pad"><dl class="facts">
    <dt>Tour cost</dt><dd>${t.feasible ? fmtCost(t.tour_cost) : '<span class="pill pill-negative">No feasible tour</span>'}</dd>
    <dt>Visiting order</dt><dd>${t.order.length ? `<span class="path-line" style="justify-content:flex-end"><span class="chip chip-depot">${t.depot}</span>${t.order.map((v) => `<span class="sep">${icon('chevron')}</span><span class="chip">${v}</span>`).join('')}<span class="sep">${icon('chevron')}</span><span class="chip chip-depot">${t.depot}</span></span>` : DASH}</dd>
    <dt>Last certificate decision</dt><dd>${lr ? routePill(lr.route_action) : DASH}</dd>
    <dt>Exact-solver steps since stops were set</dt><dd>${fmt(t.hk_transitions_pipeline)} <span class="muted">(recompute-everything: ${fmt(t.hk_transitions_reference)})</span></dd></dl>
    ${lr ? `<p class="small muted" style="margin-top:12px">${esc(routeText(lr.route_action))}</p>` : ''}</div>`;
}
