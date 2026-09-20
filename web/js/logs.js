/**
 * Algorithm Logs Modal Controller
 */

class LogsModalController {
  constructor() {
    this.modal = document.getElementById('logsModal');
    this.tbody = document.getElementById('logsTableTbody');
    this.filterSelect = document.getElementById('selectLogsFilter');
    this._bindEvents();
  }

  _bindEvents() {
    document.getElementById('btnCloseLogs')?.addEventListener('click', () => this.close());
    this.filterSelect?.addEventListener('change', () => this.loadLogs());
  }

  open() {
    if (this.modal) {
      this.modal.classList.add('active');
      this.loadLogs();
    }
  }

  close() {
    if (this.modal) {
      this.modal.classList.remove('active');
    }
  }

  async loadLogs() {
    const filter = this.filterSelect?.value || 'all';
    try {
      const data = await window.GraphPulseAPI.getLogs(filter);
      this.renderTable(data.logs);
    } catch (err) {
      console.error('Error loading logs:', err);
    }
  }

  renderTable(logs) {
    if (!this.tbody) return;
    if (!logs || logs.length === 0) {
      this.tbody.innerHTML = '<tr><td colspan="8" style="text-align:center; padding:16px; color:#94a3b8;">No log entries found.</td></tr>';
      return;
    }

    this.tbody.innerHTML = logs.map((l) => {
      const stratBadge = `
        <span class="badge-update-type" style="
          background:${l.strategy === 'cert' ? '#ecfdf5' : l.strategy === 'alt' ? '#fffbeb' : l.strategy === 'repair' ? '#eff6ff' : '#fef2f2'};
          color:${l.strategy === 'cert' ? '#059669' : l.strategy === 'alt' ? '#d97706' : l.strategy === 'repair' ? '#2563eb' : '#dc2626'};
          text-transform:uppercase;">
          ${l.strategy}
        </span>
      `;

      return `
        <tr>
          <td>#${l.id}</td>
          <td>${l.time}</td>
          <td>${l.kind === 'delete' ? 'Close' : 'Increase'} (${l.u}, ${l.v})</td>
          <td>${stratBadge}</td>
          <td><strong>${l.work.toLocaleString()}</strong></td>
          <td>SCAN=${l.scan}, PUSH=${l.push}, POP=${l.pop}, Q=${l.queue}</td>
          <td>${l.wall_time_ms} ms</td>
          <td>${l.verified ? '✔' : '✖'}</td>
        </tr>
      `;
    }).join('');
  }
}

window.addEventListener('DOMContentLoaded', () => {
  window.LogsModal = new LogsModalController();
});
