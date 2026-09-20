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

## 5. Part 2: Propagation Correctness of `find_affected`

### Lemma 4 (Distance Preservation via Unaffected In-Neighbor)
*A vertex $v \in V_T$ with at least one tight in-edge from an unaffected vertex $u \notin A$ keeps its distance: $dist'[v] = dist[v]$.*

#### Proof:
Since $u \notin A$, $dist'[u] = dist[u]$.
The tight in-edge $(u, v) \in E_T$ remains present in $G'$ with unchanged weight $w(u, v)$ (since only the edge $(x, y)$ was modified, and $u \ne x$ or the edge wasn't $(x, y)$).
Hence, the path from $s$ to $u$ in $G'$ of length $dist'[u] = dist[u]$ extended by $(u, v)$ achieves length:
$$dist'[u] + w(u, v) = dist[u] + w(u, v) = dist[v]$$
Since edge deletions and weight increases cannot decrease shortest-path distances ($dist'[v] \ge dist[v]$), it follows that $dist'[v] = dist[v]$. Thus $v \notin A$. $\blacksquare$

### Theorem 5 (Distance Increase upon Loss of All Tight Support)
*A vertex $v \in V_T$ all of whose tight in-edges in $G_T$ originate from affected vertices (or are removed/weakened) has strictly larger distance: $dist'[v] > dist[v]$ (or becomes unreachable, $dist'[v] = \infty$).*

#### Proof:
By Claim 1, $G_T$ is a DAG. We proceed by induction on the topological order induced by $dist$ on $G_T$.

**Base case:** $v$ is the head of the updated edge $(x, y)$ that lost its sole tight in-edge. By hypothesis, $tight[v] = 1$, and $(x, y)$ is either deleted or increased to $w' > w$. In $G'$, no edge entering $v$ achieves $dist'[u] + w(u, v) = dist[v]$. Any other edge in $G$ entering $v$ was strictly non-tight ($dist[u] + w(u, v) > dist[v]$). Thus every path from $s$ to $v$ in $G'$ has length strictly greater than $dist[v]$ (or no path exists), so $dist'[v] > dist[v]$. Thus $v \in A$.

**Inductive step:** Consider any vertex $z$ where all tight in-edges $(u, z) \in E_T$ have $u \in A$. By the inductive hypothesis, $dist'[u] > dist[u]$ for every such predecessor $u$.
Any path from $s$ to $z$ in $G'$ either:
1. Ends with an edge $(u, z)$ that was tight in $G$. Then its length is at least $dist'[u] + w(u, z) > dist[u] + w(u, z) = dist[z]$.
2. Ends with an edge $(u', z)$ that was non-tight in $G$. Then its length is at least $dist'[u'] + w(u', z) \ge dist[u'] + w(u', z) > dist[z]$.
Therefore, every path in $G'$ from $s$ to $z$ has length strictly greater than $dist[z]$ (or $z$ is disconnected from $s$).
Thus $dist'[z] > dist[z]$, which proves $z \in A$. $\blacksquare$

### Corollary 5.1 (Exactness and Termination of `find_affected`)
*The procedure `find_affected(state, g, v)` terminates and returns exactly the set $A$.*
1. **Termination:** Because $G_T$ is a DAG, each vertex $z$ is enqueued at most once when its in-support counter reaches 0. Since $|V_T|$ is finite, the queue empties in finite steps without cycles.
2. **Exactness:** By Lemma 4 and Theorem 5, a vertex enters $A$ if and only if all its tight predecessors are in $A$. Since the search tracks the exact in-degree support in $G_T$, the set discovered is precisely $A$.
3. **Work Complexity:** Each $x \in A$ is enqueued once and dequeued once, so $QUEUE = 2 \cdot |A|$. For each dequeued vertex, each out-edge in $g$ is examined once, so $SCAN = \sum_{x \in A} \deg^+(x)$.

---

## 6. Algorithmic Implications for Incremental Maintenance

1. **Zero-Work Certificate ($O(1)$ ops):**
   If the modified edge $(x, y)$ satisfies $dist[x] = \infty$ or $dist[x] + w(x, y) \ne dist[y]$, the certificate immediately returns without modifying distances.
2. **Alternative Support ($O(1)$ amortized / $O(\deg^-(y))$ worst-case):**
   If $(x, y)$ is tight and $tight[y] > 1$, $y$ remains unaffected if another in-neighbor is unaffected.
   If $(x, y)$ was the tree parent of $y$, selecting another tight in-neighbor $u$ of $y$ preserves a valid SPT without changing any distances in the graph.
3. **Exact Affected Set Propagation:**
   `find_affected` identifies the exact set of vertices whose shortest-path distance strictly increases in machine-independent cost:
   $$W_{\text{affected}} = 2 \cdot |A| \text{ (QUEUE)} + \sum_{x \in A} \deg^+(x) \text{ (SCAN)}$$
   This avoids touching any unaffected vertex outside the boundary of $A$.
