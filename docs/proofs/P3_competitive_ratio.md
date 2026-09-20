# Proof P3: Competitive Ratio Analysis of Budgeted Dynamic Shortest Paths

**Milestone 4.3: Theoretical Foundation for Deterministic and Randomized Budgets**

This document establishes the competitive analysis of GraphPulse-R's budgeted repair framework against an offline optimum adversary. It proves:
1. The deterministic competitive ratio $\max(1 + c, \frac{1 + c}{c})$, minimized uniquely at $c = 1$ with ratio $2.0$.
2. The randomized competitive ratio $\frac{e}{e - 1} \approx 1.582$, achieved by sampling budget multipliers from $f(x) = \frac{e^x}{e - 1}$.

---

## 1. Problem Formulation and Competitive Framework

Consider a dynamic shortest-path tree update $t$. Let:
- $F \in \mathbb{Z}^+$: The machine-independent cost of a from-scratch rebuild on the updated graph.
- $r \in \mathbb{Z}^+$: The machine-independent cost of a complete incremental repair on the updated graph.

### 1.1 The Offline Optimum ($\text{OPT}$)
An offline adversary with complete future knowledge selects the minimum-cost strategy for update $t$:
$$\text{OPT}(r, F) = \min(r, F)$$

> **Certificate Invariance:**
> Certificate checks (1 SCAN) and alternative support re-parenting ($1 + \text{indeg}(v)$ SCANs) are invariant across all strategies and are incurred equally by both the online algorithm and the offline optimum. Consequently, they contribute an identical additive term to both online cost and OPT, which cancels in competitive ratio analysis. We therefore focus on the sole-tight repair decision where online choice governs performance.

---

## 2. Deterministic Budget Analysis

Let $c > 0$ be a fixed constant. The online algorithm allocates budget $B = c \cdot F$ to incremental repair. If work exceeds $B$, repair aborts and the algorithm executes a full rebuild.

The online cost $ALG(r, F)$ is:
$$ALG(r, F) \le \begin{cases}
r & \text{if } r \le c \cdot F \\
c \cdot F + F + 1 = (1 + c) F + 1 & \text{if } r > c \cdot F
\end{cases}$$

Neglecting the unit abort slack $+1$ (which is $o(F)$ for non-trivial graphs), we evaluate the competitive ratio:
$$\mathcal{R}_c(r, F) = \frac{ALG(r, F)}{\text{OPT}(r, F)} = \frac{ALG(r, F)}{\min(r, F)}$$

### 2.1 Case Analysis
We analyze the ratio as a function of $r$ relative to $c F$ and $F$:

1. **Sub-budget Repair ($r \le c F$):**
   - If $c \le 1$: $r \le c F \le F \implies \text{OPT} = r$.
     $$\mathcal{R}_c = \frac{r}{r} = 1$$
   - If $c > 1$:
     - For $r \le F$: $\text{OPT} = r \implies \mathcal{R}_c = 1$.
     - For $F < r \le c F$: $\text{OPT} = F \implies \mathcal{R}_c = \frac{r}{F} \le \frac{c F}{F} = c$.

2. **Exceeded Budget ($r > c F$):**
   Here $ALG = (1 + c) F$. The adversary minimizes $\text{OPT} = \min(r, F)$ by choosing $r$ as small as possible subject to $r > c F$ (i.e., $r = c F + \epsilon$):
   - **Subcase $c \ge 1$:**
     Since $r > c F \ge F$, $\text{OPT} = \min(r, F) = F$.
     $$\mathcal{R}_c = \frac{(1 + c) F}{F} = 1 + c$$
   - **Subcase $c < 1$:**
     Here $c F < F$. For $r \in (c F, F]$, $\text{OPT} = \min(r, F) = r$.
     The worst-case ratio occurs as $r \to c F^+$:
     $$\mathcal{R}_c = \sup_{r > c F} \frac{(1 + c) F}{r} = \frac{(1 + c) F}{c F} = \frac{1 + c}{c} = 1 + \frac{1}{c}$$

### 2.2 Worst-Case Ratio and Optimal Budget

Combining both subcases across all $r$:
$$\mathcal{R}(c) = \max\left(1 + c, \; \frac{1 + c}{c}\right)$$

### Theorem 1 (Optimal Deterministic Competitive Ratio)
*The competitive ratio $\mathcal{R}(c)$ is strictly convex on $(0, \infty)$ and attains its unique global minimum at $c = 1$, where:*
$$\mathcal{R}(1) = 1 + 1 = 2.0$$

#### Proof:
For $c \in (0, 1]$, $\frac{1 + c}{c} = 1 + \frac{1}{c}$ is strictly decreasing with $\lim_{c \to 0^+} \mathcal{R}(c) = \infty$ and $\mathcal{R}(1) = 2$.
For $c \in [1, \infty)$, $1 + c$ is strictly increasing with $\lim_{c \to \infty} \mathcal{R}(c) = \infty$ and $\mathcal{R}(1) = 2$.
Thus, $c = 1$ is the unique minimizer, yielding the optimal competitive ratio of $2$.
$\blacksquare$

---

## 3. Randomized Budget Analysis

To beat the deterministic lower bound of $2$, we randomize the budget choice. Let the budget factor $x \in [0, 1]$ be a continuous random variable with probability density function $f(x)$ supported on $[0, 1]$. For an update with rebuild cost $F$, the budget is set to $B = x \cdot F$.

Let $\alpha = \frac{r}{F} \in [0, \infty)$ denote the ratio of repair work to rebuild work.

### 3.1 Expected Online Cost

The online algorithm pays:
- $r$ if $r \le x F \iff x \ge \alpha$ (repair completes within budget).
- $x F + F = (1 + x) F$ if $r > x F \iff x < \alpha$ (repair aborts and rebuilds).

We distinguish two regimes for $\alpha$:

#### Regime I: $\alpha > 1$ ($r > F \implies \text{OPT} = F$)
Since $x \in [0, 1]$ and $\alpha > 1$, the condition $x < \alpha$ holds with probability $1$. Repair always aborts:
$$\mathbb{E}[ALG] = \int_0^1 (1 + x) F f(x) \, dx = F \int_0^1 (1 + x) f(x) \, dx$$

#### Regime II: $\alpha \le 1$ ($r \le F \implies \text{OPT} = r = \alpha F$)
Here $x$ may fall above or below $\alpha$:
$$\mathbb{E}[ALG] = \int_0^\alpha (1 + x) F f(x) \, dx + \int_\alpha^1 r f(x) \, dx$$

### 3.2 Derivation of the Optimal Density $f(x)$

We require the expected competitive ratio $\frac{\mathbb{E}[ALG]}{\text{OPT}} = C$ to be constant for all $\alpha \in [0, \infty)$.

For $\alpha \le 1$, setting $\mathbb{E}[ALG] = C \cdot r = C \alpha F$:
$$\int_0^\alpha (1 + x) F f(x) \, dx + \alpha F \int_\alpha^1 f(x) \, dx = C \alpha F$$

Dividing by $F$:
$$\int_0^\alpha (1 + x) f(x) \, dx + \alpha \int_\alpha^1 f(x) \, dx = C \alpha$$

Differentiating both sides with respect to $\alpha$ using Leibniz's rule:
$$(1 + \alpha) f(\alpha) + \int_\alpha^1 f(x) \, dx - \alpha f(\alpha) = C$$
$$(1 + \alpha - \alpha) f(\alpha) + \int_\alpha^1 f(x) \, dx = C$$
$$f(\alpha) + \int_\alpha^1 f(x) \, dx = C$$

Differentiating with respect to $\alpha$ once more:
$$f'(\alpha) - f(\alpha) = 0 \implies f'(\alpha) = f(\alpha)$$

The general solution is the exponential family:
$$f(x) = A e^x$$

### 3.3 Normalization and Constant Determination

1. **Probability Normalization:**
   $$\int_0^1 f(x) \, dx = 1 \implies A \int_0^1 e^x \, dx = A (e - 1) = 1 \implies A = \frac{1}{e - 1}$$
   Therefore, the optimal density is:
   $$f(x) = \frac{e^x}{e - 1} \quad \text{for } x \in [0, 1]$$

2. **Competitive Ratio Evaluation:**
   Setting $\alpha = 1$ in $f(\alpha) + \int_\alpha^1 f(x) dx = C$:
   $$C = f(1) + 0 = \frac{e}{e - 1} \approx 1.5819767\dots$$

### 3.4 Verification of the Key Integrals

#### Integral 1: Normalization
$$\int_0^1 \frac{e^x}{e - 1} \, dx = \frac{1}{e - 1} [e^x]_0^1 = \frac{e - 1}{e - 1} = 1 \quad \checkmark$$

#### Integral 2: Regime I ($\alpha \ge 1$)
We verify by integration by parts:
$$\int (1 + x) e^x \, dx = (1 + x) e^x - \int e^x \, dx = (1 + x) e^x - e^x = x e^x$$
Evaluating from $0$ to $1$:
$$\int_0^1 (1 + x) e^x \, dx = [x e^x]_0^1 = 1 \cdot e^1 - 0 = e$$
Dividing by $e - 1$:
$$\int_0^1 (1 + x) \frac{e^x}{e - 1} \, dx = \frac{e}{e - 1} \quad \checkmark$$
Hence for all $r \ge F$:
$$\mathbb{E}[ALG] = \frac{e}{e - 1} F = \frac{e}{e - 1} \text{OPT}$$

#### Integral 3: Regime II ($\alpha \le 1$)
$$\begin{aligned}
\mathbb{E}[ALG] &= F \int_0^\alpha (1 + x) \frac{e^x}{e - 1} \, dx + r \int_\alpha^1 \frac{e^x}{e - 1} \, dx \\
&= \frac{F}{e - 1} [x e^x]_0^\alpha + \frac{r}{e - 1} [e^x]_\alpha^1 \\
&= \frac{F \alpha e^\alpha}{e - 1} + \frac{r (e - e^\alpha)}{e - 1}
\end{aligned}$$
Since $r = \alpha F$:
$$\mathbb{E}[ALG] = \frac{r e^\alpha}{e - 1} + \frac{r e - r e^\alpha}{e - 1} = \frac{r e}{e - 1} = \frac{e}{e - 1} r = \frac{e}{e - 1} \text{OPT} \quad \checkmark$$

The algebraic cancellation is exact for **every** $\alpha \le 1$.

### Theorem 2 (Randomized Competitive Ratio)
*Under the continuous randomized budget distribution $f(x) = \frac{e^x}{e - 1}$ on $[0, 1]$, the expected online work satisfies:*
$$\mathbb{E}[ALG(r, F)] = \frac{e}{e - 1} \min(r, F) \approx 1.582 \cdot \text{OPT}$$
*for all $r \ge 0$ and $F > 0$. The expected competitive ratio is identically $\frac{e}{e - 1}$.*

---

## 4. Sampling via Inverse Transform Method

To draw random multipliers $x \sim f(x)$:

1. Compute the Cumulative Distribution Function (CDF) $F_X(x)$ for $x \in [0, 1]$:
   $$F_X(x) = \int_0^x \frac{e^t}{e - 1} \, dt = \frac{e^x - 1}{e - 1}$$

2. Set $F_X(x) = U$, where $U \sim \text{Uniform}[0, 1)$:
   $$\frac{e^x - 1}{e - 1} = U \implies e^x - 1 = (e - 1) U \implies e^x = 1 + (e - 1) U$$
   Taking the natural logarithm:
   $$x = \ln\Big(1 + (e - 1) \cdot U\Big)$$

### 4.1 Properties of the Sampler
- **Range:** Since $U \in [0, 1)$, $1 + (e - 1) U \in [1, e)$, hence $x \in [0, 1)$.
- **Expected Value of $x$:**
  $$\begin{aligned}
  \mathbb{E}[x] &= \int_0^1 x \frac{e^x}{e - 1} \, dx = \frac{1}{e - 1} \Big( [x e^x]_0^1 - \int_0^1 e^x \, dx \Big) \\
  &= \frac{1}{e - 1} (e - (e - 1)) = \frac{1}{e - 1} \approx 0.5819767\dots
  \end{aligned}$$
This provides a direct empirical test: the sample mean of $x$ across independent draws converges to $\frac{1}{e - 1} \approx 0.582$.

---

## 5. Summary of Theoretical Results

| Strategy | Budget Rule | Worst-Case / Expected Ratio | Notes |
|---|---|---|---|
| **Deterministic** | Fixed $c = 1.0$ | $2.0$ | Minimized at $c = 1$; ski-rental lower bound |
| **Randomized** | $x \sim \frac{e^x}{e - 1}$ on $[0, 1]$ | $\frac{e}{e - 1} \approx 1.582$ | Exact ratio equality for all $r, F$ |
