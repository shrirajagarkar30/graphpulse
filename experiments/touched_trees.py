"""Distribution of `touched_trees` per update (Milestone 5.4).

Prints, per graph family and update mode, how many of the k+1 trees did real
work (strategy other than 'cert') on each update, and how many had a changed
distance.  Output goes to stdout only and is NOT committed; numbers from this
script must not be quoted in documents until Phase 7 regenerates them from
the seeded experiment runner.

Usage: python experiments/touched_trees.py [--updates N] [--k K] [--seed S] [--small]
"""

from __future__ import annotations

import argparse
import random
from collections import Counter

from graphpulse.generators import comb_adversarial, grid, hub_spoke, random_sparse, random_updates
from graphpulse.terminals import MultiTreeManager


def families(small: bool, seed: int):
    if small:
        return [
            ("grid", grid(8, 8, seed=seed)),
            ("random_sparse", random_sparse(60, 300, seed=seed)),
            ("hub_spoke", hub_spoke(4, 10, seed=seed)),
            ("comb", comb_adversarial(60)),
        ]
    return [
        ("grid", grid(20, 20, seed=seed)),
        ("random_sparse", random_sparse(400, 2000, seed=seed)),
        ("hub_spoke", hub_spoke(10, 40, seed=seed)),
        ("comb", comb_adversarial(200)),
    ]


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--updates", type=int, default=500)
    ap.add_argument("--k", type=int, default=8)
    ap.add_argument("--seed", type=int, default=0)
    ap.add_argument("--small", action="store_true")
    a = ap.parse_args(argv)

    print(f"seed={a.seed} k={a.k} updates<={a.updates} (c=1, last-F); NOT for documents")
    print(f"{'family':<14}{'mode':<12}{'n_upd':>6}{'mean touched':>14}{'mean dist-changed':>19}  histogram touched:count")
    for name, g in families(a.small, a.seed):
        terms = [0] + random.Random(a.seed).sample(range(1, g.n), a.k)
        for mode in ("uniform", "clustered", "near_source"):
            ups = random_updates(g, a.updates, seed=a.seed, mode=mode, p_delete=0.05)
            mgr = MultiTreeManager(g, terms)
            hist: Counter[int] = Counter()
            changed = 0
            for u in ups:
                st = mgr.apply(u)
                assert 0 <= st.touched_trees <= a.k + 1
                hist[st.touched_trees] += 1
                changed += st.dist_changed_trees
            n = max(1, len(ups))
            mean_t = sum(t * c for t, c in hist.items()) / n
            h = " ".join(f"{t}:{hist[t]}" for t in sorted(hist))
            print(f"{name:<14}{mode:<12}{len(ups):>6}{mean_t:>14.2f}{changed / n:>19.2f}  {h}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
