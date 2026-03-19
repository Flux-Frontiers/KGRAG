# Release Notes — KGRAG v0.3.3

> Released: 2026-03-19
> Author: Eric G. Suchanek, PhD · Flux-Frontiers

---

## What Is KGRAG?

KGRAG is a **unified orchestration and retrieval framework** for knowledge graphs
spanning multiple domains — Python codebases, document corpora, metabolic
pathways, protein structures, legal archives, personal diaries, and more. It
integrates [CodeKG](https://github.com/Flux-Frontiers/code_kg) and
[DocKG](https://github.com/Flux-Frontiers/doc_kg) as first-class backends and
provides a single, coherent interface — CLI, Python API, MCP server, and
Streamlit dashboard — for building, querying, and reasoning across all of them
simultaneously.

The central idea is that **structure is ground truth**. Every knowledge graph
compiled by KGRAG is derived deterministically from the formal structure of its
source — ASTs for code, parse trees for documents, reaction schemas for
biochemistry, statutory hierarchies for law. Semantic embeddings accelerate
retrieval; the structural graph decides what is returned. Results are always
traceable to a source file and line number. There is no hallucination at the
knowledge layer.

---

## The 0.3.x Series: From Prototype to Platform

The 0.3.x releases mark the transition of KGRAG from a working prototype into a
coherent, production-ready platform. The core federation engine, registry, corpus
abstractions, CLI, and MCP server are all complete. Three adapters — CodeKG,
DocKG, and MetaKG — are fully operational. The remaining domain adapters
(DiaryKG, VerseKG, MemoryKG, DisulfideKG, PDBFileKG, LegalKG) are stubbed and
ready to activate as their backing libraries mature.

### What Was Built

**Federation and Registry** — The `KGRAG` orchestrator and `KGRegistry` are the
heart of the system. Any number of knowledge graphs — across any mix of supported
kinds — can be registered, queried, and managed through a single persistent
SQLite-backed registry. The orchestrator fans queries out to all registered
graphs, ranks results globally, and returns a unified response with full
provenance.

**Corpus and Person Abstractions** — Knowledge about real things rarely lives in
one graph. The `CorpusRegistry` lets you group related KGs into named corpora for
scoped federated queries. The `PersonCorpusRegistry` extends this with personal
metadata — birth year, address, email, notes — making KGRAG a natural foundation
for personal knowledge management, biographical research, and AI-assisted life
logging.

**Adapter Architecture** — Every domain exposes exactly five methods
(`query`, `pack`, `stats`, `analyze`, `is_available`) through the `KGAdapter`
base class. The orchestrator treats all adapters identically. Adding a new domain
means implementing those five methods; the rest of the system — registry, CLI,
MCP server, corpus abstractions — requires no changes. This is the extensibility
guarantee that makes the TreeOfKnowledge(tm) vision achievable.

**MCP Server** — The `kgrag mcp` command exposes 23 tools to AI agents (Claude
Code, Kilo Code, GitHub Copilot, and any MCP-compatible client) via stdio
transport. The tool surface is organized in three groups:

- *Registry tools* (`kgrag_stats`, `kgrag_list`, `kgrag_info`) — inspect the
  registry and individual KG entries.
- *Federated query tools* (`kgrag_query`, `kgrag_pack`) — semantic search and
  source-snippet extraction across all registered KGs simultaneously, with
  optional kind filtering.
- *Corpus tools* (`kgrag_corpus_*`) — full lifecycle management of named corpora:
  create, delete, add/remove members, and run corpus-scoped federated queries and
  snippet packs.
- *Person tools* (`kgrag_person_*`) — the same lifecycle for person corpora,
  plus update of personal metadata (birth year, address, email, phone, notes).

Every tool returns structured JSON or Markdown, making results reliable for
agent parsing and downstream synthesis.

**CLI Tooling** — A full command suite covers the complete lifecycle: `kgrag
init` (one-shot build and register), `kgrag register / unregister / list / info /
status / scan` (registry CRUD), `kgrag query / pack` (federated retrieval),
`kgrag analyze` (architectural analysis), `kgrag mcp` (MCP server), `kgrag viz`
(Streamlit dashboard), and the new `kgrag install-hooks` (pre-commit integration).

**Streamlit Dashboard** — `kgrag viz` launches an interactive browser with tabs
for registry management, federated query, and context snippet extraction, with
per-KG-kind colour coding.

**Pre-commit Integration** — `kgrag install-hooks` installs a KGRAG-aware
pre-commit hook that automatically captures CodeKG and DocKG snapshots before
every commit, keeping the graph history in sync with the source history.

**Test Suite** — 120 tests covering primitives, registry CRUD, config loading,
adapter factory, orchestrator federation, and all CLI commands via `CliRunner`.

### Dependency Stability

`sentence-transformers` is pinned to `==4.1.0` and `transformers` is constrained
to `<5.0.0` to ensure reproducible embedding behaviour across environments. The
Python lower bound is `>=3.12` (corrected from the inadvertent `>3.12` that
excluded 3.12.0).

---

## Looking Ahead

The architecture is complete. The remaining work is domain coverage — activating
the stubbed adapters as their backing libraries ship — and the distribution layer:
the `kgrag://` URL scheme, the KG Package Index, and the TreeOfKnowledge(tm)
visualizer. Each of these is a natural extension of what is already built; none
requires changes to the federation core.

The vision is a single query interface across all human knowledge, in every
domain where a formal ontology exists. KGRAG 0.3.3 is the foundation that makes
that possible.

---

_Full changelog: [CHANGELOG.md](CHANGELOG.md)_
