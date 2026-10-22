// Small SVG charts drawn from data: straight-segment lines with a real y-scale, and thin bar lists.
import { esc } from './ui.js';

function niceStep(max, target = 4) {
  if (max <= 0) return 1;
  const raw = max / target;
  const mag = 10 ** Math.floor(Math.log10(raw));
  const norm = raw / mag;
  const step = norm <= 1 ? 1 : norm <= 2 ? 2 : norm <= 5 ? 5 : 10;
  return step * mag;
}
const abbr = (v) => (v >= 1e6 ? `${+(v / 1e6).toFixed(1)}M` : v >= 1e3 ? `${+(v / 1e3).toFixed(1)}k` : String(v));

/**
 * series: [{name, values:[...], cls}] (same length). x labels are update indices (1-based).
 * Draws the zero line even when there is no data (an empty chart is drawn, not replaced by a picture).
 */
export function lineChart({ series, height = 220, xName = 'Update' }) {
  const W = 640, H = height, L = 52, R = 12, T = 10, B = 28;
  const n = Math.max(0, ...series.map((s) => s.values.length));
  const maxV = Math.max(0, ...series.flatMap((s) => s.values));
  const step = niceStep(maxV);
  const yMax = Math.max(step, Math.ceil(maxV / step) * step);
  const x = (i) => L + (n <= 1 ? 0 : (i / (n - 1)) * (W - L - R));
  const y = (v) => T + (1 - v / yMax) * (H - T - B);
  const ticks = []; for (let t = 0; t <= yMax + 1e-9; t += step) ticks.push(t);
  let g = ticks.map((t) => `<line class="${t === 0 ? 'axis' : 'grid'}" x1="${L}" x2="${W - R}" y1="${y(t)}" y2="${y(t)}"/><text x="${L - 8}" y="${y(t) + 4}" text-anchor="end">${abbr(t)}</text>`).join('');
  const xt = n <= 1 ? [0] : [0, Math.round((n - 1) / 3), Math.round(((n - 1) * 2) / 3), n - 1].filter((v, i, a) => a.indexOf(v) === i);
  if (n > 0) g += xt.map((i) => `<text x="${x(i)}" y="${H - 8}" text-anchor="${i === 0 ? 'start' : i === n - 1 ? 'end' : 'middle'}">${i + 1}</text>`).join('');
  const lines = series.map((s) => {
    if (s.values.length === 0) return '';
    const pts = s.values.map((v, i) => `${x(i).toFixed(1)},${y(v).toFixed(1)}`).join(' ');
    return s.values.length === 1
      ? `<circle cx="${x(0)}" cy="${y(s.values[0])}" r="3" fill="${s.cls === 'series-main' ? 'var(--data)' : 'var(--muted)'}"/>`
      : `<polyline class="${s.cls}" points="${pts}"/>`;
  }).join('');
  const legend = series.length > 1
    ? `<div class="chart-legend">${series.map((s) => `<span class="legend-item"><span class="swatch-line" style="background:${s.cls === 'series-main' ? 'var(--data)' : 'var(--muted)'}"></span>${esc(s.name)}</span>`).join('')}</div>` : '';
  const label = series.map((s) => esc(s.name)).join(' and ');
  return `<div>${legend}<svg class="chart" viewBox="0 0 ${W} ${H}" role="img" aria-label="${label} per ${esc(xName.toLowerCase())}, cumulative operations">${g}${lines}</svg></div>`;
}

/** Ranked list with thin proportional bars; the top item is in ink, the rest grey. */
export function barList(rows, { unit = '' } = {}) {
  const max = Math.max(1, ...rows.map((r) => r.value));
  const top = rows.reduce((a, r, i) => (r.value > rows[a].value ? i : a), 0);
  return `<div>${rows.map((r, i) => `<div class="bar-row ${i === top && r.value > 0 ? 'is-top' : ''}"><span>${esc(r.label)}</span><span class="v">${r.value.toLocaleString('en-US')}${unit ? ` <span class="muted small">${esc(unit)}</span>` : ''}</span>
    <div class="bar" role="presentation"><span style="width:${(r.value / max) * 100}%"></span></div></div>`).join('')}</div>`;
}
