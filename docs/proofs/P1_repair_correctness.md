# Proof P1: Correctness of Incremental Shortest-Path Repair

**Milestone 3.1: Foundation for Incremental Shortest-Path Repair**

This document establishes the mathematical foundations for GraphPulse-R's incremental shortest-path repair algorithms. It proves that the tight-edge subgraph is a Directed Acyclic Graph (DAG) under strictly positive integer weights, and formalizes why vertices retaining alternative tight support do not change distance under edge deletions and weight increases.

---

## 1. Graph Model and Core Definitions

Let $G = (V, E, w)$ be a directed graph conforming to `SPEC.md`:
- $V = \{0, 1, \dots, n-1\}$.
- $E \subseteq V \times V$ contains no self-loops and no parallel edges.
- Edge weights are strictly positive integers: $w(u, v) \in \mathbb{Z}^+$ ($w(u, v) \ge 1$ for all $(u, v) \in E$).
- For a fixed source $s \in V$, $dist[v] \in \mathbb{R}_{\ge 0} \cup \{\infty\}$ denotes the exact shortest-path distance from $s$ to $v$.
- Unreachable vertices have $dist[v] = \infty$ (represented by `float('inf')`).

### 1.1 Definition: Tight Edge
An edge $(u, v) \in E$ is **tight** with respect to $dist$ rooted at source $s$ if and only if:
$$\text{tight}(u, v) \iff (dist[u] \ne \infty) \land (dist[u] + w(u, v) = dist[v])$$

> **INF Guard Rule:** In IEEE 754 floating-point arithmetic, $\infty + w = \infty$. Thus, if $dist[u] = \infty$ and $dist[v] = \infty$, the equality $dist[u] + w = dist[v]$ would evaluate to `True`. The condition $dist[u] \ne \infty$ is mathematically and programmatically mandatory to prevent spurious tight edges between unreachable vertices.

### 1.2 Definition: Tight-Edge Subgraph
The **tight-edge subgraph** $G_T = (V_T, E_T)$ is defined by:
- $V_T = \{ v \in V : dist[v] \ne \infty \}$ (the set of reachable vertices).
- $E_T = \{ (u, v) \in E : \text{tight}(u, v) \}$.

### 1.3 Definition: Tight In-Count
For every vertex $v \in V$, the tight in-count $tight[v]$ is:
$$tight[v] = |\{ u \in V : (u, v) \in E_T \}|$$
- By definition, $tight[s] = 0$ (the source has distance $0$ and no incoming edges in any shortest path from $s$).
- For any unreachable vertex $v \in V \setminus V_T$, $tight[v] = 0$.
- For every reachable non-source vertex $v \in V_T \setminus \{s\}$, $tight[v] \ge 1$.

---

## 2. Structural Property: Acyclicity of Tight Subgraph

### Claim 1 (DAG Property)
*For any graph $G$ with strictly positive edge weights ($w(u, v) \ge 1$ for all $(u, v) \in E$), the tight-edge subgraph $G_T = (V_T, E_T)$ is a Directed Acyclic Graph (DAG).*

#### Proof:
We proceed by contradiction.
Suppose $G_T$ contains a directed cycle $C = (v_0, v_1, \dots, v_k, v_0)$ of length $k + 1 \ge 1$, where $(v_i, v_{i+1}) \in E_T$ for each $i \in \{0, \dots, k-1\}$ and $(v_k, v_0) \in E_T$.

By definition of $V_T$, every vertex in $C$ has a finite distance: $dist[v_i] < \infty$ for all $i$.
Because each edge in $C$ is tight, the following equations hold:
$$\begin{aligned}
dist[v_1] &= dist[v_0] + w(v_0, v_1) \\
dist[v_2] &= dist[v_1] + w(v_1, v_2) \\
&\;\;\vdots \\
dist[v_k] &= dist[v_{k-1}] + w(v_{k-1}, v_k) \\
dist[v_0] &= dist[v_k] + w(v_k, v_0)
\end{aligned}$$

Summing these $k+1$ equations:
$$\sum_{i=0}^k dist[v_i] = \sum_{i=0}^k dist[v_i] + \sum_{i=0}^{k-1} w(v_i, v_{i+1}) + w(v_k, v_0)$$

Because all distances $dist[v_i]$ are finite real numbers, we subtract the finite sum $\sum_{i=0}^k dist[v_i]$ from both sides:
$$0 = \sum_{i=0}^{k-1} w(v_i, v_{i+1}) + w(v_k, v_0)$$

However, by the graph model, all edge weights are strictly positive integers:
$$w(u, v) \ge 1 \quad \forall (u, v) \in E$$
Therefore:
$$\sum_{i=0}^{k-1} w(v_i, v_{i+1}) + w(v_k, v_0) \ge k + 1 \ge 1 > 0$$

This yields $0 \ge 1$, a contradiction.
Hence, $G_T$ cannot contain any directed cycle. $G_T$ is a DAG. $\blacksquare$

### Corollary 1.1 (Topological Ordering by Distance)
*The distance function $dist : V_T \to \mathbb{R}_{\ge 0}$ induces a valid strict topological ordering on $G_T$. Specifically, for every directed edge $(u, v) \in E_T$:*
$$dist[u] < dist[v]$$

#### Proof:
Since $(u, v) \in E_T$, $dist[v] = dist[u] + w(u, v)$. Because $w(u, v) \ge 1 > 0$, $dist[v] > dist[u]$. $\blacksquare$

---

## 3. Dynamic Updates and the Affected Set

Consider an update that either deletes an edge $(x, y) \in E$ or increases its weight from $w(x, y)$ to $w'(x, y) > w(x, y)$.
Let $G'$ denote the updated graph, and $dist'$ denote the exact shortest-path distance vector in $G'$ from source $s$.

### 3.1 Non-Decreasing Distance Property
Under edge deletion or weight increase:
$$dist'[v] \ge dist[v] \quad \forall v \in V$$
This follows immediately because removing an edge or increasing an edge weight can never shorten any path in the graph.

### 3.2 Definition: Affected Set ($A$)
The **affected set** $A \subseteq V$ is the set of vertices whose shortest distance strictly increases:
$$A = \{ v \in V : dist'[v] > dist[v] \}$$
Vertices in $V \setminus A$ are **unaffected**: $dist'[v] = dist[v]$.

---

## 4. Correctness of Distance Preservation

### Theorem 1 (Non-Tight Update Invariance)
*If the updated edge $(x, y)$ is not tight in $G$ ($dist[x] = \infty$ or $dist[x] + w(x, y) > dist[y]$), then no shortest path in $G$ uses $(x, y)$, and $A = \emptyset$.*

#### Proof:
Every shortest path from $s$ to any vertex $v$ in $G$ consists solely of tight edges (Condition (c) of SPT).
Since $(x, y) \notin E_T$, $(x, y)$ is not used in any shortest path from $s$ to any vertex in $G$.
Therefore, deleting $(x, y)$ or increasing its weight leaves all existing shortest paths intact and with identical weight.
Thus, $dist'[v] = dist[v]$ for all $v \in V$, so $A = \emptyset$. $\blacksquare$

### Theorem 2 (Alternative Support Invariance)
*Let $(x, y) \in E_T$ be tight in $G$. Suppose $tight[y] > 1$ in $G$. Then there exists at least one other edge $(u, y) \in E_T$ with $u \ne x$. If $u \notin A$, then $y \notin A$ and $dist'[y] = dist[y]$.*

#### Proof:
Since $u \notin A$, $dist'[u] = dist[u]$.
The edge $(u, y)$ is present in $G'$ with unchanged weight $w(u, y)$.
Therefore, the path from $s$ to $u$ of length $dist'[u] = dist[u]$ extended by $(u, y)$ forms a valid path from $s$ to $y$ in $G'$ of length:
$$dist'[u] + w(u, y) = dist[u] + w(u, y) = dist[y]$$
By the non-decreasing distance property (Section 3.1), $dist'[y] \ge dist[y]$.
Because there exists a path of length $dist[y]$ in $G'$, $dist'[y] \le dist[y]$.
Hence, $dist'[y] = dist[y]$, which means $y \notin A$. $\blacksquare$

### Theorem 3 (Characterization of the Affected Set)
*A vertex $v \in V_T$ is affected ($v \in A$) if and only if every tight path from $s$ to $v$ in $G_T$ contains the updated edge $(x, y)$.*

#### Proof:
$(\implies)$ Suppose there exists a path $P$ from $s$ to $v$ in $G_T$ that does not contain $(x, y)$.
Because every edge in $P$ is in $E_T$, the total weight of $P$ is $dist[v]$.
Because $P$ does not use $(x, y)$, all edges of $P$ exist in $G'$ with their original weights.
Thus $P$ is a valid path in $G'$ of weight $dist[v]$, so $dist'[v] \le dist[v]$.
Combined with $dist'[v] \ge dist[v]$, we have $dist'[v] = dist[v]$, so $v \notin A$. By contrapositive, $v \in A$ implies every tight path from $s$ to $v$ in $G_T$ uses $(x, y)$.

$(\impliedby)$ Suppose every tight path from $s$ to $v$ in $G_T$ contains $(x, y)$.
Then in $G' \setminus \{(x, y)\}$, no path of length $dist[v]$ from $s$ to $v$ exists (since any such path would have to consist entirely of tight edges in $G$, which all use $(x, y)$).
For a weight increase of $(x, y)$ to $w' > w$, any path using $(x, y)$ has length at least $dist[x] + w' > dist[x] + w = dist[y]$, strictly greater than $dist[v]$.
Therefore, every path from $s$ to $v$ in $G'$ has length strictly greater than $dist[v]$ (or $v$ becomes unreachable). Thus $dist'[v] > dist[v]$, so $v \in A$. $\blacksquare$

---

## 5. Algorithmic Implications for Incremental Maintenance

1. **Zero-Work Certificate ($O(1)$ ops):**
   If the modified edge $(x, y)$ satisfies $dist[x] = \infty$ or $dist[x] + w(x, y) \ne dist[y]$, the certificate immediately returns without modifying distances.
2. **Alternative Support ($O(1)$ amortized / $O(\deg^-(y))$ worst-case):**
   If $(x, y)$ is tight and $tight[y] > 1$, $y$ remains unaffected if another in-neighbor is unaffected.
   If $(x, y)$ was the tree parent of $y$, selecting another tight in-neighbor $u$ of $y$ preserves a valid SPT without changing any distances in the graph.
3. **Bounded Affected Set Propagation:**
   Because $G_T$ is a DAG (Claim 1), finding the set of vertices that lose all tight support can be done via a topological traversal / queue in $G_T$ in work proportional only to the size and degree of the affected subgraph, avoiding full Dijkstra whenever $|A| \ll |V|$.
