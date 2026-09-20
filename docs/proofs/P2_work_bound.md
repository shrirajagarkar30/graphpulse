# Proof P2: Per-Update Machine-Independent Work Bound

**Milestone 4.3: Per-Update Worst-Case Work Analysis**

This document establishes the formal per-update machine-independent work bound for `BudgetedMaintainer` under the operational cost model specified in `SPEC.md`.

---

## 1. Algorithmic Cost Model and Definitions

As established in `SPEC.md`, work is measured exclusively in terms of explicit, machine-independent operation charges:

$$\text{Work} = \text{SCAN} + \text{PUSH} + \text{POP} + \text{QUEUE}$$

where:
- **`SCAN`**: Each adjacency entry inspected (forward or reverse), plus $O(1)$ certificate checks.
- **`PUSH`**: Each element inserted into a priority queue.
- **`POP`**: Each element extracted from a priority queue (including stale items).
- **`QUEUE`**: Each vertex enqueue or dequeue in FIFO queues during affected-set BFS propagation.

Per `SPEC.md`, state writes (updating `dist`, `parent`, or `tight`) are not charged separately because each write is uniquely caused by an already-charged SCAN, POP, or QUEUE operation.

### 1.1 Full Rebuild Work ($F$)
For a directed graph $G = (V, E, w)$ and source $s \in V$, the full from-scratch rebuild work $F$ consists of:
1. **Dijkstra tree construction:** $\text{dijkstra\_work} = \text{SCAN}_{\text{Dijkstra}} + \text{PUSH}_{\text{Dijkstra}} + \text{POP}_{\text{Dijkstra}}$.
2. **Tight in-count initialization:** Scanning all incoming edges for each reachable non-source vertex $v \in V \setminus \{s\}$ with $dist[v] < \infty$:
   $$\text{recount\_scans} = \sum_{v \in V \setminus \{s\}, dist[v] < \infty} \text{indeg}(v)$$
Hence:
$$F = \text{dijkstra\_work} + \sum_{v \in V \setminus \{s\}, dist[v] < \infty} \text{indeg}(v)$$
By construction, $F \ge 1$ for any reachable graph with $n \ge 2$.

### 1.2 The Budget Cap ($B$)
Given a competitive multiplier $c \ge 0$, the operational work cap for an update is:
$$B = \lceil c \cdot F \rceil$$
where $F$ is either:
- $F_{\text{last}}$: The rebuild work recorded during the most recent from-scratch rebuild (`f_mode="last"`).
- $F_{\text{true}}$: The exact rebuild work measured on the updated graph $G_t$ (`f_mode="oracle"`).

---

## 2. Decision Ordering and Strategy Case Analysis

For every non-decreasing update (edge deletion or weight increase of $(u, v)$):

### Case 1: Certificate Check (Strategy `cert`)
If $v = s$, or $dist[u] = \infty$, or $dist[u] + w_{\text{old}}(u, v) \ne dist[v]$:
- The edge was not tight in the shortest-path DAG (or directed into the source).
- By Proof P1, shortest-path distances and tree structure are strictly invariant.
- The algorithm charges exactly $1$ SCAN to evaluate the certificate condition and returns.
$$\text{work}_{\text{cert}} = 1 \le (1 + c) F + 1$$

### Case 2: Alternative Support (Strategy `alt`)
If the edge was tight ($dist[u] + w_{\text{old}} = dist[v]$) but $tight[v] > 1$:
- By Proof P1, vertex $v$ retains at least one other tight incoming edge, so its distance is invariant ($dist_{\text{new}}[v] = dist_{\text{old}}[v]$).
- $tight[v]$ is decremented by 1.
- If $parent[v] \ne u$, the tree structure is unchanged:
  $$\text{work}_{\text{alt}} = 1 \text{ SCAN}$$
- If $parent[v] = u$, incoming edges of $v$ are scanned to choose the smallest-id tight in-neighbor as the new parent:
  $$\text{work}_{\text{alt}} = 1 + \text{indeg}(v) \text{ SCANs}$$
Since $\text{indeg}(v) \le F$, we have $\text{work}_{\text{alt}} \le 1 + F \le (1 + c) F + 1$ for all $c \ge 0$.

### Case 3: Sole-Tight Edge Lost (Strategy `repair` or `fallback`)
When $tight[v] \le 1$, the sole tight in-edge supporting $v$ is invalidated. The maintainer invokes bounded repair under budget $B = \lceil c \cdot F \rceil$.

#### Case 3a: Bounded Repair Completes (Strategy `repair`)
If the incremental repair completes without exceeding $B$:
- Total work performed is $r = \text{work}_{\text{repair}} \le B = \lceil c \cdot F \rceil$.
- All changes in the copy-on-write overlay are committed to the base state.
- Fallback work is $0$.
$$\text{repair\_work} + \text{fallback\_work} = r + 0 \le \lceil c \cdot F \rceil \le c \cdot F + 1 \le (1 + c) F + 1$$

#### Case 3b: Budget Exceeded and Fallback Rebuild (Strategy `fallback`)
If at any point during identification or local Dijkstra recompute the accumulated work exceeds $B$:

1. **Wasted Work Bound (Abort Slack of 1):**
   - Work is charged in discrete integer increments ($+1$ per SCAN, PUSH, POP, or QUEUE).
   - The budget check $\Delta \text{work} > B$ executes immediately after each increment.
   - The check triggers on the exact operation that causes $\Delta \text{work}$ to equal $B + 1$.
   - Therefore, the repair aborts immediately with wasted work:
     $$\text{repair\_work} \le B + 1 = \lceil c \cdot F \rceil + 1$$
   - The copy-on-write `Overlay` is discarded, leaving the base state completely unmodified (deeply identical to the pre-update state).

2. **Rebuild Work:**
   - The maintainer executes a fresh from-scratch rebuild using `SPTState.build`.
   - The rebuild incurs work equal to the true rebuild cost of the updated graph:
     $$\text{fallback\_work} = F_{\text{true}}$$

3. **Total Work:**
   $$\begin{aligned}
   \text{total\_algorithm\_work} &= \text{repair\_work} + \text{fallback\_work} \\
   &\le (B + 1) + F_{\text{true}} \\
   &= \lceil c \cdot F \rceil + 1 + F_{\text{true}}
   \end{aligned}$$

When evaluated in oracle mode ($F = F_{\text{true}}$):
- If $c \cdot F$ is integer-valued: $\lceil c \cdot F \rceil = c \cdot F$.
  $$\text{total\_algorithm\_work} \le c \cdot F_{\text{true}} + 1 + F_{\text{true}} = (1 + c) F_{\text{true}} + 1$$
- In general, with ceil:
  $$\text{repair\_work} + \text{fallback\_work} \le (1 + c) F_{\text{true}} + 1 + \mathbf{1}_{\{c F \notin \mathbb{Z}\}}$$

---

## 3. Main Theorem (Per-Update Work Bound)

### Theorem 1 (Per-Update Work Bound)
*For any directed graph $G = (V, E, w)$ with strictly positive integer weights, any non-decreasing update (edge deletion or weight increase), and any competitive multiplier $c \ge 0$, the machine-independent work performed by `BudgetedMaintainer` in oracle mode satisfies:*

$$\text{repair\_work} + \text{fallback\_work} \le (1 + c) F_{\text{true}} + 1$$

*for integer-valued $c \cdot F_{\text{true}}$, and at most $(1 + c) F_{\text{true}} + 2$ in all cases.*

#### Proof:
The result follows directly from the exhaustive case analysis in Section 2:
- If the update is resolved by Certificate: $\text{repair\_work} = \text{fallback\_work} = 0 \le (1 + c) F_{\text{true}} + 1$.
- If resolved by Alternative Support: $\text{repair\_work} = \text{fallback\_work} = 0 \le (1 + c) F_{\text{true}} + 1$.
- If resolved by Repair (Case 3a): $\text{repair\_work} \le \lceil c \cdot F_{\text{true}} \rceil \le c \cdot F_{\text{true}} + 1 \le (1 + c) F_{\text{true}} + 1$ and $\text{fallback\_work} = 0$.
- If resolved by Fallback (Case 3b): $\text{repair\_work} \le \lceil c \cdot F_{\text{true}} \rceil + 1$ and $\text{fallback\_work} = F_{\text{true}}$.
  Summing gives $\lceil c \cdot F_{\text{true}} \rceil + F_{\text{true}} + 1 \le (1 + c) F_{\text{true}} + 1$ for integer $c F_{\text{true}}$.
$\blacksquare$

---

## 4. Sequence Amortization

For a sequence of $T$ updates $\sigma = (u_1, \dots, u_T)$:
$$\sum_{t=1}^T (\text{repair\_work}_t + \text{fallback\_work}_t) \le \sum_{t=1}^T (1 + c) F_{\text{true}, t} + T$$

The additive term $T$ represents the maximum cumulative abort slack across the sequence (at most $1$ per update). In large graphs where $F_t \gg 1$, $\frac{T}{\sum F_t} \to 0$, rendering the slack asymptotically negligible.
