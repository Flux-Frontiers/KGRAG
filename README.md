[![Python](https://img.shields.io/badge/python-3.12%20%7C%203.13-blue.svg)](https://www.python.org/)
[![License: Elastic-2.0](https://img.shields.io/badge/License-Elastic%202.0-blue.svg)](https://www.elastic.co/licensing/elastic-license)
[![Version](https://img.shields.io/badge/version-0.5.1-blue.svg)](https://github.com/Flux-Frontiers/KGRAG/releases)
[![CI](https://github.com/Flux-Frontiers/KGRAG/actions/workflows/ci.yml/badge.svg)](https://github.com/Flux-Frontiers/KGRAG/actions/workflows/ci.yml)
[![Poetry](https://img.shields.io/endpoint?url=https://python-poetry.org/badge/v0.json)](https://python-poetry.org/)
[![DOI](https://zenodo.org/badge/PLACEHOLDER.svg)](https://zenodo.org/badge/latestdoi/PLACEHOLDER)

<p align="center">
  <img src="assets/logo.png" alt="KGRAG logo" width="256"/>
</p>

**KGRAG** — Knowledge Graph Orchestration & Retrieval Framework for Semantic Code, Document, Legal & Scientific Analysis

*Author: Eric G. Suchanek, PhD*

*Flux-Frontiers, Liberty TWP, OH*

---

## Overview

KGRAG is a **unified orchestration layer** for building and querying knowledge graphs across diverse domains — from Python codebases and document corpora to legal archives, personal memories, scientific structure databases, and more. It integrates [CodeKG](https://github.com/Flux-Frontiers/code_kg) (structural code analysis), [DocKG](https://github.com/Flux-Frontiers/doc_kg) (semantic document indexing), and a growing family of specialized KG types under a single management interface, enabling you to:

- **Register and manage** multiple knowledge graphs from different repositories, document sources, and scientific datasets
- **Query across graphs** with semantic search augmented by structural relationships
- **Extract context** from code, documentation, law, and science simultaneously for holistic understanding
- **Build RAG systems** grounded in both structural analysis and semantic document retrieval
- **Organize KGs into corpora** — group related graphs under a named corpus for scoped queries and batch operations
- **Model people** — aggregate all KGs relevant to an individual (diaries, memories, documents, etc.) under a person corpus with rich personal metadata
- **Expose integrations** via MCP (Model Context Protocol) for AI-powered understanding across any domain

KGRAG treats **structure as ground truth** while using **semantics to accelerate retrieval** — making it the foundation for trustworthy Knowledge-Graph RAG (KGRAG) systems that avoid hallucination.

---

## KG Types

KGRAG supports the following knowledge graph types:

| Kind | Description |
|------|-------------|
| `code` | Python codebase — AST-extracted modules, classes, functions, call graphs |
| `doc` | Document corpus — markdown, text, RST indexed by topic and entity |
| `meta` | Metabolic pathways — biochemical reaction networks and pathway graphs |
| `diary` | Personal diary entries — chronological personal narrative |
| `verse` | Poetry and verse — structured literary content |
| `memory` | Personal memory traces — episodic recollections and associations |
| `disulfide` | Disulfide bond data — cysteine connectivity in protein structures |
| `pdbfile` | PDB structure files — 3D atomic coordinates and protein metadata |
| `legal` | Legal corpus — US Code, Supreme Court opinions, statutes, regulations |

### Corpus Types

Beyond individual KGs, KGRAG supports two corpus abstractions:

**Generic Corpus** — A named collection of any KG instances grouped for scoped federated queries. Useful for project-level, subject-area, or thematic groupings (e.g., `"all-law"` containing multiple `legal` KGs, or `"my-project"` combining code + doc KGs).

**Person Corpus** — A corpus enriched with personal metadata representing an individual. Aggregates all KGs relevant to a person — diaries, memories, verse, documents, and more — alongside structured personal data (birth year, address, email, contact info). Designed for personal knowledge management, biographical research, and AI-assisted life logging.

---

## Features

- **Multi-graph management** — Register, index, and query multiple KG instances across all supported types
- **Unified registry** — Persistent SQLite-backed storage of KG locations, metadata, corpora, and person records
- **Corpus abstraction** — Group KGs into named corpora for scoped federated queries and batch operations
- **Person corpus** — Model individuals with personal metadata and their associated KG collections
- **Hybrid querying** — Semantic search augmented with structural graph traversal (call chains, inheritance, cross-references)
- **Context packing** — Extract relevant code snippets and document sections with line numbers
- **Cross-source integration** — Correlate code definitions with documentation, legal references, and scientific data
- **MCP server** — Expose all graphs, corpora, and person records to AI agents (Claude Code, Kilo Code, GitHub Copilot, etc.)
- **CLI tooling** — Full CRUD for KGs, corpora, and person corpora; query, analyze, scan, and initialize
- **Streamlit dashboard** — Interactive browser for exploring registered knowledge graphs
- **Deterministic retrieval** — Auditable, source-grounded results with zero hallucination

---

## Quick Start

### 1. Install KGRAG

```bash
pip install 'kg-rag @ git+https://github.com/Flux-Frontiers/KGRAG.git'
```

Or with Streamlit web interface:

```bash
pip install 'kg-rag[viz] @ git+https://github.com/Flux-Frontiers/KGRAG.git'
```

### 2. Register a Knowledge Graph

Register a Python repository (auto-builds CodeKG):

```bash
kgrag register /path/to/my-repo --type code --name my-code-kg
```

Register a document corpus (auto-builds DocKG):

```bash
kgrag register /path/to/docs --type docs --name my-docs-kg
```

### 3. Query Your Graphs

```bash
# Query across all registered graphs
kgrag query "authentication flow"

# Query a specific graph
kgrag query "user login" --graph my-code-kg

# Extract context snippets for a query
kgrag pack "database connection setup" --format md --out context.md
```

### 4. Launch the Dashboard

```bash
streamlit run src/kg_rag/app.py
```

---

## Usage Examples

### Manage Knowledge Graphs

```bash
# List all registered knowledge graphs
kgrag list

# Show details of a specific graph
kgrag info my-code-kg

# Check indexing status and coverage
kgrag status

# Scan for new repositories and auto-register
kgrag scan --auto-register
```

### Query Operations

```bash
# Semantic query across code graphs
kgrag query "authentication middleware" --k 8 --hop 1

# Pack source-grounded snippets for LLM consumption
kgrag pack "error handling strategy" --format md --out llm_context.md

# Query with structural constraints
kgrag query "database operations" --rels CALLS IMPORTS --max-results 20

# Analyze which graphs are most relevant
kgrag analyze --query "caching mechanism"
```

### Use via MCP in Claude Code / Cline

Once registered, launch the MCP server:

```bash
kgrag mcp
```

Your AI agent gets access to all registered graphs:

```
graph_stats(graph_id)                  # stats for a specific graph
query_codebase(q, graph_id)           # search across code graphs
pack_snippets(q, graph_id)            # extract source with context
get_node(node_id, graph_id)           # fetch definition details
callers(node_id, graph_id)            # find all callers (impact analysis)
explain(node_id, graph_id)            # natural-language explanation
analyze_repo(graph_id)                # architectural analysis
cross_query(q)                        # search across all registered graphs
```

### Python API

```python
from kg_rag import KGRegistry

# Initialize registry
registry = KGRegistry()

# Register a code repository
registry.register("/path/to/repo", graph_type="code", name="my-repo")

# Query across all graphs
results = registry.query("authentication flow", k=8)
for node in results.nodes:
    print(f"{node['graph_id']}: {node['name']} at {node['module_path']}")

# Extract context
pack = registry.pack("user management", max_nodes=10)
pack.save("context.md")
```

---

## Installation

**Requirements:** Python ≥ 3.12, < 3.14

### Standalone (pip)

```bash
# Core install (all graph backends + MCP server)
pip install 'kg-rag @ git+https://github.com/Flux-Frontiers/KGRAG.git'

# With Streamlit web dashboard
pip install 'kg-rag[viz] @ git+https://github.com/Flux-Frontiers/KGRAG.git'

# With 3D visualizer
pip install 'kg-rag[viz3d] @ git+https://github.com/Flux-Frontiers/KGRAG.git'
```

### Existing Poetry project

```bash
# Core (MCP server + registry engine)
poetry add 'kg-rag @ git+https://github.com/Flux-Frontiers/KGRAG.git'

# With Streamlit dashboard
poetry add 'kg-rag[viz] @ git+https://github.com/Flux-Frontiers/KGRAG.git'
```

Or declare in `pyproject.toml`:

```toml
[tool.poetry.dependencies]
kg-rag = {git = "https://github.com/Flux-Frontiers/KGRAG.git"}
kg-rag = {git = "https://github.com/Flux-Frontiers/KGRAG.git", extras = ["viz"]}
```

All CLI tools are available immediately:

```bash
kgrag register --help
kgrag query --help
kgrag list
kgrag mcp --help
```

---

## CLI Reference

### Registry Management

| Command | Description |
|---------|-------------|
| `kgrag register <path>` | Register a new code or document graph |
| `kgrag unregister <name>` | Remove a graph from the registry |
| `kgrag list` | List all registered graphs with metadata |
| `kgrag info <name>` | Show detailed info about a graph |
| `kgrag status` | Check indexing status and health of all graphs |
| `kgrag scan` | Auto-discover and register repositories |

### Query & Analysis

| Command | Description |
|---------|-------------|
| `kgrag query <q>` | Semantic query across all graphs |
| `kgrag pack <q>` | Extract source-grounded context snippets |
| `kgrag analyze [--query <q>]` | Analyze graph coverage and relevance |

### Server & Integration

| Command | Description |
|---------|-------------|
| `kgrag mcp` | Start MCP server for AI agent integration |
| `kgrag dashboard` | Launch Streamlit web interface |

### Examples

```bash
# Register a repository and auto-build its knowledge graph
kgrag register /Users/egs/repos/my-project --type code --name my-proj

# Query all registered graphs
kgrag query "authentication flow"

# Show summary of registered graphs
kgrag list --format table

# Get detailed status
kgrag status --verbose

# Start MCP server for Claude Code
kgrag mcp

# Launch Streamlit dashboard
streamlit run src/kg_rag/app.py
```

---

## Web Dashboard

KGRAG includes an interactive Streamlit dashboard for exploring registered knowledge graphs:

```bash
streamlit run src/kg_rag/app.py
```

**Features:**

| Tab | Description |
|---|---|
| **📊 Registry** | View all registered graphs, import/export settings |
| **🔍 Query** | Semantic search across graphs; filter by source |
| **📦 Context** | Extract and download code/document snippets |
| **📈 Analysis** | Graph coverage, indexing status, recommendations |
| **⚙️ Settings** | Configure defaults, add custom backends |

---

## Architecture

```
Repository 1          Repository 2          Docs Corpus
     ↓                     ↓                       ↓
  CodeKG                CodeKG                  DocKG
  SQLite                SQLite                  SQLite
  LanceDB               LanceDB                 LanceDB
     ↓                     ↓                       ↓
  ┌──────────────────────────────────────────────────┐
  │        KGRAG Registry & Orchestrator             │
  │  (unified query interface, cross-graph search)   │
  └──────────────────────────────────────────────────┘
             ↓                          ↓
        CLI Tools                   MCP Server
     (query, pack,            (AI agents, Claude Code)
      register, list)
```

### Design Principles

1. **Orchestration, not reimplementation** — Builds on CodeKG and DocKG without duplicating their logic
2. **Structure is authoritative** — Graph edges are ground truth; semantics accelerate retrieval
3. **Multi-source integration** — Seamlessly correlates code and documentation
4. **Agent-first architecture** — MCP integration enables AI-powered code understanding
5. **Deterministic retrieval** — All results are traceable to source files and line numbers

### Core Components

| Component | Purpose |
|-----------|---------|
| `KGRegistry` | Central registry of code and document graphs |
| `KGClient` | Query interface across multiple graphs |
| `SnippetPacker` | Extract source-grounded context |
| `MCPServer` | Expose graphs as MCP tools for agents |
| `DashboardApp` | Streamlit interactive explorer |

---

## Project Structure

```
KGRAG/
├── README.md
├── CHANGELOG.md
├── LICENSE
├── pyproject.toml
├── src/
│   └── kg_rag/
│       ├── __init__.py
│       ├── app.py                    # Streamlit dashboard
│       ├── registry.py               # Graph registry management
│       ├── client.py                 # Query interface
│       ├── packer.py                 # Snippet extraction
│       ├── mcp_server.py             # MCP server
│       ├── cli/
│       │   ├── main.py               # Root CLI
│       │   ├── cmd_registry.py       # register, list, info, status
│       │   ├── cmd_query.py          # query, pack
│       │   ├── cmd_analyze.py        # analyze
│       │   └── options.py            # Shared CLI options
│       └── backends/
│           ├── codekg_backend.py     # CodeKG integration
│           └── dockg_backend.py      # DocKG integration
├── tests/
│   ├── test_registry.py
│   ├── test_client.py
│   └── test_integration.py
└── docs/
    └── Architecture.md
```

---

## Development

To work on KGRAG, clone the repository and install in editable mode:

```bash
git clone https://github.com/Flux-Frontiers/KGRAG.git
cd KGRAG
poetry install
poetry install -E viz  # for Streamlit dashboard
```

Run tests:

```bash
poetry run pytest -v
```

### Knowledge Graph Snapshots

The pre-commit hook (`.git/hooks/pre-commit`) automatically captures metrics
snapshots for both CodeKG and DocKG before every commit. After an initial
`codekg build` or `dockg build`, no manual steps are needed — snapshots are
staged and included in the commit automatically.

To seed the snapshot directories on a fresh clone (run once after building each KG):

```bash
codekg snapshot save $(python -c "import importlib.metadata; print(importlib.metadata.version('code-kg'))") --repo .
dockg  snapshot save $(python -c "import importlib.metadata; print(importlib.metadata.version('doc-kg'))")  --repo .
```

Skip snapshot capture for a single commit:

```bash
CODEKG_SKIP_SNAPSHOT=1 git commit ...
```

---

## Related Projects

- **[CodeKG](https://github.com/Flux-Frontiers/code_kg)** — Deterministic knowledge graph for Python codebases (structural analysis)
- **[DocKG](https://github.com/Flux-Frontiers/doc_kg)** — Semantic knowledge graph for document corpora (Markdown, plain text)
- **[MetaKG](https://github.com/Flux-Frontiers/meta_kg)** — Example KGRAG application for metabolic pathway analysis

---

## References

### Technologies

- **[CodeKG](https://github.com/Flux-Frontiers/code_kg)** — AST-based code analysis with semantic indexing
- **[DocKG](https://github.com/Flux-Frontiers/doc_kg)** — Document corpus analysis with semantic search
- **[LanceDB](https://lancedb.com/)** — Vector database for semantic indexing
- **[SQLite](https://www.sqlite.org/)** — Deterministic knowledge graph storage
- **[Model Context Protocol (MCP)](https://modelcontextprotocol.io/)** — AI agent integration
- **[Streamlit](https://streamlit.io/)** — Interactive web dashboard

### Related Work

- **[Microsoft GraphRAG](https://microsoft.com/research/)** — Probabilistic knowledge graph approaches (KGRAG uses deterministic structural analysis)
- **[Amplify](https://amplify.dev/)** — Embedding-only code search (KGRAG augments semantics with structural traversal)

---

## License

[Elastic License 2.0](https://www.elastic.co/licensing/elastic-license) — see [LICENSE](LICENSE).

Free to use, modify, and distribute. You may not offer the software as a hosted or managed service to third parties. Commercial use internally is permitted.
