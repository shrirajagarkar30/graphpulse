/**
 * Interactive Canvas Graph & Network Visualizer
 * Supports Network View (styled road network layout) and Algorithm View.
 */

class GraphRenderer {
  constructor(canvasId) {
    this.canvas = document.getElementById(canvasId);
    this.ctx = this.canvas.getContext('2d');

    this.nodes = [];
    this.edges = [];
    this.src = 0;
    this.target = null;
    this.path = [];
    this.viewMode = 'network'; // 'network' or 'algorithm'
    this.showWeights = true;
    this.showTreeOnly = false;
    this.lastUpdate = null;

    // Viewport transform
    this.zoom = 1.0;
    this.panX = 0;
    this.panY = 0;
    this.baseCenterX = 400;
    this.baseCenterY = 250;

    this.isDragging = false;
    this.dragStartX = 0;
    this.dragStartY = 0;

    // Hover & Selection
    this.hoveredNode = null;
    this.hoveredEdge = null;
    this.onEdgeClick = null;
    this.onNodeClick = null;

    // Animation frame
    this.animOffset = 0;
    this._setupEvents();
    this._startAnimationLoop();
  }

  setData(data, isNewGraph = false) {
    this.nodes = data.nodes || [];
    this.edges = data.edges || [];
    this.src = data.src;
    this.target = data.target;
    this.path = data.path || [];
    this.lastUpdate = data.last_update || null;

    if (isNewGraph || this.nodes.length === 0) {
      this.fitGraph();
    } else {
      this.render();
    }
  }

  fitGraph() {
    if (!this.nodes || this.nodes.length === 0) return;

    let minX = Infinity, maxX = -Infinity;
    let minY = Infinity, maxY = -Infinity;

    for (const n of this.nodes) {
      if (n.x < minX) minX = n.x;
      if (n.x > maxX) maxX = n.x;
      if (n.y < minY) minY = n.y;
      if (n.y > maxY) maxY = n.y;
    }

    this.baseCenterX = (minX + maxX) / 2;
    this.baseCenterY = (minY + maxY) / 2;

    const w = this.canvas.clientWidth || 800;
    const h = this.canvas.clientHeight || 500;

    const spanX = Math.max(maxX - minX, 50);
    const spanY = Math.max(maxY - minY, 50);

    const margin = 80;
    const availW = Math.max(w - 2 * margin, 200);
    const availH = Math.max(h - 2 * margin, 150);

    const scaleX = availW / spanX;
    const scaleY = availH / spanY;

    // Choose optimal zoom so graph occupies ~80% of canvas
    this.zoom = Math.min(scaleX, scaleY, 1.6);
    this.panX = 0;
    this.panY = 0;
    this.render();
  }

  setViewMode(mode) {
    this.viewMode = mode;
    this.render();
  }

  toggleWeights() {
    this.showWeights = !this.showWeights;
    this.render();
  }

  toggleTree() {
    this.showTreeOnly = !this.showTreeOnly;
    this.render();
  }

  resetView() {
    this.fitGraph();
  }

  zoomIn() {
    this.zoom = Math.min(3.5, this.zoom * 1.25);
    this.render();
  }

  zoomOut() {
    this.zoom = Math.max(0.3, this.zoom / 1.25);
    this.render();
  }

  _setupEvents() {
    window.addEventListener('resize', () => this._resize());
    setTimeout(() => {
      this._resize();
      this.fitGraph();
    }, 80);

    this.canvas.addEventListener('mousedown', (e) => {
      this.isDragging = true;
      this.dragStartX = e.clientX - this.panX;
      this.dragStartY = e.clientY - this.panY;
    });

    window.addEventListener('mousemove', (e) => {
      const rect = this.canvas.getBoundingClientRect();
      const mouseX = e.clientX - rect.left;
      const mouseY = e.clientY - rect.top;

      if (this.isDragging) {
        this.panX = e.clientX - this.dragStartX;
        this.panY = e.clientY - this.dragStartY;
        this.render();
      } else {
        this._handleHover(mouseX, mouseY);
      }
    });

    window.addEventListener('mouseup', () => {
      this.isDragging = false;
    });

    this.canvas.addEventListener('wheel', (e) => {
      e.preventDefault();
      const delta = e.deltaY > 0 ? 0.9 : 1.1;
      this.zoom = Math.max(0.3, Math.min(3.5, this.zoom * delta));
      this.render();
    }, { passive: false });

    this.canvas.addEventListener('click', (e) => {
      const rect = this.canvas.getBoundingClientRect();
      const mouseX = e.clientX - rect.left;
      const mouseY = e.clientY - rect.top;
      this._handleClick(mouseX, mouseY);
    });
  }

  _resize() {
    const parent = this.canvas.parentElement;
    if (!parent) return;
    const dpr = window.devicePixelRatio || 1;
    this.canvas.width = parent.clientWidth * dpr;
    this.canvas.height = parent.clientHeight * dpr;
    this.ctx.scale(dpr, dpr);
    this.render();
  }

  _toScreen(x, y) {
    const w = this.canvas.clientWidth;
    const h = this.canvas.clientHeight;
    return {
      x: (x - this.baseCenterX) * this.zoom + w / 2 + this.panX,
      y: (y - this.baseCenterY) * this.zoom + h / 2 + this.panY,
    };
  }

  _fromScreen(sx, sy) {
    const w = this.canvas.clientWidth;
    const h = this.canvas.clientHeight;
    return {
      x: (sx - w / 2 - this.panX) / this.zoom + this.baseCenterX,
      y: (sy - h / 2 - this.panY) / this.zoom + this.baseCenterY,
    };
  }

  _handleHover(mx, my) {
    const { x, y } = this._fromScreen(mx, my);
    let foundNode = null;
    let foundEdge = null;

    const hitRadius = Math.max(18, 16 / this.zoom);

    for (const node of this.nodes) {
      if (Math.hypot(node.x - x, node.y - y) <= hitRadius) {
        foundNode = node;
        break;
      }
    }

    this.hoveredNode = foundNode;
    this.hoveredEdge = foundEdge;
    this.canvas.style.cursor = foundNode ? 'pointer' : this.isDragging ? 'grabbing' : 'grab';
    this.render();
  }

  _handleClick(mx, my) {
    const { x, y } = this._fromScreen(mx, my);
    const hitRadius = Math.max(18, 16 / this.zoom);

    for (const node of this.nodes) {
      if (Math.hypot(node.x - x, node.y - y) <= hitRadius) {
        if (this.onNodeClick) this.onNodeClick(node);
        return;
      }
    }

    for (const edge of this.edges) {
      const uNode = this.nodes.find((n) => n.id === edge.u);
      const vNode = this.nodes.find((n) => n.id === edge.v);
      if (!uNode || !vNode) continue;

      const distToSeg = this._distToSegment({ x, y }, uNode, vNode);
      if (distToSeg <= Math.max(10, 8 / this.zoom)) {
        if (this.onEdgeClick) this.onEdgeClick(edge);
        return;
      }
    }
  }

  _distToSegment(p, v, w) {
    const l2 = (v.x - w.x) ** 2 + (v.y - w.y) ** 2;
    if (l2 === 0) return Math.hypot(p.x - v.x, p.y - v.y);
    let t = ((p.x - v.x) * (w.x - v.x) + (p.y - v.y) * (w.y - v.y)) / l2;
    t = Math.max(0, Math.min(1, t));
    return Math.hypot(p.x - (v.x + t * (w.x - v.x)), p.y - (v.y + t * (w.y - v.y)));
  }

  _startAnimationLoop() {
    const loop = () => {
      this.animOffset = (this.animOffset + 0.5) % 100;
      this.render();
      requestAnimationFrame(loop);
    };
    requestAnimationFrame(loop);
  }

  render() {
    const ctx = this.ctx;
    const w = this.canvas.clientWidth;
    const h = this.canvas.clientHeight;
    if (!w || !h) return;

    ctx.clearRect(0, 0, w, h);

    this._renderBackground(ctx, w, h);
    this._renderEdges(ctx);
    this._renderNodes(ctx);

    if (this.hoveredNode) {
      this._renderTooltip(ctx, this.hoveredNode);
    }
  }

  _renderBackground(ctx, w, h) {
    ctx.save();
    ctx.strokeStyle = '#e2e8f0';
    ctx.lineWidth = 0.5;
    const gridSize = 40 * this.zoom;
    const offsetX = (this.panX + w / 2) % gridSize;
    const offsetY = (this.panY + h / 2) % gridSize;

    ctx.beginPath();
    for (let x = offsetX; x < w; x += gridSize) {
      ctx.moveTo(x, 0);
      ctx.lineTo(x, h);
    }
    for (let y = offsetY; y < h; y += gridSize) {
      ctx.moveTo(0, y);
      ctx.lineTo(w, y);
    }
    ctx.stroke();

    ctx.font = '11px Inter, sans-serif';
    ctx.fillStyle = '#94a3b8';
    ctx.fillText('Abstract Network View — Not geographical road data', 16, h - 36);
    ctx.restore();
  }

  _renderEdges(ctx) {
    const pathEdges = new Set();
    for (let i = 0; i < this.path.length - 1; i++) {
      pathEdges.add(`${this.path[i]}->${this.path[i + 1]}`);
    }

    for (const edge of this.edges) {
      const uNode = this.nodes.find((n) => n.id === edge.u);
      const vNode = this.nodes.find((n) => n.id === edge.v);
      if (!uNode || !vNode) continue;

      const p1 = this._toScreen(uNode.x, uNode.y);
      const p2 = this._toScreen(vNode.x, vNode.y);

      const isPath = pathEdges.has(`${edge.u}->${edge.v}`);
      const isTree = edge.is_tree;
      const isLastUpdate = edge.is_last_updated;

      if (this.showTreeOnly && !isTree && !isLastUpdate) continue;

      ctx.save();
      ctx.beginPath();
      ctx.moveTo(p1.x, p1.y);
      ctx.lineTo(p2.x, p2.y);

      if (isPath) {
        ctx.strokeStyle = '#2563eb';
        ctx.lineWidth = Math.max(3.5, 4.5 * this.zoom);
        ctx.lineCap = 'round';
        ctx.stroke();

        ctx.strokeStyle = 'rgba(37, 99, 235, 0.25)';
        ctx.lineWidth = Math.max(7, 9 * this.zoom);
        ctx.stroke();
      } else if (isTree) {
        ctx.strokeStyle = '#3b82f6';
        ctx.lineWidth = Math.max(2, 2.8 * this.zoom);
        ctx.stroke();
      } else {
        ctx.strokeStyle = '#cbd5e1';
        ctx.lineWidth = Math.max(1, 1.5 * this.zoom);
        ctx.stroke();
      }

      this._drawArrow(ctx, p1, p2, isPath ? '#2563eb' : isTree ? '#3b82f6' : '#94a3b8');

      if (this.showWeights) {
        const mx = (p1.x + p2.x) / 2;
        const my = (p1.y + p2.y) / 2;
        this._drawWeightBadge(ctx, mx, my, edge.w, isPath || isTree);
      }

      ctx.restore();
    }

    if (this.lastUpdate) {
      const uNode = this.nodes.find((n) => n.id === this.lastUpdate.u);
      const vNode = this.nodes.find((n) => n.id === this.lastUpdate.v);
      if (uNode && vNode) {
        const p1 = this._toScreen(uNode.x, uNode.y);
        const p2 = this._toScreen(vNode.x, vNode.y);
        const mx = (p1.x + p2.x) / 2;
        const my = (p1.y + p2.y) / 2;

        ctx.save();
        if (this.lastUpdate.kind === 'delete') {
          ctx.beginPath();
          ctx.setLineDash([6, 4]);
          ctx.strokeStyle = '#ef4444';
          ctx.lineWidth = Math.max(2.5, 3 * this.zoom);
          ctx.moveTo(p1.x, p1.y);
          ctx.lineTo(p2.x, p2.y);
          ctx.stroke();

          this._drawEdgeRemovedBadge(ctx, mx, my);
        } else if (this.lastUpdate.kind === 'increase') {
          this._drawWeightChangeBadge(ctx, mx, my, this.lastUpdate.old_w, this.lastUpdate.new_w);
        }
        ctx.restore();
      }
    }
  }

  _drawArrow(ctx, from, to, color) {
    const headLen = Math.max(6, 8 * this.zoom);
    const angle = Math.atan2(to.y - from.y, to.x - from.x);
    const nodeRadius = Math.max(14, 17 * this.zoom);
    const endX = to.x - nodeRadius * Math.cos(angle);
    const endY = to.y - nodeRadius * Math.sin(angle);

    ctx.save();
    ctx.fillStyle = color;
    ctx.beginPath();
    ctx.moveTo(endX, endY);
    ctx.lineTo(
      endX - headLen * Math.cos(angle - Math.PI / 6),
      endY - headLen * Math.sin(angle - Math.PI / 6)
    );
    ctx.lineTo(
      endX - headLen * Math.cos(angle + Math.PI / 6),
      endY - headLen * Math.sin(angle + Math.PI / 6)
    );
    ctx.closePath();
    ctx.fill();
    ctx.restore();
  }

  _drawWeightBadge(ctx, x, y, weight, isPrimary) {
    ctx.save();
    const fontSize = Math.max(9, Math.min(12, 11 * this.zoom));
    ctx.font = `600 ${fontSize}px 'JetBrains Mono', monospace`;
    const text = String(weight);
    const metrics = ctx.measureText(text);
    const bw = metrics.width + 8;
    const bh = fontSize + 4;

    ctx.fillStyle = isPrimary ? '#eff6ff' : '#ffffff';
    ctx.strokeStyle = isPrimary ? '#93c5fd' : '#cbd5e1';
    ctx.lineWidth = 1;
    ctx.beginPath();
    ctx.roundRect(x - bw / 2, y - bh / 2, bw, bh, 3);
    ctx.fill();
    ctx.stroke();

    ctx.fillStyle = isPrimary ? '#1d4ed8' : '#64748b';
    ctx.textAlign = 'center';
    ctx.textBaseline = 'middle';
    ctx.fillText(text, x, y);
    ctx.restore();
  }

  _drawEdgeRemovedBadge(ctx, x, y) {
    ctx.save();
    const text = 'Edge Removed';
    ctx.font = `700 ${Math.max(10, 11 * this.zoom)}px Inter, sans-serif`;
    const metrics = ctx.measureText(text);
    const bw = metrics.width + 20;
    const bh = 20;

    ctx.fillStyle = '#ef4444';
    ctx.shadowColor = 'rgba(239, 68, 68, 0.4)';
    ctx.shadowBlur = 6;
    ctx.beginPath();
    ctx.roundRect(x - bw / 2, y - bh / 2 - 10, bw, bh, 10);
    ctx.fill();

    ctx.fillStyle = '#ffffff';
    ctx.textAlign = 'center';
    ctx.textBaseline = 'middle';
    ctx.fillText(`✖ ${text}`, x, y - 10);
    ctx.restore();
  }

  _drawWeightChangeBadge(ctx, x, y, old_w, new_w) {
    ctx.save();
    const text = `+${new_w - old_w} (${old_w}→${new_w})`;
    ctx.font = `700 ${Math.max(10, 11 * this.zoom)}px 'JetBrains Mono', monospace`;
    const metrics = ctx.measureText(text);
    const bw = metrics.width + 14;
    const bh = 18;

    ctx.fillStyle = '#f59e0b';
    ctx.beginPath();
    ctx.roundRect(x - bw / 2, y - bh / 2 - 10, bw, bh, 5);
    ctx.fill();

    ctx.fillStyle = '#ffffff';
    ctx.textAlign = 'center';
    ctx.textBaseline = 'middle';
    ctx.fillText(text, x, y - 10);
    ctx.restore();
  }

  _renderNodes(ctx) {
    const baseR = Math.max(13, 16 * this.zoom);

    for (const node of this.nodes) {
      const p = this._toScreen(node.x, node.y);
      const isSrc = node.is_source;
      const isTgt = node.is_target;
      const isAff = node.is_affected;
      const inPath = this.path.includes(node.id);
      const r = isSrc || isTgt ? baseR + 2 : baseR;

      ctx.save();
      ctx.shadowColor = 'rgba(0,0,0,0.08)';
      ctx.shadowBlur = 4;

      ctx.beginPath();
      ctx.arc(p.x, p.y, r, 0, Math.PI * 2);

      if (isSrc) {
        ctx.fillStyle = '#10b981';
        ctx.strokeStyle = '#ffffff';
        ctx.lineWidth = 3;
        ctx.fill();
        ctx.stroke();

        ctx.beginPath();
        ctx.arc(p.x, p.y, r + 4, 0, Math.PI * 2);
        ctx.strokeStyle = 'rgba(16, 185, 129, 0.45)';
        ctx.lineWidth = 2;
        ctx.stroke();
      } else if (isTgt) {
        ctx.fillStyle = '#ef4444';
        ctx.strokeStyle = '#ffffff';
        ctx.lineWidth = 3;
        ctx.fill();
        ctx.stroke();

        ctx.beginPath();
        ctx.arc(p.x, p.y, r + 4, 0, Math.PI * 2);
        ctx.strokeStyle = 'rgba(239, 68, 68, 0.45)';
        ctx.lineWidth = 2;
        ctx.stroke();
      } else if (isAff) {
        ctx.fillStyle = '#f59e0b';
        ctx.strokeStyle = '#b45309';
        ctx.lineWidth = 2;
        ctx.fill();
        ctx.stroke();

        ctx.beginPath();
        ctx.arc(p.x, p.y, r + 3, 0, Math.PI * 2);
        ctx.strokeStyle = 'rgba(245, 158, 11, 0.4)';
        ctx.lineWidth = 1.5;
        ctx.stroke();
      } else if (inPath) {
        ctx.fillStyle = '#2563eb';
        ctx.strokeStyle = '#ffffff';
        ctx.lineWidth = 2.5;
        ctx.fill();
        ctx.stroke();
      } else {
        ctx.fillStyle = node.reachable ? '#ffffff' : '#f1f5f9';
        ctx.strokeStyle = node.reachable ? '#94a3b8' : '#cbd5e1';
        ctx.lineWidth = 2;
        ctx.fill();
        ctx.stroke();
      }

      ctx.font = `600 ${Math.max(9, Math.min(13, 11 * this.zoom))}px Inter, sans-serif`;
      ctx.textAlign = 'center';
      ctx.textBaseline = 'middle';
      if (isSrc) {
        ctx.fillStyle = '#ffffff';
        ctx.fillText('S', p.x, p.y);
      } else if (isTgt) {
        ctx.fillStyle = '#ffffff';
        ctx.fillText('T', p.x, p.y);
      } else {
        ctx.fillStyle = inPath || isAff ? '#ffffff' : '#334155';
        ctx.fillText(String(node.id), p.x, p.y);
      }

      if (isSrc || isTgt) {
        ctx.font = `700 10.5px Inter, sans-serif`;
        ctx.fillStyle = isSrc ? '#047857' : '#b91c1c';
        ctx.fillText(isSrc ? 'Source' : 'Target', p.x, p.y + r + 10);
      }

      ctx.restore();
    }
  }

  _renderTooltip(ctx, node) {
    const p = this._toScreen(node.x, node.y);
    const boxW = 160;
    const boxH = 96;
    const tx = p.x + 18;
    const ty = p.y - boxH / 2;

    ctx.save();
    ctx.fillStyle = 'rgba(15, 23, 42, 0.95)';
    ctx.beginPath();
    ctx.roundRect(tx, ty, boxW, boxH, 8);
    ctx.fill();

    ctx.fillStyle = '#ffffff';
    ctx.font = '700 12px Inter, sans-serif';
    ctx.fillText(`Node ${node.id}${node.is_source ? ' (Source)' : ''}`, tx + 12, ty + 20);

    ctx.font = '11px Inter, sans-serif';
    ctx.fillStyle = '#94a3b8';
    ctx.fillText(`Shortest cost : `, tx + 12, ty + 38);
    ctx.fillText(`Parent node   : `, tx + 12, ty + 54);
    ctx.fillText(`Tight in-edges: `, tx + 12, ty + 70);
    ctx.fillText(`Reachable     : `, tx + 12, ty + 86);

    ctx.font = '600 11px JetBrains Mono, monospace';
    ctx.fillStyle = '#60a5fa';
    ctx.fillText(node.dist !== null ? `${node.dist} units` : 'INF', tx + 98, ty + 38);
    ctx.fillText(node.parent !== -1 ? String(node.parent) : 'None', tx + 98, ty + 54);
    ctx.fillText(String(node.tight), tx + 98, ty + 70);
    ctx.fillStyle = node.reachable ? '#34d399' : '#f87171';
    ctx.fillText(node.reachable ? 'True' : 'False', tx + 98, ty + 86);
    ctx.restore();
  }
}

window.GraphRenderer = GraphRenderer;
