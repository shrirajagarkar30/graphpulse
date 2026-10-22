// Theme-aware canvas renderer for the road network. Draws on demand (no animation loop),
// handles device-pixel-ratio, pan / zoom / pinch via pointer events, and optional tour overlay.
import { canvasPalette } from './theme.js';

export class GraphView {
  constructor(canvas, { interactive = true, onNode = null, onEdge = null } = {}) {
    this.canvas = canvas;
    this.ctx = canvas.getContext('2d');
    this.interactive = interactive;
    this.onNode = onNode; this.onEdge = onEdge;
    this.nodes = []; this.edges = []; this.nodeById = new Map();
    this.path = []; this.pathEdges = new Set(); this.lastUpdate = null;
    this.overlay = null;                       // { terminals: [vertex ids], order: [vertex ids] }
    this.showWeights = true; this.showTree = false;
    this.zoom = 1; this.panX = 0; this.panY = 0; this.cx = 400; this.cy = 250;
    this.hover = null; this._raf = 0; this.pal = canvasPalette();
    this.pointers = new Map(); this._moved = 0; this._pinch = 0;
    this._ro = new ResizeObserver(() => this._resize());
    this._ro.observe(canvas.parentElement);
    this._onTheme = () => { this.pal = canvasPalette(); this.schedule(); };
    window.addEventListener('gp:theme', this._onTheme);
    if (interactive) this._bind();
    this._resize();
  }

  destroy() { this._ro.disconnect(); window.removeEventListener('gp:theme', this._onTheme); cancelAnimationFrame(this._raf); }

  setData(data, { fit = false } = {}) {
    this.nodes = data.nodes || []; this.edges = data.edges || [];
    this.nodeById = new Map(this.nodes.map((n) => [n.id, n]));
    this.path = data.path || [];
    this.pathEdges = new Set(this.path.slice(1).map((v, i) => `${this.path[i]}>${v}`));
    this.lastUpdate = data.last_update || null;
    if (fit || !this._fitted) this.fit(); else this.schedule();
  }
  setOverlay(o) { this.overlay = o; this.schedule(); }
  setOptions({ showWeights, showTree }) {
    if (showWeights !== undefined) this.showWeights = showWeights;
    if (showTree !== undefined) this.showTree = showTree;
    this.schedule();
  }

  fit() {
    if (!this.nodes.length) { this.schedule(); return; }
    const xs = this.nodes.map((n) => n.x), ys = this.nodes.map((n) => n.y);
    const minX = Math.min(...xs), maxX = Math.max(...xs), minY = Math.min(...ys), maxY = Math.max(...ys);
    this.cx = (minX + maxX) / 2; this.cy = (minY + maxY) / 2;
    const w = this.w || 800, h = this.h || 500, m = 48;
    this.zoom = Math.min((w - 2 * m) / Math.max(maxX - minX, 40), (h - 2 * m) / Math.max(maxY - minY, 40), 1.8);
    this.panX = 0; this.panY = 0; this._fitted = true;
    this.schedule();
  }
  zoomBy(f) { this.zoom = Math.max(0.2, Math.min(4, this.zoom * f)); this.schedule(); }

  _resize() {
    const p = this.canvas.parentElement;
    const dpr = window.devicePixelRatio || 1;
    this.w = p.clientWidth; this.h = p.clientHeight;
    this.canvas.width = Math.max(1, Math.round(this.w * dpr)); this.canvas.height = Math.max(1, Math.round(this.h * dpr));
    this.ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
    if (this.nodes.length && !this._fitted) this.fit(); else this.schedule();
  }
  schedule() { if (!this._raf) this._raf = requestAnimationFrame(() => { this._raf = 0; this.render(); }); }

  _toScreen(x, y) { return { x: (x - this.cx) * this.zoom + this.w / 2 + this.panX, y: (y - this.cy) * this.zoom + this.h / 2 + this.panY }; }
  _fromScreen(x, y) { return { x: (x - this.w / 2 - this.panX) / this.zoom + this.cx, y: (y - this.h / 2 - this.panY) / this.zoom + this.cy }; }

  _bind() {
    const c = this.canvas;
    c.addEventListener('pointerdown', (e) => {
      c.setPointerCapture(e.pointerId);
      this.pointers.set(e.pointerId, { x: e.clientX, y: e.clientY });
      this._moved = 0;
      if (this.pointers.size === 2) this._pinch = this._pinchDist();
    });
    c.addEventListener('pointermove', (e) => {
      const rect = c.getBoundingClientRect();
      const prev = this.pointers.get(e.pointerId);
      if (prev) {
        this.pointers.set(e.pointerId, { x: e.clientX, y: e.clientY });
        if (this.pointers.size === 1) { this.panX += e.clientX - prev.x; this.panY += e.clientY - prev.y; this._moved += Math.abs(e.clientX - prev.x) + Math.abs(e.clientY - prev.y); this.schedule(); }
        else if (this.pointers.size === 2) { const d = this._pinchDist(); if (this._pinch) this.zoomBy(d / this._pinch); this._pinch = d; this._moved += 10; }
      } else {
        this._setHover(this._nodeAt(e.clientX - rect.left, e.clientY - rect.top));
      }
    });
    const up = (e) => {
      const rect = c.getBoundingClientRect();
      const wasClick = this._moved < 6 && this.pointers.size === 1;
      this.pointers.delete(e.pointerId);
      if (wasClick) this._click(e.clientX - rect.left, e.clientY - rect.top);
    };
    c.addEventListener('pointerup', up);
    c.addEventListener('pointercancel', (e) => this.pointers.delete(e.pointerId));
    c.addEventListener('pointerleave', () => this._setHover(null));
    // Plain scrolling keeps scrolling the page; Ctrl (or Cmd) + wheel zooms the map.
    c.addEventListener('wheel', (e) => { if (!(e.ctrlKey || e.metaKey)) return; e.preventDefault(); this.zoomBy(e.deltaY > 0 ? 0.9 : 1.1); }, { passive: false });
    c.tabIndex = 0;
    c.addEventListener('keydown', (e) => {
      if (e.key === '+' || e.key === '=') this.zoomBy(1.2); else if (e.key === '-') this.zoomBy(1 / 1.2); else if (e.key === '0') this.fit();
      else if (e.key === 'ArrowLeft') { this.panX += 30; this.schedule(); } else if (e.key === 'ArrowRight') { this.panX -= 30; this.schedule(); }
      else if (e.key === 'ArrowUp') { this.panY += 30; this.schedule(); } else if (e.key === 'ArrowDown') { this.panY -= 30; this.schedule(); }
    });
  }
  _pinchDist() { const p = [...this.pointers.values()]; return p.length < 2 ? 0 : Math.hypot(p[0].x - p[1].x, p[0].y - p[1].y); }
  _radius() { return Math.max(9, Math.min(17, 15 * this.zoom)); }
  _nodeAt(sx, sy) {
    const r = this._radius() + 4;
    for (const n of this.nodes) { const p = this._toScreen(n.x, n.y); if (Math.hypot(p.x - sx, p.y - sy) <= r) return n; }
    return null;
  }
  _setHover(n) { if (n !== this.hover) { this.hover = n; this.canvas.style.cursor = n ? 'pointer' : 'grab'; this.schedule(); } }
  _click(sx, sy) {
    const n = this._nodeAt(sx, sy);
    if (n) { if (this.onNode) this.onNode(n); return; }
    let best = null, bd = 9;
    for (const e of this.edges) {
      const a = this.nodeById.get(e.u), b = this.nodeById.get(e.v);
      if (!a || !b) continue;
      const pa = this._toScreen(a.x, a.y), pb = this._toScreen(b.x, b.y);
      const d = this._distSeg(sx, sy, pa, pb);
      if (d < bd) { bd = d; best = e; }
    }
    if (best && this.onEdge) this.onEdge(best);
  }
  _distSeg(px, py, a, b) {
    const l2 = (a.x - b.x) ** 2 + (a.y - b.y) ** 2;
    if (!l2) return Math.hypot(px - a.x, py - a.y);
    const t = Math.max(0, Math.min(1, ((px - a.x) * (b.x - a.x) + (py - a.y) * (b.y - a.y)) / l2));
    return Math.hypot(px - (a.x + t * (b.x - a.x)), py - (a.y + t * (b.y - a.y)));
  }

  render() {
    const { ctx, w, h, pal } = this;
    if (!w || !h) return;
    ctx.clearRect(0, 0, w, h);
    ctx.fillStyle = pal.bg; ctx.fillRect(0, 0, w, h);
    this._grid();
    this._edges();
    this._nodes();
    if (this.overlay) this._tour();
    if (this.hover) this._tooltip(this.hover);
  }
  _grid() {
    const { ctx, w, h, pal } = this;
    const s = Math.max(24, 40 * this.zoom);
    ctx.strokeStyle = pal.grid; ctx.lineWidth = 1; ctx.beginPath();
    for (let x = ((this.panX + w / 2) % s + s) % s; x < w; x += s) { ctx.moveTo(x, 0); ctx.lineTo(x, h); }
    for (let y = ((this.panY + h / 2) % s + s) % s; y < h; y += s) { ctx.moveTo(0, y); ctx.lineTo(w, y); }
    ctx.stroke();
  }
  _edges() {
    const { ctx, pal } = this;
    const small = this.zoom < 0.55;
    for (const e of this.edges) {
      const a = this.nodeById.get(e.u), b = this.nodeById.get(e.v);
      if (!a || !b) continue;
      const isPath = this.pathEdges.has(`${e.u}>${e.v}`);
      if (this.showTree && !e.is_tree && !isPath && !e.is_last_updated) continue;
      const [pa, pb] = this._lane(a, b);
      ctx.beginPath(); ctx.moveTo(pa.x, pa.y); ctx.lineTo(pb.x, pb.y);
      ctx.lineCap = 'round';
      if (isPath) { ctx.strokeStyle = pal.path; ctx.lineWidth = Math.max(3, 4 * this.zoom); }
      else if (e.is_tree) { ctx.strokeStyle = pal.tree; ctx.lineWidth = Math.max(1.8, 2.4 * this.zoom); }
      else { ctx.strokeStyle = pal.edge; ctx.lineWidth = Math.max(1, 1.2 * this.zoom); }
      ctx.stroke();
      if (!small) this._arrow(pa, pb, isPath ? pal.path : e.is_tree ? pal.tree : pal.edge);
      if (this.showWeights && !small && this.zoom > 0.7 && !e.is_last_updated) this._weight((pa.x + pb.x) / 2, (pa.y + pb.y) / 2, e.w, isPath || e.is_tree);
    }
    const lu = this.lastUpdate;
    if (lu) {
      const a = this.nodeById.get(lu.u), b = this.nodeById.get(lu.v);
      if (a && b) {
        const [pa, pb] = this._lane(a, b);
        ctx.save();
        if (lu.kind === 'delete') {
          ctx.setLineDash([6, 5]); ctx.strokeStyle = pal.negative; ctx.lineWidth = 2.5;
          ctx.beginPath(); ctx.moveTo(pa.x, pa.y); ctx.lineTo(pb.x, pb.y); ctx.stroke(); ctx.setLineDash([]);
          this._tag((pa.x + pb.x) / 2, (pa.y + pb.y) / 2 - 12, 'Closed', pal.negative);
        } else {
          ctx.strokeStyle = pal.affected; ctx.lineWidth = 3;
          ctx.beginPath(); ctx.moveTo(pa.x, pa.y); ctx.lineTo(pb.x, pb.y); ctx.stroke();
          this._tag((pa.x + pb.x) / 2, (pa.y + pb.y) / 2 - 12, `${lu.old_w} to ${lu.new_w}`, pal.affected);
        }
        ctx.restore();
      }
    }
  }
  /** Screen points for a directed road, shifted sideways so the two directions of a road do not overlap. */
  _lane(a, b) {
    const pa = this._toScreen(a.x, a.y), pb = this._toScreen(b.x, b.y);
    const dx = pb.x - pa.x, dy = pb.y - pa.y, len = Math.hypot(dx, dy) || 1;
    const off = Math.min(6, 2.5 + this.zoom * 2.5), nx = (-dy / len) * off, ny = (dx / len) * off;
    return [{ x: pa.x + nx, y: pa.y + ny }, { x: pb.x + nx, y: pb.y + ny }];
  }
  _arrow(from, to, color) {
    const { ctx } = this;
    const ang = Math.atan2(to.y - from.y, to.x - from.x), r = this._radius() + 2, hl = Math.max(6, 7 * this.zoom);
    const ex = to.x - r * Math.cos(ang), ey = to.y - r * Math.sin(ang);
    ctx.fillStyle = color; ctx.beginPath(); ctx.moveTo(ex, ey);
    ctx.lineTo(ex - hl * Math.cos(ang - 0.5), ey - hl * Math.sin(ang - 0.5));
    ctx.lineTo(ex - hl * Math.cos(ang + 0.5), ey - hl * Math.sin(ang + 0.5)); ctx.closePath(); ctx.fill();
  }
  _weight(x, y, wt, emph) {
    const { ctx, pal } = this;
    ctx.font = `500 11px ${pal.font}`;
    const t = String(wt), tw = ctx.measureText(t).width + 8;
    ctx.fillStyle = pal.bg; ctx.fillRect(x - tw / 2, y - 8, tw, 16);
    ctx.fillStyle = emph ? pal.path : pal.label; ctx.textAlign = 'center'; ctx.textBaseline = 'middle'; ctx.fillText(t, x, y + 0.5);
  }
  _tag(x, y, text, color) {
    const { ctx, pal } = this;
    ctx.font = `600 11px ${pal.font}`;
    const tw = ctx.measureText(text).width + 12;
    ctx.fillStyle = color; ctx.beginPath(); ctx.roundRect(x - tw / 2, y - 10, tw, 20, 4); ctx.fill();
    ctx.fillStyle = '#ffffff'; ctx.textAlign = 'center'; ctx.textBaseline = 'middle'; ctx.fillText(text, x, y + 0.5);
  }
  _nodes() {
    const { ctx, pal } = this;
    const r = this._radius();
    const term = this.overlay ? new Set(this.overlay.terminals) : null;
    for (const n of this.nodes) {
      const p = this._toScreen(n.x, n.y);
      if (p.x < -30 || p.y < -30 || p.x > this.w + 30 || p.y > this.h + 30) continue;
      const inPath = this.path.includes(n.id);
      let fill = n.reachable ? pal.node : pal.unreachable, line = n.reachable ? pal.nodeLine : pal.edge, ink = pal.nodeInk, lw = 1.6;
      if (n.is_source) { fill = pal.source; line = pal.source; ink = '#ffffff'; }
      else if (n.is_target) { fill = pal.target; line = pal.target; ink = '#ffffff'; }
      else if (n.is_affected) { fill = pal.affected; line = pal.affected; ink = '#ffffff'; }
      else if (inPath) { fill = pal.path; line = pal.path; ink = '#ffffff'; }
      if (term && term.has(n.id)) lw = 3;
      ctx.beginPath(); ctx.arc(p.x, p.y, r, 0, Math.PI * 2); ctx.fillStyle = fill; ctx.fill();
      ctx.strokeStyle = term && term.has(n.id) ? pal.nodeInk : line; ctx.lineWidth = lw; ctx.stroke();
      if (r >= 10) {
        ctx.fillStyle = ink; ctx.font = `600 ${Math.max(9, Math.min(12, 10.5 * this.zoom))}px ${pal.font}`;
        ctx.textAlign = 'center'; ctx.textBaseline = 'middle';
        ctx.fillText(n.is_source ? 'S' : n.is_target ? 'T' : String(n.id), p.x, p.y + 0.5);
      }
    }
  }
  _tour() {
    const { ctx, pal } = this;
    const { terminals, order } = this.overlay;
    if (!terminals || !terminals.length) return;
    const seq = order && order.length ? [terminals[0], ...order, terminals[0]] : null;
    ctx.save(); ctx.setLineDash([10, 6]); ctx.strokeStyle = pal.nodeInk; ctx.lineWidth = 2; ctx.lineCap = 'round';
    if (seq) {
      for (let i = 0; i < seq.length - 1; i++) {
        const a = this.nodeById.get(seq[i]), b = this.nodeById.get(seq[i + 1]);
        if (!a || !b) continue;
        const pa = this._toScreen(a.x, a.y), pb = this._toScreen(b.x, b.y);
        ctx.beginPath(); ctx.moveTo(pa.x, pa.y); ctx.lineTo(pb.x, pb.y); ctx.stroke();
      }
    }
    ctx.restore();
    ctx.font = `600 11px ${pal.font}`; ctx.textAlign = 'center'; ctx.textBaseline = 'middle';
    terminals.forEach((id, i) => {
      const n = this.nodeById.get(id); if (!n) return;
      const p = this._toScreen(n.x, n.y), r = this._radius();
      const label = i === 0 ? 'Depot' : seq ? String(order.indexOf(id) + 1) : '';
      if (!label) return;
      const tw = ctx.measureText(label).width + 10;
      ctx.fillStyle = pal.nodeInk; ctx.beginPath(); ctx.roundRect(p.x - tw / 2, p.y - r - 22, tw, 18, 4); ctx.fill();
      ctx.fillStyle = pal.bg; ctx.fillText(label, p.x, p.y - r - 12.5);
    });
  }
  _tooltip(n) {
    const { ctx, pal } = this;
    const p = this._toScreen(n.x, n.y);
    const rows = [['Vertex', `${n.id}${n.is_source ? ' (source)' : ''}`], ['Distance', n.dist === null ? 'unreachable' : String(n.dist)],
      ['Parent', n.parent === -1 ? 'none' : String(n.parent)], ['Tight in-edges', String(n.tight)]];
    const bw = 170, bh = 12 + rows.length * 18 + 6;
    let x = p.x + 20, y = p.y - bh / 2;
    if (x + bw > this.w - 6) x = p.x - bw - 20;
    y = Math.max(6, Math.min(y, this.h - bh - 6));
    ctx.fillStyle = pal.tipBg; ctx.beginPath(); ctx.roundRect(x, y, bw, bh, 6); ctx.fill();
    ctx.font = `12px ${pal.font}`; ctx.textBaseline = 'middle';
    rows.forEach(([k, v], i) => {
      ctx.textAlign = 'left'; ctx.fillStyle = pal.tipMuted; ctx.fillText(k, x + 10, y + 18 + i * 18);
      ctx.textAlign = 'right'; ctx.fillStyle = pal.tipInk; ctx.fillText(v, x + bw - 10, y + 18 + i * 18);
    });
  }
}
