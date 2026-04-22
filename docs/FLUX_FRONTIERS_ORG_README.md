<p align="center">
  <img src="assets/logo.png" alt="Flux Frontiers" width="192"/>
</p>

<h1 align="center">Flux Frontiers</h1>

<p align="center">
  <em>One registry. Many KGs. Infinite domains.</em>
</p>

<p align="center">
  <img src="https://img.shields.io/badge/python-3.12%20%7C%203.13-blue.svg" alt="Python">
  <a href="https://www.elastic.co/licensing/elastic-license"><img src="https://img.shields.io/badge/License-Elastic%202.0-blue.svg" alt="License"></a>
  <img src="https://img.shields.io/badge/status-active-brightgreen" alt="Status">
</p>

---

## What We Build

Flux Frontiers is a research and engineering organization focused on **deterministic knowledge-graph retrieval** — turning formally structured artifacts (source code, documents, biochemical pathways, legal statutes, protein structures, personal diaries) into queryable knowledge graphs that AI agents can reason over without hallucination.

Our central conviction: **structure is ground truth**. When an ontology is well-defined — Python's AST, KEGG reaction schemas, PDB file format, statute hierarchies — a knowledge graph derived from it carries the same guarantees as the source itself. Semantics then *accelerate* retrieval; they do not replace correctness.

We build the full stack: individual domain KG libraries, a federated orchestration platform, and MCP server integrations that expose every graph as native tool calls to AI agents.

---

## The Stack

### Domain Knowledge Graph Libraries

| Repository | Kind | Description |
|---|---|---|
| [**PyCodeKG**](https://github.com/Flux-Frontiers/code_kg) | `code` | Python codebase analysis via AST — complete call graph, class hierarchies, import chains, and docstring embeddings. Structural truth + semantic retrieval. |
| [**DocKG**](https://github.com/Flux-Frontiers/doc_kg) | `doc` | Semantic knowledge graph for document corpora — Markdown, plain text, RST. Extracts sections, topics, entities, and cross-references. |
| [**MetaboKG**](https://github.com/Flux-Frontiers/meta_kg) | `meta` | Metabolic pathway knowledge graph backed by KEGG/BioCyc reaction schemas. Supports FBA, ODE simulation, and what-if perturbation analysis. |
| [**DiaryKG**](https://github.com/Flux-Frontiers/diary_kg) | `diary` | Personal diary corpus as a temporally ordered knowledge graph. Chronological narrative + semantic search. |
| [**MemoryKG**](https://github.com/Flux-Frontiers/memory_kg) | `memory` | Episodic memory traces — personal recollections structured as an associative knowledge graph. |
| [**AgentKG**](https://github.com/Flux-Frontiers/agent_kg) | `agent` | Conversational memory as a live knowledge graph. Persists agent session context across turns; queryable by topic and entity. |
| [**FTreeKG**](https://github.com/Flux-Frontiers/ftree_kg) | `ftree` | File system tree knowledge graph — directory hierarchies, file metadata, and structural relationships across codebases and archives. |

### Scientific Computing

| Repository | Description |
|---|---|
| [**ProteusPy**](https://github.com/Flux-Frontiers/proteusPy) | Python library for protein structure analysis — disulfide bond geometry, PDB parsing, torsion angle calculation, visualization. Used in structural bioinformatics research. |
| **WaveRider** *(coming soon)* | Riemannian manifold ML stack — zero-parameter classifiers, geometric gradient descent, and intrinsic dimensionality probes for high-dimensional embedding spaces. |

---

## How It Works

All domain KG libraries implement a common `KGAdapter` protocol — a clean three-method interface (`query`, `pack`, `stats`). Our federation platform uses this contract to fan queries out across every registered graph simultaneously, globally rank the results, and return a unified answer set with full source provenance:

```
User Query: "glucose transport mechanism"
    │
    ├──▶ PyCodeKG  (analysis codebase)   → 3 functions, 1 class
    ├──▶ DocKG     (research papers)     → 4 document sections
    └──▶ MetaboKG  (metabolic pathways)  → 2 pathway nodes, 5 reactions
                               │
                    ┌──────────▼──────────────┐
                    │  Globally Ranked Results │
                    │  (unified relevance)     │
                    └─────────────────────────┘
```

MCP integration means any AI agent — Claude, GitHub Copilot, Cursor, or a custom agent — can make federated queries as native tool calls. The knowledge graph becomes part of the agent's cognitive apparatus.

---

## Design Principles

1. **Structure is authoritative** — Graph edges are derived from formal grammars and ontologies; they are not approximated or inferred.
2. **Semantics accelerate, they do not replace** — Vector embeddings make retrieval fast; structural traversal makes it correct.
3. **Adapter-first extensibility** — Adding a new knowledge domain requires only implementing `KGAdapter`. The federation layer requires no changes.
4. **Agent-first architecture** — MCP integration is first-class, not an afterthought. Every KG is immediately usable by any MCP-compatible agent.
5. **Deterministic retrieval** — Every result is traceable to a source file, line number, or pathway node. Zero hallucination by construction.

---

## Research & Vision

The long-term goal is a **universal knowledge compiler**: a framework that can ingest any formally structured artifact — in any language, any scientific domain — and produce a queryable, traversable knowledge graph that participates fully in federated retrieval.

Near-term expansion targets: TypeScript/JavaScript (`tskg`), C++ (`cppkg`), genomics, US legal corpus, and infrastructure-as-code. The same adapter pattern applies to all of them.

---

## Contact

**Eric G. Suchanek, PhD** — Liberty TWP, OH
[suchanek@flux-frontiers.com](mailto:suchanek@flux-frontiers.com)
OEM licensing, partnership inquiries, and enterprise engagements welcome.

---

*Flux Frontiers — Knowledge graphs as cognitive infrastructure for the AI age.*
