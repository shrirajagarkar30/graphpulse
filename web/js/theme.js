// Persistent user settings (theme, motion, density, canvas defaults) and theme application.
const KEY = 'gp.settings';
const DEFAULTS = { theme: 'system', motion: 'system', density: 'comfortable', showWeights: true, showTree: false, autoRefresh: false };
const listeners = new Set();
let cache = null;

function read() {
  try { return { ...DEFAULTS, ...(JSON.parse(localStorage.getItem(KEY) || '{}')) }; } catch { return { ...DEFAULTS }; }
}

export const Settings = {
  get() { if (!cache) cache = read(); return cache; },
  set(patch) {
    cache = { ...this.get(), ...patch };
    try { localStorage.setItem(KEY, JSON.stringify(cache)); } catch { /* storage unavailable: keep in memory */ }
    applyAll();
    listeners.forEach((fn) => fn(cache));
  },
  subscribe(fn) { listeners.add(fn); return () => listeners.delete(fn); },
};

export function resolvedTheme() {
  const t = Settings.get().theme;
  if (t === 'light' || t === 'dark') return t;
  return window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light';
}

export function applyAll() {
  const d = document.documentElement;
  d.setAttribute('data-theme', resolvedTheme());
  const s = Settings.get();
  if (s.motion === 'reduced') d.setAttribute('data-motion', 'reduced'); else d.removeAttribute('data-motion');
  d.setAttribute('data-density', s.density);
  window.dispatchEvent(new CustomEvent('gp:theme'));
}

export function cycleTheme() {
  const order = ['light', 'dark', 'system'];
  const next = order[(order.indexOf(Settings.get().theme) + 1) % order.length];
  Settings.set({ theme: next });
  return next;
}

export function initTheme() {
  applyAll();
  window.matchMedia('(prefers-color-scheme: dark)').addEventListener('change', () => {
    if (Settings.get().theme === 'system') applyAll();
  });
}

/** Colours for canvas drawing, read from the active theme's CSS variables. */
export function canvasPalette() {
  const cs = getComputedStyle(document.documentElement);
  const g = (n) => cs.getPropertyValue(n).trim();
  return {
    bg: g('--cv-bg'), grid: g('--cv-grid'), edge: g('--cv-edge'), tree: g('--cv-edge-tree'), path: g('--cv-path'),
    node: g('--cv-node'), nodeInk: g('--cv-node-ink'), nodeLine: g('--cv-node-line'), unreachable: g('--cv-unreachable'),
    source: g('--cv-source'), target: g('--cv-target'), affected: g('--cv-affected'), label: g('--cv-label'),
    tipBg: g('--cv-tip-bg'), tipInk: g('--cv-tip-ink'), tipMuted: g('--cv-tip-muted'), font: g('--font'),
    negative: g('--negative'),
  };
}
