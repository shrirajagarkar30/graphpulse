"""Competitive ratio analysis and offline optimum measurement (Milestone 4.3).

This module provides tools to empirically evaluate the competitive ratio of
online shortest-path maintenance against the offline optimum:
- `measure()`: executes an update sequence on both the online `BudgetedMaintainer`
  and an offline oracle player, recording exact machine-independent operation costs.
- `theoretical_competitive_ratio()`: returns the proven worst-case competitive ratio
  for a given budget multiplier c or the randomized distribution.
- `MeasurementResult`: holds online cost, offline OPT cost, ratio, and per-update traces.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Any, Callable, Iterator, Sequence

from graphpulse.controller import BudgetedMaintainer, RandomizedBudget
from graphpulse.dijkstra import INF
from graphpulse.generators import Update, apply_update
from graphpulse.graph import DiGraph
from graphpulse.maintainer import UpdateStats
from graphpulse.opcount import OpCounter
from graphpulse.repair import repair
from graphpulse.spt import SPTState


def theoretical_competitive_ratio(c: float | str | RandomizedBudget) -> float:
    """Return the proven competitive ratio for budget multiplier c.

    Parameters
    ----------
    c : float, 'random', or RandomizedBudget
        Deterministic multiplier c > 0 or 'random'.

    Returns
    -------
    float
        Deterministic: max(1 + c, (1 + c) / c). Minimized at c = 1.0 with ratio 2.0.
        Randomized: e / (e - 1) ≈ 1.5819767.
    """
    if isinstance(c, (RandomizedBudget, str)) and (
        isinstance(c, RandomizedBudget) or str(c).lower() == "random"
    ):
        return math.e / (math.e - 1.0)
    c_val = float(c)
    if c_val <= 0:
        raise ValueError(f"Multiplier c must be positive, got {c!r}")
    return max(1.0 + c_val, (1.0 + c_val) / c_val)


@dataclass
class MeasurementResult:
    """Results from measuring online vs offline optimum costs.

    Supports tuple unpacking: `online, opt = result`.
    """

    online_cost: int
    opt_cost: int
    ratio: float
    updates_count: int
    strategy_counts: dict[str, int]
    per_update_online: list[int] = field(default_factory=list)
    per_update_opt: list[int] = field(default_factory=list)
    per_update_stats: list[UpdateStats] = field(default_factory=list)

    def __iter__(self) -> Iterator[int]:
        """Yield (online_cost, opt_cost) for tuple unpacking."""
        yield self.online_cost
        yield self.opt_cost

    def __getitem__(self, index: int) -> int:
        if index == 0:
            return self.online_cost
        if index == 1:
            return self.opt_cost
        raise IndexError(f"Index {index} out of range for 2-element unpackable result")

    def __len__(self) -> int:
        return 2


def measure(
    make_graph: Callable[[], DiGraph] | DiGraph,
    updates: Sequence[Update],
    c: float | str | RandomizedBudget = 1.0,
    mode: str = "oracle",
    src: int = 0,
    seed: int | None = None,
    verify: bool = False,
) -> MeasurementResult:
    """Measure online maintainer work vs offline optimum over an update sequence.

    For each update t:
    - Certificate / alternative support: cost is incurred equally by online and OPT.
    - Sole tight edge lost:
      - OPT computes min(r_t, F_t), where r_t is obtained via a dry-run repair with
        unlimited budget on a scratch copy of the current state, and F_t is the full
        rebuild work on a scratch copy of the updated graph.
      - Online algorithm runs BudgetedMaintainer with budget B = ceil(c * F)
        (or sampled from RandomizedBudget).
    - Accumulates total online cost and total offline optimum cost.

    Parameters
    ----------
    make_graph : Callable[[], DiGraph] or DiGraph instance.
    updates    : Sequence of Update operations.
    c          : Budget multiplier (float, 'random', or RandomizedBudget).
    mode       : Budget estimation mode ('oracle' or 'last'). Default is 'oracle'.
    src        : Source vertex ID.
    seed       : Optional RNG seed for RandomizedBudget.
    verify     : If True, validates tree state invariants after each update.

    Returns
    -------
    MeasurementResult
        Summary and traces of online vs offline costs.
    """
    if mode not in ("oracle", "last"):
        raise ValueError(f"Unknown mode {mode!r}; expected 'oracle' or 'last'")

    if updates is None:
        raise TypeError("updates cannot be None")

    if not callable(make_graph) and not isinstance(make_graph, DiGraph):
        raise TypeError(f"make_graph must be a callable or DiGraph, got {type(make_graph)}")

    strategy_counts = {"cert": 0, "alt": 0, "repair": 0, "fallback": 0}

    # Handle empty updates list
    if len(updates) == 0:
        return MeasurementResult(
            online_cost=0,
            opt_cost=0,
            ratio=1.0,
            updates_count=0,
            strategy_counts=strategy_counts,
            per_update_online=[],
            per_update_opt=[],
            per_update_stats=[],
        )

    # Instantiate graph
    if callable(make_graph):
        g = make_graph()
    else:
        g = make_graph.copy()

    # Online maintainer
    maintainer = BudgetedMaintainer(
        g,
        src=src,
        c=c,
        f_mode=mode,
        verify=verify,
        seed=seed,
    )

    per_update_online: list[int] = []
    per_update_opt: list[int] = []
    per_update_stats: list[UpdateStats] = []

    total_online = 0
    total_opt = 0

    for upd in updates:
        u, v = upd.u, upd.v
        old_w = maintainer.graph.weight(u, v)

        # Pre-check whether this update triggers Decision 1 (cert), 2 (alt), or 3 (sole tight)
        is_cert = (
            v == maintainer.src
            or maintainer.state.dist[u] == INF
            or maintainer.state.dist[u] + old_w != maintainer.state.dist[v]
        )

        if is_cert:
            stats = maintainer.apply(upd)
            online_w = stats.work
            opt_w = stats.work  # Certificate work charged equally to both
        elif maintainer.state.tight[v] > 1:
            stats = maintainer.apply(upd)
            online_w = stats.work
            opt_w = stats.work  # Alt work charged equally to both
        else:
            # Sole tight edge lost: measure r_t and F_t on scratch copies
            scratch_state = maintainer.state.copy()
            scratch_g = maintainer.graph.copy()
            apply_update(scratch_g, upd)

            # Dry run repair with unlimited budget to measure true repair work r_t
            dry_counter = OpCounter()
            repair(
                scratch_state,
                scratch_g,
                u,
                v,
                budget=None,
                counter=dry_counter,
            )
            r_t = dry_counter.work

            # Scratch rebuild to measure true rebuild work F_t
            rebuild_counter = OpCounter()
            SPTState.build(scratch_g, maintainer.src, rebuild_counter)
            F_t = rebuild_counter.work

            opt_w = min(r_t, F_t)

            # Online maintainer execution
            stats = maintainer.apply(upd)
            online_w = stats.work

        strategy_counts[stats.strategy] = strategy_counts.get(stats.strategy, 0) + 1
        per_update_online.append(online_w)
        per_update_opt.append(opt_w)
        per_update_stats.append(stats)

        total_online += online_w
        total_opt += opt_w

    ratio = total_online / total_opt if total_opt > 0 else 1.0

    return MeasurementResult(
        online_cost=total_online,
        opt_cost=total_opt,
        ratio=ratio,
        updates_count=len(updates),
        strategy_counts=strategy_counts,
        per_update_online=per_update_online,
        per_update_opt=per_update_opt,
        per_update_stats=per_update_stats,
    )


__all__ = ["MeasurementResult", "measure", "theoretical_competitive_ratio"]
