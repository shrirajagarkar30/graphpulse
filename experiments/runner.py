"""Seeded experiment runner with a cross-variant correctness check (Milestone 7.2).

One path from a config to a result row.  The update sequence is generated once
per (config minus variant) and replayed for every variant; every variant must
produce identical terminal matrices and tour costs (within 1 + eps in epsilon
mode).  A disagreement raises `CrossVariantMismatch` - it is a bug, not a result.

Results are reported in operation counts; `wall_seconds` is secondary and is
excluded from every equality check.
"""

from __future__ import annotations

import csv
import hashlib
import json
import math
import platform
import random
import subprocess
import sys
import time
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path

from graphpulse.dijkstra import INF, dijkstra
from graphpulse.generators import (
    Update, apply_update, comb_adversarial, grid, hub_spoke, partial_comb, random_sparse, random_updates,
)
from graphpulse.graph import DiGraph
from graphpulse.opcount import OpCounter
from graphpulse.pipeline import RoutingPipeline
from graphpulse.spt import SPTState
from graphpulse.tour import HELD_KARP_MAX_K, held_karp

VARIANTS = ("rebuild_always", "repair_always", "cert_only", "gp", "gp_random")
MODES = ("uniform", "clustered", "near_source", "tree_edges")
FAMILIES = {
    "grid": lambda p, seed: grid(p["rows"], p["cols"], seed=seed),
    "random_sparse": lambda p, seed: random_sparse(p["n"], p["m"], seed=seed),
    "hub_spoke": lambda p, seed: hub_spoke(p["hubs"], p["spokes"], seed=seed),
    "comb": lambda p, seed: comb_adversarial(p["n"]),
    "partial_comb": lambda p, seed: partial_comb(p["n"], p["frac"]),
}

COLUMNS = [
    "family", "params", "k", "variant", "c", "eps", "mode", "p_delete", "lazy_tour", "seed",
    "T_requested", "T_actual", "updates_sha", "matrix_sha",
    "tree_work", "hk_transitions", "strat_cert", "strat_alt", "strat_repair", "strat_fallback",
    "strat_rebuild", "mean_touched", "mean_dist_changed", "worst_update_work",
    "kept", "kept_eps", "resolved", "infeasible", "wall_seconds",
]


class CrossVariantMismatch(RuntimeError):
    """Two variants disagreed on a matrix or tour cost."""


@dataclass
class RunConfig:
    family: str
    family_params: dict
    k: int
    variant: str = "gp"
    c: float = 1.0
    eps: float = 0.0
    mode: str = "uniform"
    p_delete: float = 0.05
    T: int = 100
    seed: int = 0
    lazy_tour: bool = True

    def validate(self) -> None:
        if self.variant not in VARIANTS:
            raise ValueError(f"unknown variant {self.variant!r}; expected one of {VARIANTS}")
        if self.family not in FAMILIES:
            raise ValueError(f"unknown family {self.family!r}")
        if self.mode not in MODES:
            raise ValueError(f"unknown mode {self.mode!r}")
        if isinstance(self.T, bool) or not isinstance(self.T, int) or self.T <= 0:
            raise ValueError(f"T must be a positive integer, got {self.T!r}")
        if isinstance(self.k, bool) or not isinstance(self.k, int) or not (0 <= self.k <= HELD_KARP_MAX_K):
            raise ValueError(f"k must be an integer in 0..{HELD_KARP_MAX_K}, got {self.k!r}")
        if not isinstance(self.c, (int, float)) or isinstance(self.c, bool) or self.c < 0:
            raise ValueError(f"c must be a non-negative number, got {self.c!r}")
        if not isinstance(self.eps, (int, float)) or isinstance(self.eps, bool) or self.eps < 0 or math.isinf(self.eps):
            raise ValueError(f"eps must be a finite non-negative number, got {self.eps!r}")
        if not (0.0 <= self.p_delete <= 1.0):
            raise ValueError(f"p_delete must be in [0, 1], got {self.p_delete!r}")

    def group_key(self) -> tuple:
        """Everything except the variant (and the variant-specific c / lazy switches)."""
        return (self.family, json.dumps(self.family_params, sort_keys=True), self.k, self.eps, self.mode,
                self.p_delete, self.T, self.seed)


@dataclass
class Instance:
    graph: DiGraph
    terminals: list[int]
    updates: list[Update]
    updates_sha: str


@dataclass
class RunResult:
    row: dict
    costs: list[float] = field(default_factory=list)


def build_instance(cfg: RunConfig) -> Instance:
    cfg.validate()
    g = FAMILIES[cfg.family](cfg.family_params, cfg.seed)
    if cfg.k + 1 > g.n:
        raise ValueError(f"k={cfg.k} needs {cfg.k + 1} vertices but the graph has {g.n}")
    terminals = [0] + random.Random(cfg.seed).sample(range(1, g.n), cfg.k)
    updates = random_updates(g, cfg.T, seed=cfg.seed, mode=cfg.mode, p_delete=cfg.p_delete)
    sha = hashlib.sha256(repr([(u.kind, u.u, u.v, u.new_w) for u in updates]).encode()).hexdigest()[:16]
    return Instance(g, terminals, updates, sha)


def _fmt(x: float) -> str:
    return "inf" if math.isinf(x) else str(x)


def _run_rebuild_always(cfg: RunConfig, inst: Instance) -> RunResult:
    g = inst.graph.copy()
    terms = inst.terminals
    tree_work = hk = worst = 0
    costs: list[float] = []
    msha = hashlib.sha256()
    t0 = time.perf_counter()
    for upd in inst.updates:
        apply_update(g, upd)
        work = 0
        D = []
        for a in terms:
            c = OpCounter()
            st = SPTState.build(g, a, c)       # full rebuild incl. tight recount = F
            work += c.work
            D.append([st.dist[b] for b in terms])
        cnt = OpCounter()
        cost, _ = held_karp(D, cnt)
        tree_work += work
        hk += cnt.dp
        worst = max(worst, work)
        costs.append(cost)
        msha.update(repr(D).encode())
    n_upd = len(inst.updates)
    row = _row(cfg, inst, tree_work, hk, {"rebuild": n_upd * len(terms)}, 0.0, 0.0, worst,
               {}, msha.hexdigest()[:16], time.perf_counter() - t0)
    return RunResult(row, costs)


def _run_pipeline(cfg: RunConfig, inst: Instance) -> RunResult:
    c: float | str = {"repair_always": math.inf, "cert_only": 0.0, "gp": cfg.c, "gp_random": "random"}[cfg.variant]
    pipe = RoutingPipeline(inst.graph, inst.terminals, c=c, eps=cfg.eps, lazy_tour=cfg.lazy_tour, seed=cfg.seed)
    tree_work = hk = worst = 0
    strat: dict[str, int] = {}
    actions: dict[str, int] = {}
    touched = changed = 0
    costs: list[float] = []
    msha = hashlib.sha256()
    t0 = time.perf_counter()
    for upd in inst.updates:
        s = pipe.apply(upd)
        tree_work += s.total_work
        hk += s.hk_transitions
        worst = max(worst, s.total_work)
        touched += s.touched_trees
        changed += s.dist_changed_trees
        for name, cnt in s.strategy_counts.items():
            strat[name] = strat.get(name, 0) + cnt
        actions[s.route_action] = actions.get(s.route_action, 0) + 1
        costs.append(s.tour_cost)
        msha.update(repr(pipe.matrix.D).encode())
    n_upd = max(1, len(inst.updates))
    row = _row(cfg, inst, tree_work, hk, strat, touched / n_upd, changed / n_upd, worst,
               actions, msha.hexdigest()[:16], time.perf_counter() - t0)
    return RunResult(row, costs)


def _row(cfg, inst, tree_work, hk, strat, mean_touched, mean_changed, worst, actions, msha, wall) -> dict:
    return {
        "family": cfg.family, "params": json.dumps(cfg.family_params, sort_keys=True), "k": cfg.k,
        "variant": cfg.variant, "c": _fmt(float(cfg.c)), "eps": cfg.eps, "mode": cfg.mode,
        "p_delete": cfg.p_delete, "lazy_tour": int(cfg.lazy_tour), "seed": cfg.seed,
        "T_requested": cfg.T, "T_actual": len(inst.updates), "updates_sha": inst.updates_sha, "matrix_sha": msha,
        "tree_work": tree_work, "hk_transitions": hk,
        "strat_cert": strat.get("cert", 0), "strat_alt": strat.get("alt", 0),
        "strat_repair": strat.get("repair", 0), "strat_fallback": strat.get("fallback", 0),
        "strat_rebuild": strat.get("rebuild", 0),
        "mean_touched": round(mean_touched, 6), "mean_dist_changed": round(mean_changed, 6),
        "worst_update_work": worst,
        "kept": actions.get("kept", 0), "kept_eps": actions.get("kept_eps", 0),
        "resolved": actions.get("resolved", 0), "infeasible": actions.get("infeasible", 0),
        "wall_seconds": round(wall, 4),
    }


def run_one(cfg: RunConfig, inst: Instance | None = None) -> RunResult:
    cfg.validate()
    inst = inst or build_instance(cfg)
    return _run_rebuild_always(cfg, inst) if cfg.variant == "rebuild_always" else _run_pipeline(cfg, inst)


def run_group(
    base: RunConfig,
    variants: tuple[str, ...] | list[str] = VARIANTS,
    lazy_flags: tuple[bool, ...] = (True,),
) -> list[dict]:
    """Run several variants on the identical update sequence and cross-check them.

    The reference is an exact `rebuild_always` run (reused if requested).  Raises
    `CrossVariantMismatch` on any disagreement of matrices or tour costs.
    """
    base.validate()
    inst = build_instance(base)
    ref_cfg = RunConfig(**{**asdict(base), "variant": "rebuild_always"})
    ref = run_one(ref_cfg, inst)
    rows: list[dict] = []
    done_ref = False
    for v in variants:
        for lazy in (lazy_flags if v != "rebuild_always" else (True,)):
            cfg = RunConfig(**{**asdict(base), "variant": v, "lazy_tour": lazy})
            if v == "rebuild_always":
                res, done_ref = ref, True
                res = RunResult({**ref.row, "variant": "rebuild_always"}, ref.costs)
            else:
                res = run_one(cfg, inst)
            _cross_check(cfg, ref, res)
            rows.append(res.row)
    return rows


def _cross_check(cfg: RunConfig, ref: RunResult, res: RunResult) -> None:
    if len(res.costs) != len(ref.costs):
        raise CrossVariantMismatch(f"{cfg.variant}: {len(res.costs)} costs vs reference {len(ref.costs)}")
    exact = cfg.variant == "rebuild_always" or cfg.eps == 0
    if res.row["matrix_sha"] != ref.row["matrix_sha"]:
        raise CrossVariantMismatch(f"{cfg.variant}: terminal matrices differ from the reference")
    for i, (a, b) in enumerate(zip(res.costs, ref.costs)):
        if math.isinf(a) and math.isinf(b):
            continue
        ok = (a == b) if exact else (b <= a <= (1 + cfg.eps) * b)
        if not ok:
            raise CrossVariantMismatch(f"{cfg.variant}: tour cost {a} vs reference {b} at update {i}")


# ------------------------------------------------------------------ output
def git_short_hash() -> str:
    try:
        out = subprocess.run(["git", "rev-parse", "--short", "HEAD"], capture_output=True, text=True,
                             cwd=Path(__file__).resolve().parent.parent, timeout=10)
        return out.stdout.strip() or "unknown"
    except Exception:
        return "unknown"


def write_rows(rows: list[dict], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=COLUMNS, lineterminator="\n")
        w.writeheader()
        for r in rows:
            w.writerow({c: r[c] for c in COLUMNS})


def write_meta(path: Path, seeds: list[int], extra: dict | None = None) -> None:
    import graphpulse

    meta = {
        "git_hash": git_short_hash(),
        "python": sys.version.split()[0],
        "platform": platform.platform(),
        "graphpulse": graphpulse.__version__,
        "seeds": sorted(set(seeds)),
        "utc_time": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "packages": _package_versions(),
    }
    meta.update(extra or {})
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(meta, indent=2, sort_keys=True), encoding="utf-8")


def _package_versions() -> dict[str, str]:
    from importlib import metadata

    out = {}
    for name in ("pytest", "hypothesis", "networkx", "pandas", "matplotlib"):
        try:
            out[name] = metadata.version(name)
        except metadata.PackageNotFoundError:
            pass
    return out


__all__ = [
    "COLUMNS", "CrossVariantMismatch", "FAMILIES", "Instance", "MODES", "RunConfig", "RunResult", "VARIANTS",
    "build_instance", "git_short_hash", "run_group", "run_one", "write_meta", "write_rows",
]
