# Empirical Benchmark Evaluation (Milestone 4 Hardening)

**Benchmark Configuration:** Fixed Seed = `42`, `updates_per_family = 1,000`, `c = 1.0`, `p_delete = 0.4`.
Measurements captured directly from `UpdateStats.strategy` and `UpdateStats.work` against baseline `RecomputeMaintainer`.

## Summary Results Table

| Topology Family | Vertices ($n$) | Edges ($m$) | Updates | Pure Cert Hit Rate (%) | Cert + Alt Hit Rate (%) | Online Work | Rebuild Work | Work Savings (%) | Online / Rebuild Ratio |
|---|---|---|---|---|---|---|---|---|---|
| `grid` | 1,225 | 4,760 | 1,000 | 70.6% | 74.3% | 175,010 | 7,611,474 | +97.7% | 0.023x |
| `hub_spoke` | 2,265 | 4,500 | 1,000 | 97.7% | 97.7% | 1,148 | 582,867 | +99.8% | 0.002x |
| `random_sparse` | 400 | 4,000 | 1,000 | 87.6% | 92.1% | 14,861 | 5,140,124 | +99.7% | 0.003x |
| `comb_adversarial` | 450 | 1,346 | 1,000 | 45.4% | 76.4% | 13,430 | 2,199,075 | +99.4% | 0.006x |

## Empirical Strategy Distribution

| Topology Family | Total Updates | `cert` (1 SCAN) | `alt` (O(indeg)) | `repair` (<= B) | `fallback` (Abort + Rebuild) |
|---|---|---|---|---|---|
| `grid` | 1,000 | 706 (70.6%) | 37 | 257 | 0 |
| `hub_spoke` | 1,000 | 977 (97.7%) | 0 | 23 | 0 |
| `random_sparse` | 1,000 | 876 (87.6%) | 45 | 79 | 0 |
| `comb_adversarial` | 1,000 | 454 (45.4%) | 310 | 236 | 0 |

## Observations (computed from the tables above)

1. **Certificate hit rate** on grid, hub_spoke and random_sparse ranged from 70.6% to 97.7% (single seed).
2. **Work savings** versus Dijkstra-only recomputation ranged from 97.7% to 99.8% across all four families.
3. **Fallbacks:** 0 in total. Uniform random updates rarely delete the critical chain edge of `comb_adversarial`, so this run does *not* exercise the worst case of the work bound (1 + c)F + 2; adversarial tightness is a Phase 7 experiment (E4).

**Scope:** one seed, 1,000 uniform random updates per family, c = 1, `f_mode="last"`; the rebuild baseline is Dijkstra only (F additionally includes the tight-edge recount). These are benign-workload measurements, not worst-case guarantees.
