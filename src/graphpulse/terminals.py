"""Multi-terminal shortest-path engine (Milestones 5.2-5.3).

`MultiTreeManager` keeps one budgeted shortest-path tree per terminal on a
single shared graph.  The graph is mutated exactly once per update; every tree
then processes the update using the weight the edge had *before* it.  Each tree
has its own F and its own budget (nothing is shared between trees).

`terminals[0]` is the depot.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from graphpulse.controller import BudgetedMaintainer, RandomizedBudget
from graphpulse.generators import Update, apply_update
from graphpulse.graph import DiGraph
from graphpulse.maintainer import UpdateStats
from graphpulse.dijkstra import INF
from graphpulse.verify import InvariantViolation, check_state


@dataclass
class MultiStats:
    """Per-update statistics over all trees.

    touched_trees       : trees whose strategy is not 'cert' (includes 'alt').
    dist_changed_trees  : trees whose distances actually changed ('repair' or
                          'fallback'; 'alt' and 'cert' never change a distance).
    total_work          : sum of per-tree work.
    """

    per_tree: list[UpdateStats]
    touched_trees: int
    dist_changed_trees: int
    total_work: int
    strategy_counts: dict[str, int] = field(default_factory=dict)


class MultiTreeManager:
    """k+1 budgeted shortest-path trees on one shared graph."""

    def __init__(
        self,
        g: DiGraph,
        terminals: list[int],
        c: float | str = 1.0,
        f_mode: str = "last",
        verify: bool = False,
        seed: int | None = None,
    ) -> None:
        if not isinstance(terminals, (list, tuple)) or len(terminals) == 0:
            raise ValueError("terminals must be a non-empty list of vertex ids")
        for t in terminals:
            if isinstance(t, bool) or not isinstance(t, int) or not (0 <= t < g.n):
                raise ValueError(f"Terminal {t!r} out of range [0, {g.n - 1}]")
        if len(set(terminals)) != len(terminals):
            raise ValueError(f"Terminals must be distinct, got {list(terminals)!r}")

        self._g: DiGraph = g.copy()
        self._terminals: list[int] = list(terminals)
        self._verify = verify
        self._trees: list[BudgetedMaintainer] = []
        for i, t in enumerate(self._terminals):
            if isinstance(c, str) and c.lower() == "random":
                # Independent randomized-budget stream per tree.
                cc: float | str | RandomizedBudget = RandomizedBudget(seed=(42 if seed is None else seed) + i)
            else:
                cc = c
            self._trees.append(
                BudgetedMaintainer(self._g, t, c=cc, f_mode=f_mode, own_graph=False)
            )
        self._last: MultiStats | None = None

    @property
    def graph(self) -> DiGraph:
        return self._g

    @property
    def terminals(self) -> list[int]:
        return list(self._terminals)

    @property
    def trees(self) -> list[BudgetedMaintainer]:
        return list(self._trees)

    @property
    def k(self) -> int:
        """Number of delivery stops (terminals excluding the depot)."""
        return len(self._terminals) - 1

    @property
    def last_stats(self) -> MultiStats | None:
        return self._last

    def apply(self, update: Update) -> MultiStats:
        """Mutate the shared graph once, then let every tree handle the update.

        Raises ValueError (nothing modified) if the update is invalid.
        """
        old_w = apply_update(self._g, update)
        per_tree = [tree.handle_applied(update, old_w) for tree in self._trees]

        counts: dict[str, int] = {}
        for s in per_tree:
            counts[s.strategy] = counts.get(s.strategy, 0) + 1
        stats = MultiStats(
            per_tree=per_tree,
            touched_trees=sum(1 for s in per_tree if s.strategy != "cert"),
            dist_changed_trees=sum(1 for s in per_tree if s.strategy in ("repair", "fallback")),
            total_work=sum(s.work for s in per_tree),
            strategy_counts=counts,
        )
        self._last = stats
        if self._verify:
            for tree in self._trees:
                check_state(self._g, tree.state)
        return stats


class TerminalMatrix:
    """Terminal distance matrix D[i][j] = dist from terminals[i] to terminals[j].

    Entries are ints or INF; D[i][i] = 0.  Updates are increase-only, so no entry
    may ever decrease: `refresh()` raises InvariantViolation (leaving the stored
    matrix untouched) if one does.  The O(k^2) comparison per refresh is
    bookkeeping, not shortest-path work; it is counted separately in
    `matrix_cells` so the main work metric stays comparable with single-tree runs.
    """

    def __init__(self, manager: MultiTreeManager) -> None:
        self._mgr = manager
        self.matrix_cells: int = 0
        self._D: list[list[float]] = self._read()

    def _read(self) -> list[list[float]]:
        terms = self._mgr.terminals
        return [[tree.state.dist[t] for t in terms] for tree in self._mgr.trees]

    @property
    def D(self) -> list[list[float]]:
        """A copy of the current matrix."""
        return [row[:] for row in self._D]

    def refresh(self) -> set[tuple[int, int]]:
        """Recompute the matrix from the trees; return the set of changed entries."""
        new = self._read()
        size = len(new)
        self.matrix_cells += size * size
        changed: set[tuple[int, int]] = set()
        for i in range(size):
            for j in range(size):
                old_v, new_v = self._D[i][j], new[i][j]
                if new_v < old_v:
                    raise InvariantViolation(
                        f"Monotonicity violated: D[{i}][{j}] decreased from {old_v} to {new_v}"
                    )
                if new_v != old_v:
                    changed.add((i, j))
        self._D = new
        return changed

    def snapshot(self) -> tuple[tuple[float, ...], ...]:
        """Immutable copy of the current matrix."""
        return tuple(tuple(row) for row in self._D)

    def is_complete(self) -> bool:
        """True when every off-diagonal entry is finite."""
        n = len(self._D)
        return all(self._D[i][j] != INF for i in range(n) for j in range(n) if i != j)


__all__ = ["MultiStats", "MultiTreeManager", "TerminalMatrix"]
