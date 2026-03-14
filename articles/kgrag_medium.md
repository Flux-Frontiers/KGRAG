# One Query, Every Knowledge Graph: How KGRAG Federates Code, Docs, and Domain Data

*Eric G. Suchanek, PhD — Flux-Frontiers*

---

Software systems generate knowledge in incompatible silos. Source code captures structure and behavior. Documentation captures intent and usage. Databases and ontologies capture domain facts. When you need to understand a system in full, you cross-reference all three manually.

KGRAG eliminates that crossing. It federates heterogeneous knowledge graphs — code, documentation, scientific corpora — under a single query interface. One natural-language question fans out to every registered graph simultaneously, and results come back globally ranked with full source provenance.

No language model is involved in building the graphs or executing the queries.

---

## Why Graph, Not Vector

The dominant retrieval approach embeds documents as vectors and finds the nearest matches to a query. This works for text. It does not work for the kinds of questions that matter most in a software system:

- Which functions call the session invalidation path?
- Which documentation sections reference this API?
- Which metabolic pathways share this enzyme?

These questions have precise structural answers. Vector search approximates; it does not traverse. A Python call graph cannot be recovered from embedding similarity, and neither can a document cross-reference graph.

KGRAG builds knowledge graphs from the formal structure of each source domain, using deterministic parsers. Embeddings are added on top of the structural graph — not instead of it — to handle natural-language entry points. You search in natural language; the system finds relevant entry points in the graph and then traverses structure to return everything connected to those entry points.

---

## Five Layers, One Interface

The architecture is explicit about its abstraction levels.

**Layer 1: Source parsing.** Each backend module builds its graph from the formal structure of its domain.

- *CodeKG* runs two deterministic passes over the Python abstract syntax tree: one to extract definitions and structural edges (contains, imports, inherits), one to extract the call graph with call-site evidence. A data-flow visitor adds reads, writes, and attribute-access edges. Nothing is inferred; everything is extracted from syntax.

- *DocKG* parses Markdown corpora into six node kinds — documents, sections, chunks, entities, keywords, and topics — connected by eight typed edge relations. Section hierarchy, cross-document links, and keyword co-occurrence are all structural properties of the source; the same corpus produces the same graph every time.

- *MetaKG* wraps any domain-specific backend behind the same interface. The parsing strategy is domain-defined; the contract is uniform.

**Layer 2: Graph storage.** SQLite holds the structural record: a nodes table and an edges table. Every node carries a stable identifier encoding its origin — for example, `fn:src/auth/jwt.py:JWTValidator.validate` — so results are directly addressable in the source. Every edge may carry evidence: the line number and expression text of a call site, or the offset of a document reference.

**Layer 3: Semantic indexing.** LanceDB holds sentence-transformer embeddings of node descriptions. The vector index has one job: given a query string, return the IDs of the most semantically relevant nodes. Those IDs become entry points for structural traversal. The vector index is disposable; deleting it and rebuilding does not affect the structural record.

**Layer 4: The adapter protocol.** `KGAdapter` is an abstract interface with five methods: `is_available`, `query`, `pack`, `stats`, `analyze`. Every backend module implements this interface. Everything above it is domain-agnostic.

**Layer 5: The federation orchestrator.** `KGRAG` holds a registry of all known knowledge graph instances. On each query, it asks every available adapter for results, merges them, ranks them globally by score, and returns a unified result with per-source attribution.

---

## The Query Lifecycle

When you issue a federated query:

1. The orchestrator consults the registry and dispatches the query to each available adapter.
2. Each adapter embeds the query and retrieves seed nodes from its vector index.
3. From those seeds, each adapter performs bounded breadth-first traversal through the structural graph — following typed edges, recording hop distance and provenance at each step.
4. Nodes are ranked by hop distance from seed, embedding distance, and node kind; deduplicated by source span; and returned as typed result objects.
5. The orchestrator merges all adapter results and sorts by score.

The returned result knows which graph each hit came from, what kind of node it is, and exactly where in the source it lives.

For a codebase of 100,000 lines and a documentation corpus of 800 nodes, a federated query completes in under one second on a laptop. The bottleneck is embedding the query string; structural traversal and SQLite lookups are negligible.

---

## Ground Truth, Not Inference

The most important property of this system is the one that sounds obvious once stated: the knowledge graphs are correct by construction.

A `CALLS` edge exists because a call expression was found in the AST at a specific line. A `REFERENCES` edge in a document graph exists because a hyperlink was found in the Markdown source. No edge was extracted by a language model from prose. No relationship was inferred.

This matters when those graphs are used to ground an AI agent. Every piece of context delivered to a downstream language model carries a verified source address. The model can't fabricate a function signature or invent a call relationship that isn't in the graph, because the graph was built from the syntax and the model didn't build it.

Compare this with systems like Microsoft's GraphRAG, which use a language model to extract entities and relationships from text. GraphRAG makes sense for large unstructured corpora where structure must be inferred because none is explicit. But code is not unstructured text. A Python file is a formal document; its call graph is derived, not guessed. Using an LLM to extract a call graph from source code is like using a machine learning model to parse JSON: it can work, but it introduces errors that a parser would not make.

KGRAG's graphs are extracted by parsers. The accuracy guarantee at the structural layer is independent of any model's performance.

---

## Adding a New Domain

The adapter protocol makes KGRAG extensible without modifying the federation layer. Implementing a new knowledge domain means writing one class with five methods:

```python
class MyDomainAdapter(KGAdapter):
    def is_available(self) -> bool: ...      # library installed and DB built?
    def query(self, q, k) -> list[CrossHit]: ...    # hybrid query
    def pack(self, q, k, context) -> list[CrossSnippet]: ...  # snippet extraction
    def stats(self) -> dict: ...             # node/edge counts
    def analyze(self) -> str: ...            # Markdown analysis report
```

The orchestrator, registry, CLI, and MCP server need no changes. The new domain becomes queryable immediately through every existing interface.

Planned modules include TypeScript, C++, Rust, SQL schemas, Terraform infrastructure, legal corpora, and genomics ontologies. Each one is an independent implementation of the same five methods.

---

## The MCP Interface

An MCP (Model Context Protocol) server wraps the federation layer and exposes five tools to any compatible AI agent:

- `kgrag_query(q)` — federated semantic query across all registered graphs
- `kgrag_pack(q)` — federated snippet extraction, formatted for LLM context
- `kgrag_stats()` — registry summary
- `kgrag_list()` — registered KG entries
- `kgrag_info(name)` — detail on a specific entry

This makes every registered knowledge graph immediately available as a tool in Claude Code, Kilo Code, GitHub Copilot, or Claude Desktop, without any configuration per agent or per graph. Register a graph once; all agents see it.

---

## Temporal Tracking

Knowledge graphs change as their sources change. A pre-commit hook captures a snapshot before each commit, keyed by the tree hash of the files being committed. Each snapshot records node counts, edge counts, a coverage score, and deltas against the previous snapshot and against the baseline.

Over time, this record shows which commits expanded the graph, which contracted it, and how semantic coverage trended. For a large codebase with multiple contributors, it is the primary instrument for detecting documentation decay and tracking structural drift.

---

## What This Enables

A developer onboarding to a large system can issue a single query — "authentication flow" — and receive a ranked set of results spanning the implementation functions, the documentation sections that describe the flow, and the configuration schema that governs it, all in one response.

A research scientist can query "NADH electron transport chain" and receive results from analysis code, pathway data, and published papers simultaneously.

An AI agent coding assistant can retrieve grounded, verified context from across a project's entire knowledge corpus before generating any response, without hallucinating function signatures or misrepresenting call relationships.

The graphs are local. No data leaves the machine. No API call is made at query time. The entire pipeline — parsing, indexing, querying, traversal, snippet extraction — runs on the developer's own infrastructure.

---

*KGRAG is open source. See [github.com/Flux-Frontiers/KGRAG](https://github.com/Flux-Frontiers/KGRAG). The CodeKG module is described in detail in a companion technical paper.*
