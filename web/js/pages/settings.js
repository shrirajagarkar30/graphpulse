// Settings: only settings that do something. Appearance and workspace defaults are stored in this browser;
// the budget multiplier is applied to the engine through the API. Each control saves itself.
import { Api } from '../api.js';
import { Store } from '../store.js';
import { Settings } from '../theme.js';
import { icon } from '../icons.js';
import { esc, toast, confirmDialog, downloadFile } from '../ui.js';

const TABS = [['appearance', 'Appearance'], ['workspace', 'Workspace'], ['engine', 'Engine'], ['data', 'Data']];

export default function settings(view, ctx) {
  const tab = TABS.some(([k]) => k === ctx.param) ? ctx.param : 'appearance';
  const s = Settings.get();
  const saved = (el) => { const m = el.closest('.setting').querySelector('.saved'); if (m) { m.classList.add('on'); setTimeout(() => m.classList.remove('on'), 1400); } };
  const row = (title, desc, control) => `<div class="setting"><div><h3>${title}</h3><p class="desc">${desc}</p></div><div class="setting-control">${control}<span class="saved" aria-live="polite">Saved</span></div></div>`;

  let body = '';
  if (tab === 'appearance') {
    body = row('Theme', 'Light, dark, or follow your system.', `<div class="segmented" role="group" aria-label="Theme">${['light', 'dark', 'system'].map((t) => `<button type="button" data-theme="${t}" aria-pressed="${s.theme === t}">${icon(t === 'light' ? 'sun' : t === 'dark' ? 'moon' : 'monitor')}${t[0].toUpperCase() + t.slice(1)}</button>`).join('')}</div>`)
      + row('Density', 'Compact tightens tables, controls and panel padding to show more at once.', `<div class="select-wrap"><select class="select" id="st-density" aria-label="Density"><option value="comfortable" ${s.density === 'comfortable' ? 'selected' : ''}>Comfortable</option><option value="compact" ${s.density === 'compact' ? 'selected' : ''}>Compact</option></select></div>`)
      + row('Motion', 'Reduce animation and transitions. Your system setting is respected by default.', `<div class="select-wrap"><select class="select" id="st-motion" aria-label="Motion"><option value="system" ${s.motion !== 'reduced' ? 'selected' : ''}>Follow system</option><option value="reduced" ${s.motion === 'reduced' ? 'selected' : ''}>Reduce motion</option></select></div>`);
  } else if (tab === 'workspace') {
    body = row('Show road weights', 'Label each road on the map with its weight when you open the Network page.', `<label class="setting-switch"><span>Show weights by default</span><span class="switch"><input type="checkbox" id="st-weights" ${s.showWeights ? 'checked' : ''}><span class="track"></span><span class="thumb"></span></span></label>`)
      + row('Tree only', 'Hide roads that are not part of the shortest-path tree when you open the Network page.', `<label class="setting-switch"><span>Show only the tree by default</span><span class="switch"><input type="checkbox" id="st-tree" ${s.showTree ? 'checked' : ''}><span class="track"></span><span class="thumb"></span></span></label>`);
  } else if (tab === 'engine') {
    const c = Store.state.config ? Store.state.config.c : 1;
    const mode = c === 'random' ? 'random' : c === 'inf' ? 'inf' : c === 0 ? 'zero' : c === 1 ? 'one' : 'custom';
    body = row('Repair budget', 'How much work repair may spend, as a multiple of a full rebuild. A value of one is the setting with the best proven worst-case ratio. Changing it restarts the engines from the initial graph and clears the activity log.',
      `<div class="select-wrap"><select class="select" id="st-c" aria-label="Repair budget"><option value="one" ${mode === 'one' ? 'selected' : ''}>One times the rebuild cost (recommended)</option><option value="custom" ${mode === 'custom' ? 'selected' : ''}>Custom multiple</option><option value="zero" ${mode === 'zero' ? 'selected' : ''}>Never repair (always rebuild)</option><option value="inf" ${mode === 'inf' ? 'selected' : ''}>Always repair (never rebuild)</option><option value="random" ${mode === 'random' ? 'selected' : ''}>Randomized</option></select></div>
       <div class="field" id="st-custom-wrap" ${mode === 'custom' ? '' : 'hidden'}><label for="st-custom">Multiple of the rebuild cost</label><input class="input num" id="st-custom" type="number" min="0" step="0.25" value="${typeof c === 'number' ? c : 1}"></div>
       <p class="error-text" id="st-err" role="alert" hidden></p><button class="btn btn-primary" type="button" id="st-apply" data-busy="Applying">Apply and restart engines</button>
       <p class="muted small">Current value: <strong>${c === 'inf' ? 'always repair' : c === 'random' ? 'randomized' : esc(String(c))}</strong></p>`);
  } else {
    body = row('Export activity', 'Download every update and the decision taken as a CSV file.', `<button class="btn" type="button" id="st-export">${icon('download')}Export CSV</button>`)
      + `<div class="danger-zone setting"><div><h3>Reset workspace</h3><p class="desc">Restores the initial graph and clears the activity log and routing counters. Your appearance settings are kept.</p></div><div class="setting-control"><button class="btn btn-danger" type="button" id="st-reset">${icon('trash')}Reset workspace</button></div></div>`;
  }

  view.innerHTML = `<header class="page-head"><div><h1 class="page-title">Settings</h1><p class="page-sub">Appearance and workspace preferences are kept in this browser. The repair budget is applied to the engine.</p></div></header>
    <nav class="tabs" aria-label="Settings areas">${TABS.map(([k, l]) => `<a class="tab" href="#/settings/${k}" ${k === tab ? 'aria-current="page"' : ''}>${l}</a>`).join('')}</nav>
    <div class="panel panel-pad" style="padding-top:0;padding-bottom:0">${body}</div>
    ${tab === 'appearance' ? preview() : ''}`;

  const q = (x) => view.querySelector(x);
  view.querySelectorAll('[data-theme]').forEach((b) => b.addEventListener('click', () => {
    Settings.set({ theme: b.dataset.theme });
    view.querySelectorAll('[data-theme]').forEach((x) => x.setAttribute('aria-pressed', String(x === b))); saved(b);
  }));
  q('#st-density')?.addEventListener('change', (e) => { Settings.set({ density: e.target.value }); saved(e.target); });
  q('#st-motion')?.addEventListener('change', (e) => { Settings.set({ motion: e.target.value }); saved(e.target); });
  q('#st-weights')?.addEventListener('change', (e) => { Settings.set({ showWeights: e.target.checked }); saved(e.target); });
  q('#st-tree')?.addEventListener('change', (e) => { Settings.set({ showTree: e.target.checked }); saved(e.target); });
  q('#st-c')?.addEventListener('change', (e) => { q('#st-custom-wrap').hidden = e.target.value !== 'custom'; });
  q('#st-apply')?.addEventListener('click', async (ev) => {
    const btn = ev.currentTarget;            // captured now: currentTarget is null after the first await
    const v = q('#st-c').value;
    let c = v === 'one' ? 1 : v === 'zero' ? 0 : v === 'inf' ? 'inf' : v === 'random' ? 'random' : Number(q('#st-custom').value);
    const err = q('#st-err');
    if (typeof c === 'number' && (!Number.isFinite(c) || c < 0)) { err.textContent = 'Enter a number that is zero or greater.'; err.hidden = false; return; }
    err.hidden = true;
    const ok = await confirmDialog({ title: 'Restart the engines?', body: 'The repair budget changes how updates are handled. The graph returns to its initial state and the activity log is cleared.', confirm: 'Apply and restart' });
    if (!ok) return;
    btn.disabled = true;
    try { await Api.setConfig(c); await Store.refresh(); toast('Repair budget updated'); settings(view, ctx); }
    catch (e2) { err.textContent = e2.message; err.hidden = false; btn.disabled = false; }
  });
  q('#st-export')?.addEventListener('click', () => {
    const logs = Store.state.logs || [];
    if (!logs.length) return toast('There is no activity to export yet', 'error');
    const cols = ['id', 'time', 'kind', 'u', 'v', 'old_w', 'new_w', 'strategy', 'work', 'baseline_work', 'budget'];
    downloadFile('graphpulse-activity.csv', [cols.join(','), ...[...logs].reverse().map((l) => cols.map((c) => l[c] ?? '').join(','))].join('\n'), 'text/csv');
  });
  q('#st-reset')?.addEventListener('click', async () => {
    const ok = await confirmDialog({ title: 'Reset the workspace?', body: 'This restores the initial graph and clears the activity log and routing counters.', confirm: 'Reset workspace', danger: true });
    if (!ok) return;
    try { await Api.reset(); await Store.refresh(); toast('Workspace reset'); } catch (e) { toast(e.message, 'error'); }
  });
  if (!Store.state.loaded) Store.refresh().then(() => { if (tab === 'engine') settings(view, ctx); });
  return () => {};
}


// A small live sample, drawn with the same tokens as the app, so theme and density changes are visible here.
function preview() {
  return `<section class="section"><div class="section-head"><h2 class="section-title">Preview</h2><span class="muted small">Sample values, for appearance only</span></div>
    <div class="kpis" style="--cols:3"><div class="kpi"><div class="kpi-label">Updates applied</div><div class="kpi-value">12</div></div>
      <div class="kpi"><div class="kpi-label">Operations used</div><div class="kpi-value">182</div></div>
      <div class="kpi"><div class="kpi-label">Operations saved</div><div class="kpi-value">94.3<span class="unit">%</span></div></div></div>
    <div class="panel table-wrap" style="margin-top:12px"><table class="table"><thead><tr><th>Update</th><th>Resolved by</th><th class="num">Operations</th></tr></thead><tbody>
      <tr><td>Slowed road <span class="num">12 to 18</span><span class="sub">sample data</span></td><td><span class="pill pill-data">Repair</span></td><td class="num">45</td></tr>
      <tr><td>Closed road <span class="num">4 to 5</span><span class="sub">sample data</span></td><td><span class="pill">Certificate</span></td><td class="num">1</td></tr></tbody></table></div></section>`;
}
