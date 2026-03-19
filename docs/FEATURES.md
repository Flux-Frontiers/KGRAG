# KGRAG Feature List

**KGRAG v0.3.0** — Federated Knowledge Graph Orchestration Layer

---

## Core Architecture

### Multi-KG Registry
- **SQLite-backed persistent registry** at `~/.kgrag/registry.sqlite` (or `KGRAG_REGISTRY` env var)
- Register, list, inspect, and remove KG instances from any repository
- Per-entry metadata: name, kind, paths, version, tags, build timestamps
- `is_built` status check — detects whether SQLite/LanceDB databases actually exist
- Auto-scan directories to discover unregistered KG databases (`kgrag scan`)

### Federated Query Engine
- **Cross-KG semantic search** — one query, results from all registered KGs simultaneously
- **Global relevance ranking** across all graph kinds
- Filter results by KG kind (`--kind code|doc|meta|diary|verse|memory|...`)
- Configurable top-k results per KG (`-k`, default 8)
- JSON output mode for scripting and pipeline integration (`--json`)

### Hybrid Retrieval
- Semantic (vector) search via **LanceDB** and **sentence-transformers**
- Structural graph traversal via **SQLite** adjacency tables
- All results traced to **source files and line numbers** — no hallucinated references

### Snippet Packing
- Extract **context-aware source snippets** ready for LLM prompting
- Configurable context window (`--context N` lines before/after)
- Batch output to Markdown file (`--out snippets.md`)
- Scoped to a specific KG kind or all registered KGs

---

## Supported Knowledge Graph Types

| Kind | Domain | Backend |
|------|--------|---------|
| `code` | Python source — AST-extracted modules, classes, functions, call graphs | CodeKG |
| `doc` | Markdown / RST documentation — topics, entities, cross-references | DocKG |
| `meta` | Biochemical / metabolic pathways — reaction networks | MetaKG |
| `diary` | Personal diary entries — chronological narrative | DiaryKG |
| `verse` | Poetry and verse — structured literary content | VerseKG |
| `memory` | Personal memory traces — episodic recollections | MemoryKG |
| `disulfide` | Protein disulfide bond data — cysteine connectivity | DisulfideKG |
| `pdbfile` | PDB structure files — 3D atomic coordinates | PdbFileKG |
| `legal` | Legal corpus — US Code, Supreme Court opinions | LegalKG |
| `person` | Person corpus — aggregated personal knowledge | PersonAdapter |

---

## Corpus Abstraction

### Named Corpora
- Group arbitrary KGs into **named collections** for scoped queries
- CRUD operations: `corpus create`, `corpus delete`, `corpus add`, `corpus remove`
- List and inspect all corpora (`corpus list`, `corpus info`)
- **Corpus-scoped federated query** — search only within a named group
- **Corpus-scoped snippet pack** — extract snippets from a named group

### Person Corpora
- Individual-centric KG collections with **personal metadata**
  - Birth year and date, address, email, phone, notes
- Aggregate all KGs relevant to a person (diaries, memories, documents, etc.)
- CRUD operations: `corpus person create`, `corpus person update`, `corpus person delete`
- Per-person federated query and snippet pack
- Rich biographical knowledge management

---

## CLI Commands

### Registry Management
| Command | Description |
|---------|-------------|
| `kgrag register` | Register a KG instance with path and metadata |
| `kgrag unregister` | Remove a KG from the registry |
| `kgrag list [--kind]` | List all (or filtered) registered KGs |
| `kgrag info <name>` | Show detailed KG metadata |
| `kgrag status` | Health check — counts, build status, missing paths |
| `kgrag scan [root]` | Auto-discover KG databases and optionally register them |

### Query & Analysis
| Command | Description |
|---------|-------------|
| `kgrag query <text>` | Cross-KG semantic search |
| `kgrag pack <text>` | Extract source snippets to file or stdout |
| `kgrag analyze` | Cross-KG statistics and coverage metrics |

### Corpus Management
| Command | Description |
|---------|-------------|
| `kgrag corpus create/delete` | Manage named corpora |
| `kgrag corpus add/remove` | Modify corpus membership |
| `kgrag corpus list/info` | Inspect corpora |
| `kgrag corpus query/pack` | Scoped query and snippet extraction |
| `kgrag corpus person *` | Full person corpus lifecycle |

### Initialization
| Command | Description |
|---------|-------------|
| `kgrag init [path]` | Auto-detect, build, and register all KG layers |

Options: `--layer code|doc`, `--name`, `--wipe` (rebuild from scratch), `--corpus NAME` (add to existing corpus)

### Integration
| Command | Description |
|---------|-------------|
| `kgrag mcp` | Launch MCP server for AI agent integration |
| `kgrag viz` | Launch interactive Streamlit web dashboard |

---

## MCP Server (AI Agent Integration)

Exposes **30+ tools** to AI agents via Model Context Protocol (stdio transport):

**Registry tools:** `kgrag_stats`, `kgrag_list`, `kgrag_info`

**Query tools:** `kgrag_query`, `kgrag_pack`

**Corpus tools:** `kgrag_corpus_list`, `kgrag_corpus_info`, `kgrag_corpus_create`,
`kgrag_corpus_delete`, `kgrag_corpus_add`, `kgrag_corpus_remove`,
`kgrag_corpus_query`, `kgrag_corpus_pack`

**Person tools:** `kgrag_person_list`, `kgrag_person_info`, `kgrag_person_create`,
`kgrag_person_delete`, `kgrag_person_add`, `kgrag_person_remove`,
`kgrag_person_update`, `kgrag_person_query`, `kgrag_person_pack`

Compatible with **Claude Code**, **Claude Desktop**, **Cursor**, **GitHub Copilot (Kilo Code / Cline)**.

---

## Streamlit Web Dashboard (`kgrag viz`)

- **Registry tab** — browse all registered KGs with live statistics
- **Query tab** — cross-KG semantic search with interactive results table
- **Snippets tab** — view and copy source snippets from query results
- Color-coded KG kind indicators (code = blue, doc = green, meta = purple)
- Registry path selector and query parameter controls in sidebar
- JSON export support

---

## Adapter Layer

Uniform `KGAdapter` protocol over all backends:

| Method | Description |
|--------|-------------|
| `is_available()` | Check if backend library and databases are present |
| `query(text, k)` | Semantic search, returns ranked hits |
| `pack(text, k, context)` | Extract snippets with surrounding context |
| `stats()` | Node/edge counts and index metadata |
| `analyze()` | Structural metrics and coverage |
| `snapshot()` | Point-in-time graph snapshot |

Stub adapter (`_StubAdapter`) provides graceful degradation when a backend is unavailable.

---

## Knowledge Compilation Model

- **Build cost paid once** — embedding is the slow step (like compiling), paid at `kgrag init` time
- **Queries execute in milliseconds** against the pre-built index
- **Snapshot system** — point-in-time snapshots enable differential queries:
  *"What changed since last week?"* — new nodes, new edges, new topics
- **Incremental ingestion with restart** — large corpora ingest in batches; each run resumes where the last stopped; corpus is queryable throughout

---

## Configuration

| Method | Description |
|--------|-------------|
| `KGRAG_REGISTRY` env var | Override default registry path |
| `--registry PATH` flag | Per-command registry override |
| `[tool.kgrag]` in `pyproject.toml` | Project-level KGRAG settings |
| `.mcp.json` | MCP server wiring for Claude Code / Cursor |

---

## Python API

```python
from kg_rag import KGRAG, KGRegistry

# Registry CRUD
with KGRegistry() as reg:
    entries = reg.list(kind="code")
    stats = reg.stats()

# Federated queries
with KGRAG() as kg:
    result = kg.query("authentication flow", k=8)
    pack   = kg.pack("error handling", k=5, context=10)
    result = kg.query_corpus("my-project", "database connection")
    result = kg.query_person("Jane Doe", "childhood memories")
```

---

## Claude Code Integration

- **KGRAG skill** at `.claude/skills/kgrag-usage/` — triggers automatically when querying multiple KGs
- **MCP wiring** via `.mcp.json` — knowledge graphs become agent tools
- **Pre-commit snapshot hook** — auto-captures CodeKG and DocKG snapshots on each commit
- All MCP tools return structured JSON for reliable agent parsing

---

## Data Primitives

| Type | Description |
|------|-------------|
| `KGKind` | StrEnum for all supported graph types |
| `KGEntry` | Single KG instance record (paths, metadata, build status) |
| `RegistryStats` | Aggregate counts by kind and build status |
| `CorpusEntry` | Named collection of KG UUIDs |
| `PersonCorpusEntry` | Person record with metadata and KG list |
| `CrossHit` | Single query result (score, name, kind, summary, source path) |
| `CrossQueryResult` | Ranked list of hits with query metadata |
| `CrossSnippet` | Source snippet with surrounding context lines |
| `CrossSnippetPack` | Collection of snippets with Markdown rendering |

---

## Planned Features (Roadmap)

- **Forest of Knowledge visualizer** — fractal tree rendering of KG topology; corpora as groves; full registry as the TreeOfKnowledge™
- **Graph federation** — cross-KG edge inference (call graph ↔ doc reference ↔ metabolic pathway)
- **Differential federated search** — compare two registry snapshots
- **Additional KG backends** — genomics, legal, financial time-series
- **3D visualization** — `kgrag viz3d` with PyVista / trame-VTK

---

**Last updated:** 2026-03-18
**KGRAG Version:** 0.3.0
