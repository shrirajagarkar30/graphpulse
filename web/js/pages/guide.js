// Guide: a short path through the product, plus a scripted scenario that runs on the real engine.
import { runSampleScenario } from '../scenario.js';
import { icon } from '../icons.js';
import { toast, withBusy } from '../ui.js';

const STEPS = [
  ['Load a graph', 'Start from a grid, a hub-and-spoke network, a random sparse graph, or the comb that is the worst case for repair.', '#/network', 'Open the network'],
  ['Close or slow a road', 'Click a road on the map or type its two ends. A closure removes the road; a slowdown raises its weight.', '#/network', 'Apply an update'],
  ['Read the decision', 'The engine tells you which of four decisions it took (certificate, alternative support, repair, or rebuild) and what it cost against recomputing.', '#/activity', 'See the activity log'],
  ['Plan the tour', 'Choose a depot and stops. The tour is solved exactly, then kept up to date; a certificate skips the solver when the old tour is provably still optimal.', '#/routing', 'Set up stops'],
  ['Check the result', 'Verification recomputes everything from scratch and compares it with the engine\'s state.', '#/verification', 'Run verification'],
];

export default function guide(view) {
  view.innerHTML = `<header class="page-head"><div><h1 class="page-title">Guide</h1><p class="page-sub">Five steps from a blank workspace to a verified result.</p></div>
    <div class="page-actions"><button class="btn btn-primary" type="button" id="gd-run" data-busy="Running scenario">${icon('play')}Run a sample scenario</button></div></header>
    <div class="panel panel-pad" style="padding-top:4px;padding-bottom:4px">${STEPS.map(([t, p, href, label]) => `<div class="guide-step"><div><h3>${t}</h3><p>${p}</p></div><a class="btn btn-sm" href="${href}">${label}</a></div>`).join('')}</div>
    <p class="muted small" style="margin-top:16px">The sample scenario loads a small grid, sets a depot and four stops, applies twelve random slowdowns and closures through the same API as the buttons, and then opens the overview. Everything you see afterwards comes from the engine.</p>`;
  view.querySelector('#gd-run').addEventListener('click', async (ev) => {
    await withBusy(ev.currentTarget, async () => {
      try { await runSampleScenario(12); toast('Scenario complete'); location.hash = '#/overview'; }
      catch (e) { toast(e.message, 'error'); }
    });
  });
  return () => {};
}
