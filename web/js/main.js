// Bootstrap: loader, hash router (landing and app pages), sidebar, account menu, landing behaviours.
import { installSprite, icon } from './icons.js';
import { initTheme, Settings, cycleTheme, resolvedTheme } from './theme.js';
import { Store, scopeLabel } from './store.js';
import { GraphView } from './graph_view.js';
import { openMenu, closeMenu, esc } from './ui.js';
import overview from './pages/overview.js';
import network from './pages/network.js';
import routing from './pages/routing.js';
import activity from './pages/activity.js';
import verification from './pages/verification.js';
import inspector from './pages/inspector.js';
import guide from './pages/guide.js';
import glossary from './pages/glossary.js';
import settings from './pages/settings.js';
import pune from './pages/pune.js';
import { runSampleScenario } from './scenario.js';
import { lineChart } from './charts.js';
import { fmt, fmtCost, DASH, strategyPill, strategyText, routePill, withBusy, toast } from './ui.js';

const PAGES = { overview, network, routing, activity, verification, state: inspector, guide, glossary, settings, pune };
const TITLES = { overview: 'Overview', network: 'Network', routing: 'Routing', activity: 'Activity', verification: 'Verification', state: 'State inspector', guide: 'Guide', glossary: 'Glossary', settings: 'Settings', pune: 'Pune Map Demo' };
const NAV = [
  { group: 'Workspace', items: [['overview', 'Overview', 'overview'], ['network', 'Network', 'network'], ['routing', 'Routing', 'route'], ['pune', 'Pune Map Demo', 'map']] },
  { group: 'Analysis', items: [['activity', 'Activity', 'list'], ['verification', 'Verification', 'shield'], ['state', 'State inspector', 'table']] },
  { group: 'Learn', items: [['guide', 'Guide', 'book'], ['glossary', 'Glossary', 'info']] },
];

const $ = (s) => document.querySelector(s);
const root = document.documentElement;
let cleanup = null;
let landingView = null;

// ---------------------------------------------------------------- sidebar
function navItem(id, label, ic, current, extra = '') {
  return `<a class="nav-item" href="#/${id}" data-tip="${esc(label)}" ${current === id ? 'aria-current="page"' : ''}>${icon(ic)}<span class="label">${esc(label)}</span>${extra}</a>`;
}
function renderSidebar(current) {
  const count = Store.state.logs ? Store.state.logs.length : 0;
  $('#sidebar-nav').innerHTML = NAV.map((g) => `<div class="nav-group"><div class="nav-label">${g.group}</div>${g.items.map(([id, label, ic]) =>
    navItem(id, label, ic, current, id === 'activity' && count ? `<span class="count">${count}</span>` : '')).join('')}</div>`).join('');
  const theme = Settings.get().theme;
  $('#sidebar-foot').innerHTML = `${navItem('settings', 'Settings', 'settings', current)}
    <div class="foot-row"><div class="theme-seg" role="group" aria-label="Theme">${['light', 'dark', 'system'].map((t) => `<button type="button" data-theme-set="${t}" aria-pressed="${theme === t}" aria-label="${t[0].toUpperCase() + t.slice(1)} theme" title="${t[0].toUpperCase() + t.slice(1)}">${icon(t === 'light' ? 'sun' : t === 'dark' ? 'moon' : 'monitor')}</button>`).join('')}</div>
      <button class="theme-cycle" type="button" data-theme-cycle data-tip="Theme: ${theme}" aria-label="Change theme, current ${theme}">${icon(resolvedTheme() === 'dark' ? 'moon' : 'sun')}</button></div>
    <button class="account-btn" type="button" id="account-btn" aria-haspopup="menu"><span class="avatar" aria-hidden="true">LW</span><span class="account-text"><strong>Local workspace</strong><span>Runs on this computer</span></span></button>`;
  renderScope();
}
function renderScope() {
  const s = scopeLabel(); const online = Store.state.online;
  $('#scope').innerHTML = `<span class="scope-label">Workspace</span><span class="scope-value" title="${esc(s.meta)}"><span class="dot ${online ? 'dot-ok' : 'dot-bad'}" aria-hidden="true"></span><span>${esc(s.name)}${s.meta ? ` <span class="muted small">${esc(s.meta)}</span>` : ''}</span></span>`;
}
function setSidebar(collapsed, persist = true) {
  if (collapsed) root.setAttribute('data-sidebar', 'collapsed'); else root.removeAttribute('data-sidebar');
  const b = $('#sb-toggle');
  b.setAttribute('aria-expanded', String(!collapsed)); b.setAttribute('aria-label', collapsed ? 'Expand sidebar' : 'Collapse sidebar');
  if (persist) { try { localStorage.setItem('gp.sidebar', collapsed ? 'collapsed' : 'expanded'); } catch { /* ignore */ } }
}
function accountMenu(anchor) {
  const st = Store.state;
  openMenu(anchor, `<div class="menu-head"><strong>Local workspace</strong><div class="muted small">No sign-in: this app runs on your computer and keeps its data in memory.</div></div>
    <div class="menu-sep"></div>
    <div class="menu-head" style="padding-top:0"><div class="small muted">Engine</div><div style="display:flex;align-items:center;gap:8px"><span class="dot ${st.online ? 'dot-ok' : 'dot-bad'}"></span>${st.online ? `Online${st.status ? `, version ${esc(st.status.version)}` : ''}` : 'Not reachable'}</div></div>
    <div class="menu-sep"></div>
    <a class="menu-item" href="#/settings" data-close>${icon('settings')}Settings</a>
    <a class="menu-item" href="#/" data-close>${icon('home')}Back to the landing page</a>`, { placement: 'above' });
}
let tipEl = null;
function hideTip() { if (tipEl) { tipEl.remove(); tipEl = null; } }
function showTip(el) {
  if (root.getAttribute('data-sidebar') !== 'collapsed' || window.innerWidth <= 820) return;
  hideTip();
  tipEl = document.createElement('div'); tipEl.className = 'rail-tip'; tipEl.textContent = el.dataset.tip;
  document.body.appendChild(tipEl);
  const r = el.getBoundingClientRect();
  tipEl.style.left = `${r.right + 10}px`; tipEl.style.top = `${r.top + r.height / 2 - tipEl.offsetHeight / 2}px`;
}
function bindShell() {
  document.addEventListener('mouseover', (e) => { const t = e.target.closest('.sidebar [data-tip]'); if (t) showTip(t); else hideTip(); });
  document.addEventListener('focusin', (e) => { const t = e.target.closest('.sidebar [data-tip]'); if (t) showTip(t); });
  document.addEventListener('focusout', hideTip);
  window.addEventListener('scroll', hideTip, true);
  $('#sb-toggle').addEventListener('click', () => setSidebar(root.getAttribute('data-sidebar') !== 'collapsed'));
  $('#mobile-menu').addEventListener('click', () => root.setAttribute('data-nav-open', 'true'));
  $('#sidebar-scrim').addEventListener('click', () => root.removeAttribute('data-nav-open'));
  document.addEventListener('keydown', (e) => { if (e.key === 'Escape') root.removeAttribute('data-nav-open'); });
  $('#sidebar-foot').addEventListener('click', (e) => {
    const t = e.target.closest('[data-theme-set]'); if (t) { Settings.set({ theme: t.dataset.themeSet }); return; }
    if (e.target.closest('[data-theme-cycle]')) { cycleTheme(); return; }
    const a = e.target.closest('#account-btn'); if (a) accountMenu(a);
  });
  $('#sidebar-nav').addEventListener('click', () => root.removeAttribute('data-nav-open'));
  Settings.subscribe(() => { renderSidebar(currentPage()); syncThemeButtons(); });
  Store.subscribe(() => { const cur = currentPage(); if ($('#app') && !$('#app').hidden) { renderSidebar(cur); } });
}
const syncThemeButtons = () => {
  const dark = resolvedTheme() === 'dark';
  document.querySelectorAll('.l-nav [data-theme-cycle] use').forEach((u) => u.setAttribute('href', dark ? '#i-moon' : '#i-sun'));
};

// ---------------------------------------------------------------- router
function parseRoute() {
  const parts = location.hash.replace(/^#\/?/, '').split('/').filter(Boolean);
  if (!parts.length || !(parts[0] in PAGES)) return { name: null, param: null };
  return { name: parts[0], param: parts[1] || null };
}
const currentPage = () => parseRoute().name;

function route() {
  closeMenu();
  root.removeAttribute('data-nav-open');
  if (cleanup) { try { cleanup(); } catch { /* ignore */ } cleanup = null; }
  const { name, param } = parseRoute();
  if (!name) { showLanding(); return; }
  $('#landing').hidden = true; $('#landing').replaceChildren(); $('#app').hidden = false;
  document.body.classList.add('in-app');
  renderSidebar(name);
  document.title = `${TITLES[name]} · GraphPulse-R`;
  $('#mobile-title').textContent = TITLES[name];
  const view = $('#view');
  view.innerHTML = '';
  view.className = `page${['settings', 'guide', 'glossary', 'verification'].includes(name) ? ' page-narrow' : ''}${name === 'pune' ? ' page-full' : ''}`;
  cleanup = PAGES[name](view, { param }) || null;
  Store.refresh();
  window.scrollTo(0, 0);
  view.focus({ preventScroll: true });
}

// ---------------------------------------------------------------- landing
function showLanding() {
  $('#app').hidden = true; $('#landing').hidden = false;
  if (!$('#landing').firstElementChild) { $('#landing').appendChild($('#landing-tpl').content.cloneNode(true)); bindLanding(); }
  document.body.classList.remove('in-app');
  document.title = 'GraphPulse-R: routes that stay right when roads change';
  window.scrollTo(0, 0);
  setTimeout(() => $('#landing').classList.add('is-ready'), 50);
  syncThemeButtons();
  const io = new IntersectionObserver((entries) => entries.forEach((en) => { if (en.isIntersecting) { en.target.classList.add('in'); io.unobserve(en.target); } }), { threshold: 0.12 });
  document.querySelectorAll('#landing .reveal').forEach((el) => io.observe(el));
  cleanup = () => { io.disconnect(); if (landingView) { landingView.destroy(); landingView = null; } };
  setupLiveFragment();
}
function setupLiveFragment() {
  const canvas = $('#landing-canvas'); const msg = $('#landing-stage-msg');
  const paint = () => {
    const g = Store.state.graph;
    if (!g) { msg.hidden = false; msg.textContent = Store.state.error ? 'Start the engine with python run_ui.py to see it running here.' : 'Connecting to the engine…'; return; }
    msg.hidden = true;
    if (!landingView) landingView = new GraphView(canvas, { interactive: false });
    landingView.setOptions({ showWeights: false, showTree: true });
    landingView.setData(g, { fit: true });
  };
  const un = Store.subscribe(() => { if (!$('#landing').hidden) paint(); });
  paint();
  const prev = cleanup;
  cleanup = () => { un(); if (prev) prev(); };
}
function paintFragments() {
  const st = Store.state; const g = st.graph; const lu = g && g.last_update; const t = st.tour;
  const d = $('#frag-decision'), tr = $('#frag-tour'), ch = $('#frag-chart');
  if (!d) return;
  d.innerHTML = `<h3>Last decision</h3>${lu ? `<div>${strategyPill(lu.strategy)}</div><p class="muted">${esc(strategyText(lu.strategy))}</p><p>${fmt(lu.work)} operations; recomputing would have used ${fmt(lu.baseline_work)}.</p>`
    : '<p class="muted">No update yet. Run the sample scenario to see which decision the engine takes for each closure.</p>'}`;
  tr.innerHTML = `<h3>Delivery tour</h3>${t && t.terminals_set ? `<p style="font-size:24px">${t.feasible ? fmtCost(t.tour_cost) : DASH}<span class="muted"> total cost</span></p>
      <div class="path-line">${t.order.length ? `<span class="chip chip-depot">${t.depot}</span>${t.order.map((v) => `<span class="sep">${icon('chevron')}</span><span class="chip">${v}</span>`).join('')}<span class="sep">${icon('chevron')}</span><span class="chip chip-depot">${t.depot}</span>` : ''}</div>
      ${t.last_route ? `<div>${routePill(t.last_route.route_action)}</div>` : ''}`
    : '<p class="muted">No stops yet. The sample scenario sets a depot and four stops and solves the tour exactly.</p>'}`;
  const logs = [...(st.logs || [])].reverse(); let a = 0, b = 0; const on = [], base = [];
  logs.forEach((l) => { a += l.work; b += l.baseline_work; on.push(a); base.push(b); });
  ch.innerHTML = `<h3>Operations used</h3>${lineChart({ series: [{ name: 'GraphPulse-R', values: on, cls: 'series-main' }, { name: 'Recompute baseline', values: base, cls: 'series-ref' }], height: 150 })}${logs.length ? '' : '<p class="muted">The chart fills as updates are applied.</p>'}`;
}
function bindLanding() {
  const run = $('#landing-run');
  if (run) run.addEventListener('click', async () => {
    await withBusy(run, async () => { try { await runSampleScenario(12); toast('Sample scenario finished'); } catch (e) { toast(e.message, 'error'); } });
  });
  document.querySelectorAll('[data-scroll]').forEach((a) => a.addEventListener('click', (e) => {
    e.preventDefault();
    const el = document.getElementById(a.dataset.scroll);
    if (el) window.scrollTo({ top: el.getBoundingClientRect().top + window.scrollY - 56, behavior: root.getAttribute('data-motion') === 'reduced' ? 'auto' : 'smooth' });
  }));
  document.querySelectorAll('.l-nav [data-theme-cycle]').forEach((b) => b.addEventListener('click', () => { cycleTheme(); syncThemeButtons(); }));
  const ver = () => { const v = $('#landing-version'); if (v && Store.state.status) v.textContent = `Version ${Store.state.status.version}`; paintFragments(); };
  ver();
  const un = Store.subscribe(ver);
  const prevCleanup = cleanup;
  cleanup = () => { un(); if (prevCleanup) prevCleanup(); };
}

// ---------------------------------------------------------------- boot
async function boot() {
  installSprite();
  initTheme();
  bindShell();
  const reduced = root.getAttribute('data-motion') === 'reduced' || window.matchMedia('(prefers-reduced-motion: reduce)').matches;
  const minLoader = new Promise((r) => setTimeout(r, reduced ? 250 : 1300));
  const fetchDone = Store.refresh();
  await Promise.race([Promise.all([minLoader, fetchDone]), new Promise((r) => setTimeout(r, 4000))]);
  window.addEventListener('hashchange', route);
  route();
  const loader = $('#loader');
  loader.classList.add('done');
  setTimeout(() => { loader.hidden = true; }, 450);
}
boot();
