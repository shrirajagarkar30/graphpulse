# Proof P4: NP-Completeness of the Directed Tour Decision Problem

**Reviewer sign-off:** PENDING (requires two team members other than the author; not signed by the tool that drafted this file)

**Milestone 6.6.** Justifies why the exact tour layer is restricted to small k (Held–Karp, k ≤ 18).

## 1. Problem

**DTOUR.** Instance: a complete directed matrix `D` over terminals `0..k` (entries non-negative integers, `D[i][i]=0`) and an integer `B`. Question: does a permutation `π` of `1..k` exist with
`cost(π) = D[0][π₁] + Σ D[π_r][π_{r+1}] + D[π_k][0] ≤ B`?

**Scope statement (important).** This proves that the *tour problem on a distance matrix* is NP-complete. It does **not** make the dynamic-update system "NP-complete"; the shortest-path layer is polynomial.

## 2. Membership in NP
A certificate is the permutation `π`. Computing `cost(π)` takes `O(k)` additions of numbers of polynomial bit-length; compare with `B`. Hence DTOUR ∈ NP.

## 3. NP-hardness (reduction from directed Hamiltonian cycle)

**DHC.** Given a digraph `H = (V_H, E_H)` with `h = |V_H| ≥ 3`, does `H` contain a directed cycle visiting every vertex exactly once? DHC is NP-complete (Karp, 1972).

**Construction.** Let `G` be the complete digraph on `V_H` with weight `w(a,b) = 1` if `(a,b) ∈ E_H` and `w(a,b) = 2` otherwise. Take all `h` vertices as terminals; fix any vertex as the depot (vertex 0), the other `h−1` are stops (`k = h−1`). Set `B = h`. Construction time `O(h²)`.

**Lemma 1 (distance matrix equals the weights).** For all `a ≠ b`, `dist_G(a,b) = w(a,b)`.
*Proof.* Any path of at least two edges costs ≥ 2 (each edge weighs ≥ 1). The direct edge costs 1 or 2. If `w(a,b)=1` the direct edge is shortest (nothing is cheaper than 1). If `w(a,b)=2` any path costs ≥ 2 = `w(a,b)`, so the direct edge is shortest. ∎ (Executable check: `tests/test_np_reduction.py`, T6.6-04.)

**Lemma 2.** A tour of cost ≤ h exists iff `H` has a Hamiltonian cycle.
*Proof.* A tour visits all `h` terminals and returns, so it uses exactly `h` legs, each of cost ≥ 1 (Lemma 1), hence `cost ≥ h`, with equality iff every leg has cost 1, i.e. every leg is an edge of `E_H`. A tour all of whose legs are edges of `E_H` is a closed walk through all `h` vertices using `h` edges, i.e. a Hamiltonian cycle; conversely a Hamiltonian cycle rotated to start at the depot gives such a tour. ∎

Since DHC reduces to DTOUR in polynomial time, DTOUR is NP-hard; with §2 it is NP-complete. ∎

## 4. Consequences for the project
* No polynomial exact algorithm is expected; Held–Karp `Θ(k²2ᵏ)` time / `Θ(k2ᵏ)` space is the standard exact method, and the project caps `k ≤ 18`.
* The reduction also gives the cost range `h ≤ OPT ≤ 2h` on the constructed instances (T6.6-05).
* Executable evidence: `tests/test_np_reduction.py` checks the iff property on 300 random digraphs (`h ∈ 4..6`), 100 planted yes-instances and 100 no-instances.
