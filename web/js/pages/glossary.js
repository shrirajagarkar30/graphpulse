// Glossary: the terms the dashboard uses, with the precise meaning from the project's specification.
const TERMS = [
  ['Shortest-path tree', 'For a chosen source, the set of roads each vertex uses to reach the source by a shortest path. The engine keeps one tree per terminal.'],
  ['Tight road', 'A road whose weight exactly closes the gap between the distances of its two ends: distance of the start plus the weight equals the distance of the end. Only tight roads can lie on shortest paths.'],
  ['Certificate', 'A cheap test that proves the previous answer is still valid. For a closure it is one check: the closed road was not tight, so no distance changes.'],
  ['Alternative support', 'The closed road was tight, but its destination has another tight road, so its distance stays the same. Only a counter and a pointer change.'],
  ['Affected set', 'The vertices whose shortest distance really changes after an update. Repair recomputes only these.'],
  ['Repair', 'Recomputing distances inside the affected set, starting from its boundary, on a copy-on-write overlay so that abandoning it leaves the state untouched.'],
  ['Rebuild cost F', 'The number of operations a complete rebuild of one tree would take, including recounting tight roads.'],
  ['Budget multiplier c', 'Repair may spend at most c times F operations. If it needs more it is abandoned and the tree is rebuilt. With an exact estimate of F, one update costs at most (1 + c) · F + 2, and the competitive ratio is max(1 + c, (1 + c) / c), smallest at c = 1. In the deployed mode F is the last observed rebuild cost, for which no such guarantee is proved.'],
  ['Competitive ratio', 'The worst-case cost of the online decision divided by the cost of the cheaper of repair and rebuild for the same update.'],
  ['Operations', 'The machine-independent cost unit: adjacency scans, heap pushes, heap pops and queue operations. Wall-clock time is shown only as a secondary figure.'],
  ['Terminal matrix', 'The shortest-path distance between every pair of the depot and the stops. Distances only grow under closures and slowdowns, so no entry ever decreases.'],
  ['Held–Karp', 'The exact dynamic program for the shortest closed tour. It is used for up to eighteen stops because its memory grows exponentially.'],
  ['Lazy tour certificate', 'If no matrix entry used by the current optimal tour has changed since it was last solved, that tour is still optimal and the solver is skipped. An optional tolerance keeps a tour that is provably close to optimal.'],
  ['Unreachable', 'No path exists from the source. Distances to unreachable vertices are shown as such; a tour that needs one has no feasible solution.'],
];

export default function glossary(view) {
  view.innerHTML = `<header class="page-head"><div><h1 class="page-title">Glossary</h1><p class="page-sub">The terms used across the dashboard.</p></div></header>
    <dl class="gloss panel panel-pad" style="padding-top:0">${TERMS.map(([t, d]) => `<dt>${t}</dt><dd>${d}</dd>`).join('')}</dl>`;
  return () => {};
}
