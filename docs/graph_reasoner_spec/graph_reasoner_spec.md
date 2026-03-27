# GraphReasoner: Formal Specification

## Abstract

The GraphReasoner is a semantic reasoning engine that navigates knowledge
graphs along weighted edges using an N-dimensional turtle navigator for
directional coherence. It discovers inference paths through discrete graph
structures by combining lazy edge discovery, heading-aware steering, and
multi-hop chaining with backtracking and beam search.

Unlike gradient-based optimizers (ManifoldWalker) that operate on continuous
manifolds, the GraphReasoner traverses discrete nodes connected by typed,
weighted semantic edges. Unlike compressed-space navigators (WaveRider),
it operates on ground-truth knowledge structures where every connection is
empirically grounded.

## 1. Preliminaries

### 1.1 Knowledge Graph

A knowledge graph $G = (V, E, \phi, w, \tau)$ where:

- $V$ is a finite set of nodes, each identified by a string $v_i$
- $E \subseteq V \times V$ is a set of directed edges
- $\phi: V \to \mathbb{R}^n$ maps each node to an $n$-dimensional embedding
- $w: E \to [0, 1]$ assigns a weight (semantic strength) to each edge
- $\tau: E \to \Sigma$ assigns a type label from alphabet $\Sigma$

### 1.2 Lazy Edge Discovery

Edges may be **pre-computed** or **discovered lazily** by an
`EdgeDiscoverer` $\mathcal{D}$. Given node $v$ and optional heading
$\hat{h}$:

$$\mathcal{D}(v, G, \hat{h}) \to \{(v, u, w_{vu}, \tau_{vu}) \mid u \in V\}$$

Three discoverers are defined:

**RadiusDiscoverer.** All nodes within distance $r$:
$$\mathcal{D}_r(v) = \{u \in V \mid d(\phi(v), \phi(u)) \leq r,\; u \neq v\}$$

Edge weight: $w_{vu} = 1 - d(\phi(v), \phi(u)) / r$

**KNNDiscoverer.** The $k$ nearest neighbors by distance $d$:
$$\mathcal{D}_k(v) = \text{argmin}_{S \subset V \setminus \{v\},\; |S|=k} \sum_{u \in S} d(\phi(v), \phi(u))$$

Edge weight: $w_{vu} = 1 - d(\phi(v), \phi(u)) / d_{\max}$ where $d_{\max}$
is the distance to the $k$-th neighbor.

**DirectedDiscoverer.** Decorates an inner discoverer, filtering to a forward
cone of half-angle $\alpha$:
$$\mathcal{D}_\alpha(v, \hat{h}) = \{u \in \mathcal{D}_{inner}(v) \mid \cos\angle(\phi(u) - \phi(v), \hat{h}) \geq \cos\alpha\}$$

### 1.3 Distance Metrics

**Euclidean:** $d_E(a, b) = \|a - b\|_2$

**Angular (periodic):** For angle vectors in degrees with wrapping at $\pm 180°$:
$$d_A(a, b) = \left\|\min(|a_i - b_i|, 360 - |a_i - b_i|)\right\|_2$$

This correctly handles the circular topology of dihedral angles.

### 1.4 Turtle Navigation Frame

The reasoner maintains a `TurtleND` with:
- Position $p \in \mathbb{R}^n$ (the current node's embedding)
- Orthonormal frame $F \in \mathbb{R}^{n \times n}$ where $F_0 = \hat{h}$ (heading)

The heading encodes the current **line of reasoning** — the semantic direction
along which the reasoner is traveling through the graph.

## 2. Steering Strategies

A steering strategy $\sigma$ scores a candidate transition from current
embedding $c$ to candidate embedding $q$ given heading $\hat{h}$, edge $e$,
and path history $P$:

$$\sigma(c, q, \hat{h}, e, P) \to \mathbb{R}$$

Higher scores are preferred.

### 2.1 TargetSteering

Steers toward a target embedding $t$:

$$\sigma_T = w_a \cdot \text{align}(c, q, \hat{h}) + (1 - w_a) \cdot \text{progress}(c, q, t) + 0.1 \cdot w_e$$

where:
- $\text{align}(c, q, \hat{h}) = \hat{d} \cdot \hat{h}$, $\hat{d} = (q - c)/\|q - c\|$
- $\text{progress}(c, q, t) = (\|t - c\| - \|t - q\|) / \|t - c\|$
- $w_e$ is the edge weight

### 2.2 GradientSteering

Steers along the gradient of a scalar field $f$:

$$\sigma_G = 0.5 \cdot \Delta f + 0.3 \cdot \text{align} + 0.2 \cdot w_e$$

where $\Delta f = f(c) - f(q)$ (for minimization) or $f(q) - f(c)$ (for
maximization).

### 2.3 ExplorationSteering

Maximizes coverage of the embedding space:

$$\sigma_X = 0.4 \cdot \min_{e_i \in P} \|q - e_i\| + 0.3 \cdot \text{align} + 0.3 \cdot w_e$$

The novelty term rewards candidates far from all previously visited embeddings.

## 3. Reasoning Algorithm

### 3.1 Single Step

```
STEP(G, turtle, path, visited, strategy, edge_type):
    v ← path.last
    c ← φ(v)
    ĥ ← turtle.heading

    edges ← G.discover_neighbors(v, ĥ)
    candidates ← ∅

    for each edge (v, u, w, τ) in edges:
        if u ∈ visited: continue
        if edge_type ≠ null and τ ≠ edge_type: continue
        q ← φ(u)
        s ← strategy.score(c, q, ĥ, edge, path)
        candidates ← candidates ∪ {(s, u, q, edge)}

    if candidates = ∅: return null  // dead end

    (s*, u*, q*, e*) ← argmax_s candidates

    turtle.position ← q*
    ALIGN_HEADING(turtle, q* - c)

    path.append(u*, q*, e*, s*)
    visited ← visited ∪ {u*}

    return u*
```

### 3.2 Multi-Hop Reasoning

```
REASON(G, start, max_hops, min_score, edge_type):
    START(start)

    for i = 1 to max_hops:
        u ← STEP(G, turtle, path, visited, strategy, edge_type)
        if u = null: break  // dead end
        if path.scores[-1] < min_score:
            BACKTRACK(1)
            break

    return path
```

### 3.3 Targeted Reasoning

```
REASON_TOWARD(G, start, target, max_hops, edge_type):
    old_strategy ← strategy
    strategy ← TargetSteering(φ(target))
    START(start)
    ALIGN_HEADING(turtle, φ(target) - φ(start))

    for i = 1 to max_hops:
        u ← STEP(...)
        if u = null or u = target: break

    strategy ← old_strategy
    return path
```

### 3.4 Beam Search

```
BEAM_REASON(G, start, max_hops, beam_width, min_score, edge_type):
    beams ← [(0, Path(start), {start})]

    for hop = 1 to max_hops:
        candidates ← ∅

        for (cum_score, path, visited) in beams:
            v ← path.last
            ĥ ← heading_from_path(path)
            edges ← G.discover_neighbors(v, ĥ)

            for each edge (v, u, w, τ):
                if u ∈ visited: continue
                s ← strategy.score(φ(v), φ(u), ĥ, edge, path)
                if s < min_score: continue
                new_path ← path + (u, edge, s)
                candidates ← candidates ∪ {(cum_score + s, new_path, visited ∪ {u})}

        if candidates = ∅: break
        beams ← top_k(candidates, beam_width)

    return [path for (_, path, _) in beams]
```

### 3.5 Heading Alignment

When the reasoner moves from $c$ to $q$, the turtle's heading is rotated
toward the step direction $\hat{d} = (q - c)/\|q - c\|$ via a Givens rotation
in the plane most aligned with the desired rotation:

```
ALIGN_HEADING(turtle, direction):
    d̂ ← direction / ‖direction‖
    ĥ ← turtle.heading
    θ ← arccos(ĥ · d̂)

    if θ ≈ 0: return  // already aligned

    // Find perpendicular component
    p ← d̂ - (ĥ · d̂)ĥ
    p̂ ← p / ‖p‖

    // Find best rotation plane
    i* ← argmax_{i > 0} |turtle.basis(i) · p̂|

    turtle.rotate(θ, 0, i*)
```

### 3.6 Backtracking

```
BACKTRACK(n_steps):
    for i = 1 to min(n_steps, |path| - 1):
        path.pop()  // remove last node, edge, score

    turtle.position ← path.embeddings[-1]
    // Note: visited set is NOT modified — prevents revisiting
```

## 4. Correctness Properties

**P1 (No revisits).** A node visited during reasoning is never visited again,
even after backtracking. Formally: $|P.\text{node\_ids}| = |\text{set}(P.\text{node\_ids})|$ at all times.

**P2 (Heading coherence).** After each step, the turtle's heading has positive
projection onto the step direction:
$\hat{h}_{new} \cdot \hat{d} > 0$ where $\hat{d} = (\phi(u_{new}) - \phi(u_{prev}))/\|\cdot\|$

**P3 (Path consistency).** $|P.\text{edges}| = |P.\text{scores}| = |P.\text{node\_ids}| - 1$

**P4 (Greedy optimality).** At each step, the selected node has the highest
strategy score among all unvisited candidates.

**P5 (Beam ordering).** Beam search returns paths sorted by cumulative score
in descending order.

## 5. Complexity Analysis

### Per-Step Complexity

| Operation | Complexity | Notes |
|-----------|-----------|-------|
| Matrix rebuild | $O(N \cdot n)$ | Amortized once per graph mutation |
| RadiusDiscoverer | $O(N \cdot n)$ | Vectorized distance computation |
| KNNDiscoverer | $O(N \cdot n + N \log k)$ | Distance + partial sort |
| DirectedDiscoverer | $O(K \cdot n)$ | Filter $K$ inner results |
| Strategy scoring | $O(K \cdot n)$ | Score $K$ candidates |
| Heading alignment | $O(n^2)$ | Basis search + Givens rotation |
| **Total per step** | $O(N \cdot n)$ | Dominated by discovery |

Where $N = |V|$, $n = \text{ndim}$, $K$ = number of candidates after discovery.

### Multi-Hop Complexity

| Algorithm | Complexity |
|-----------|-----------|
| `reason` (greedy) | $O(H \cdot N \cdot n)$ |
| `reason_toward` | $O(H \cdot N \cdot n)$ |
| `beam_reason` | $O(H \cdot B \cdot N \cdot n)$ |

Where $H$ = max_hops, $B$ = beam_width.

## 6. Integration Points

### 6.1 Domain Adapters

The `graph_from_disulfides()` factory demonstrates the adapter pattern.
Any domain can provide:
1. A mapping from domain objects to node IDs and embeddings
2. An appropriate `EdgeDiscoverer` (with domain-specific distance metric)
3. An appropriate `SteeringStrategy` (with domain-specific scoring)

### 6.2 Cross-Corpus Reasoning

Multiple corpora are connected by adding bridge edges:
```python
graph.add_edge(SemanticEdge("corpus1:nodeA", "corpus2:nodeB", 0.7, "cross-corpus"))
```

The reasoner follows these edges like any other, enabling cross-domain
inference chains.

### 6.3 KGRAG Integration

The GraphReasoner serves as the traversal engine for Knowledge Graph
Retrieval-Augmented Generation (KGRAG). In this architecture:

- **Knowledge graphs** encode domain ontologies as typed, weighted graphs
- **The reasoner** discovers multi-hop inference paths through these graphs
- **An LLM** synthesizes natural-language answers from the discovered paths
- The LLM does NOT reason — it synthesizes. The graph does the reasoning.

## 7. Discussion

### Relationship to Graph Neural Networks

GNNs learn node representations by aggregating neighbor features through
message passing. The GraphReasoner does not learn representations — it
navigates pre-computed embedding spaces using geometric steering. This
makes it:
- **Interpretable**: every step in a reasoning path is a concrete edge
- **Deterministic**: given the same graph and strategy, paths are reproducible
- **Zero-shot**: no training required, only a graph and a steering strategy

### Relationship to A* Search

A* finds optimal shortest paths using $f(n) = g(n) + h(n)$. The GraphReasoner
uses steering strategies that combine heading alignment, edge weight, and
task-specific criteria. Unlike A*, the reasoner:
- Maintains directional coherence (the heading)
- Does not require an admissible heuristic
- Supports beam search for multi-hypothesis exploration
- Handles lazy edge discovery (edges not known until visited)

### The Surfing Metaphor

The turtle's heading is the wave. The edges are the surface. The reasoner
rides along the surface where semantic coherence is highest. Turning the
turtle changes the line of inquiry. Good edges keep you on the manifold
of valid reasoning. Bad edges are noise — the steering strategy filters
them out. The beam search maintains multiple surfers on parallel waves.

This is fundamentally different from:
- **LLM reasoning** — which hallucinates connections
- **Standard graph traversal** — which ignores semantic direction
- **ManifoldWalker** — which optimizes a scalar on continuous space
- **WaveRider** — which navigates compressed model representations
