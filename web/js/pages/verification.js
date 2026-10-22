// Verification: re-check the live state against an independent recomputation.
import { Api } from '../api.js';
import { Store } from '../store.js';
import { icon } from '../icons.js';
import { esc, fmt, fmtCost, toast, withBusy } from '../ui.js';

export default function verification(view) {
  const draw = () => {
    const v = Store.state.lastVerify;
    const t = Store.state.tour;
    view.innerHTML = `<header class="page-head"><div><h1 class="page-title">Verification</h1><p class="page-sub">Recompute the shortest paths from scratch and compare them with what the engine holds.</p></div>
      <div class="page-actions"><button class="btn btn-primary" type="button" id="vf-run" data-busy="Verifying">${icon('shield')}Run verification</button></div></header>
      ${v ? result(v, t) : `<div class="empty"><div><strong>Not run yet</strong><p>Verification checks every distance against Dijkstra and the engine's internal invariants: tight-edge counts, parents and child links.</p></div></div>`}
      ${t && t.terminals_set ? `<section class="section"><h2 class="section-title" style="margin-bottom:12px">Routing check</h2><div class="panel panel-pad"><dl class="facts"><dt>Pipeline tour cost</dt><dd>${fmtCost(t.tour_cost)}</dd><dt>Recompute-everything reference</dt><dd>${fmtCost(t.reference_cost)}</dd><dt>Result</dt><dd>${t.tour_cost === t.reference_cost ? '<span class="pill pill-positive">Equal</span>' : '<span class="pill pill-negative">Different</span>'}</dd></dl></div></section>` : ''}`;
    view.querySelector('#vf-run').addEventListener('click', async (ev) => {
      await withBusy(ev.currentTarget, async () => {
        try { const r = await Api.verify(); Store.setVerify(r); toast(r.verified ? 'State verified' : 'Verification failed', r.verified ? 'info' : 'error'); }
        catch (e) { toast(e.message, 'error'); }
      });
    });
  };
  const unsub = Store.subscribe(draw);
  draw(); if (!Store.state.loaded) Store.refresh();
  return unsub;
}

function result(v) {
  return `<div class="panel panel-pad stack">
    <div style="display:flex;align-items:center;gap:10px;flex-wrap:wrap"><h2 class="panel-title">${v.verified ? 'State is correct' : 'Verification failed'}</h2>
      ${v.verified ? '<span class="pill pill-positive">Verified</span>' : '<span class="pill pill-negative">Failed</span>'}<span class="stamp">${esc(v.timestamp)}</span></div>
    <dl class="facts"><dt>Vertices checked</dt><dd>${fmt(v.vertices_checked)}</dd><dt>Roads checked</dt><dd>${fmt(v.edges_checked)}</dd>
    <dt>Distances that differ from Dijkstra</dt><dd>${fmt(v.distance_mismatches)}</dd><dt>Invariants</dt><dd>${esc(v.invariant_message)}</dd></dl></div>`;
}
