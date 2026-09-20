/**
 * Main Dashboard Controller
 * Connects API, Canvas Renderer, Controls, and Telemetry cards.
 */

class DashboardController {
  constructor() {
    this.api = window.GraphPulseAPI;
    this.renderer = null;
    this.currentUpdateMode = 'delete'; // 'delete' or 'increase'
    this.currentData = null;

    this.init();
  }

  async init() {
    // 1. Initialize Canvas Renderer
    this.renderer = new window.GraphRenderer('graphCanvas');

    // 2. Wire edge & node click callbacks
    this.renderer.onEdgeClick = (edge) => {
      document.getElementById('inputFromNode').value = edge.u;
      document.getElementById('inputToNode').value = edge.v;
      if (this.currentUpdateMode === 'increase') {
        document.getElementById('inputWeight').value = edge.w + 5;
      }
    };

    this.renderer.onNodeClick = (node) => {
      // If clicking a node, optionally offer to set as target or source
      if (node.id !== this.currentData.src) {
        this.setTargetNode(node.id);
      }
    };

    // 3. Bind UI buttons & events
    this._bindEvents();

    // 4. Start live header clock
    this._startClock();

    // 5. Initial data load
    await this.refreshAll();
  }

  _startClock() {
    const clockEl = document.getElementById('headerClock');
    const update = () => {
      const now = new Date();
      const options = { month: 'short', day: 'numeric', year: 'numeric', hour: '2-digit', minute: '2-digit', hour12: true };
      clockEl.textContent = now.toLocaleString('en-US', options);
    };
    update();
    setInterval(update, 10000);
  }

  _bindEvents() {
    // Preset dropdown
    const presetSelect = document.getElementById('presetSelect');
    if (presetSelect) {
      presetSelect.addEventListener('change', async (e) => {
        const preset = e.target.value;
        try {
          await this.api.loadPreset(preset);
          await this.refreshAll();
        } catch (err) {
          alert(`Error loading preset: ${err.message}`);
        }
      });
    }

    // View mode toggle (Network vs Algorithm)
    const btnNetwork = document.getElementById('btnViewNetwork');
    const btnAlgo = document.getElementById('btnViewAlgo');
    if (btnNetwork && btnAlgo) {
      btnNetwork.addEventListener('click', () => {
        btnNetwork.classList.add('active');
        btnAlgo.classList.remove('active');
        this.renderer.setViewMode('network');
      });
      btnAlgo.addEventListener('click', () => {
        btnAlgo.classList.add('active');
        btnNetwork.classList.remove('active');
        this.renderer.setViewMode('algorithm');
      });
    }

    // Canvas zoom & reset buttons
    document.getElementById('btnZoomIn')?.addEventListener('click', () => this.renderer.zoomIn());
    document.getElementById('btnZoomOut')?.addEventListener('click', () => this.renderer.zoomOut());
    document.getElementById('btnResetView')?.addEventListener('click', () => this.renderer.resetView());

    // Toggle Weights & Tree
    document.getElementById('btnToggleWeights')?.addEventListener('click', () => this.renderer.toggleWeights());
    document.getElementById('btnToggleTree')?.addEventListener('click', () => this.renderer.toggleTree());

    // Update Control Segmented Tabs
    const tabClose = document.getElementById('tabCloseRoad');
    const tabIncrease = document.getElementById('tabIncreaseWeight');
    const tabReset = document.getElementById('tabResetGraph');
    const weightGroup = document.getElementById('groupWeightInput');

    tabClose?.addEventListener('click', () => {
      this.currentUpdateMode = 'delete';
      tabClose.classList.add('active');
      tabIncrease.classList.remove('active');
      weightGroup.style.display = 'none';
      document.getElementById('btnApplyUpdate').innerHTML = '<span>✖ Close Road & Reoptimize</span>';
    });

    tabIncrease?.addEventListener('click', () => {
      this.currentUpdateMode = 'increase';
      tabIncrease.classList.add('active');
      tabClose.classList.remove('active');
      weightGroup.style.display = 'flex';
      document.getElementById('btnApplyUpdate').innerHTML = '<span>▲ Increase Weight & Reoptimize</span>';
    });

    tabReset?.addEventListener('click', async () => {
      try {
        await this.api.resetGraph();
        await this.refreshAll();
        this._showNotification('Graph reset to initial state');
      } catch (err) {
        alert(err.message);
      }
    });

    // Apply Update Button
    const btnApply = document.getElementById('btnApplyUpdate');
    btnApply?.addEventListener('click', () => this.handleApplyUpdate());

    // Navigation Menu Items
    document.getElementById('navLoadGraph')?.addEventListener('click', () => {
      document.getElementById('presetSelect')?.focus();
    });
    document.getElementById('navShortestPaths')?.addEventListener('click', () => {
      window.InspectorModal?.open();
    });
    document.getElementById('navVerification')?.addEventListener('click', () => {
      window.VerificationModal?.open();
    });
    document.getElementById('navAlgorithmLogs')?.addEventListener('click', () => {
      window.LogsModal?.open();
    });
    document.getElementById('btnHeaderDemo')?.addEventListener('click', () => {
      window.DemoFlow?.start();
    });
  }

  async refreshAll() {
    try {
      // 1. Fetch graph
      const graphData = await this.api.getGraph();
      this.currentData = graphData;
      this.renderer.setData(graphData);

      // 2. Fetch metrics
      const metricsData = await this.api.getMetrics();

      // 3. Update UI Cards
      this._updateShortestPathCard(graphData);
      this._updatePerformanceCard(metricsData, graphData.last_update);
      this._updateRecentTable(metricsData.last_run);
      this._updateDecisionBanner(graphData.last_update);

      // Pre-fill update input with suggested candidate if empty
      const uInput = document.getElementById('inputFromNode');
      const vInput = document.getElementById('inputToNode');
      if (!uInput.value && graphData.edges.length > 0) {
        const treeEdge = graphData.edges.find((e) => e.is_tree) || graphData.edges[0];
        uInput.value = treeEdge.u;
        vInput.value = treeEdge.v;
      }
    } catch (err) {
      console.error('Error refreshing dashboard:', err);
    }
  }

  async setTargetNode(targetId) {
    try {
      const res = await this.api.setTarget(targetId);
      this.currentData.target = targetId;
      this.currentData.path = res.path;
      this.currentData.path_dist = res.path_dist;
      this.renderer.setData(this.currentData);
      this._updateShortestPathCard(this.currentData);
    } catch (err) {
      console.error('Error setting target node:', err);
    }
  }

  async handleApplyUpdate() {
    const u = parseInt(document.getElementById('inputFromNode').value, 10);
    const v = parseInt(document.getElementById('inputToNode').value, 10);
    const newW = parseInt(document.getElementById('inputWeight').value || 0, 10);

    if (isNaN(u) || isNaN(v)) {
      alert('Please enter valid source and destination vertex IDs.');
      return;
    }

    const btn = document.getElementById('btnApplyUpdate');
    btn.disabled = true;
    btn.innerHTML = '<span>Processing Reoptimization...</span>';

    try {
      const res = await this.api.applyUpdate(this.currentUpdateMode, u, v, newW);
      await this.refreshAll();
      this._showNotification(`Update applied: strategy ${res.update.strategy}`);
    } catch (err) {
      alert(`Update Error: ${err.message}`);
    } finally {
      btn.disabled = false;
      const label = this.currentUpdateMode === 'delete' ? '✖ Close Road & Reoptimize' : '▲ Increase Weight & Reoptimize';
      btn.innerHTML = `<span>${label}</span>`;
    }
  }

  _updateShortestPathCard(data) {
    document.getElementById('valSourceNode').textContent = `Node ${data.src}`;
    document.getElementById('valTargetNode').textContent = data.target !== null ? `Node ${data.target}` : 'None (SSSP)';
    document.getElementById('valDistance').textContent = data.path_dist !== null ? `${data.path_dist} km` : 'Unreachable';

    const pathBox = document.getElementById('valPathSequence');
    if (data.path && data.path.length > 0) {
      pathBox.textContent = data.path.join(' → ');
    } else {
      pathBox.textContent = 'No route available';
    }
  }

  _updatePerformanceCard(metrics, lastUpdate) {
    const valRepairOps = document.getElementById('valRepairOps');
    const valFallbackOps = document.getElementById('valFallbackOps');
    const valTotalOps = document.getElementById('valTotalOps');
    const valWallTime = document.getElementById('valWallTime');
    const badgeVerified = document.getElementById('badgeVerified');

    if (lastUpdate) {
      valRepairOps.textContent = lastUpdate.repair_work.toLocaleString();
      valFallbackOps.textContent = lastUpdate.fallback_work.toLocaleString();
      valTotalOps.textContent = lastUpdate.work.toLocaleString();
      valWallTime.textContent = `${lastUpdate.wall_time_ms} ms`;
      badgeVerified.innerHTML = lastUpdate.verified ? '✔ Verified' : '✖ Mismatch';
      badgeVerified.style.color = lastUpdate.verified ? '#10b981' : '#ef4444';
    } else {
      valRepairOps.textContent = '0';
      valFallbackOps.textContent = '0';
      valTotalOps.textContent = '0';
      valWallTime.textContent = '0.00 ms';
      badgeVerified.innerHTML = '✔ Initialized';
    }
  }

  _updateRecentTable(lastRun) {
    const tbody = document.getElementById('recentUpdatesTbody');
    if (!tbody) return;

    if (!lastRun) {
      tbody.innerHTML = '<tr><td colspan="5" style="text-align:center; color:#94a3b8; padding:12px;">No updates applied yet.</td></tr>';
      return;
    }

    const typeBadge = lastRun.kind === 'delete'
      ? '<span class="badge-update-type close">Close</span>'
      : '<span class="badge-update-type increase">Increase</span>';

    const deltaW = lastRun.kind === 'increase' ? `+${lastRun.new_w - lastRun.old_w}` : '—';

    tbody.innerHTML = `
      <tr>
        <td>${lastRun.id}</td>
        <td>${typeBadge}</td>
        <td>(${lastRun.u}, ${lastRun.v})</td>
        <td>${deltaW}</td>
        <td>${lastRun.time}</td>
      </tr>
    `;
  }

  _updateDecisionBanner(lastUpdate) {
    const banner = document.getElementById('decisionBanner');
    if (!banner) return;

    if (!lastUpdate) {
      banner.style.display = 'none';
      return;
    }

    banner.style.display = 'flex';
    banner.className = `decision-banner ${lastUpdate.strategy}`;

    let title = '';
    let desc = '';
    if (lastUpdate.strategy === 'cert') {
      title = 'CERTIFICATE HIT';
      desc = 'Repair skipped; certificate-check cost recorded separately';
    } else if (lastUpdate.strategy === 'alt') {
      title = 'ALTERNATIVE SUPPORT';
      desc = 'Local in-edge scan; re-parented with zero distance impact';
    } else if (lastUpdate.strategy === 'repair') {
      title = 'INCREMENTAL REPAIR';
      desc = `Affected set |A| = ${lastUpdate.affected_size}; bounded Dijkstra executed`;
    } else if (lastUpdate.strategy === 'fallback') {
      title = 'BUDGET EXCEEDED FALLBACK';
      desc = `Work cap B = ${lastUpdate.budget} reached; aborted & full rebuild executed`;
    }

    banner.innerHTML = `
      <div>
        <strong>${title}</strong>: ${desc}
      </div>
      <div style="font-family:var(--font-mono); font-weight:700;">
        ${lastUpdate.work} ops
      </div>
    `;
  }

  _showNotification(msg) {
    console.log('[Notification]:', msg);
  }
}

window.addEventListener('DOMContentLoaded', () => {
  window.Dashboard = new DashboardController();
});
