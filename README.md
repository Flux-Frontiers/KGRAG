[![Python](https://img.shields.io/badge/python-3.12%20%7C%203.13-blue.svg)](https://www.python.org/)
[![License: Elastic-2.0](https://img.shields.io/badge/License-Elastic%202.0-blue.svg)](https://www.elastic.co/licensing/elastic-license)
[![Version](https://img.shields.io/badge/version-0.14.0-blue.svg)](https://github.com/Flux-Frontiers/KGRAG/releases)
[![CI](https://github.com/Flux-Frontiers/KGRAG/actions/workflows/ci.yml/badge.svg)](https://github.com/Flux-Frontiers/KGRAG/actions/workflows/ci.yml)
[![Poetry](https://img.shields.io/endpoint?url=https://python-poetry.org/badge/v0.json)](https://python-poetry.org/)
[![DOI](https://img.shields.io/badge/DOI-10.5281%2Fzenodo.20018524-blue.svg)](https://doi.org/10.5281/zenodo.20018524)

<p align="center">
  <img src="assets/logos/logo_256.png" alt="KGRAG logo" width="256"/>
</p>

**KGRAG** — Knowledge Compiler and Federated Retrieval Layer for Ontologically Grounded Domains

*Author: Eric G. Suchanek, PhD · Flux-Frontiers, Liberty TWP, OH*

---

## Overview

<p align="center">
  <img src="assets/kgrag_arch.png" alt="KGRAG architecture" width="720"/>
</p>

KGRAG is a **federation and orchestration layer** for structural knowledge graphs derived from heterogeneous source domains. It integrates [PyCodeKG](https://github.com/Flux-Frontiers/pycode_kg) (Python codebase analysis), [DocKG](https://github.com/Flux-Frontiers/doc_kg) (semantic document indexing), [MetaboKG](https://github.com/Flux-Frontiers/metabo_kg) (metabolic pathways), [DiaryKG](https://github.com/Flux-Frontiers/diary_kg) (personal diary corpora), [AgentKG](https://github.com/Flux-Frontiers/agent_kg) (conversational memory), [FTreeKG](https://github.com/Flux-Frontiers/ftree_kg) (file system trees), and a growing family of domain-specific backends under a **single five-method adapter protocol**.

KGRAG treats **derived structure as ground truth** and uses **semantic embeddings strictly as an acceleration layer** for locating entry points into that structure. All graph traversal, ranking, and snippet extraction is deterministic. When KGRAG output is passed to a language model for synthesis, the model receives verified facts with full source provenance — not approximate embeddings.

**How this differs from RAG and KG-RAG:**
RAG embeds text chunks and retrieves by approximate similarity — no structure, no provenance. KG-RAG (GraphRAG, LlamaIndex KG) uses an LLM to extract entities and edges from text: the graph is inferred, inheriting the extractor's hallucinations. KGRAG derives its graphs from **formal source structure** — ASTs for code, parse trees for prose, reaction schemas for biochemistry — with no language model in the pipeline. The graph is correct by construction. Embeddings are disposable; the graph is not. The retrieval layer **cannot** hallucinate.

→ [Technical paper](articles/kgrag.pdf) · [Manifesto](docs/MANIFESTO.md)

---

## KG Types

### Fully Implemented

| Kind | Backend | Description |
|------|---------|-------------|
| `code` | PyCodeKG | Python codebase — AST-extracted modules, classes, functions, call graphs |
| `doc` | DocKG | Document corpus — Markdown/RST/text indexed by topic, section, and entity |
| `meta` | MetaboKG | Metabolic pathways — biochemical reaction networks (KEGG, BioCyc) |
| `diary` | DiaryKG | Personal diary entries — timestamped chunk graphs with temporal edges |
| `agent` | AgentKG | Conversational memory — Turn/Topic/Task/Summary graph (live session) |
| `filetree` | FTreeKG | File system tree — directory/file/module/dependency structure |
| `memory` | MemoryKG | Episodic memory — hybrid semantic + structural graph for conversation/event corpora |
| `gutenberg` | GutenbergKG | Project Gutenberg book corpus — literature indexed by author, genre, and chapter via DocKG-compatible indices |

### Stub Adapters (protocol boundary, backends under development)

| Kind | Backend | Description |
|------|---------|-------------|
| `ia` | IABookKG | Internet Archive book corpus — public-domain books indexed by genre and topic |
| `pdbfile` | — | PDB structure files — 3D atomic coordinates and protein metadata |
| `disulfide` | — | Disulfide bond data — cysteine connectivity in protein structures |
| `verse` | — | Scripture/verse — Book → Chapter → Verse hierarchy and cross-references |
| `person` | — | Personal knowledge — biographical and relational graphs |
| `legal` | — | Legal corpus — statutory codes and regulations *(TBD)* |

### Corpus Abstractions

**Generic Corpus** — A named collection of any KG instances grouped for scoped federated queries. Useful for project-level or thematic groupings (e.g., `"KGRAG_repos"` combining code + doc KGs).

**Person Corpus** — A corpus enriched with personal metadata representing an individual. Aggregates all KGs relevant to a person — diaries, memories, documents, agent sessions, and more — alongside structured personal data (birth year, address, email, contact info).

---

## Features

- **Document ingestion** — `kgrag ingest` turns loose PDFs, Word documents, EPUBs, spreadsheets, slide decks and Markdown into a staged corpus, builds a KG over it, and registers the result in one command
- **Multi-domain federation** — Query code, docs, metabolic pathways, diary entries, and conversation history simultaneously
- **Five-method adapter protocol** — `is_available`, `query`, `pack`, `stats`, `analyze`; add a new domain by implementing five methods
- **Unified registry** — Persistent SQLite-backed storage of KG locations, metadata, corpora, and person records
- **Corpus abstraction** — Group KGs into named corpora for scoped federated queries
- **Person corpus** — Model individuals with personal metadata and their associated KG collections
- **Hybrid querying** — Semantic seeding via sqlite-vec (legacy LanceDB stores still readable) + structural BFS traversal
- **Context packing** — Extract source-grounded snippets with line numbers for direct LLM ingestion
- **MCP server** — 22 tools exposing registry, corpus, and person operations to any MCP-compatible agent
- **CLI tooling** — Full CRUD for KGs, corpora, and person corpora; query, pack, analyze, synthesize
- **Streamlit dashboard** — Interactive browser for exploring and querying registered knowledge graphs
- **Deterministic retrieval** — Auditable, source-grounded results; zero hallucination at the knowledge layer

---

## Quick Start

```bash
pip install kg-rag

# With Streamlit dashboard
pip install 'kg-rag[viz]'

# With the common adapter backends (PyCodeKG, DocKG, MemoryKG).
# DocKG also backs every GutenbergKG corpus, which queries through it.
pip install 'kg-rag[kg]'

# DiaryKG and FileTreeKG back kinds most registries never hold, so they
# have their own extras rather than riding along with [kg].
pip install 'kg-rag[diary]'
pip install 'kg-rag[filetree]'

# With multi-format document ingestion (PDF, Word, PowerPoint, Excel, EPUB, ...)
pip install 'kg-rag[ingest]'

# Everything except [pi], which needs a compiler toolchain
pip install 'kg-rag[all]'
```

```bash
# Ingest a folder of mixed-format documents: convert → build → register
kgrag ingest ~/Documents/specs --into ~/corpora/specs

# Register a Python codebase
kgrag register my-code code /path/to/my-repo

# Federated query across all registered KGs
kgrag query "authentication flow"

# Snippet pack for LLM ingestion
kgrag pack "database connection setup" --out context.md

# Launch the dashboard
kgrag viz
```

→ [Full installation guide](docs/INSTALLATION.md) · [Usage guide](docs/USAGE.md) · [CLI reference](docs/CLI_REFERENCE.md)

---

## MCP Integration

KGRAG ships a built-in MCP server exposing **22 tools** to any MCP-compatible agent (Claude Code, Cursor, GitHub Copilot, Claude Desktop):

```bash
kgrag mcp
```

```json
{
  "mcpServers": {
    "kgrag": {
      "command": "/path/to/venv/bin/kgrag",
      "args": ["mcp"]
    }
  }
}
```

Tools span three groups: **core KG** (`kgrag_stats`, `kgrag_list`, `kgrag_info`, `kgrag_query`, `kgrag_pack`), **corpus** (8 tools), and **person corpus** (9 tools).

→ [Full MCP reference](docs/MCP.md)

---

## Documentation

| Document | Description |
|----------|-------------|
| [Technical Paper](articles/kgrag.pdf) | Architecture, design principles, and formal treatment |
| [Manifesto](docs/MANIFESTO.md) | The case for Structurally-Grounded Synthetic Intelligence |
| [Installation Guide](docs/INSTALLATION.md) | Prerequisites, venv setup, extras |
| [Usage Guide](docs/USAGE.md) | Workflows, patterns, and examples |
| [CLI Reference](docs/CLI_REFERENCE.md) | Complete command reference |
| [Ingestion Pipeline](docs/INGESTION.md) | Converting loose documents into a registered KG — converters, staging, manifest |
| [MCP Reference](docs/MCP.md) | Tool reference and agent configuration |
| [Adapter Spec](docs/ADAPTER_SPEC.md) | Five-method protocol for new backends |
| [Troubleshooting](docs/TROUBLESHOOTING.md) | Common issues and fixes |
| [Fleet Versions](docs/FLEET_VERSIONS.md) | Generated version & constraint state across the KG fleet |

---

## Related Projects

| Project | Description |
|---------|-------------|
| [PyCodeKG](https://github.com/Flux-Frontiers/pycode_kg) | Deterministic knowledge graph for Python codebases |
| [DocKG](https://github.com/Flux-Frontiers/doc_kg) | Semantic knowledge graph for document corpora |
| [MetaboKG](https://github.com/Flux-Frontiers/metabo_kg) | Metabolic pathway knowledge graph |
| [DiaryKG](https://github.com/Flux-Frontiers/diary_kg) | Diary and personal journal corpus knowledge graph |
| [AgentKG](https://github.com/Flux-Frontiers/agent_kg) | Conversational memory knowledge graph |
| [FTreeKG](https://github.com/Flux-Frontiers/ftree_kg) | File system tree knowledge graph |
| [GutenbergKG](https://github.com/Flux-Frontiers/gutenberg_kg) | Project Gutenberg book corpus knowledge graph |
| MemoryKG *(coming soon)* | Episodic memory knowledge graph for conversation and event corpora |
| IABookKG *(coming soon)* | Internet Archive book corpus knowledge graph |

---

## License

[Elastic License 2.0](https://www.elastic.co/licensing/elastic-license) — see [LICENSE](LICENSE).

Free to use, modify, and distribute. You may not offer the software as a hosted or managed service to third parties. Commercial internal use is permitted.

*The Knowledge Compiler concept and its execution are the subject of a pending U.S. provisional patent application.*

---

## Citation

If you use KGRAG in your research or project, please cite it:

[![DOI](https://img.shields.io/badge/DOI-10.5281%2Fzenodo.20018524-blue.svg)](https://doi.org/10.5281/zenodo.20018524)

> Suchanek, E. G. (2026). *KGRAG: Knowledge Compiler and Federated Retrieval Layer* (Version 0.14.0) [Software]. Flux-Frontiers. https://doi.org/10.5281/zenodo.20018524

```bibtex
@software{suchanek_kgrag,
  author    = {Suchanek, Eric G.},
  title     = {{KGRAG}: Knowledge Compiler and Federated Retrieval Layer},
  version   = {0.14.0},
  year      = {2026},
  publisher = {Flux-Frontiers},
  url       = {https://github.com/Flux-Frontiers/KGRAG},
  doi       = {10.5281/zenodo.20018524},
}
```

---
