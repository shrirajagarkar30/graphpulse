// Shared UI helpers: escaping, formatting, pills, toasts, menus, dialogs, drawers, busy buttons.
import { icon } from './icons.js';

export const esc = (s) => String(s ?? '').replace(/[&<>"']/g, (c) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' }[c]));
export const DASH = '<span class="dash" aria-label="not available">–</span>';

export function fmt(n, digits = 0) {
  if (n === null || n === undefined || Number.isNaN(n)) return DASH;
  return Number(n).toLocaleString('en-US', { minimumFractionDigits: digits, maximumFractionDigits: digits });
}
export const fmtCost = (x) => (x === null || x === undefined ? DASH : fmt(x));

const STRATEGIES = {
  cert: { label: 'Certificate', cls: 'pill', text: 'The road was on no shortest path, so nothing changed. One operation.' },
  alt: { label: 'Alternative support', cls: 'pill', text: 'The road was on a shortest path, but its destination has another equally short road. Only counters and a pointer changed.' },
  repair: { label: 'Repair', cls: 'pill pill-data', text: 'Distances changed for some vertices; only those were recomputed, within the work budget.' },
  fallback: { label: 'Rebuild after abort', cls: 'pill pill-warning', text: 'Repair would have cost more than the budget, so it was discarded for free and the tree was rebuilt.' },
};
const ROUTE = {
  kept: { label: 'Tour kept', cls: 'pill pill-positive', text: 'No road the current tour uses got worse, so it is still optimal and the exact solver was skipped.' },
  kept_eps: { label: 'Tour kept (tolerance)', cls: 'pill pill-positive', text: 'The tour stayed within the allowed tolerance of the stored lower bound.' },
  resolved: { label: 'Tour re-solved', cls: 'pill pill-data', text: 'A road the tour uses got worse, so the exact solver ran again.' },
  infeasible: { label: 'No feasible tour', cls: 'pill pill-negative', text: 'Some stop can no longer be reached, so no tour exists. Distances only grow, so it stays infeasible.' },
};
export const strategyPill = (s) => { const m = STRATEGIES[s] || { label: s, cls: 'pill' }; return `<span class="${m.cls}">${esc(m.label)}</span>`; };
export const routePill = (s) => { const m = ROUTE[s] || { label: s, cls: 'pill' }; return `<span class="${m.cls}">${esc(m.label)}</span>`; };
export const strategyText = (s) => (STRATEGIES[s] || {}).text || '';
export const routeText = (s) => (ROUTE[s] || {}).text || '';
export const strategyLabel = (s) => (STRATEGIES[s] || { label: s }).label;

// ---- toasts --------------------------------------------------------------------------------
export function toast(message, kind = 'info', ms = 3200) {
  const host = document.getElementById('toasts');
  if (!host) return;
  const el = document.createElement('div');
  el.className = `toast ${kind === 'error' ? 'toast-error' : ''}`;
  el.textContent = message;
  host.appendChild(el);
  setTimeout(() => { el.style.opacity = '0'; el.style.transition = 'opacity 200ms'; setTimeout(() => el.remove(), 220); }, ms);
}

// ---- busy button ----------------------------------------------------------------------------
export async function withBusy(btn, fn) {
  if (!btn) return fn();
  const html = btn.innerHTML;
  btn.disabled = true;
  btn.innerHTML = `<span class="spinner" aria-hidden="true"></span><span>${btn.dataset.busy || 'Working'}</span>`;
  try { return await fn(); } finally { btn.disabled = false; btn.innerHTML = html; }
}

// ---- popover menu -----------------------------------------------------------------------------
let openMenuEl = null;
export function closeMenu() { if (openMenuEl) { openMenuEl.remove(); openMenuEl = null; } }
export function openMenu(anchor, html, { align = 'start', placement = 'below' } = {}) {
  closeMenu();
  const el = document.createElement('div');
  el.className = 'menu'; el.setAttribute('role', 'menu'); el.innerHTML = html;
  document.body.appendChild(el);
  const r = anchor.getBoundingClientRect();
  const mw = el.offsetWidth, mh = el.offsetHeight;
  let left = align === 'end' ? r.right - mw : r.left;
  left = Math.max(8, Math.min(left, window.innerWidth - mw - 8));
  let top = placement === 'above' ? r.top - mh - 8 : r.bottom + 8;
  if (top + mh > window.innerHeight - 8) top = Math.max(8, r.top - mh - 8);
  el.style.left = `${left}px`; el.style.top = `${top}px`;
  openMenuEl = el;
  const off = (e) => { if (!el.contains(e.target) && !anchor.contains(e.target)) { closeMenu(); cleanup(); } };
  const key = (e) => { if (e.key === 'Escape') { closeMenu(); cleanup(); anchor.focus(); } };
  const cleanup = () => { document.removeEventListener('mousedown', off); document.removeEventListener('keydown', key); };
  setTimeout(() => { document.addEventListener('mousedown', off); document.addEventListener('keydown', key); }, 0);
  el.addEventListener('click', (e) => { if (e.target.closest('[data-close]')) { closeMenu(); cleanup(); } });
  return el;
}

// ---- confirm dialog -----------------------------------------------------------------------------
export function confirmDialog({ title, body, confirm = 'Confirm', danger = false }) {
  return new Promise((resolve) => {
    const scrim = document.createElement('div');
    scrim.className = 'dialog-scrim';
    scrim.innerHTML = `<div class="dialog" role="alertdialog" aria-modal="true" aria-labelledby="dlg-title">
      <div class="dialog-head"><h2 class="panel-title" id="dlg-title">${esc(title)}</h2>
        <button class="btn btn-ghost btn-icon btn-sm" type="button" data-cancel aria-label="Close">${icon('x')}</button></div>
      <div class="dialog-body"><p>${esc(body)}</p></div>
      <div class="dialog-foot"><button class="btn" type="button" data-cancel>Cancel</button>
        <button class="btn ${danger ? 'btn-danger' : 'btn-primary'}" type="button" data-ok>${esc(confirm)}</button></div></div>`;
    const prev = document.activeElement;
    const done = (v) => { document.removeEventListener('keydown', key); scrim.remove(); if (prev && prev.focus) prev.focus(); resolve(v); };
    const key = (e) => { if (e.key === 'Escape') done(false); };
    scrim.addEventListener('click', (e) => { if (e.target === scrim || e.target.closest('[data-cancel]')) done(false); else if (e.target.closest('[data-ok]')) done(true); });
    document.addEventListener('keydown', key);
    document.body.appendChild(scrim);
    scrim.querySelector('[data-ok]').focus();
  });
}

// ---- drawer ------------------------------------------------------------------------------------
export function openDrawer(title, html) {
  const scrim = document.createElement('div'); scrim.className = 'drawer-scrim';
  const d = document.createElement('aside'); d.className = 'drawer'; d.setAttribute('role', 'dialog'); d.setAttribute('aria-label', title);
  d.innerHTML = `<div class="drawer-head"><h2 class="panel-title">${esc(title)}</h2>
    <button class="btn btn-ghost btn-icon btn-sm" type="button" aria-label="Close">${icon('x')}</button></div><div class="drawer-body">${html}</div>`;
  const prev = document.activeElement;
  const close = () => { document.removeEventListener('keydown', key); scrim.remove(); d.remove(); if (prev && prev.focus) prev.focus(); };
  const key = (e) => { if (e.key === 'Escape') close(); };
  scrim.addEventListener('click', close);
  d.querySelector('button').addEventListener('click', close);
  document.addEventListener('keydown', key);
  document.body.append(scrim, d);
  d.querySelector('button').focus();
  return close;
}

export function emptyState(title, text, actionHtml = '') {
  return `<div class="empty"><div><strong>${esc(title)}</strong><p>${esc(text)}</p></div>${actionHtml}</div>`;
}
export function errorNotice(message, retry = true) {
  return `<div class="notice notice-error" role="alert">${icon('alert')}<span>${esc(message)}</span>${retry ? '<button class="btn btn-sm" type="button" data-retry>Retry</button>' : ''}</div>`;
}
export const skeletonKpis = (n) => `<div class="kpis" style="--cols:${n}">${Array.from({ length: n }, () => '<div class="kpi"><div class="skeleton skeleton-line skel-w70"></div><div class="skeleton skeleton-kpi" style="margin-top:10px"></div></div>').join('')}</div>`;

export function downloadFile(name, text, type = 'text/plain') {
  const url = URL.createObjectURL(new Blob([text], { type }));
  const a = document.createElement('a'); a.href = url; a.download = name; document.body.appendChild(a); a.click(); a.remove();
  setTimeout(() => URL.revokeObjectURL(url), 1000);
}
