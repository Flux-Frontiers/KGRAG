# Patent 1 — Figure Image Generation Prompts
# DETERMINISTIC KNOWLEDGE COMPILATION — Figure Prompts for Paper Banana

---

## FIG. 1 — Phase Diagram: Compilation Phase vs. Query Phase

A clean, professional technical patent diagram in black and white with light grey shading, showing a two-column phase diagram divided by a bold vertical dashed line down the center. The left column is labeled "BUILD PHASE (Compile Once)" at the top and the right column is labeled "QUERY PHASE (Execute Many Times)."

In the left column, four rectangular process boxes are stacked vertically connected by downward arrows: (1) "Source Parsing — Domain-specific parser traverses formal grammar/schema; emits typed node records and directed edge records," (2) "Graph Storage — Typed nodes and edges persisted to relational database (SQLite); stable identifiers, kind labels, metadata," (3) "Canonical Text Construction — Node name, kind label, docstring, and adjacent prose assembled into canonical text string," (4) "Semantic Indexing — Canonical text encoded into dense vector via sentence transformer; stored in vector database (LanceDB)." Two output arrows from the bottom of the left column point rightward into a cylindrical database icon labeled "Compiled Knowledge Graph (SQLite)" and a second cylindrical database icon labeled "Semantic Vector Index (LanceDB)."

In the right column, three rectangular process boxes are stacked vertically connected by downward arrows: (1) "Semantic Seeding — Query string encoded into dense vector; k-nearest-neighbor search over vector index returns seed node set (k ≈ 8)," (2) "Structural Traversal — Bounded breadth-first search from seed nodes over compiled graph; follows CALLS, CONTAINS, IMPORTS, INHERITS edges to depth limit," (3) "Provenance Extraction — Each result node enriched with stable ID, verified file path, line span, actual source text, and relevance score." A final output box labeled "Ranked Provenance-Tagged Result Records" sits at the bottom of the right column. Input arrows from the two database cylinders feed into the top of the right column. A single "Query String" input arrow enters the top right. Label the dashed center divider "Compile/Execute Boundary."

Style: clean patent line art, engineering schematic aesthetic, no color fill, thin precise lines, all text in a neutral sans-serif font at a readable size.

---

## FIG. 2 — Data Structure Diagram: Stable Node Addressing Scheme

A clean technical patent diagram showing the anatomy of a stable node identifier string. At the top center, a large rectangular box contains an example identifier string in monospace font: `fn:src/orchestrator.py:KGRAG.query`. Three horizontal bracket annotations point downward from three segments of the string: the first bracket spans `fn` and is labeled "Kind Prefix (fn = function, cl = class, mo = module, me = method)"; the second bracket spans `src/orchestrator.py` and is labeled "Source File Path (repository-relative)"; the third bracket spans `KGRAG.query` and is labeled "Qualified Entity Name (dot-qualified within module)."

Below this top section, a table with four rows shows example identifiers for different source domains: Row 1, "Python Function": `fn:src/retriever.py:HybridRetriever.query`; Row 2, "Python Module": `mo:src/compiler.py`; Row 3, "Documentation Section": `sec:docs/usage.md:Installation`; Row 4, "PDB Residue": `res:data/1abc.pdb:A:42`. Each row has three columns — Domain, Kind, and Full Identifier — with light grey alternating row shading.

At the bottom, a small inset box labeled "Stability Guarantee" contains three bullet points: "• Same source + same ontology version → same identifier on every compilation," "• Enables set-difference change detection between corpus versions," "• Supports stable cross-references from external systems."

Style: patent technical diagram, black on white, monospace font for all identifiers, sans-serif for all labels, engineering schematic aesthetic.

---

## FIG. 3 — Flow Diagram: Two-Pass AST Compiler for Python Source Code

A clean vertical flow diagram split into two parallel swim lanes. The left swim lane is labeled "PASS 1: Definition Extraction" and the right swim lane is labeled "PASS 2: Call Graph and Data-Flow Extraction." At the top, a single input box labeled "Python Source File (.py)" spans both lanes, with an arrow forking down into each lane.

In the left lane, sequential process boxes connected by arrows: (1) "AST Parse — Python `ast` module parses file into Abstract Syntax Tree," (2) "Visit Module node — emit `mo:path` node with docstring and import list," (3) "Visit ClassDef nodes — emit `cl:path:ClassName` node with docstring, bases, decorators; emit CONTAINS edge from module," (4) "Visit FunctionDef / AsyncFunctionDef nodes — emit `fn:path:QualName` node with docstring, params, return type; emit CONTAINS edge from parent," (5) "Visit Import / ImportFrom nodes — emit IMPORTS edges to referenced module identifiers." Output box at bottom of left lane: "Node Records + CONTAINS, IMPORTS, INHERITS Edges stored in SQLite."

In the right lane, sequential process boxes connected by arrows: (1) "Re-traverse AST with scope tracker active," (2) "Visit Call nodes — resolve callee to qualified name via scope tracker; emit CALLS edge to call-site stub node," (3) "Symbol Resolution Post-Pass — match call-site stubs to first-party definition nodes; emit RESOLVES_TO edges for successful matches; retain unresolved stubs as `stub` kind nodes," (4) "Visit Attribute nodes — emit ATTR_ACCESS edges for known object references," (5) "Visit Name nodes (Load/Store) — emit READS and WRITES edges for known symbols." Output box at bottom of right lane: "CALLS, RESOLVES_TO, ATTR_ACCESS, READS, WRITES Edges stored in SQLite."

Both output boxes merge into a single bottom box: "Complete Compiled Knowledge Graph: Nodes + All Edge Types."

Style: clean patent flow diagram, rectangular boxes with rounded corners, standard flowchart arrowheads, swim lane vertical divider, black on white, all text in a neutral sans-serif font.

---

## FIG. 4 — Flow Diagram: Hybrid Retrieval Algorithm

A clean horizontal two-stage flow diagram. At the far left, an input box labeled "Natural Language Query String q" feeds a downward arrow into Stage 1.

Stage 1 box (light grey background, bold border) labeled "STAGE 1: SEMANTIC SEEDING." Inside: process step "Encode q into dense vector using sentence transformer (same model as build phase)" → "Submit vector to LanceDB semantic index as k-nearest-neighbor query (k = 8 default)" → "Return ordered list of k node identifiers with highest cosine similarity scores." Output of Stage 1: a small list icon labeled "Seed Set S = {s₁, s₂, … s_k} with similarity scores."

A rightward arrow connects Stage 1 output to Stage 2.

Stage 2 box (light grey background, bold border) labeled "STAGE 2: STRUCTURAL TRAVERSAL." Inside: process step "For each seed node sᵢ in S: perform bounded breadth-first search over SQLite graph storage layer" → "Expand following edges: CALLS, CONTAINS, IMPORTS, INHERITS (code); CONTAINS, REFERENCES, SEMANTICALLY_LINKS (docs)" → "Collect all nodes reached within hop bound (depth ≤ 2 for code, ≤ 3 for docs) into candidate set C." A small inset graph diagram shows a seed node with radiating 1-hop and 2-hop neighbor nodes.

A rightward arrow connects Stage 2 output to the Ranking box.

Ranking box labeled "COMPOSITE RANKING." Inside: formula displayed as: "Score(n) = w₁ × (1 / hop_distance) + w₂ × cosine_similarity(query_vector, nearest_seed_vector)." Description: "Nodes structurally adjacent to semantically relevant seeds rank highest. Resolves needle-in-a-haystack by navigating from approximate semantic entry points to exact structural neighbors."

Output box at far right: "Ranked Candidate Set with Composite Scores → Provenance Extraction."

Style: patent flow diagram with clearly delineated stage boxes, horizontal left-to-right flow, bold stage labels, inset miniature graph schematic within Stage 2, black on white.

---

## FIG. 5 — Conceptual Diagram: The Ontology-Determinism Principle

A clean two-column mapping diagram. The left column is titled "FORMAL SOURCE DOMAIN SPECIFICATION" and the right column is titled "COMPILED KNOWLEDGE GRAPH ONTOLOGY." A bold title banner at the top reads "Ontology-Determinism Principle: The Formal Specification IS the Ontology."

Six rows connect left entries to right entries via rightward horizontal arrows. Each left entry is a rounded rectangle and each right entry is a table-like box listing node kinds and edge types.

Row 1: Left "Python Language Grammar + AST Specification (.py files)" → Right "Node kinds: module, class, function, method, stub | Edge types: CONTAINS, IMPORTS, INHERITS, CALLS, RESOLVES_TO, ATTR_ACCESS, READS, WRITES."

Row 2: Left "CommonMark / RST Parse Tree Specification (.md, .rst files)" → Right "Node kinds: document, section, chunk | Edge types: CONTAINS, REFERENCES, SEMANTICALLY_LINKS."

Row 3: Left "PDB File Format Specification (.pdb files)" → Right "Node kinds: chain, residue, atom | Edge types: BONDED_TO, CONTAINS, SPATIAL_CONTACT."

Row 4: Left "Statutory Numbering Hierarchy (Title → Chapter → Section → Subsection)" → Right "Node kinds: title, chapter, section, subsection, clause | Edge types: CONTAINS, CROSS_REFERENCES."

Row 5: Left "KEGG / BioCyc Biochemical Pathway Schema" → Right "Node kinds: reaction, compound, enzyme, pathway | Edge types: CATALYZES, CONSUMES, PRODUCES, PART_OF."

Row 6: Left "Timestamped Diary / Journal Entry Schema" → Right "Node kinds: entry, chunk | Edge types: PRECEDES, CONTAINS."

At the bottom, a bold annotation box states: "Correctness Guarantee: Every extracted node corresponds to a real entity as defined by the specification. No node or edge is hypothesized, inferred, or approximated."

Style: patent mapping diagram, clean aligned rows, double-headed directional arrows, light grey row separators, black on white, sans-serif font.

---

## FIG. 6 — Data Flow Diagram: Provenance-Grounded Synthesis Pipeline

A clean left-to-right data flow diagram. Three major zones separated by vertical dashed lines: "RETRIEVAL LAYER," "PROVENANCE LAYER," and "SYNTHESIS LAYER."

In the RETRIEVAL LAYER: a box "Compiled Knowledge Graph (SQLite + LanceDB)" with an input arrow from "Natural Language Query q." Inside shows "Hybrid Retrieval: Semantic Seeding + Structural Traversal." Output: a list of "Result Nodes with Stable IDs, Kinds, Relevance Scores."

In the PROVENANCE LAYER: input from result nodes flows into "Provenance Extraction." Process box describes: "For each result node: (a) verify source file exists at stored path, (b) read actual source text at stored line span, (c) attach to result record." Output: a structured record icon labeled "Provenance Record" with visible fields: `id: fn:src/retriever.py:HybridRetriever.query`, `kind: function`, `file: src/retriever.py`, `lines: 45–89`, `source_text: [actual code]`, `relevance: 0.87`, `summary: [canonical text]`.

In the SYNTHESIS LAYER: provenance records flow into "LLM Context Window Construction." Arrow labeled "Inject as structured context (not free-form prose)" enters an LLM icon labeled "Language Model (synthesis only)." The LLM produces "Synthesized Answer." A bold annotation box on the LLM states: "Grounded Synthesis Guarantee: LLM role is synthesis over provided facts only — NOT recall from training weights. Every factual claim traces to a verified source address."

A contrast inset box in the bottom-right labeled "Standard RAG (contrast)" shows: "Retrieved prose chunks (approximate) → LLM fills structural gaps by generation → hallucination risk." A red X marks the gap-filling arrow.

Style: clean data flow diagram, bold zone labels above dashed vertical dividers, structured record icon with visible field names in monospace, black on white patent style.

---

## FIG. 7 — Comparison Diagram: Needle-in-a-Haystack Problem and Structural Traversal Solution

A clean side-by-side comparison diagram split vertically into two panels. A large title at top: "Needle-in-a-Haystack: Semantic Failure vs. Structural Traversal Solution."

LEFT PANEL labeled "STANDARD DENSE RETRIEVAL (Failure Mode)": Shows a horizontal ranked list of document chunks labeled 1 through 8 by cosine similarity to the query. Chunk #1 (highest similarity) is labeled "Semantically similar prose about the topic — but NOT the target function." Chunk #7 is labeled "TARGET: the actual function being sought — low surface similarity to query string." A red arrow points to chunk #7 with annotation "Target ranked #7 — below retrieval cutoff k=5." A dashed red box around chunks #6–#8 labeled "Never retrieved." A sad face icon or X symbol at the bottom labeled "Query fails: target not in result set."

RIGHT PANEL labeled "HYBRID STRUCTURAL-SEMANTIC RETRIEVAL (Solution)": Shows a small graph diagram. A node labeled "Seed Node s₁ (highest similarity — the caller function)" is highlighted in grey at center. Arrows radiate from s₁: a bold rightward arrow labeled "1 hop: CALLS edge" points to "TARGET NODE (the called function — exact match)." Surrounding nodes at 2 hops are shown with lighter lines. An annotation states: "Semantic seeding finds s₁ (approximately correct starting point). Structural traversal follows CALLS edge to TARGET in 1 hop. Target ranked #1 by composite function: hop=1 + high seed similarity." A checkmark icon at bottom labeled "Query succeeds: target retrieved deterministically regardless of semantic similarity to query string."

Style: patent comparison diagram, left panel as a ranked list bar chart aesthetic, right panel as a graph node diagram, strong visual contrast between failure and solution panels, black on white.

---

## FIG. 8 — Architecture Diagram: Multi-Domain Compiler Registry

A clean layered architecture diagram. Three horizontal layers separated by bold lines, labeled from top to bottom: "SOURCE ARTIFACTS LAYER," "COMPILER ADAPTER LAYER," and "UNIFIED RETRIEVAL INTERFACE LAYER."

In the SOURCE ARTIFACTS LAYER, six rectangular icons in a row labeled: "Python Source Code (.py)," "Markdown / RST Documentation (.md, .rst)," "Protein Structure Files (.pdb)," "Legal Statutes (hierarchical text)," "Diary / Journal Corpora (timestamped entries)," "Biochemical Pathway Databases (KEGG/BioCyc)."

Each source artifact icon has a downward arrow into the COMPILER ADAPTER LAYER. In the COMPILER ADAPTER LAYER, six corresponding compiler adapter boxes: "CodeKG Compiler Adapter," "DocKG Compiler Adapter," "ProteinKG Compiler Adapter," "StatuteKG Compiler Adapter," "DiaryKG Compiler Adapter," "MetaKG Compiler Adapter." Each box shows the uniform interface methods: `is_available()`, `query(q, k)`, `pack(q, k, ctx)`, `stats()`, `snapshot(v, l)`. All six boxes have a common bold border indicating "Uniform Compiler Adapter Interface."

Each compiler adapter box has a downward arrow pointing to a central box in the UNIFIED RETRIEVAL INTERFACE LAYER labeled "Federation Orchestrator." Inside: "Iterates over all registry records → calls is_available() → calls query() on available adapters → merges and globally ranks result lists by relevance score → returns globally ranked result list with per-result provenance (domain kind + registry instance name)." The orchestrator box connects to a "Registry Database (SQLite)" icon on the right showing record fields: UUID, name, domain_kind, source_path, tags, metadata.

A single output arrow from the Federation Orchestrator points down to "Globally Ranked Provenance-Tagged Results spanning all compiled knowledge graphs."

Style: clean three-layer architecture diagram, bold horizontal layer separators with text labels, box-and-arrow style, monospace font for interface method names, black on white patent schematic.

---
