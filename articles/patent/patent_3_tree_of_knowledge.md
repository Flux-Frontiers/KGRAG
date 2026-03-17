# Patent Application

**TREEOFKNOWLEDGE: FRACTAL FOREST VISUALIZATION OF COMPILED KNOWLEDGE GRAPHS
WITH TEMPORAL ANIMATION AND FEDERATED QUERY ILLUMINATION**

---

CROSS-REFERENCE TO RELATED APPLICATIONS

This application claims priority to and incorporates by reference the
disclosures of: U.S. Patent Application No. [PENDING-1], entitled
"Deterministic Knowledge Compilation from Formally-Structured Source Artifacts
with Hybrid Structural-Semantic Retrieval and Provenance-Grounded Synthesis,"
filed [DATE]; and U.S. Patent Application No. [PENDING-2], entitled "System
and Method for Federated Retrieval-Augmented Generation over Structurally
Derived Heterogeneous Knowledge Graphs," filed [DATE]. This application is the
third in a series of three related applications. The disclosures of [PENDING-1]
and [PENDING-2] are incorporated herein by reference in their entirety.

---

STATEMENT REGARDING FEDERALLY SPONSORED RESEARCH

Not Applicable.

---

FIELD OF THE INVENTION

The present invention relates to information visualization, and more
particularly to a system and method for rendering a registry of compiled
knowledge graphs as a fractal forest in which each knowledge graph is
represented as a procedurally generated tree whose visual properties —
height, branching geometry, colour, and species — are a direct encoding of
the graph's structural metrics, and for animating the forest through time
using snapshot history and illuminating query-active branches in real time
during federated retrieval operations.

---

BACKGROUND OF THE INVENTION

Knowledge graphs compiled from formally-structured source artifacts, as
described in related Application [PENDING-1], are invisible by default.
The result of compilation is a relational database and a vector index — data
structures legible to machines but presenting no intuitive visual form to
human observers. A knowledge base containing two million nodes and five
million edges is indistinguishable from one containing two thousand nodes
and three thousand edges when examined only through query interfaces.

This invisibility has practical consequences. A corpus that stopped growing
six months ago because its source was not re-ingested cannot be distinguished
at a glance from one ingested this morning. A knowledge graph with dense
structural connectivity cannot be distinguished from one that is semantically
thin. A personal knowledge base spanning three decades of diary, code, and
research cannot be distinguished from a recently created single-file stub.

Prior art visualization approaches for knowledge graphs include: node-link
diagrams in which every node is drawn as a circle and every edge as a line —
these are effective for small graphs but become visually intractable at tens
of thousands of nodes; force-directed layouts that cluster related nodes —
effective for topology but convey no information about the scale, age, or
coverage of the graph; and tabular dashboards displaying numerical statistics —
informative but not spatial or intuitive.

What is needed is a visualization that simultaneously conveys the scale,
structural density, domain kind, temporal depth, semantic coverage, and growth
history of a compiled knowledge graph in a form that is immediately intuitive,
spatially organized, and capable of animating both historical growth and
real-time query activity across a registry of many heterogeneous knowledge
graphs. The present invention provides such a visualization by mapping the
structural properties of each compiled knowledge graph to the visual properties
of a fractal tree, composing the trees into a spatial forest, and providing
temporal animation and real-time query illumination.

---

SUMMARY OF THE INVENTION

The present invention provides a knowledge graph forest visualization system
comprising: a tree parameter derivation module that maps the structural
metrics of a compiled knowledge graph to a set of visual tree parameters
including tree height, branching factor, branch spread angle, branch length
ratio, species classification, and colour; a fractal tree renderer that
generates a procedural tree image from the derived parameters using a
stochastic Lindenmayer system algorithm, producing a tree whose structural
complexity is a direct visual encoding of the knowledge graph's node count
and edge density; a forest layout engine that assigns two-dimensional spatial
positions to all trees in the registry using a force-directed placement
algorithm incorporating knowledge graph metadata, with person corpus groves
rendered as bounded ellipses and named corpus groups rendered as loose rings;
a temporal animation engine that replays the snapshot history of one or more
knowledge graphs by interpolating between consecutive tree parameter sets,
growing new-growth branch tips for added nodes and fading decaying branches
for removed nodes; and a query illumination engine that, upon receipt of a
federated query result, maps each result record to its source knowledge graph
tree, triggers a radial pulse animation from the trunk of each result-bearing
tree, and illuminates individual branches with brightness proportional to the
result's relevance score.

The aggregate rendering of all registered knowledge graphs in the registry
constitutes the **TreeOfKnowledge(tm)**: a single living visualization of all
compiled knowledge, in all domains, at a point in time, animated through its
growth history and responsive to federated queries in real time.

---

BRIEF DESCRIPTION OF THE DRAWINGS

FIG. 1 is a parameter derivation diagram illustrating the mapping from
compiled knowledge graph structural metrics to fractal tree visual parameters,
showing the source property, the derived tree parameter, and the scaling
function for each mapping.

FIG. 2 is a species reference diagram illustrating the ten tree species
corresponding to the ten supported knowledge graph domain kinds, showing the
trunk profile, branching angle distribution, and colour palette for each
species.

FIG. 3 is a flow diagram illustrating the stochastic Lindenmayer system
fractal tree generation algorithm, showing the recursive branch drawing
procedure, the Poisson child-count sampling, the jitter function, and the
leaf rendering terminal case.

FIG. 4 is a forest layout diagram illustrating the two-dimensional spatial
organization of the TreeOfKnowledge, showing individual tree placement, person
corpus grove ellipses, named corpus group rings, and the force-directed
position computation.

FIG. 5 is a temporal animation diagram illustrating the snapshot replay
sequence, showing parameter interpolation between consecutive snapshots, the
new-growth tip rendering for added nodes, and the decay animation for removed
nodes.

FIG. 6 is a query illumination diagram illustrating the mapping from a
federated query result to branch illumination events, showing the trunk pulse
animation, the branch brightness scaling by relevance score, and the dimming
of non-result trees.

FIG. 7 is an architecture diagram illustrating the full TreeOfKnowledge system,
showing data flow from the knowledge graph registry and snapshot store through
the parameter derivation, layout, rendering, animation, and illumination
modules to the output display.

FIG. 8 is an example rendering of a mixed-domain forest containing conifer
code trees, deciduous documentation trees, gnarled diary oak trees, and
lattice metabolic pathway trees, with a person corpus grove marked by a soft
elliptical boundary and an illuminated query response visible as bright gold
branches on two trees.

---

DETAILED DESCRIPTION OF THE INVENTION

The following detailed description sets forth specific embodiments of the
invention with reference to the accompanying figures. Like reference numerals
refer to like elements throughout.

**I. THE TREE PARAMETER DERIVATION MODULE**

Referring to FIG. 1, the tree parameter derivation module accepts a KGEntry
metadata record and a graph statistics dictionary, as produced by the
`_graph_stats` method of the compiler adapter described in related Application
[PENDING-1], and produces a TreeParams record comprising the following fields.

**I.A. Height and Scale**

The tree height parameter, which governs the number of recursive branching
levels generated by the fractal renderer, is computed as:

    depth = ceil(log2(max(node_count, 2)))

This log-scaled mapping ensures that knowledge graphs of very different sizes
remain visually comparable: a graph with 100 nodes produces a tree of depth 7,
while a graph with 10,000 nodes produces a tree of depth 14, a factor of two
in depth for a factor of one hundred in node count. The overall scale of the
rendered tree — the length of the trunk and first-level branches — is computed
as a linear function of the square root of the node count, clamped to a
configurable minimum and maximum, ensuring that no tree is rendered too small
to be visible and no tree dominates the canvas.

**I.B. Branching Factor**

The branching factor parameter governs the expected number of child branches
emitted at each recursive level. It is computed as:

    branching_factor = clamp(edge_count / max(node_count, 1), 1.2, 4.0)

A knowledge graph with low edge-to-node ratio, such as a sparsely connected
documentation graph, produces a tree with few branches per node — a slender,
open form. A knowledge graph with high edge-to-node ratio, such as a Python
code graph with dense call relationships, produces a bushy, many-branched
tree. The clamp range [1.2, 4.0] prevents degenerate cases: a branching
factor below 1.2 produces a linear chain rather than a tree, and a branching
factor above 4.0 produces an impenetrably dense canopy.

**I.C. Species Classification**

The species parameter maps the knowledge graph's domain kind to a set of
species-specific visual constants. Referring to FIG. 2, the ten supported
species are:

| Domain Kind | Species | Trunk | Spread Angle | Length Ratio | Palette |
|---|---|---|---|---|---|
| `code` | Conifer / spruce | Dense, symmetrical | 28 deg | 0.68 | Dark green |
| `doc` | Broad-leaf deciduous | Wide, irregular | 55 deg | 0.72 | Light green |
| `diary` | Gnarled oak | Asymmetric, temporal | 48 deg | 0.70 | Warm amber |
| `meta` | Lattice / fern | Recursive, loop-bearing | 35 deg | 0.65 | Teal-blue |
| `verse` | Weeping willow | Drooping, long | 65 deg | 0.78 | Silver-grey |
| `memory` | Birch | Sparse, vertical | 22 deg | 0.66 | Pale white |
| `disulfide` | Vine / tangle | Short internodes | 80 deg | 0.60 | Bronze |
| `pdbfile` | Crystal / dendrite | Angular, symmetric | 42 deg | 0.67 | Gold |
| `legal` | Columnar poplar | Strict vertical | 15 deg | 0.64 | Deep burgundy |
| `person` | Bonsai (composite) | Multi-stem, compact | 40 deg | 0.69 | Mixed foliage |

The spread angle governs the angular range over which child branches are
distributed relative to their parent. The length ratio governs the ratio of
each child branch length to its parent branch length.

**I.D. Colour and Opacity**

The base colour of each tree is determined by its species palette. Colour
saturation is modulated by the semantic coverage score of the knowledge graph,
if available: a graph with high semantic coverage renders in fully saturated
colour, while a graph with low coverage renders in a desaturated, grey-green
variant of its species palette. This allows an observer to immediately identify
knowledge graphs that are structurally rich but semantically thin.

The opacity of the rendered tree is modulated by the availability status
reported by the compiler adapter: a knowledge graph whose adapter reports
`is_available = True` renders at full opacity; a knowledge graph whose adapter
reports `is_available = False` — because its backing library is not installed
or its compiled database does not exist — renders as a pale, ghost-opacity
outline, visually marking it as a registered but uncompleted compilation.

**I.E. Reproducible Seed**

The stochastic elements of the fractal renderer are governed by a
pseudorandom number generator seeded with a deterministic value derived from
the knowledge graph's registry UUID:

    seed = int.from_bytes(uuid.bytes[:4], 'big')

This seed ensures that the same knowledge graph always renders as the same
tree. Changes in the knowledge graph's structural metrics change the tree
parameters and therefore the tree's shape, but the stochastic variation
around the parameters is stable for a given registry entry.

**I.F. New-Growth and Decay Markers**

When a snapshot delta record is available — as described in related
Application [PENDING-2] — two additional parameters are set. The new-growth
intensity is proportional to the positive `delta_node_count` of the most
recent snapshot, and causes the tips of newly extended branches to be rendered
in a bright, fresh green distinct from the species palette. The decay
intensity is proportional to the absolute value of any negative
`delta_node_count`, and causes branches in a randomly selected subset of
the tree's periphery to be rendered in a desaturated amber, indicating
portions of the knowledge graph that were removed or truncated in the most
recent ingestion.

**II. THE FRACTAL TREE RENDERER**

Referring to FIG. 3, the fractal tree renderer generates a tree image from a
TreeParams record using a stochastic Lindenmayer system algorithm.

**II.A. The Recursive Branch Drawing Procedure**

The renderer maintains a drawing canvas and a current drawing state comprising
position, angle, branch length, and recursion depth. The root invocation is
called with the base of the trunk position, a vertical upward angle, the
computed trunk length, the computed tree depth, and the TreeParams record.

At each invocation, the procedure executes the following steps:

Step 1. If the current depth is zero, draw a leaf primitive at the current
position using the leaf shape associated with the knowledge graph's tags in
the TreeParams record, and return.

Step 2. Draw a line segment from the current position in the current direction
for the current branch length, using the stroke colour and width associated
with the current depth level.

Step 3. Advance the current position to the endpoint of the drawn segment.

Step 4. Sample the number of child branches `n_children` from a Poisson
distribution with rate parameter equal to the `branching_factor` field of the
TreeParams record.

Step 5. For each child index `i` from 0 to `n_children - 1`:
  a. Compute the child angle as the current angle plus the species spread
     angle multiplied by `(i - n_children / 2)`, plus a jitter term drawn
     from a zero-mean uniform distribution with width equal to one-quarter
     of the species spread angle, seeded by a deterministic function of the
     current position and depth.
  b. Compute the child length as the current branch length multiplied by
     the species length ratio, plus a jitter term drawn from a zero-mean
     uniform distribution with width equal to five percent of the child
     length, seeded by a deterministic function of the child angle and depth.
  c. Recurse with the new position, child angle, child length, depth minus
     one, and the same TreeParams record.

This procedure produces a tree whose global topology — height, width, and
branch density — is determined by the TreeParams record, and whose local
variation — individual branch angles and lengths — is stochastically varied
but reproducibly so, via the deterministic jitter seed.

**II.B. The Jitter Function**

The jitter function accepts a seed value, a range, and a current state
tuple (position, depth), and returns a scalar offset. The implementation
computes a hash of the state tuple concatenated with the global tree seed
from TreeParams, maps the hash to [0, 1] by modular reduction, and scales
to the requested range. This function is deterministic — the same inputs
always produce the same output — ensuring tree reproducibility.

**II.C. Rendering Targets**

The fractal tree renderer supports two output targets: a raster image using
the Pillow library (producing PNG output), and a scalable vector graphic using
the svgwrite library (producing SVG output). The SVG output assigns each
branch segment a unique element identifier encoding its depth and child index
path, enabling downstream selection of individual branches by the query
illumination engine.

**III. THE FOREST LAYOUT ENGINE**

Referring to FIG. 4, the forest layout engine assigns a two-dimensional
position on the composite canvas to each tree in the registry, ensuring that
trees are spatially organized by their registry relationships and that canopies
do not overlap.

**III.A. Force-Directed Placement**

The initial position of each tree is computed by a force-directed layout
algorithm. Each tree is treated as a particle; pairs of trees are connected
by attractive springs if they share tags or corpus membership, and all pairs
are subject to repulsive forces proportional to the inverse square of their
distance. The simulation is run for a configurable number of iterations until
kinetic energy falls below a threshold. The resulting positions form a
spatial organization in which related trees are clustered — trees sharing
tags stand near each other, trees in the same corpus group cluster — while
the repulsive forces prevent canopy overlap.

A minimum separation constraint is enforced: after the simulation, any pair
of trees whose assigned positions are closer than the sum of their trunk-base
radii plus a configurable padding margin are pushed apart along the
displacement vector until the constraint is satisfied.

**III.B. Person Corpus Groves**

All knowledge graphs belonging to a `PersonCorpusEntry`, as described in
related Application [PENDING-2], are rendered within a bounded ellipse whose
center is the centroid of the force-directed positions of the member trees.
The ellipse is scaled to contain all member tree canopies with a configurable
margin. The member trees are re-positioned to radiate outward from the grove
center, with the diary-kind tree, if present, placed at the center as the
primary trunk, and remaining member trees arranged in an arc around it.

A soft glow effect is rendered at the grove boundary: a radially decreasing
alpha-blended circle in a warm pale color (in a preferred embodiment,
pale amber at 30% opacity), marking the grove's extent without obscuring
the trees within.

**III.C. Named Corpus Group Rings**

All knowledge graphs belonging to a named `CorpusEntry` that is not a person
corpus are arranged in a loose ring centered on the corpus centroid. The ring
radius is proportional to the count of member trees. A subtle ground-fog
effect — a horizontally elongated, low-opacity grey ellipse rendered beneath
the trees — visually distinguishes the corpus ring from ungrouped trees
standing in clearings between groups.

**III.D. The TreeOfKnowledge Rendering**

The TreeOfKnowledge(tm) rendering is the composite of all registered knowledge
graphs at a reduced zoom level sufficient to place all trees on a single
canvas. Person groves appear as warm-glowing clusters; named corpus rings
appear with their ground fog; ungrouped trees stand in clearings between
groups. A global illumination pass adjusts ambient brightness by corpus
activity: trees whose snapshot history records activity within a configurable
recent window render at full ambient brightness; trees with no recent activity
render at reduced ambient brightness. This allows the observer to identify,
at a glance, which portions of the compiled knowledge base are actively
maintained and which are dormant.

**IV. THE TEMPORAL ANIMATION ENGINE**

Referring to FIG. 5, the temporal animation engine replays the growth history
of one or more trees in the forest using the snapshot history stored by the
snapshot subsystem described in related Application [PENDING-2].

**IV.A. Snapshot Parameter Derivation**

For each snapshot record in the chronological history of a knowledge graph,
the animation engine derives a TreeParams record by invoking the tree parameter
derivation module with the snapshot's node count, edge count, and metadata.
The result is a sequence of TreeParams records, one per snapshot, ordered
chronologically.

**IV.B. Parameter Interpolation**

The animation engine interpolates between consecutive TreeParams records using
a linear tween applied to each scalar parameter (depth, branching factor,
scale, spread angle, length ratio). Non-scalar parameters (species, colour
palette, seed) are held constant at the later snapshot's value; the seed
changes only when the knowledge graph is re-registered with a new registry
entry.

The interpolation produces a continuous sequence of intermediate TreeParams
records at the rendering frame rate. For each intermediate record, the fractal
tree renderer generates the corresponding tree image. The sequence of generated
images constitutes the animation of one tree's growth history.

**IV.C. New-Growth and Decay Animation**

At the transition between consecutive snapshots, the animation engine sets the
new-growth and decay marker parameters of the intermediate TreeParams records
based on the snapshot delta record:

If `delta_node_count` is positive, the new-growth intensity is set to a
normalized value proportional to `delta_node_count / node_count` of the earlier
snapshot, causing bright fresh-green tips to appear at the periphery of the
growing tree throughout the transition animation.

If `delta_node_count` is negative, the decay intensity is set proportionally,
causing peripheral branches to fade through amber and then to transparent
throughout the transition animation.

If both `delta_node_count` is positive and `delta_edge_count` is
disproportionately large (ratio of new edges to new nodes exceeds the
species branching factor), the branching factor parameter is ramped up rapidly
during the transition, causing the tree to temporarily become bushier before
settling at the target value.

**IV.D. Forest-Level Animation**

When all trees in the registry have snapshot histories, the animation engine
can animate the full forest simultaneously. Each tree animates at its own pace
determined by its snapshot timestamps; a global timeline maps wall-clock time
to corpus-time at a configurable rate. Trees whose first snapshot was recorded
at a later corpus-time begin as invisible and appear as saplings — small trees
at depth 1 — on the frame corresponding to their first snapshot. This produces
the visual effect of new knowledge graphs being planted as new corpora are
registered and compiled.

**V. THE QUERY ILLUMINATION ENGINE**

Referring to FIG. 6, the query illumination engine receives a federated query
result record, as produced by the federation orchestrator described in related
Application [PENDING-2], and maps it to a set of visual illumination events
applied to the forest rendering.

**V.A. Result-to-Tree Mapping**

The query result record contains, for each result hit, the registry instance
name of the knowledge graph that produced the hit. The illumination engine
maintains a mapping from registry instance names to rendered tree objects.
For each hit, the engine identifies the corresponding tree.

**V.B. Trunk Pulse Animation**

For each tree that contains one or more result hits, the engine triggers a
trunk pulse animation: a radially expanding circle of increased brightness,
originating at the base of the trunk and propagating outward through the
branch structure at a configurable propagation speed. The pulse color is
a warm gold distinct from the species palette. Trees that returned no results
in the query receive no pulse.

**V.C. Branch Illumination**

For each result hit, the engine maps the hit's node kind to a set of branches
in the rendered tree that correspond to that node kind. The mapping is
defined by the species table: for code-kind trees, function-kind hits
illuminate third and fourth-depth branches; class-kind hits illuminate
second-depth branches; module-kind hits illuminate the trunk. For doc-kind
trees, section-kind hits illuminate second-depth branches; chunk-kind hits
illuminate leaf-level branches.

Selected branches are rendered in illumination-gold for the duration of the
result display, with brightness proportional to the hit's relevance score:
a hit with relevance score 0.9 causes the branch to render at 90% of the
maximum illumination-gold brightness; a hit with score 0.4 renders at 40%.

**V.D. Non-Result Tree Dimming**

Trees that returned no results in the query are dimmed to 60% of their normal
ambient brightness for the duration of the result display. This asymmetric
treatment — brightening result trees, dimming non-result trees — guides the
observer's attention to the portions of the compiled knowledge base that
responded to the query without completely obscuring the non-responding trees.

**V.E. The "Which Trees Know About This?" Readout**

The combination of trunk pulse, branch illumination, and non-result dimming
creates what the present invention terms the "Which Trees Know About This?"
readout: a real-time visual answer to the question of which compiled knowledge
graphs contain information relevant to a given query. This readout is not
decorative — it is a diagnostic instrument. An unexpectedly bright response
from a domain tree on a query outside that domain's typical subject matter
signals an unexpected cross-domain connection worth investigating. A tree that
never illuminates across many queries signals a knowledge graph that may be
redundant or disconnected from the active query space.

**VI. THE TREEOFKNOWLEDGE(TM)**

The TreeOfKnowledge(tm) is the ultimate realization of the knowledge
compilation architecture described across the three related patent applications
in this series.

Related Application [PENDING-1] established that any domain whose structure
is governed by a formal specification can be compiled into a knowledge graph
that is correct by construction, queryable in milliseconds, and provenance-
tagged to its source.

Related Application [PENDING-2] established that knowledge graphs from
heterogeneous domains — code, documentation, protein structures, legal
statutes, diary corpora, verse, metabolic pathways — can be registered in a
shared registry, federated through a uniform adapter interface, and queried
simultaneously through a single query string.

The present invention provides the visualization that makes this registry
visible: every compiled knowledge graph is a tree; every person corpus is a
grove; every corpus group is a ring; the full registry rendered simultaneously
is the TreeOfKnowledge — a living forest representing all compiled knowledge
in all registered domains.

The TreeOfKnowledge is not a static rendering. It is animated through the
snapshot history of every registered knowledge graph, growing in real time as
new ingestion runs add nodes and edges. It illuminates in response to every
federated query, showing which trees hold knowledge relevant to each question.
It dims where knowledge is stale; it glows where knowledge is fresh.

The formal properties of the system make the visual metaphor exact rather
than approximate:

- A tree's height is determined by `ceil(log2(node_count))` — a tree with
  more compiled nodes is geometrically taller.
- A tree's branch density is determined by `edge_count / node_count` — a
  more densely connected graph is visually bushier.
- A tree's species is determined by its domain kind — code graphs are
  conifers, diary graphs are oaks, the mapping is fixed and reproducible.
- A tree's colour saturation reflects its semantic coverage — a
  well-indexed graph is vivid; a partially indexed graph is muted.
- A tree's growth animation is driven by its snapshot deltas — actual
  quantitative changes in the compiled graph produce actual visual growth.
- A tree's illumination intensity during a query is proportional to its
  result relevance score — visual brightness is a direct linear encoding
  of retrieval relevance.

Every visual property of every tree in the TreeOfKnowledge is a deterministic
function of the compiled knowledge graph's structural metrics. The forest is
not a metaphor applied to the knowledge base — it IS the knowledge base,
rendered as a spatial, temporal, interactive object.

**VII. ALTERNATIVE EMBODIMENTS**

In alternative embodiments, the fractal tree renderer may operate in three
dimensions using the PyVista or Three.js rendering libraries, with branches
extending in three-dimensional space and camera controls providing pan, rotate,
and zoom over the three-dimensional forest. Three-dimensional rendering
provides additional depth cues and canopy separation at the cost of increased
rendering complexity.

In alternative embodiments, the tree species may be extended or modified to
encompass new domain kinds registered in the compiler registry, by defining
a new row in the species table with domain-specific trunk profile, spread
angle, length ratio, and colour palette.

In alternative embodiments, the query illumination engine may receive streaming
query results from a federated query in progress, illuminating tree branches
incrementally as each knowledge graph adapter returns its results, providing
a live visual indication of query propagation across the forest.

In alternative embodiments, the temporal animation engine may export the
animated forest as a video file in MP4 or GIF format, enabling offline
sharing of the forest growth history.

In alternative embodiments, the forest may be rendered as a web application
using the Three.js or Babylon.js frameworks, with a WebSocket bridge receiving
real-time query illumination events from the federation server, enabling the
TreeOfKnowledge visualization to be embedded in any web browser without
requiring a local rendering installation.

In alternative embodiments, clicking on a tree in an interactive rendering
may display a sidebar panel showing the registry entry metadata, the current
structural statistics, the snapshot history with growth deltas, and the most
recent query hits, providing a drill-down from the visual overview to the
numeric detail.

---

CLAIM OR CLAIMS

**Claim 1.**
A computer-implemented system for visualizing a registry of compiled knowledge
graphs as a fractal forest, the system comprising:
  one or more processors; and
  one or more non-transitory computer-readable media storing instructions
  that, when executed, cause the processors to perform:
    a parameter derivation operation that, for each compiled knowledge graph
    instance in a registry, retrieves the instance's node count and edge count
    from the compiled graph storage layer and derives a set of visual tree
    parameters comprising a tree height as a ceiling function of the base-2
    logarithm of the node count, a branching factor as the ratio of edge count
    to node count clamped to a configurable range, a species identifier mapped
    from the domain kind of the knowledge graph, a colour saturation value
    proportional to a semantic coverage metric of the knowledge graph, and a
    deterministic pseudorandom seed derived from the knowledge graph's registry
    identifier;
    a fractal tree rendering operation that generates a tree image from the
    derived parameter set using a recursive stochastic Lindenmayer system
    algorithm in which each recursion level emits a branch segment and
    spawns a number of child branches sampled from a Poisson distribution with
    rate equal to the branching factor parameter, with child angles distributed
    around the parent angle with spread equal to the species spread angle plus
    a deterministically seeded jitter term, and terminates at depth zero by
    rendering a leaf primitive; and
    a forest composition operation that assigns a two-dimensional spatial
    position to each generated tree using a force-directed placement algorithm
    and renders all trees on a composite canvas.

**Claim 2.**
The system of claim 1, wherein the parameter derivation operation further
derives a new-growth intensity parameter from a positive node count delta
in the most recent snapshot record of the knowledge graph, and a decay
intensity parameter from a negative node count delta in the most recent
snapshot record; and wherein the fractal tree rendering operation renders
branch tips at the periphery of the tree in a bright green colour scaled by
the new-growth intensity parameter, and renders a randomly selected subset
of peripheral branches in a desaturated amber colour scaled by the decay
intensity parameter.

**Claim 3.**
The system of claim 1, wherein the species identifier maps each domain kind
in an enumerated set of supported domain kinds to a corresponding species
record comprising a trunk profile, a base spread angle, a branch length ratio,
and a colour palette, such that knowledge graphs of the same domain kind
always render as trees of the same species with the same visual character.

**Claim 4.**
The system of claim 1, wherein the forest composition operation further:
  identifies all knowledge graph instances belonging to a person corpus group
  in the registry and positions them within a bounded ellipse whose centre is
  the centroid of their force-directed positions, with each member tree's
  trunk radiating outward from the ellipse centre, and renders a soft radially-
  decreasing glow effect at the ellipse boundary to mark the grove extent; and
  identifies all knowledge graph instances belonging to a named corpus group
  that is not a person corpus group and arranges them in a loose ring around
  the corpus centroid, rendering a ground-fog effect beneath the ring to
  distinguish it from ungrouped trees.

**Claim 5.**
The system of claim 1, further comprising a temporal animation engine
configured to:
  retrieve the ordered sequence of snapshot records for one or more registered
  knowledge graph instances from a snapshot manifest index;
  for each consecutive pair of snapshot records, derive a TreeParams record
  from each snapshot's node count and edge count, and compute a sequence of
  intermediate TreeParams records by linear interpolation of each scalar
  parameter between the two endpoint records at the rendering frame rate; and
  for each intermediate TreeParams record, invoke the fractal tree rendering
  operation to produce a frame, the sequence of frames constituting an
  animation of the knowledge graph's compiled growth history.

**Claim 6.**
The system of claim 5, wherein the temporal animation engine is further
configured to animate all registered knowledge graph instances simultaneously
on a shared timeline, such that trees whose first snapshot was recorded at a
later point in the timeline begin as invisible and emerge as single-depth
saplings on the frame corresponding to their first snapshot, producing a visual
representation of new knowledge graphs being registered and compiled into the
forest over time.

**Claim 7.**
The system of claim 1, further comprising a query illumination engine
configured to:
  receive a federated query result record comprising, for each result hit,
  a relevance score and a registry instance name identifying the knowledge
  graph that produced the hit;
  for each knowledge graph tree that produced one or more result hits, trigger
  a radially expanding pulse animation originating at the base of the tree
  trunk and propagating outward through the branch structure; and
  illuminate the branches of each result-bearing tree in a query-response
  colour with brightness linearly proportional to the relevance score of the
  highest-scoring result hit from that knowledge graph; and
  reduce the ambient brightness of trees that produced no result hits.

**Claim 8.**
The system of claim 7, wherein the query illumination engine further maps
each result hit's node kind to a subset of branches in the rendered tree,
based on a species-specific node-kind-to-branch-depth mapping, and illuminates
only the branches in the mapped subset, such that function-kind hits illuminate
deep peripheral branches of code trees and section-kind hits illuminate
intermediate branches of documentation trees.

**Claim 9.**
A computer-implemented method for procedurally generating a tree image whose
visual structure encodes the structural properties of a compiled knowledge
graph, the method comprising:
  receiving a node count and an edge count from a compiled knowledge graph
  storage layer;
  computing a recursion depth as the ceiling of the base-2 logarithm of the
  node count;
  computing a branching factor as the ratio of the edge count to the node
  count, clamped to the range [1.2, 4.0];
  selecting a species record from a species table indexed by the domain kind
  of the compiled knowledge graph, the species record specifying a spread
  angle, a branch length ratio, and a colour palette;
  deriving a deterministic pseudorandom seed from the compiled knowledge
  graph's registry identifier;
  invoking a recursive branch drawing procedure with initial parameters
  comprising a trunk base position, a vertical angle, a trunk length
  proportional to the square root of the node count, the computed recursion
  depth, the computed branching factor, the species spread angle, the species
  branch length ratio, and the derived seed, the procedure at each recursion
  level drawing a branch segment, sampling a child count from a Poisson
  distribution with rate equal to the branching factor, computing each child's
  angle as the parent angle plus a fraction of the spread angle plus a
  deterministically seeded jitter, computing each child's length as the parent
  length multiplied by the branch length ratio plus a deterministically seeded
  jitter, and recursing until depth zero; and
  returning the generated tree image.

**Claim 10.**
The method of claim 9, further comprising:
  receiving a sequence of snapshot records for the compiled knowledge graph,
  each snapshot record comprising a node count, an edge count, and a
  timestamp;
  for each consecutive pair of snapshot records, deriving a tree parameter
  set from each record's node count and edge count and computing a linear
  interpolation between the two parameter sets at a specified frame rate; and
  invoking the recursive branch drawing procedure for each interpolated
  parameter set to produce a frame, the resulting frame sequence constituting
  a time-lapse animation of the compiled knowledge graph's structural growth.

**Claim 11.**
The method of claim 9, further comprising, upon receiving a federated query
result comprising one or more result hits each carrying a relevance score:
  selecting, for each result hit, the branch subset of the generated tree
  that corresponds to the hit's node kind according to a species-specific
  node-kind-to-depth mapping;
  rendering the selected branches in a query-response colour with brightness
  proportional to the hit's relevance score; and
  triggering a radially expanding brightness pulse originating at the trunk
  base position and propagating toward the branch tips at a configurable
  propagation speed.

**Claim 12.**
A non-transitory computer-readable medium storing a forest visualization
program that, when executed by one or more processors:
  reads, from a knowledge graph registry database, records for a plurality
  of compiled knowledge graph instances of heterogeneous domain kinds, each
  record comprising a domain kind indicator and paths to the compiled graph
  storage database;
  for each registry record, queries the compiled graph storage database to
  obtain the node count and edge count, and derives a visual tree parameter
  set comprising at minimum a recursion depth computed from the node count,
  a branching factor computed from the ratio of edge count to node count, a
  species record selected by domain kind from a species table, a colour
  palette from the species record, and a deterministic seed from the registry
  record identifier;
  generates a tree image for each registry record by executing a stochastic
  Lindenmayer system algorithm parameterized by the derived tree parameter
  set, the algorithm recursively branching to the computed recursion depth
  with child counts sampled from a Poisson distribution at the computed
  branching factor;
  computes a two-dimensional position for each generated tree using a force-
  directed layout algorithm, with attractive forces between trees sharing
  tags or corpus membership and repulsive forces between all pairs;
  composites all generated trees at their computed positions onto a single
  canvas, with person corpus members grouped within bounded ellipses marked
  by glow effects and named corpus members grouped within rings marked by
  ground-fog effects; and
  exports the composited canvas as a raster image, a scalable vector graphic,
  or an interactive display.

**Claim 13.**
The non-transitory computer-readable medium of claim 12, wherein the program
further, upon receipt of a federated query result record:
  identifies, for each result hit in the result record, the generated tree
  corresponding to the hit's source knowledge graph instance by name;
  triggers a trunk pulse animation on each identified tree, the pulse
  propagating outward from the trunk base through the branch structure;
  sets the brightness of branches in each identified tree proportional to
  the maximum relevance score of result hits from that tree; and
  reduces the rendered opacity of all trees not identified in the result record
  to a configured dimming level;
  whereby the composite canvas provides a real-time visual readout of which
  compiled knowledge graphs contain information relevant to the submitted query.

---

ABSTRACT OF THE DISCLOSURE

A fractal forest visualization system renders each compiled knowledge graph
in a registry as a procedurally generated tree whose height, branching
geometry, species form, and color encode the graph's node count, edge
density, domain kind, and semantic coverage. A stochastic Lindenmayer system
algorithm parameterized by these structural metrics generates each tree image
reproducibly from the registry entry's identifier. A force-directed layout
engine arranges trees spatially, grouping person corpora as glowing groves
and named corpus groups as ringed clearings. A temporal animation engine
replays snapshot histories as time-lapse growth sequences, sprouting bright
new-growth tips for added nodes and fading amber decay for removed nodes.
A query illumination engine maps federated query result hits to branch
illumination events, with brightness proportional to relevance score,
enabling real-time identification of which knowledge domains responded to
a query. The aggregate rendering of all registered knowledge graphs
constitutes the TreeOfKnowledge(tm).
