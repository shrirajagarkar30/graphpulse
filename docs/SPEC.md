# GraphPulse-R Specification (SPEC.md)

**Frozen Specification: Graph Model, Update Model, Cost Model, and Core Invariants**

This document serves as the single source of truth for definitions, models, operation charges, and invariants for GraphPulse-R. All algorithms, proofs, data structures, and tests must adhere strictly to this specification.

---

## 1. Graph Model

A network is modeled as a directed graph $G = (V, E, w)$:
- **Vertices:** $V = \{0, 1, 2, \dots, n-1\}$, indexed contiguously from $0$.
- **Edges:** $E \subseteq V \times V$, directed pairs $(u, v)$.
  - **Simple Graph:** No self-loops ($(u, u) \notin E$) and no parallel edges (at most one directed edge from $u$ to $v$).
- **Weights:** Strictly positive integers: $w(u, v) \in \mathbb{Z}^+$ ($w(u, v) \ge 1$ for all $(u, v) \in E$). Floating-point weights and zero/negative weights are strictly prohibited.
- **Unreachability:** Distance from source $s$ to an unreachable vertex $v$ is $dist[v] = \infty$, represented in Python by `INF = float("inf")` (and encoded as `null` in JSON serialization).
- **INF Guard Rule:** In floating-point arithmetic, $\infty + w = \infty$. Therefore, evaluating `dist[u] + w == dist[v]` when `dist[u] == INF` falsely evaluates to `True` for unreachable nodes. **Every tight-edge test must explicitly check `dist[u] != INF` first.**

---

## 2. Dynamic Update Model

GraphPulse-R maintains single-source shortest path trees (SPT) under non-decreasing distance updates:
1. **Edge Deletion (`delete(u, v)`):**
   - Precondition: Directed edge $(u, v) \in E$.
   - Effect: Edge $(u, v)$ is removed from $G$, so $E \leftarrow E \setminus \{(u, v)\}$.
2. **Weight Increase (`increase(u, v, new_w)`):**
   - Precondition: Directed edge $(u, v) \in E$, with $new_w > w(u, v)$ where $new_w \in \mathbb{Z}^+$.
   - Effect: $w(u, v) \leftarrow new_w$.

*Note:* Edge insertions and weight decreases are out of scope for Phase 0 through Phase 4.

---

## 3. Core Definitions

### 3.1 Tight Edges
An edge $(u, v) \in E$ is **tight** with respect to a distance vector $dist$ rooted at source $s$ iff:
$$\text{tight}(u, v) \iff (dist[u] \ne \infty) \land (dist[u] + w(u, v) = dist[v])$$

Because edge weights are strictly positive ($w \ge 1$), the subgraph of tight edges is always an acyclic directed graph (DAG).

### 3.2 Tight In-Count (`tight[v]`)
For every vertex $v \in V$, `tight[v]` is the number of incoming tight edges:
$$tight[v] = |\{ u \in V : (u, v) \in E \text{ and } \text{tight}(u, v) \}|$$
- If $v = s$, $tight[s] = 0$ (the source has distance $0$ and no incoming shortest-path edges).
- If $v$ is unreachable ($dist[v] = \infty$), $tight[v] = 0$.
- If $v$ is reachable and $v \ne s$, $tight[v] \ge 1$.

### 3.3 Affected Set ($A$)
Following an update to an edge $(u, v)$, the **affected set** $A \subseteq V$ is the set of vertices whose shortest distance from source $s$ strictly increases:
$$A = \{ x \in V : dist_{new}[x] > dist_{old}[x] \}$$
Vertices in $V \setminus A$ retain their previous shortest path distance ($dist_{new}[x] = dist_{old}[x]$).

### 3.4 Full Rebuild Work ($F$)
$F$ denotes the total machine-independent operations executed by a complete from-scratch rebuild:
1. Running Dijkstra's algorithm from source $s$ on graph $G$.
2. Recounting all tight incoming edges across the graph to populate `tight[:]`.

### 3.5 Repair Work ($r$) and Budget ($B$)
- $r$ is the total machine-independent operations executed by an incremental repair procedure.
- $B$ is the operational budget cap:
$$B = \lceil c \cdot F \rceil$$
where $c > 0$ is the competitive factor (e.g., $c = 1.0$ for standard 2-competitive deterministic ski-rental). If repair exceeds $B$ operations, repair is aborted and a full rebuild is executed.

---

## 4. Cost Model (Machine-Independent Operation Charges)

All runtime bounds and performance metrics are measured via an explicit `OpCounter`. Wall-clock time is machine-dependent and never used for algorithmic assertions.

| Operation | Charge Condition | Algorithmic Context |
|---|---|---|
| **`SCAN`** | Each adjacency entry examined (forward or reverse), and the single $O(1)$ certificate check | Dijkstra edge relaxation, reverse BFS in repair, tight count calculation |
| **`PUSH`** | Each priority queue element insertion | Dijkstra heap insertion, repair priority queue insertions |
| **`POP`** | Each priority queue element extraction | Dijkstra heap pop (including stale entries), repair priority queue pop |
| **`QUEUE`** | Each FIFO queue enqueue or dequeue | Affected-set BFS propagation / discovery |

*State writes (updating `dist[v]`, `parent[v]`, or `tight[v]`) are not charged separately, as each write is uniquely caused by an already-charged SCAN, POP, or QUEUE operation (a standard constant-factor modeling assumption).*

---

## 5. Golden Graph Suite

The test suite validates algorithms against three hand-computed golden instances stored in `tests/golden/`:

### 5.1 `g1_diamond.json`
- **Description:** Diamond topology with two alternative equal-length shortest paths from source 0 to vertex 3.
- **Vertices:** $n = 4$, $V = \{0, 1, 2, 3\}$, source $s = 0$.
- **Edges:** $(0, 1, 1), (0, 2, 1), (1, 3, 1), (2, 3, 1)$.
- **Hand-computed Distances:** $dist = [0, 1, 1, 2]$.
- **Hand-computed Tight Counts:** $tight = [0, 1, 1, 2]$ (`tight[3] = 2` because both $(1, 3)$ and $(2, 3)$ are tight).

### 5.2 `g2_chain.json`
- **Description:** Linear directed chain.
- **Vertices:** $n = 4$, $V = \{0, 1, 2, 3\}$, source $s = 0$.
- **Edges:** $(0, 1, 2), (1, 2, 3), (2, 3, 4)$.
- **Hand-computed Distances:** $dist = [0, 2, 5, 9]$.
- **Hand-computed Tight Counts:** $tight = [0, 1, 1, 1]$.

### 5.3 `g3_unreachable.json`
- **Description:** Chain with an isolated/unreachable vertex having no incoming edges. Demonstrates the `INF` guard and handling of disconnected components.
- **Vertices:** $n = 5$, $V = \{0, 1, 2, 3, 4\}$, source $s = 0$.
- **Edges:** $(0, 1, 2), (1, 2, 3), (2, 3, 4)$.
- **Hand-computed Distances:** $dist = [0, 2, 5, 9, \text{null}]$ (vertex 4 is unreachable).
- **Hand-computed Tight Counts:** $tight = [0, 1, 1, 1, 0]$ (vertex 4 has 0 incoming tight edges).
