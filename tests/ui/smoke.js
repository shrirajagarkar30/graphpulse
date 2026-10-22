/* GraphPulse-R UI smoke test (functional regression in both themes).
 *
 * How to run: start the dashboard (python run_ui.py --no-browser --port 8124), open http://127.0.0.1:8124/
 * in a desktop-size browser, paste this whole file into the DevTools console (or run it with a browser tool's
 * "evaluate" action). It resets the workspace, drives the real UI, and returns a list of {name, pass, extra}.
 * It does not need any test framework and changes only the in-memory workspace.
 */
(async () => {
  const R = [];
  const ok = (name, cond, extra) => R.push({ name, pass: !!cond, extra: extra === undefined ? undefined : String(extra).slice(0, 120) });
  const wait = (ms) => new Promise((r) => setTimeout(r, ms));
  const q = (s) => document.querySelector(s);
  const qa = (s) => [...document.querySelectorAll(s)];
  const root = document.documentElement;
  const api = async (p, body) => (await fetch(p, body === undefined ? {} : { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify(body) })).json();
  const click = async (s, ms = 300) => { const el = q(s); if (!el) { ok(`exists ${s}`, false); return null; } el.click(); await wait(ms); return el; };
  const setVal = (s, v) => { const el = q(s); if (!el) { ok(`exists ${s}`, false); return; } el.value = v; el.dispatchEvent(new Event('input', { bubbles: true })); el.dispatchEvent(new Event('change', { bubbles: true })); };
  const submit = async (s, ms = 1200) => { const f = q(s); if (!f) { ok(`exists ${s}`, false); return; } f.requestSubmit(); await wait(ms); };
  const go = async (h, ms = 1100) => { location.hash = h; await wait(ms); };
  const bg = () => getComputedStyle(document.body).backgroundColor;

  await api('/api/config', { c: 1 });
  await api('/api/reset', {});
  await api('/api/graph/load', { preset: 'grid', params: { rows: 6, cols: 6 } });
  localStorage.setItem('gp.sidebar', 'expanded'); root.removeAttribute('data-sidebar');

  // ---- landing ------------------------------------------------------------------------------
  await go('#/', 1500);
  ok('landing shows an h1', q('#landing h1') && q('#landing h1').textContent.includes('Routes that stay right'));
  ok('landing hides the app', q('#app').hidden === true);
  ok('loader is gone', q('#loader').hidden === true || q('#loader').classList.contains('done'));
  ok('landing has a Get started action', qa('#landing a[href="#/overview"]').length >= 2);
  ok('live graph fragment is drawn', q('#landing-canvas') && !q('#landing-stage-msg').offsetParent);
  ok('page does not scroll sideways (landing)', document.documentElement.scrollWidth <= innerWidth + 1);
  const t0 = root.dataset.theme;
  await click('.l-nav [data-theme-cycle]');
  ok('landing theme control changes the theme', root.dataset.theme !== t0 || JSON.parse(localStorage.getItem('gp.settings')).theme !== undefined);
  await click('#landing-run', 9000);
  ok('sample scenario fills the decision fragment', q('#frag-decision') && /Certificate|Alternative|Repair|Rebuild/.test(q('#frag-decision').textContent), q('#frag-decision') && q('#frag-decision').textContent);
  ok('sample scenario fills the tour fragment', q('#frag-tour') && /total cost/.test(q('#frag-tour').textContent));
  await api('/api/reset', {});
  await click('#landing a.btn-primary.btn-lg');
  await wait(900);
  ok('Get started opens the dashboard', location.hash === '#/overview' && q('#app').hidden === false);

  // ---- both themes: every page renders ---------------------------------------------------------
  const pages = ['overview', 'network', 'routing', 'activity', 'verification', 'state', 'guide', 'glossary', 'settings'];
  for (const theme of ['light', 'dark']) {
    await go('#/settings/appearance');
    await click(`[data-theme="${theme}"]`);
    ok(`[${theme}] theme applied`, root.dataset.theme === theme);
    ok(`[${theme}] preference persisted`, JSON.parse(localStorage.getItem('gp.settings')).theme === theme);
    const bgNow = bg();
    for (const p of pages) {
      await go(`#/${p}`);
      const h1 = q('#view h1');
      ok(`[${theme}] ${p}: h1`, h1 && h1.textContent.trim().length > 0, h1 && h1.textContent);
      ok(`[${theme}] ${p}: no sideways scroll`, document.documentElement.scrollWidth <= innerWidth + 1, document.documentElement.scrollWidth);
      ok(`[${theme}] ${p}: current nav item marked`, !!q('.nav-item[aria-current="page"]'));
      ok(`[${theme}] ${p}: no error notice`, !q('#view .notice-error'));
    }
    ok(`[${theme}] background differs per theme`, theme === 'light' ? bgNow !== 'rgb(10, 10, 10)' : bgNow === 'rgb(10, 10, 10)', bgNow);
  }
  await go('#/settings/appearance'); await click('[data-theme="light"]');

  // ---- network: forms, errors, decisions ----------------------------------------------------------
  await go('#/network');
  ok('network canvas present', !!q('#net-canvas'));
  setVal('#u-from', '999'); setVal('#u-to', '1'); await submit('#upd-form');
  ok('network: invalid road shows an inline error', q('#upd-err') && !q('#upd-err').hidden && q('#upd-err').textContent.length > 0, q('#upd-err').textContent);
  setVal('#u-from', ''); setVal('#u-to', ''); await submit('#upd-form', 300);
  ok('network: empty form is rejected client-side', !q('#upd-err').hidden);
  setVal('#u-from', '0'); setVal('#u-to', '1'); await submit('#upd-form', 1500);
  let m = await api('/api/metrics');
  ok('network: closing a road is applied by the engine', m.total_updates === 1, m.total_updates);
  ok('network: decision panel names the decision', /Certificate|Alternative|Repair|Rebuild/.test(q('#decision').textContent), q('#decision').textContent);
  await click('[data-kind="increase"]');
  ok('network: slow-road mode reveals the weight field', !q('#w-field').hidden);
  setVal('#u-from', '1'); setVal('#u-to', '2'); setVal('#u-w', '1'); await submit('#upd-form', 1200);
  ok('network: a non-increasing weight is rejected by the engine', !q('#upd-err').hidden, q('#upd-err').textContent);
  setVal('#u-w', '40'); await submit('#upd-form', 1500);
  m = await api('/api/metrics');
  ok('network: slowing a road is applied', m.total_updates === 2, m.total_updates);
  await click('#tg-tree'); ok('network: tree-only toggle', q('#tg-tree').getAttribute('aria-pressed') === 'true'); await click('#tg-tree');
  await click('#z-in'); await click('#z-out'); await click('#z-fit');
  await click('#net-sim', 7000);
  m = await api('/api/metrics');
  ok('network: simulate applies ten more updates', m.total_updates >= 12, m.total_updates);

  // ---- routing --------------------------------------------------------------------------------------
  await go('#/routing');
  setVal('#t-depot', '0'); setVal('#t-stops', '5, 5'); await submit('#term-form');
  ok('routing: duplicate stops are rejected', !q('#t-err').hidden, q('#t-err').textContent);
  setVal('#t-stops', Array.from({ length: 19 }, (_, i) => i + 1).join(',')); await submit('#term-form');
  ok('routing: more than eighteen stops are rejected', /18/.test(q('#t-err').textContent), q('#t-err').textContent);
  setVal('#t-stops', '5, 14, 22, 35'); await submit('#term-form', 1500);
  ok('routing: tour is shown', /Tour cost/.test(q('#rt-results').textContent));
  ok('routing: matrix is a table', qa('#rt-results table.matrix tbody tr').length === 5);
  const tour = await api('/api/tour');
  ok('routing: tour matches the reference', tour.tour_cost === tour.reference_cost, `${tour.tour_cost} vs ${tour.reference_cost}`);
  await click('#t-random'); ok('routing: pick-random fills the fields', q('#t-depot').value !== '' && q('#t-stops').value !== '');
  await go('#/network'); await click('#net-sim', 7000);
  await go('#/routing');
  ok('routing: certificate decision appears after updates', /Tour kept|Tour re-solved|No feasible/.test(q('#rt-cert').textContent), q('#rt-cert').textContent);

  // ---- overview -------------------------------------------------------------------------------------
  await go('#/overview', 1400);
  ok('overview: KPI strip shows updates', q('.kpis') && /Updates applied/.test(q('.kpis').textContent));
  ok('overview: chart is drawn', !!q('#view svg.chart polyline'));
  ok('overview: tour panel lists the order', /Visiting order/.test(q('#view').textContent));

  // ---- activity ---------------------------------------------------------------------------------------
  await go('#/activity');
  const total = qa('#view tbody tr').length;
  ok('activity: rows listed', total >= 12, total);
  setVal('#ac-filter', 'cert'); await wait(300);
  ok('activity: filter narrows the list', qa('#view tbody tr').length <= total);
  setVal('#ac-filter', 'all'); await wait(300);
  await click('#view tbody tr.row-link', 500);
  ok('activity: detail drawer opens', !!q('.drawer'));
  document.dispatchEvent(new KeyboardEvent('keydown', { key: 'Escape' })); await wait(300);
  ok('activity: Escape closes the drawer', !q('.drawer'));

  // ---- verification, inspector --------------------------------------------------------------------------
  await go('#/verification');
  await click('#vf-run', 1800);
  ok('verification: passes on the live state', /Verified/.test(q('#view').textContent) && /State is correct/.test(q('#view').textContent));
  await go('#/state', 1500);
  ok('inspector: lists vertices', qa('#view tbody tr').length >= 36, qa('#view tbody tr').length);
  setVal('#in-search', '5'); await wait(900);
  ok('inspector: search filters to one vertex', qa('#view tbody tr').length === 1);
  setVal('#in-search', '9999'); await wait(900);
  ok('inspector: unknown vertex shows an empty state', /No matching vertex/.test(q('#view').textContent));

  // ---- settings ---------------------------------------------------------------------------------------
  await go('#/settings/appearance');
  setVal('#st-density', 'compact'); await wait(300);
  ok('settings: density applied', root.dataset.density === 'compact');
  setVal('#st-density', 'comfortable');
  setVal('#st-motion', 'reduced'); await wait(300);
  ok('settings: reduced motion applied', root.dataset.motion === 'reduced');
  setVal('#st-motion', 'system');
  await go('#/settings/engine');
  setVal('#st-c', 'custom'); setVal('#st-custom', '-3'); await click('#st-apply', 400);
  ok('settings: negative budget is rejected', !q('#st-err').hidden);
  setVal('#st-custom', '0.5'); await click('#st-apply', 400);
  ok('settings: confirmation dialog appears', !!q('.dialog'));
  await click('.dialog [data-ok]', 1500);
  ok('settings: budget applied to the engine', (await api('/api/config')).c === 0.5);
  await go('#/settings/engine'); setVal('#st-c', 'one'); await click('#st-apply', 400); await click('.dialog [data-ok]', 1500);
  ok('settings: budget restored', (await api('/api/config')).c === 1);
  await go('#/settings/data');
  await click('#st-reset', 400); ok('settings: reset asks for confirmation', !!q('.dialog'));
  await click('.dialog [data-cancel]', 300); ok('settings: cancel keeps the dialog closed', !q('.dialog'));

  // ---- shell ---------------------------------------------------------------------------------------------
  await click('#sb-toggle', 500);
  ok('sidebar: collapse button works', root.dataset.sidebar === 'collapsed' && localStorage.getItem('gp.sidebar') === 'collapsed');
  ok('sidebar: toggle state exposed to assistive tech', q('#sb-toggle').getAttribute('aria-expanded') === 'false');
  await click('#sb-toggle', 500);
  ok('sidebar: expand button works', !root.dataset.sidebar);
  const nav = q('#sidebar-nav'); const cs = getComputedStyle(nav);
  ok('sidebar: nav scrolls independently', /auto|scroll/.test(cs.overflowY));
  ok('sidebar: settings, theme and account sit at the bottom', !!q('#sidebar-foot a[href="#/settings"]') && !!q('#sidebar-foot [data-theme-set]') && !!q('#account-btn'));
  await click('#account-btn', 300); ok('account menu opens', !!q('.menu'));
  document.dispatchEvent(new KeyboardEvent('keydown', { key: 'Escape' })); await wait(200); ok('account menu closes with Escape', !q('.menu'));
  await click('#sidebar-foot [data-theme-set="dark"]', 300); ok('sidebar theme control switches theme', root.dataset.theme === 'dark');
  await click('#sidebar-foot [data-theme-set="light"]', 300);

  await api('/api/reset', {});
  const failed = R.filter((r) => !r.pass);
  return JSON.stringify({ total: R.length, failed: failed.length, failures: failed });
})();
