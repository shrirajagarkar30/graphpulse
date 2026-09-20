/**
 * GraphPulse-R API Client Service Layer
 * Connects frontend directly to the Python HTTP server endpoints.
 */

const API_BASE_URL = window.GRAPH_PULSE_API_URL || '';

class GraphPulseAPI {
  static async _request(endpoint, options = {}) {
    const url = `${API_BASE_URL}${endpoint}`;
    try {
      const response = await fetch(url, {
        headers: {
          'Content-Type': 'application/json',
          ...(options.headers || {}),
        },
        ...options,
      });

      if (!response.ok) {
        let errMessage = `HTTP error ${response.status}`;
        try {
          const errData = await response.json();
          if (errData.error) errMessage = errData.error;
        } catch (_) {}
        throw new Error(errMessage);
      }

      return await response.json();
    } catch (error) {
      console.error(`API Error [${endpoint}]:`, error);
      throw error;
    }
  }

  // 1. Status & Phase info
  static async getStatus() {
    return this._request('/api/status');
  }

  // 2. Active graph topology & node coordinates
  static async getGraph() {
    return this._request('/api/graph');
  }

  // 3. Load graph generator preset (grid, comb, hub_spoke, random_sparse)
  static async loadPreset(preset, params = {}) {
    return this._request('/api/graph/load', {
      method: 'POST',
      body: JSON.stringify({ preset, params }),
    });
  }

  // 4. Set single-source vertex root
  static async setSource(src) {
    return this._request('/api/graph/set-source', {
      method: 'POST',
      body: JSON.stringify({ src: parseInt(src, 10) }),
    });
  }

  // 5. Set optional target vertex for path highlighting
  static async setTarget(target) {
    return this._request('/api/graph/set-target', {
      method: 'POST',
      body: JSON.stringify({ target: target !== null ? parseInt(target, 10) : null }),
    });
  }

  // 6. Apply dynamic edge update (delete or increase weight)
  static async applyUpdate(kind, u, v, new_w = 0) {
    return this._request('/api/update', {
      method: 'POST',
      body: JSON.stringify({
        kind,
        u: parseInt(u, 10),
        v: parseInt(v, 10),
        new_w: parseInt(new_w, 10),
      }),
    });
  }

  // 7. Reset graph to initial pre-update state
  static async resetGraph() {
    return this._request('/api/reset', { method: 'POST' });
  }

  // 8. State inspector table query
  static async getState(search = '') {
    const q = search ? `?search=${encodeURIComponent(search)}` : '';
    return this._request(`/api/state${q}`);
  }

  // 9. Active invariant verification execution
  static async verifyState() {
    return this._request('/api/verify', { method: 'POST' });
  }

  // 10. Audit logs query
  static async getLogs(filter = 'all') {
    return this._request(`/api/logs?filter=${encodeURIComponent(filter)}`);
  }

  // 11. Performance & empirical metrics
  static async getMetrics() {
    return this._request('/api/metrics');
  }
}

window.GraphPulseAPI = GraphPulseAPI;
