# Related work and novelty check (Milestone 8.3)

**Status: literature search NOT yet performed with sources.** This file records the *procedure* and the *current conservative novelty wording*. No paper below is asserted to say anything specific until it has been located and read; entries marked "to verify" are candidate starting points from general knowledge, not findings.

## Questions to answer

1. Does **budgeted repair with a rebuild fallback** (repair under a work cap `c·F`, abort for free on an overlay, rebuild, with a proven work bound and ski-rental competitive ratio) already exist for dynamic shortest paths?
2. Does the **lazy tour certificate** (skip an exact tour re-solve when no distance-matrix entry used by the incumbent tour changed, under monotone updates; ε-tolerant keep with a non-ratcheted lower bound) already exist?

## Candidate starting points (to verify before citing)

| Topic | Candidate | Status |
|---|---|---|
| Bounded incremental shortest-path repair | Ramalingam & Reps, dynamic shortest-path algorithms (1990s) | to verify |
| Decremental / fully dynamic APSP and SSSP | Even–Shiloach trees; Demetrescu & Italiano | to verify |
| Held–Karp dynamic program for TSP | Held & Karp (1962); Bellman (1962) | to verify |
| NP-completeness of Hamiltonian cycle | Karp (1972) | to verify |
| Ski rental and randomized e/(e−1) | Karlin, Manasse, Rudolph, Sleator; Karlin, Manasse, McGeoch, Owicki | to verify |
| Algorithms with predictions / reoptimization | literature on reoptimization of NP-hard problems | to verify |

## Search protocol (to run before submission)

Queries to record with date and database: "dynamic shortest path ski rental", "bounded repair rebuild threshold shortest path tree", "reoptimization traveling salesman edge weight increase", "certificate dynamic shortest path tree tight edge", "lazy re-solve vehicle routing edge weight increase".
For each hit: citation, one-sentence relevant claim *as read from the paper*, verdict on questions 1 and 2.

## Conservative novelty wording (used until the search says otherwise)

> GraphPulse-R **integrates** known ingredients (tight-edge certificates, bounded incremental repair, a rent-or-buy budget analysis, Held–Karp, and monotone-update reasoning for tours) and **evaluates them end to end in machine-independent operation counts**. We do not claim a new algorithm.

Reviewer sign-off on the final verdicts: PENDING.
