/**
 * State Inspector & Active Verification Modal Controllers
 */

class InspectorModalController {
  constructor() {
    this.modal = document.getElementById('inspectorModal');
    this.tbody = document.getElementById('stateTableTbody');
    this.searchInput = document.getElementById('inputSearchVertex');
    this._bindEvents();
  }

  _bindEvents() {
    document.getElementById('btnCloseInspector')?.addEventListener('click', () => this.close());
    this.searchInput?.addEventListener('input', () => this.loadData());
    document.getElementById('btnExportState')?.addEventListener('click', () => this.exportJSON());
  }

  open() {
    if (this.modal) {
      this.modal.classList.add('active');
      this.loadData();
    }
  }

  close() {
    if (this.modal) {
      this.modal.classList.remove('active');
    }
  }

  async loadData() {
    const search = this.searchInput?.value.trim() || '';
    try {
      const data = await window.GraphPulseAPI.getState(search);
      this.renderTable(data.rows);
    } catch (err) {
      console.error('Error loading state:', err);
    }
  }

  renderTable(rows) {
    if (!this.tbody) return;
    if (!rows || rows.length === 0) {
      this.tbody.innerHTML = '<tr><td colspan="7" style="text-align:center; padding:16px; color:#94a3b8;">No vertices found.</td></tr>';
      return;
    }

    this.tbody.innerHTML = rows.map((r) => `
      <tr style="${r.is_source ? 'background-color:#ecfdf5;' : r.is_affected ? 'background-color:#fffbeb;' : ''}">
        <td><strong>${r.v}</strong> ${r.is_source ? '<span style="color:#059669; font-size:10px;">(Src)</span>' : ''}</td>
        <td>${r.dist}</td>
        <td>${r.parent}</td>
        <td>${r.tight}</td>
        <td>${r.reachable ? '<span style="color:#10b981;">True</span>' : '<span style="color:#ef4444;">False</span>'}</td>
        <td>[${r.children.join(', ')}]</td>
        <td>${r.is_affected ? '<span style="color:#d97706; font-weight:700;">In A</span>' : '—'}</td>
      </tr>
    `).join('');
  }

  async exportJSON() {
    try {
      const data = await window.GraphPulseAPI.getState('');
      const blob = new Blob([JSON.stringify(data, null, 2)], { type: 'application/json' });
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `graphpulse_state_${Date.now()}.json`;
      a.click();
      URL.revokeObjectURL(url);
    } catch (err) {
      alert('Error exporting state: ' + err.message);
    }
  }
}

class VerificationModalController {
  constructor() {
    this.modal = document.getElementById('verificationModal');
    this._bindEvents();
  }

  _bindEvents() {
    document.getElementById('btnCloseVerification')?.addEventListener('click', () => this.close());
    document.getElementById('btnRunVerification')?.addEventListener('click', () => this.runVerification());
  }

  open() {
    if (this.modal) {
      this.modal.classList.add('active');
      this.runVerification();
    }
  }

  close() {
    if (this.modal) {
      this.modal.classList.remove('active');
    }
  }

  async runVerification() {
    const btn = document.getElementById('btnRunVerification');
    const resultBox = document.getElementById('verificationResultBox');
    if (btn) btn.disabled = true;

    try {
      const res = await window.GraphPulseAPI.verifyState();
      const isOk = res.verified;

      resultBox.innerHTML = `
        <div style="display:flex; align-items:center; gap:10px; margin-bottom:16px;">
          <div style="font-size:24px;">${isOk ? '✅' : '❌'}</div>
          <div>
            <h3 style="font-size:16px; font-weight:700; color:${isOk ? '#065f46' : '#991b1b'};">
              Verification Result: ${res.status}
            </h3>
            <div style="font-size:12px; color:#64748b;">Completed at ${res.timestamp}</div>
          </div>
        </div>

        <div style="display:grid; grid-template-columns:repeat(2, 1fr); gap:12px; font-size:13px;">
          <div style="background:#f8fafc; padding:10px; border-radius:8px; border:1px solid #e2e8f0;">
            <div style="color:#64748b; font-size:11px;">VERTICES CHECKED</div>
            <div style="font-weight:700; font-family:var(--font-mono);">${res.vertices_checked}</div>
          </div>
          <div style="background:#f8fafc; padding:10px; border-radius:8px; border:1px solid #e2e8f0;">
            <div style="color:#64748b; font-size:11px;">EDGES CHECKED</div>
            <div style="font-weight:700; font-family:var(--font-mono);">${res.edges_checked}</div>
          </div>
          <div style="background:#f8fafc; padding:10px; border-radius:8px; border:1px solid #e2e8f0;">
            <div style="color:#64748b; font-size:11px;">DISTANCE MISMATCHES</div>
            <div style="font-weight:700; font-family:var(--font-mono); color:${res.distance_mismatches === 0 ? '#10b981' : '#ef4444'};">
              ${res.distance_mismatches}
            </div>
          </div>
          <div style="background:#f8fafc; padding:10px; border-radius:8px; border:1px solid #e2e8f0;">
            <div style="color:#64748b; font-size:11px;">INVARIANT STATUS</div>
            <div style="font-weight:600; font-size:12px; color:${isOk ? '#059669' : '#dc2626'};">
              ${res.invariant_message}
            </div>
          </div>
        </div>
      `;
    } catch (err) {
      resultBox.innerHTML = `<div style="color:#ef4444;">Verification execution failed: ${err.message}</div>`;
    } finally {
      if (btn) btn.disabled = false;
    }
  }
}

window.addEventListener('DOMContentLoaded', () => {
  window.InspectorModal = new InspectorModalController();
  window.VerificationModal = new VerificationModalController();
});
