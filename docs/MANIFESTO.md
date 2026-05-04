# Structurally-Grounded Synthetic Intelligence

*A Manifesto*

**Eric G. Suchanek, PhD — Flux-Frontiers — 2026-04-23**

---

## The Limitation of Probabilistic AI

The dominant paradigm in artificial intelligence today is probabilistic: large language models learn statistical patterns from text and generate responses that are *plausible* — not *proven*. They hallucinate. They confabulate. They produce answers that feel authoritative and are structurally indistinguishable from correct ones, even when wrong.

This is not a bug to be patched. It is a fundamental property of systems trained to predict the next token. Probability is their substrate. Confidence is their affect. Accuracy is incidental.

---

## A New Field

We are moving from the era of probabilistic AI to **Structurally-Grounded Synthetic Intelligence** (SGSI).

SGSI systems do not guess. They *derive*. Every claim is anchored to a verifiable node in a knowledge structure. Every answer is traceable — from the synthesized response back through the retrieval layer, back to the original source, with provenance intact at every step.

The architecture is not new. Knowledge graphs have existed for decades. Dense semantic retrieval has existed for over a decade. What is new is the combination: a federated graph layer that spans entire corpora, a retrieval mechanism that combines vector similarity with deterministic structural traversal, and a synthesis layer that assembles meaning from verified fragments rather than from learned probability distributions.

Hallucination risk is bounded to the synthesis stage and is **zero** at the knowledge-retrieval stage. The synthesis model still uses a language model — but a mid-tier one is sufficient, because it operates on facts that are correct by construction, not on approximate embeddings.

---

## What This Looks Like in Practice

Ask a probabilistic system: *"How do the Stoics and Russian novelists differ in their understanding of suffering and redemption?"*

It will answer fluently. It may cite Epictetus. It may cite Dostoevsky. It may invent a passage that sounds like Marcus Aurelius. You cannot know which.

Ask an SGSI system the same question — one built on a knowledge graph of the actual texts — and it seeds on vector similarity, traverses the structural graph, and returns the most relevant passages from Marcus Aurelius, Epictetus, Dostoevsky, and Tolstoy, with every passage carrying its book, chapter, and line number as provenance. A language model then synthesizes an answer from those verified passages. The retrieval layer cannot hallucinate what Dostoevsky said, because it did not learn Dostoevsky — it *holds* him.

That is the difference. Not smarter guessing. Grounded knowing.

→ This is not a thought experiment. See [Stoics vs. Russians on Suffering and Redemption](STOICS_VS_RUSSIANS.md) — a recorded live KGRAG run answering this exact question against the actual texts, with every passage carrying full source provenance.

---

## The Pattern in Practice

SGSI is not a proposal awaiting validation. It runs in production today across three radically different domains. Each demonstrates a different facet of what becomes possible when retrieval is grounded in formal structure rather than learned probability.

### Code — PyCodeKG

A Python codebase is a formal structure. The grammar specifies every legal program, and a deterministic parser extracts every function, class, import, and call site without inference. PyCodeKG walks the AST of every module in a repository and stores the typed relationships that actually hold the code together — `CONTAINS`, `CALLS`, `IMPORTS`, `INHERITS`, `RESOLVES_TO` — in SQLite, with a LanceDB vector index alongside.

The result is a graph that knows things `grep` cannot derive. Ask *"who calls `AuthMiddleware.process_request`?"* and a two-phase reverse traversal returns every call site, including those that go through import aliases. Ask *"what are the bridge nodes in this codebase?"* and a betweenness centrality computation surfaces the architectural pinch points. Snapshot the graph across releases and watch where complexity migrates. The call graph is not an approximation — it is a theorem about the source code.

### Metabolism — MetaboKG

This is the case no probabilistic system can match. MetaboKG ingests metabolic pathways in the formats biology actually publishes in — KGML, SBML, BioPAX — and normalizes them into a unified graph of compounds, reactions, enzymes, and pathways with typed relationships (`SUBSTRATE_OF`, `PRODUCT_OF`, `CATALYZES`, `INHIBITS`, `ACTIVATES`). The complete *Homo sapiens* metabolome is 369 pathways, 17,000+ nodes, 40,000+ edges. The iCHO2441 genome-scale model adds 6,337 reactions, 4,174 metabolites, and 2,441 gene products.

What makes MetaboKG unique is that the structural graph is also a *dynamical model*. The same nodes that answer *"trace the shortest path from glucose to ATP"* can be simulated: flux balance analysis on the steady state, kinetic ODE simulations with time courses, perturbation analysis where enzymes are knocked out and downstream effects are computed. No language model can simulate metabolism. KGRAG, sitting on top of MetaboKG, exposes both the structural query surface *and* the simulation surface to an AI agent over MCP. This is SGSI extended past retrieval, into computation.

### Literature — GutenbergKG

GutenbergKG — *The Knowledge Press* — demonstrates that the same pattern scales. Seventy-eight of history's most important works — 445,486 nodes, 4,525,716 edges — indexed as a unified, queryable knowledge graph using the DocKG + KGRAG framework.

The name is deliberate. The Gutenberg press did not change what was written — it changed who could hold it. The Knowledge Press does the same for structured knowledge: any digitized text source, whether Project Gutenberg, the Internet Archive, or a local file corpus, feeds into the same ingestion pipeline and emerges as a queryable knowledge graph. The source is irrelevant; the structure is everything.

When all 75,000 works in the Project Gutenberg corpus — and the millions more in the Internet Archive — are treated not as downloadable files but as a living, queryable knowledge structure, the entire written record of human civilization becomes answerable in seconds, with every claim traceable to a specific passage in a specific work.

### One Architecture

Three domains. Three pipelines. One pattern: take whatever formal structure the source already has — grammar, ontology, document hierarchy — and build the knowledge graph from it. Add semantic embeddings strictly as an acceleration layer for finding entry points. Federate. Query deterministically. Synthesize, when needed, from verified facts.

The same architecture handles ASTs, metabolic networks, and Russian novels because every one of them has a derivable structure. Where formal structure exists, SGSI applies. The only open question is which domain to model next.

---

## The Vision

We are not building a better search engine.

We are building a new kind of mind — one that does not speculate about what Shakespeare meant, but reads him; one that does not approximate Kant, but traverses him; one that synthesizes across Homer, Cervantes, Twain, and Tolstoy not because it was trained on summaries of their work, but because it holds their actual words in a structure it can reason over.

This is Structurally-Grounded Synthetic Intelligence.

The era of probabilistic AI has been transformative. The era of SGSI will be definitive.

---

*First usage of the term "Structurally-Grounded Synthetic Intelligence": April 23, 2026.*

*KGRAG: https://github.com/Flux-Frontiers/KGRAG*
*PyCodeKG: https://github.com/Flux-Frontiers/pycode_kg*
*MetaboKG: https://github.com/Flux-Frontiers/metabo_kg*
*GutenbergKG: https://github.com/Flux-Frontiers/gutenberg_kg*
*Flux-Frontiers: https://github.com/Flux-Frontiers*
