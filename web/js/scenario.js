// A scripted scenario that runs on the real engine through the public API (used by the Guide and the landing page).
import { Api } from './api.js';
import { Store } from './store.js';

/** Loads a small grid, sets a depot and four stops, applies `count` random updates, then refreshes the store. */
export async function runSampleScenario(count = 12) {
  await Api.loadGraph('grid', { rows: 6, cols: 6 });
  await Api.setTerminals(0, [5, 14, 22, 35]);
  for (let i = 0; i < count; i++) {
    const g = await Api.graph();
    const e = g.edges[Math.floor(Math.random() * g.edges.length)];
    const del = Math.random() < 0.2;
    await Api.update(del ? 'delete' : 'increase', e.u, e.v, e.w + 1 + Math.floor(Math.random() * 9));
  }
  await Store.refresh();
}
