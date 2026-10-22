// State inspector: the per-vertex state the engine holds (distance, parent, tight in-edges, children).
import { Api } from '../api.js';
import { Store } from '../store.js';
import { icon } from '../icons.js';
import { esc, fmt, DASH, emptyState, errorNotice, downloadFile } from '../ui.js';

export default function inspector(view) {
  let rows = [], total = 0, search = '', shown = 50, error = '', loading = true;
  const load = async () => {
    loading = true; draw();
    try { const r = await Api.state(search); rows = r.rows; total = r.total_vertices; error = ''; }
    catch (e) { error = e.message; }
    loading = false; draw();
  };
  const draw = () => {
    const focus = document.activeElement && document.activeElement.id === 'in-search';
    view.innerHTML = `<header class="page-head"><div><h1 class="page-title">State inspector</h1><p class="page-sub">What the engine holds for each vertex, measured from the source.</p></div>
      <div class="page-actions"><button class="btn" type="button" id="in-export" ${rows.length ? '' : 'disabled'}>${icon('download')}Export JSON</button></div></header>
      ${error ? errorNotice(error) : ''}
      <div class="row-wrap" style="margin-bottom:12px;justify-content:space-between"><div style="width:240px"><label class="sr-only" for="in-search">Search vertex</label><input class="input num" id="in-search" placeholder="Vertex number" inputmode="numeric" value="${esc(search)}" autocomplete="off"></div>
        <span class="muted">${loading ? 'Loading…' : `${fmt(rows.length)} of ${fmt(total)} vertices`}</span></div>
      ${loading && !rows.length ? '<div class="panel panel-pad"><div class="skeleton skeleton-line skel-row"></div><div class="skeleton skeleton-line skel-row"></div><div class="skeleton skeleton-line skel-row"></div></div>'
        : rows.length ? `<div class="panel table-wrap"><table class="table"><thead><tr><th>Vertex</th><th class="num">Distance</th><th class="num">Parent</th><th class="num hide-sm">Tight in-edges</th><th class="hide-sm">Children</th></tr></thead><tbody>
        ${rows.slice(0, shown).map((r) => `<tr><td class="num">${r.v} ${r.is_source ? '<span class="pill pill-data">Source</span>' : ''} ${r.is_affected ? '<span class="pill pill-warning">Affected</span>' : ''}</td>
          <td class="num">${r.dist === 'INF' ? '<span class="pill pill-negative">unreachable</span>' : fmt(r.dist)}</td><td class="num">${r.parent === 'None' ? DASH : r.parent}</td><td class="num hide-sm">${fmt(r.tight)}</td>
          <td class="hide-sm">${r.children.length ? r.children.slice(0, 8).join(', ') + (r.children.length > 8 ? ` and ${r.children.length - 8} more` : '') : DASH}</td></tr>`).join('')}</tbody></table></div>
        ${rows.length > shown ? `<div style="margin-top:12px"><button class="btn" type="button" id="in-more">Show ${fmt(Math.min(50, rows.length - shown))} more</button></div>` : ''}`
        : emptyState('No matching vertex', 'Enter a vertex number that exists in the current graph.')}`;
    const s = view.querySelector('#in-search');
    if (focus) { s.focus(); s.setSelectionRange(s.value.length, s.value.length); }
    let t; s.addEventListener('input', () => { clearTimeout(t); t = setTimeout(() => { search = s.value.trim(); shown = 50; load(); }, 250); });
    view.querySelector('#in-more')?.addEventListener('click', () => { shown += 50; draw(); });
    view.querySelector('#in-export')?.addEventListener('click', () => downloadFile('graphpulse-state.json', JSON.stringify(rows, null, 2), 'application/json'));
    view.querySelector('[data-retry]')?.addEventListener('click', load);
  };
  load();
  return Store.subscribe(() => {});
}
