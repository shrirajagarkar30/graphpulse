// Central client state, refreshed from the API. Pages subscribe and re-render from it.
import { Api, ApiError } from './api.js';

const state = {
  status: null, config: null, graph: null, metrics: null, logs: [], tour: null,
  lastVerify: null, online: true, loading: false, error: null, loaded: false,
};
const subs = new Set();
const notify = () => subs.forEach((fn) => fn(state));

export const Store = {
  state,
  subscribe(fn) { subs.add(fn); return () => subs.delete(fn); },

  /** Fetch every part the UI shows, in parallel. A failure marks the engine offline instead of throwing. */
  async refresh() {
    state.loading = true; notify();
    try {
      const [status, config, graph, metrics, logs, tour] = await Promise.all([
        Api.status(), Api.config(), Api.graph(), Api.metrics(), Api.logs('all'), Api.terminals(),
      ]);
      Object.assign(state, { status, config, graph, metrics, logs: logs.logs || [], tour, online: true, error: null, loaded: true });
    } catch (err) {
      state.online = !(err instanceof ApiError) || err.status !== 0;
      state.error = err.message;
    } finally {
      state.loading = false; notify();
    }
  },
  setVerify(v) { state.lastVerify = v; notify(); },
};

export function scopeLabel() {
  const g = state.graph;
  if (!g) return { name: 'No graph loaded', meta: '' };
  const names = { grid: 'Grid', comb: 'Comb', hub_spoke: 'Hub and spoke', random_sparse: 'Random sparse' };
  return { name: names[g.preset] || g.preset, meta: `${g.n} vertices, ${g.m} roads` };
}
