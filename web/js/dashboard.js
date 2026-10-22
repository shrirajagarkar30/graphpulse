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
      if (node.id !== this.currentData.src) {
        this.setTargetNode(node.id);
      }
    };

    // 3. Bind UI buttons & events
    this._bindEvents();

    // 4. Start live header clock
    this._startClock();

    // 5. Initial data load (sets isNewGraph = true for auto-fit)
    await this.refreshAll(true);
  }

  _startClock() {
    const clockEl = document.getElementById('headerClock');
    const update = () => {
      const now = new Date();
      const options = { month: 'short', day: 'numeric', year: 'numeric', hour: '2-digit', minute: '2-digit', hour12: true };
      if (clockEl) clockEl.textContent = now.toLocaleString('en-US', options);
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
          await this.refreshAll(true);
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
    document.getElementById('btnFitGraph')?.addEventListener('click', () => this.renderer.fitGraph());

    // Toggle Weights & Tree
    const btnWeights = document.getElementById('btnToggleWeights');
    if (btnWeights) {
      btnWeights.classList.add('active-toggle'); // on by default
      btnWeights.addEventListener('click', () => {
        this.renderer.toggleWeights();
        btnWeights.classList.toggle('active-toggle', this.renderer.showWeights);
      });
    }

    const btnTree = document.getElementById('btnToggleTree');
    btnTree?.addEventListener('click', () => {
      this.renderer.toggleTree();
      btnTree.classList.toggle('active-toggle', this.renderer.showTreeOnly);
    });

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
      document.getElementById('btnApplyUpdate').innerHTML = '<span>✖ Close Edge & Reoptimize</span>';
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
        await this.refreshAll(false);
      } catch (err) {
        alert(err.message);
      }
    });

    // Apply Update Button
    const btnApply = document.getElementById('btnApplyUpdate');
    btnApply?.addEventListener('click', () => this.handleApplyUpdate());

    // Clear Target Button
    document.getElementById('btnClearTarget')?.addEventListener('click', () => this.clearTarget());

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
    document.getElementById('btnOpenGlossary')?.addEventListener('click', () => {
      document.getElementById('glossaryModal')?.classList.add('active');
    });
    document.getElementById('btnCloseGlossary')?.addEventListener('click', () => {
      document.getElementById('glossaryModal')?.classList.remove('active');
    });
  }

  async refreshAll(isNewGraph = false) {
    try {
      const graphData = await this.api.getGraph();
      this.currentData = graphData;
      this.renderer.setData(graphData, isNewGraph);

      const metricsData = await this.api.getMetrics();

      this._updateShortestPathCard(graphData);
      this._updatePerformanceCard(metricsData, graphData.last_update);
      this._updateAlgorithmStatusCard(graphData);
      this._updateRecentTable(metricsData.last_run);
      this._updateDecisionBanner(graphData.last_update);
      this._updateHeaderGraphInfo(graphData);

      const statusText = document.getElementById('headerStatusText');
      if (statusText) statusText.textContent = 'Connected (50%)';

      const uInput = document.getElementById('inputFromNode');
      const vInput = document.getElementById('inputToNode');
      if (!uInput.value && graphData.edges.length > 0) {
        const treeEdge = graphData.edges.find((e) => e.is_tree) || graphData.edges[0];
        uInput.value = treeEdge.u;
        vInput.value = treeEdge.v;
      }
    } catch (err) {
      console.error('Error refreshing dashboard:', err);
      const statusText = document.getElementById('headerStatusText');
      if (statusText) statusText.textContent = 'Offline / Error';
    }
  }

  _updateHeaderGraphInfo(data) {
    const infoEl = document.getElementById('headerGraphInfo');
    if (infoEl) {
      const presetNames = {
        grid: 'Grid Graph (6x6)',
        comb: 'Adversarial Comb',
        hub_spoke: 'Hub-Spoke Topology',
        random_sparse: 'Random Sparse Graph',
      };
      const name = presetNames[data.preset] || data.preset;
      infoEl.textContent = `${name} | ${data.n} nodes, ${data.m} edges | Source: Node ${data.src}`;
    }
  }

  async setTargetNode(targetId) {
    try {
      const res = await this.api.setTarget(targetId);
      this.currentData.target = targetId;
      this.currentData.path = res.path;
      this.currentData.path_dist = res.path_dist;
      this.renderer.setData(this.currentData, false);
      this._updateShortestPathCard(this.currentData);
    } catch (err) {
      console.error('Error setting target node:', err);
    }
  }

  async clearTarget() {
    try {
      await this.api.setTarget(null);
      this.currentData.target = null;
      this.currentData.path = [];
      this.currentData.path_dist = null;
      this.renderer.setData(this.currentData, false);
      this._updateShortestPathCard(this.currentData);
    } catch (err) {
      console.error('Error clearing target:', err);
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
      await this.api.applyUpdate(this.currentUpdateMode, u, v, newW);
      // Keep user's zoom and pan during incremental update!
      await this.refreshAll(false);
    } catch (err) {
      alert(`Update Error: ${err.message}`);
    } finally {
      btn.disabled = false;
      const label = this.currentUpdateMode === 'delete' ? '✖ Close Edge & Reoptimize' : '▲ Increase Weight & Reoptimize';
      btn.innerHTML = `<span>${label}</span>`;
    }
  }

  _updateShortestPathCard(data) {
    document.getElementById('valSourceNode').textContent = `Node ${data.src}`;
    const targetEl = document.getElementById('valTargetNode');
    const distEl = document.getElementById('valDistance');
    const pathBox = document.getElementById('valPathSequence');
    const clearBtn = document.getElementById('btnClearTarget');

    if (data.target !== null) {
      targetEl.textContent = `Node ${data.target}`;
      distEl.textContent = data.path_dist !== null ? `${data.path_dist} units` : 'Unreachable';
      if (clearBtn) clearBtn.style.display = 'inline-block';

      if (data.path && data.path.length > 0) {
        pathBox.textContent = data.path.join(' → ');
      } else {
        pathBox.textContent = 'No route available (Unreachable)';
      }
    } else {
      targetEl.textContent = 'None (Full Tree)';
      distEl.textContent = 'Complete SSSP Tree';
      if (clearBtn) clearBtn.style.display = 'none';
      pathBox.textContent = `Showing complete single-source shortest-path tree rooted at Node ${data.src}`;
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
      valWallTime.textContent = `${lastUpdate.wall_time_ms} ms (single run)`;
      badgeVerified.innerHTML = lastUpdate.verified ? '✔ Verified' : '✖ Mismatch';
      badgeVerified.style.color = lastUpdate.verified ? '#10b981' : '#ef4444';
    } else {
      valRepairOps.textContent = '0';
      valFallbackOps.textContent = '0';
      valTotalOps.textContent = '0';
      valWallTime.textContent = '0.00 ms (single run)';
      badgeVerified.innerHTML = '✔ Initialized';
      badgeVerified.style.color = '#10b981';
    }
  }

  _updateAlgorithmStatusCard(data) {
    const statusReady = document.getElementById('statusBadgeReady');
    if (statusReady) {
      statusReady.innerHTML = `
        <svg width="13" height="13" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="3">
          <polyline points="20 6 9 17 4 12"></polyline>
        </svg>
        <span>Backend connected & SPT ready (F=${data.F_ops} ops)</span>
      `;
    }

    const tagVerified = document.getElementById('tagVerified');
    if (tagVerified) {
      const isVer = data.last_update ? data.last_update.verified : true;
      tagVerified.className = `status-tag ${isVer ? 'active' : ''}`;
      tagVerified.innerHTML = `<span class="tag-dot ${isVer ? 'green' : 'blue'}"></span>Last update ${isVer ? 'verified' : 'unverified'}`;
    }

    const tagFallback = document.getElementById('tagFallback');
    if (tagFallback) {
      const isFallback = data.last_update?.strategy === 'fallback';
      tagFallback.className = `status-tag ${isFallback ? 'active' : ''}`;
      tagFallback.innerHTML = `<span class="tag-dot ${isFallback ? 'blue' : 'green'}"></span>Fallback ${isFallback ? 'triggered (Cap B reached)' : 'not triggered'}`;
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
}

window.addEventListener('DOMContentLoaded', () => {
  window.Dashboard = new DashboardController();
});
