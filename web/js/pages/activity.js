// Activity: every update with the decision taken, filterable, with a detail drawer and CSV export.
import { Store } from '../store.js';
import { icon } from '../icons.js';
import { esc, fmt, fmtCost, DASH, strategyPill, strategyText, routePill, routeText, emptyState, errorNotice, openDrawer, downloadFile } from '../ui.js';

const FILTERS = [['all', 'All updates'], ['cert', 'Certificate'], ['alt', 'Alternative support'], ['repair', 'Repair'], ['fallback', 'Rebuild after abort'], ['delete', 'Closures'], ['increase', 'Slowdowns']];

export default function activity(view) {
  let filter = 'all';
  const draw = () => {
    const st = Store.state;
    const all = st.logs || [];
    const rows = all.filter((l) => filter === 'all' || l.strategy === filter || l.kind === filter);
    view.innerHTML = `<header class="page-head"><div><h1 class="page-title">Activity</h1><p class="page-sub">Every update and the decision the engine took, newest first.</p></div>
      <div class="page-actions"><button class="btn" type="button" id="ac-export" ${all.length ? '' : 'disabled'}>${icon('download')}Export CSV</button></div></header>
      ${st.error && !st.online ? errorNotice(st.error) : ''}
      <div class="row-wrap" style="margin-bottom:12px;justify-content:space-between"><div class="select-wrap" style="width:220px"><label class="sr-only" for="ac-filter">Filter</label><select class="select" id="ac-filter">${FILTERS.map(([v, l]) => `<option value="${v}" ${v === filter ? 'selected' : ''}>${esc(l)}</option>`).join('')}</select></div>
        <span class="muted">${fmt(rows.length)} of ${fmt(all.length)} updates</span></div>
      ${rows.length ? `<div class="panel table-wrap"><table class="table"><thead><tr><th>Update</th><th>Resolved by</th><th class="num">Operations</th><th class="num hide-sm">Baseline</th><th class="num hide-sm">Budget</th><th class="hide-sm">Verified</th></tr></thead><tbody>
        ${rows.map((l) => `<tr class="row-link" tabindex="0" data-id="${l.id}"><td>${l.kind === 'delete' ? 'Closed' : 'Slowed'} road <span class="num">${l.u} to ${l.v}</span><span class="sub">${esc(l.time)}${l.kind === 'increase' ? `, weight ${l.old_w} to ${l.new_w}` : ''}</span></td>
        <td>${strategyPill(l.strategy)}</td><td class="num">${fmt(l.work)}</td><td class="num hide-sm">${fmt(l.baseline_work)}</td><td class="num hide-sm">${l.budget === null ? DASH : fmt(l.budget)}</td>
        <td class="hide-sm">${l.verified ? '<span class="pill pill-positive">Verified</span>' : '<span class="pill pill-negative">Failed</span>'}</td></tr>`).join('')}</tbody></table></div>`
        : emptyState(all.length ? 'Nothing matches this filter' : 'No updates yet', all.length ? 'Choose another filter to see more updates.' : 'Close or slow a road on the Network page and it will appear here.', all.length ? '' : '<a class="btn btn-primary btn-sm" href="#/network">Apply an update</a>')}`;
    view.querySelector('#ac-filter').addEventListener('change', (e) => { filter = e.target.value; draw(); view.querySelector('#ac-filter').focus(); });
    view.querySelector('#ac-export')?.addEventListener('click', () => exportCsv(all));
    view.querySelector('[data-retry]')?.addEventListener('click', () => Store.refresh());
    const open = (tr) => { const l = all.find((x) => String(x.id) === tr.dataset.id); if (l) openDrawer(`Update ${l.id}`, detail(l)); };
    view.querySelectorAll('tr.row-link').forEach((tr) => { tr.addEventListener('click', () => open(tr)); tr.addEventListener('keydown', (e) => { if (e.key === 'Enter') open(tr); }); });
  };
  const unsub = Store.subscribe(draw);
  draw(); if (!Store.state.loaded) Store.refresh();
  return unsub;
}

function detail(l) {
  const r = l.route;
  return `<div>${strategyPill(l.strategy)}<p class="muted" style="margin-top:8px">${esc(strategyText(l.strategy))}</p></div>
    <dl class="facts"><dt>Road</dt><dd>${l.u} to ${l.v}</dd><dt>Change</dt><dd>${l.kind === 'delete' ? 'Closed' : `Weight ${l.old_w} to ${l.new_w}`}</dd><dt>Time</dt><dd>${esc(l.time)}</dd>
    <dt>Operations</dt><dd>${fmt(l.work)}</dd><dt>Scans, pushes, pops, queue</dt><dd>${fmt(l.scan)}, ${fmt(l.push)}, ${fmt(l.pop)}, ${fmt(l.queue)}</dd>
    <dt>Budget</dt><dd>${l.budget === null ? DASH : fmt(l.budget)}</dd><dt>Repair work</dt><dd>${fmt(l.repair_work)}</dd><dt>Rebuild work</dt><dd>${fmt(l.fallback_work)}</dd>
    <dt>Recompute baseline</dt><dd>${fmt(l.baseline_work)}</dd><dt>Vertices affected</dt><dd>${fmt(l.affected_size)}</dd><dt>Wall-clock (secondary)</dt><dd>${fmt(l.wall_time_ms, 2)} ms</dd>
    <dt>State check</dt><dd>${l.verified ? '<span class="pill pill-positive">Verified</span>' : '<span class="pill pill-negative">Failed</span>'}</dd></dl>
    ${l.affected_nodes && l.affected_nodes.length ? `<div><div class="label">Affected vertices</div><div class="path-line" style="margin-top:8px">${l.affected_nodes.slice(0, 40).map((v) => `<span class="chip">${v}</span>`).join('')}${l.affected_nodes.length > 40 ? `<span class="muted small">and ${l.affected_nodes.length - 40} more</span>` : ''}</div></div>` : ''}
    ${r ? `<div><div class="label">Tour</div><div style="margin-top:8px">${routePill(r.route_action)}</div><p class="muted small" style="margin-top:6px">${esc(routeText(r.route_action))}</p>
      <dl class="facts" style="margin-top:12px"><dt>Tour cost</dt><dd>${fmtCost(r.tour_cost)}</dd><dt>Reference cost</dt><dd>${fmtCost(r.reference_cost)}</dd><dt>Exact-solver steps</dt><dd>${fmt(r.hk_transitions)}</dd><dt>Trees touched</dt><dd>${fmt(r.touched_trees)}</dd></dl></div>` : ''}`;
}

function exportCsv(logs) {
  const cols = ['id', 'time', 'kind', 'u', 'v', 'old_w', 'new_w', 'strategy', 'work', 'baseline_work', 'budget', 'repair_work', 'fallback_work', 'affected_size', 'verified'];
  const line = (l) => cols.map((c) => { const v = l[c]; return v === null || v === undefined ? '' : String(v).includes(',') ? `"${v}"` : v; }).join(',');
  downloadFile('graphpulse-activity.csv', [cols.join(','), ...[...logs].reverse().map(line)].join('\n'), 'text/csv');
}
