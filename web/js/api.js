// Thin client for the local GraphPulse-R API (see docs/API.md). Every value shown in the UI comes from here.
export class ApiError extends Error {
  constructor(message, status = 0) { super(message); this.name = 'ApiError'; this.status = status; }
}

async function request(path, options = {}) {
  let res;
  try {
    res = await fetch(path, {
      headers: { 'Content-Type': 'application/json' },
      ...options,
      body: options.body === undefined ? undefined : JSON.stringify(options.body),
    });
  } catch (err) {
    throw new ApiError('Cannot reach the engine. Start it with python run_ui.py and retry.', 0);
  }
  let data = null;
  try { data = await res.json(); } catch { /* non-JSON body */ }
  if (!res.ok || (data && data.success === false)) {
    throw new ApiError((data && data.error) || `Request failed (${res.status})`, res.status);
  }
  return data;
}

const post = (path, body = {}) => request(path, { method: 'POST', body });

export const Api = {
  status: () => request('/api/status'),
  graph: () => request('/api/graph'),
  metrics: () => request('/api/metrics'),
  logs: (filter = 'all') => request(`/api/logs?filter=${encodeURIComponent(filter)}`),
  state: (search = '') => request(`/api/state${search ? `?search=${encodeURIComponent(search)}` : ''}`),
  config: () => request('/api/config'),
  setConfig: (c) => post('/api/config', { c }),
  terminals: () => request('/api/terminals'),
  setTerminals: (depot, stops) => post('/api/terminals', { depot, stops }),
  tour: () => request('/api/tour'),
  loadGraph: (preset, params = {}) => post('/api/graph/load', { preset, params }),
  setSource: (src) => post('/api/graph/set-source', { src }),
  setTarget: (target) => post('/api/graph/set-target', { target }),
  update: (kind, u, v, new_w = 0) => post('/api/update', kind === 'increase' ? { kind, u, v, new_w } : { kind, u, v }),
  reset: () => post('/api/reset'),
  verify: () => post('/api/verify'),
};
