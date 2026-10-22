# Road-network data

**Status (2026-10-22): no real road dataset was used in this repository's results.**
Every experiment in `docs/results/` uses the synthetic families (`grid`, `random_sparse`,
`hub_spoke`, `comb`, `partial_comb`). Consequently the paper must **not** claim results on
"real road networks" (Playbook assumption A7). The loader below is implemented and tested on a
hand-made file, so real data can be added without code changes.

## How to add a real network

1. Download a directed road graph in the DIMACS `.gr` format with integer weights, e.g. a
   9th DIMACS Challenge shortest-path road network (check the current download location and the
   licence yourself). Put the file in `data/raw/` (git-ignored; never commit raw data).
2. Load, clean and extract a strongly connected subgraph:

```python
from graphpulse.roadnet import load_gr, largest_scc, induced_subgraph, bfs_ball, pick_terminals, sha256_file

g = load_gr("data/raw/<file>.gr")                  # cleaned: no self-loops, min weight on duplicates
comp = largest_scc(g)                              # iterative Tarjan, no recursion
core, _ = induced_subgraph(g, comp)
sub, mapping = bfs_ball(core, center=0, size=5000) # ~5,000-vertex strongly connected subgraph
terminals = pick_terminals(sub, k=8, seed=1)       # depot first
print(sha256_file("data/raw/<file>.gr"))
```

3. Record the provenance below so another person can reproduce the exact input.

## Provenance record (fill in when a real dataset is used)

| Field | Value |
|---|---|
| Dataset name | *none used* |
| Source URL | — |
| Retrieval date | — |
| SHA-256 of the file | — |
| n, m (raw) | — |
| Largest SCC size | — |
| Extracted subgraph (centre, size, SHA-256 of its `.gr` dump) | — |

## Committed test data

`tests/data/tiny.gr` is a hand-made 6-vertex file with a self-loop, a duplicate arc and one-way
vertices; it is the only `.gr` file tracked by git (`.gitignore` excludes all others).

## Optional OpenStreetMap conversion

Not implemented. An OSM extract would need a converter that writes integer travel times
(`ceil(length / speed)` in seconds) as `.gr`; OSM lengths are floats, and the algorithms require
integer weights.
