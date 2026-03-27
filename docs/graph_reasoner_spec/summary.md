# GraphReasoner & DisulfideTree: A Semantic Reasoning Engine for Knowledge Graphs

## The Thesis

**The graph reasons. The LLM synthesizes.**

Large language models hallucinate connections. They compress knowledge into
statistical shadows and then confabulate relationships that don't exist.
The solution isn't better prompting or larger context windows. The solution
is to separate reasoning from synthesis entirely.

Reasoning is graph traversal. It is the act of following grounded, empirically
weighted edges through a knowledge structure where every connection is real.
Synthesis is what LLMs are actually good at — taking a set of verified facts
and producing coherent natural language.

This work introduces two modules that implement this separation:

1. **GraphReasoner** — a general-purpose semantic reasoning engine that
   navigates knowledge graphs along weighted edges using an N-dimensional
   turtle for directional coherence.

2. **DisulfideTree** — a hierarchical classification tree that organizes
   175,000+ protein disulfide bonds into a four-level ontology and produces
   structured snippets for Knowledge Graph Retrieval-Augmented Generation
   (KGRAG).

Neither module requires an LLM to run. They require only numpy and a graph.

---

## The Architecture

```
Domain Data (PDB structures, ontologies, corpora)
        │
        ▼
  KnowledgeGraph
  ├── nodes: entities with N-dimensional embeddings
  ├── edges: typed, weighted semantic connections
  └── discoverers: lazy neighbor finding (Radius, KNN, Directed)
        │
        ▼
  GraphReasoner
  ├── TurtleND heading encodes "line of reasoning"
  ├── SteeringStrategy scores candidate edges
  ├── Multi-hop traversal with backtracking
  └── Beam search for parallel hypothesis paths
        │
        ▼
  ReasoningPath (ordered chain of grounded inferences)
        │
        ▼
  KGRAG Snippets → LLM synthesis → Natural language answers
```

The key insight: the turtle's heading in embedding space IS the current line
of reasoning. Turning the turtle changes the line of inquiry. Good edges keep
you on the manifold of valid inference. Bad edges are noise — the steering
strategy filters them out. The beam search maintains multiple hypotheses
simultaneously.

---

## GraphReasoner: The Engine

### Core Abstractions

| Component | Purpose |
|-----------|---------|
| **KnowledgeGraph** | Typed, weighted graph with lazy edge discovery and vectorized numpy operations |
| **EdgeDiscoverer** | Finds neighbors on arrival — no precomputation of the full edge set |
| **SteeringStrategy** | Scores candidates by alignment, progress, edge weight, and task criteria |
| **GraphReasoner** | Steers through the graph via TurtleND, maintaining directional coherence |
| **ReasoningPath** | The inference trace: nodes, edges, scores — fully auditable |

### Edge Discovery

Edges are not precomputed. With 175,000 nodes, precomputing all pairwise
edges is O(N²) ≈ 30 billion comparisons. Instead, edges are discovered
lazily when the reasoner arrives at a node:

- **RadiusDiscoverer**: All nodes within distance threshold. Vectorized numpy,
  O(N·n) per step. Supports angular wrapping for periodic spaces (dihedral angles).
- **KNNDiscoverer**: k nearest neighbors via partial sort. O(N·n + N·log k).
- **DirectedDiscoverer**: Decorator that filters any inner discoverer to a
  forward cone around the turtle's heading. Only follow edges that maintain
  semantic coherence.

### Steering Strategies

The strategy is the "intelligence" of the reasoner. It scores each candidate
next-node by combining:

- **TargetSteering**: Steer toward a specific embedding. Balances alignment
  with heading (stay on course) against progress toward target (close distance).
- **GradientSteering**: Follow a scalar field gradient. Minimize energy,
  maximize similarity, descend loss landscapes — but on a discrete graph.
- **ExplorationSteering**: Maximize coverage. Favor nodes far from everything
  already visited. Discover the full topology.

### Reasoning Modes

- **`reason(start, max_hops)`** — Greedy multi-hop: follow the best edge at
  each step, backtrack if score drops below threshold.
- **`reason_toward(start, target)`** — Pathfinding: temporarily install
  TargetSteering, orient heading toward target, follow the best path.
- **`beam_reason(start, beam_width)`** — Beam search: maintain multiple
  hypothesis paths simultaneously, prune to top-k at each hop.
- **`backtrack(n)`** — Back up n steps. Visited nodes remain marked, forcing
  exploration of alternatives (like logical reasoning hitting a dead end).

### Why This Is Not Standard Graph Traversal

BFS and DFS explore graphs blindly. A* requires an admissible heuristic.
The GraphReasoner:

- **Maintains directional coherence** via the turtle's heading. Each step
  aligns the heading toward the step direction using Givens rotations.
- **Scores edges semantically**, not just by distance. The strategy combines
  alignment, progress, edge weight, and path history.
- **Supports lazy discovery**. The full graph never needs to be known.
- **Records auditable traces**. Every step in a ReasoningPath is a concrete,
  grounded edge with a score.

---

## DisulfideTree: The Ontology

### The Hierarchy

Protein disulfide bonds are characterized by five dihedral angles (χ₁–χ₅),
each in [-180°, 180°]. The classification tree progressively quantizes this
5D angular space:

| Level | Base | Classes | Bin Size | Suffix |
|-------|------|---------|----------|--------|
| Binary | 2 | 2⁵ = 32 | 180° | `b` |
| Quadrant | 4 | 4⁵ = 1,024 | 90° | `q` |
| Sextant | 6 | 6⁵ = 7,776 | 60° | `s` |
| Octant | 8 | 8⁵ = 32,768 | 45° | `o` |

Each level refines the previous. Parent-child relationships are determined
by center-angle mapping: the center of each finer bin falls deterministically
into exactly one coarser bin.

```
root (175,000+ disulfides)
 └── 00000b  -LHSpiral (23.4%)        ← binary: click to see family
      └── 33334q (5.1%)               ← quadrant: finer grouping
           └── 553354s (1.2%)          ← sextant: finer still
                └── 77544o (0.3%)      ← octant: finest classification
                     └── 1egs_24_84    ← leaf: click to see disulfide
```

**Branch length = occupancy.** The 23.4% -LHSpiral binary class gets a
thick branch. A rare octant class with 3 members gets a thin one. The tree
is weighted by reality.

### KGRAG Snippets

Every node in the tree produces a structured snippet for KGRAG consumption:

```python
{
    "entity_type": "disulfide_binary_class",
    "class_id": "00000b",
    "level": "binary",
    "occupancy": 40943,
    "occupancy_pct": 23.36,
    "class_name": "-LHSpiral",
    "functional_annotation": "Allosteric",
    "consensus_torsions": [-60.5, -62.3, -88.1, -59.8, -61.2],
    "description": "Binary class 00000b (-LHSpiral). 40943 members (23.36%).
                    Function: Allosteric. Consensus torsions: [-60.5, -62.3,
                    -88.1, -59.8, -61.2]."
}
```

Click a node → see the family. Click a leaf → see the disulfide. Every
snippet carries its own description for LLM synthesis.

### The Tree as a KnowledgeGraph

The DisulfideTree stores itself as a `KnowledgeGraph`. Nodes are classification
levels with circular-mean centroid embeddings. Edges are:
- **hierarchy**: parent → child (weighted by occupancy fraction)
- **membership**: octant → individual disulfide

The GraphReasoner can traverse it. Start at root, steer toward a target
conformation, and the reasoning path IS the ontological descent through the
classification hierarchy.

---

## The Three Navigators

proteusPy now has three distinct navigation systems, each for a different
domain:

| Navigator | Domain | Traverses | Optimizes |
|-----------|--------|-----------|-----------|
| **TurtleND** | Coordinate spaces | Continuous N-D space | Molecular geometry |
| **ManifoldWalker** | Embedding manifolds | Continuous manifolds via local PCA | Scalar objectives (loss) |
| **GraphReasoner** | Knowledge graphs | Discrete typed graphs | Semantic coherence (steering score) |

TurtleND is the foundation. ManifoldWalker uses it for Riemannian-aware
gradient descent. GraphReasoner uses it for heading-aware graph traversal.
Same geometric primitive, three levels of abstraction.

---

## Integration with KGRAG

proteusPy provides the structural biology domain for KGRAG:

1. **The PDB parser** (`ssparser.py`, `DisulfideExtractor_mp.py`) ingests
   protein structures from the RCSB and extracts disulfide bonds.
2. **The DisulfideTree** organizes them into a navigable ontology with
   KGRAG-compatible snippets at every node.
3. **The GraphReasoner** traverses the tree (or any KnowledgeGraph) and
   produces ReasoningPaths — ordered chains of grounded inferences.
4. **KGRAG** consumes the paths and snippets for retrieval-augmented generation.
5. **The LLM** synthesizes natural-language answers from the paths.

The LLM never reasons. It never needs to. The graph already did.

---

## Implementation

| File | Lines | Tests | Purpose |
|------|-------|-------|---------|
| `graph_reasoner.py` | 650 | 51 | Core reasoning engine |
| `disulfide_tree.py` | 420 | 29 | Classification tree + KGRAG snippets |
| `graph_reasoner_spec.md` | 280 | — | Formal specification |
| Total | 1,350 | **80** | |

Dependencies: numpy. That's it.

---

## What This Means

We don't need an LLM to reason over structured knowledge. We need a graph
and a turtle. The LLM is for the last mile — turning a chain of verified
facts into prose.

This is not RAG. RAG retrieves documents and hopes the LLM figures out what's
relevant. This is KGRAG — Knowledge Graph RAG — where the retrieval IS the
reasoning. The graph traversal IS the inference. The path IS the proof.

**The graph reasons. The LLM synthesizes.**
