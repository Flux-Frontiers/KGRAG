# KGAdapter Module Specification

*The contract every KGRAG knowledge graph module must satisfy.*

---

## Overview

Every KG backend plugs into KGRAG by implementing the `KGAdapter` abstract base
class (`src/kg_rag/adapters/base.py`). The adapter wraps one KG library instance,
exposes a uniform five-method interface to the KGRAG orchestrator, and is
instantiated on demand by the `make_adapter()` factory.

The orchestrator never calls a KG library directly — it always goes through an
adapter. This is the boundary that makes federation possible.

```
KGRAG Orchestrator
      │
      ▼
  KGAdapter  (abstract contract)
      │
      ├── CodeKGAdapter  ──▶  code_kg.CodeKG
      ├── DocKGAdapter   ──▶  doc_kg.DocKG
      ├── MetaKGAdapter  ──▶  metakg.MetaKGOrchestrator
      └── <YourAdapter>  ──▶  <your_library>
```

---

## The Contract: `KGAdapter`

```python
from abc import ABC, abstractmethod
from typing import Any
from kg_rag.primitives import CrossHit, CrossSnippet, KGEntry

class KGAdapter(ABC):
    def __init__(self, entry: KGEntry) -> None: ...

    @abstractmethod
    def is_available(self) -> bool: ...

    @abstractmethod
    def query(self, q: str, k: int = 8) -> list[CrossHit]: ...

    @abstractmethod
    def pack(self, q: str, k: int = 8, context: int = 5) -> list[CrossSnippet]: ...

    @abstractmethod
    def stats(self) -> dict[str, Any]: ...

    @abstractmethod
    def analyze(self) -> str: ...
```

All five methods are **abstract** — every new adapter must implement all of them.

---

## Method Specifications

### `__init__(entry: KGEntry) -> None`

Store `entry` as `self.entry`. Do **not** load the KG library or open any
database connections here — initialization must be cheap and side-effect-free.
Defer all I/O to `_load()` called lazily from the other methods.

```python
def __init__(self, entry: KGEntry) -> None:
    super().__init__(entry)
    self._kg: Any = None   # populated lazily by _load()
```

**Pattern:** All three existing adapters use a private `_load()` method that is
called at the top of every I/O method and returns immediately if already loaded
(`if self._kg is not None: return`).

---

### `is_available() -> bool`

Return `True` if and only if:
1. The underlying KG library can be imported, **and**
2. The database files exist and are non-empty (`entry.is_built` is `True`).

Must not raise. Must not load the KG. Must be cheap (import check + path check).

```python
def is_available(self) -> bool:
    try:
        import my_kg_library  # noqa: F401
        return self.entry.is_built
    except ImportError:
        return False
```

**The orchestrator calls `is_available()` before every query.** If it returns
`False`, the KG is silently skipped in permissive mode or raises `ImportError`
in strict mode.

---

### `query(q: str, k: int = 8) -> list[CrossHit]`

Execute a semantic (and optionally structural) query against the KG. Return up
to `k` results ranked by descending relevance score.

**Returns:** `list[CrossHit]` — each hit must set:

| Field | Type | Description |
|-------|------|-------------|
| `kg_name` | `str` | `self.entry.name` |
| `kg_kind` | `KGKind` | `KGKind.CODE` / `.DOC` / `.META` |
| `node_id` | `str` | Stable unique identifier within this KG |
| `name` | `str` | Human-readable name (function name, section title, entity name) |
| `kind` | `str` | Node type (`"function"`, `"chunk"`, `"pathway"`, …) |
| `score` | `float` | Relevance in `[0.0, 1.0]` |
| `summary` | `str` | Docstring, excerpt, or description (may be empty) |
| `source_path` | `str` | File path or source identifier (may be empty) |

**Must not raise** on query errors — return `[]` and log the exception.

---

### `pack(q: str, k: int = 8, context: int = 5) -> list[CrossSnippet]`

Execute a query and return source snippets suitable for direct inclusion in an
LLM context window. `context` is the number of surrounding lines (meaningful for
code KGs; ignored for doc/meta KGs).

**Returns:** `list[CrossSnippet]` — each snippet must set:

| Field | Type | Description |
|-------|------|-------------|
| `kg_name` | `str` | `self.entry.name` |
| `kg_kind` | `KGKind` | Source KG kind |
| `node_id` | `str` | Stable unique identifier |
| `source_path` | `str` | File path or document path |
| `content` | `str` | The actual text/code to include in context |
| `score` | `float` | Relevance in `[0.0, 1.0]` |
| `lineno` | `int \| None` | Start line (code KGs); `None` for doc/meta |
| `end_lineno` | `int \| None` | End line (code KGs); `None` for doc/meta |

**Must not raise** — return `[]` on error.

---

### `stats() -> dict[str, Any]`

Return basic statistics about this KG instance. The dict must include:

| Key | Type | Required | Description |
|-----|------|----------|-------------|
| `"kind"` | `str` | **Yes** | `"code"`, `"doc"`, or `"meta"` |
| `"node_count"` | `int \| str` | Recommended | Total meaningful nodes, or `"n/a"` |
| `"edge_count"` | `int \| str` | Recommended | Total edges, or `"n/a"` |
| `"status"` | `str` | Optional | `"available"` / `"unavailable"` |
| `"error"` | `str` | On failure | Error description |

**Must not raise** — return `{"kind": "...", "error": "..."}` on failure.

Called by the orchestrator's `kgrag_stats` MCP tool and the `kgrag status` CLI.

---

### `analyze() -> str`

Run a full analysis of this KG instance and return a **Markdown-formatted**
report string. The report is adapter-specific in content but must:

1. Begin with a level-1 heading: `# <KG Type> Analysis Report`
2. Include the KG name and path for identification
3. Include the key structural metrics (node count, edge count)
4. Include domain-specific quality signals (coverage, centrality, issues, strengths)
5. Be valid Markdown that can be written to a `.md` file or rendered in a browser

**Must not raise** — return a Markdown error message on failure:
```python
return f"# {KG_TYPE} Analysis\n\nAnalysis failed: {exc}\n"
```

#### Per-Adapter Requirements

**CodeKGAdapter** — delegates to `code_kg.CodeKG.analyze()` which produces:
- Baseline metrics (nodes, edges, node kinds, edge kinds)
- CodeRank top-25 (structural PageRank)
- Fan-in / fan-out analysis
- Docstring coverage percentage
- Public API inventory
- Inheritance hierarchy summary
- Module coupling matrix
- Key call chains

**DocKGAdapter** — uses `doc_kg.dockg_thorough_analysis.DocKGAnalyzer` which produces:
- Baseline metrics (total nodes, total edges)
- Semantic coverage: topic, entity, keyword coverage percentages
- Per-document metrics table (chunks, sections, references, semantic links)
- Hot chunks (highest connectivity)
- Issues list (low coverage, orphaned nodes, etc.)
- Strengths list (well-covered areas)

**MetaKGAdapter** — delegates to `MetaKGOrchestrator.analyze()` when available;
falls back to a stats-based summary. The fallback includes:
- Availability status
- Node count and edge count (if the orchestrator exposes `stats()`)
- A note directing implementors to add `MetaKGOrchestrator.analyze()`

**Future adapters** — the analyze report format is open. Implement what is
meaningful for your domain. At minimum include the three required elements above.

---

## Implementation Checklist

When building a new adapter (e.g., `TypeScriptKGAdapter`):

- [ ] Create `src/kg_rag/adapters/<name>_adapter.py`
- [ ] Subclass `KGAdapter`
- [ ] Implement all five abstract methods
- [ ] Add `_load()` with lazy initialization and import guard
- [ ] Register the new kind in `KGKind` enum (`src/kg_rag/primitives.py`)
- [ ] Add a branch in `make_adapter()` factory (`src/kg_rag/adapters/__init__.py`)
- [ ] Write unit tests in `tests/test_adapters.py` covering:
  - `is_available()` with library present/absent and db built/unbuilt
  - `query()` returns correct `CrossHit` fields
  - `pack()` returns correct `CrossSnippet` fields
  - `stats()` returns dict with `kind` and graceful error fallback
  - `analyze()` returns Markdown string and graceful error fallback
- [ ] Add the new kind to the MCP schema's `kinds` enum in `mcp_server.py`
- [ ] Document in `docs/ADAPTER_SPEC.md` under "KG Module Catalog"

---

## MCP Tool Surface

Each KG adapter's capabilities are exposed through three MCP server layers:

### Per-KG MCP Servers (CodeKG, DocKG, MetaKG)

Each KG library ships its own MCP server with deep, domain-specific tools:

**CodeKG MCP** (`codekg mcp`) — 17 tools:

| Tool | Description |
|------|-------------|
| `query_codebase` | Hybrid semantic + structural query; configurable hop depth, rerank modes, path filtering |
| `pack_snippets` | Source-grounded snippet pack with line numbers for LLM context |
| `callers` | All callers of a node (impact analysis / blast radius) |
| `get_node` | Fetch a single node by ID with optional edge inclusion |
| `graph_stats` | Node/edge counts by kind and relation type |
| `list_nodes` | Enumerate nodes filtered by module path or kind |
| `centrality` | PageRank structural importance ranking |
| `bridge_centrality` | Betweenness centrality (architectural bridges) |
| `framework_nodes` | High-degree dependency nodes (most depended-upon) |
| `analyze_repo` | Full architectural analysis — metrics, call chains, coverage |
| `explain` | Natural-language explanation of a node |
| `rank_nodes` | Custom ranking by configurable signals |
| `query_ranked` | Query + ranking combined |
| `explain_rank` | Explain why a node ranked highly for a query |
| `snapshot_list` | List temporal metric snapshots |
| `snapshot_show` | Show a named snapshot |
| `snapshot_diff` | Diff two snapshots for evolution analysis |

**DocKG MCP** (`dockg mcp`) — 4 tools:

| Tool | Description |
|------|-------------|
| `query_docs` | Hybrid semantic + graph query across the document corpus |
| `pack_docs` | Markdown text pack for LLM context |
| `get_node` | Fetch a single DocKG node by ID |
| `graph_stats` | Node/edge counts for the current corpus |

**MetaKG MCP** (coming) — planned tools:

| Tool | Description |
|------|-------------|
| `query_pathways` | Semantic query across domain entities/pathways |
| `pack_domain` | Domain context pack for LLM |
| `get_entity` | Fetch a single domain node |
| `graph_stats` | Node/edge counts |
| `analyze_domain` | Domain-specific analysis report |

### Federated MCP Server (KGRAG)

The KGRAG MCP server (`kgrag mcp`) federates across all registered KGs:

| Tool | Description |
|------|-------------|
| `kgrag_stats` | Registry summary: total KGs, per-kind counts, built status |
| `kgrag_list` | List all registered KG instances with paths and build status |
| `kgrag_info` | Full detail for a single registered KG |
| `kgrag_query` | Federated semantic query across all KGs — one query, all results |
| `kgrag_pack` | Federated snippet pack — code + docs + domain in one context window |

---

## `.mcp.json` Configuration

All three servers use absolute paths. The canonical configuration for this
repository:

```json
{
  "mcpServers": {
    "codekg": {
      "command": "/home/user/KGRAG/.venv/bin/codekg",
      "args": [
        "mcp",
        "--repo",    "/home/user/KGRAG",
        "--db",      "/home/user/KGRAG/.codekg/graph.sqlite",
        "--lancedb", "/home/user/KGRAG/.codekg/lancedb"
      ]
    },
    "dockg": {
      "command": "/home/user/KGRAG/.venv/bin/dockg",
      "args": [
        "mcp",
        "--repo",    "/home/user/KGRAG",
        "--db",      "/home/user/KGRAG/.dockg/graph.sqlite",
        "--lancedb", "/home/user/KGRAG/.dockg/lancedb"
      ]
    },
    "kgrag": {
      "command": "/home/user/KGRAG/.venv/bin/kgrag",
      "args": ["mcp"]
    }
  }
}
```

**Rules:**
- Always use absolute paths — relative paths break when MCP clients change CWD
- Specify `--db` and `--lancedb` explicitly — don't rely on defaults when running
  from an agent context
- The `kgrag` server reads `~/.kgrag/registry.sqlite` by default; override with
  `--registry /abs/path/to/registry.sqlite` for non-default locations

---

## Data Types Reference

### `KGEntry` (registry entry)

```python
@dataclass
class KGEntry:
    id: str                    # UUID
    name: str                  # human-readable label
    kind: KGKind               # CODE | DOC | META
    repo_path: Path            # repository / corpus root
    venv_path: Path            # Python virtual environment
    sqlite_path: Path | None   # SQLite database file
    lancedb_path: Path | None  # LanceDB directory
    version: str               # KG library version
    tags: list[str]            # grouping/filtering labels
    created_at: datetime
    updated_at: datetime
    metadata: dict[str, Any]   # extension point

    @property
    def is_built(self) -> bool:
        """True if at least one DB file exists and is non-empty."""
```

### `CrossHit` (single query result)

```python
@dataclass
class CrossHit:
    kg_name: str       # source KG name
    kg_kind: KGKind    # source KG kind
    node_id: str       # stable ID within the source KG
    name: str          # human-readable name
    kind: str          # node type (function, chunk, pathway, …)
    score: float       # relevance [0.0, 1.0]
    summary: str       # docstring / excerpt / description
    source_path: str   # file path or source identifier
```

### `CrossSnippet` (LLM context snippet)

```python
@dataclass
class CrossSnippet:
    kg_name: str          # source KG name
    kg_kind: KGKind       # source KG kind
    node_id: str          # stable ID within the source KG
    source_path: str      # file or document path
    content: str          # text / code to include in context
    score: float          # relevance [0.0, 1.0]
    lineno: int | None    # start line (code); None for doc/meta
    end_lineno: int | None
```

---

## KG Module Catalog

| Module | Kind | Library | `analyze()` Source | Status |
|--------|------|---------|-------------------|--------|
| CodeKG-Python | `code` | `code-kg` | `CodeKG.analyze()` | ✅ Production |
| DocKG | `doc` | `doc-kg` | `DocKGAnalyzer.run_analysis()` | ✅ Production |
| MetaKG | `meta` | `metakg` | `MetaKGOrchestrator.analyze()` + fallback | ✅ Adapter ready |
| CodeKG-TypeScript | `code` | `tskg` (planned) | `TypeScriptKG.analyze()` | 🔲 Planned |
| CodeKG-Cpp | `code` | `cppkg` (planned) | `CppKG.analyze()` | 🔲 Planned |
| SchemaKG | `meta` | `schemakg` (planned) | `SchemaKGAnalyzer.run_analysis()` | 🔲 Planned |
| InfraKG | `meta` | `infrakg` (planned) | `InfraKGAnalyzer.run_analysis()` | 🔲 Planned |

---

*For federation architecture, see [VISION.md](VISION.md).*
*For use cases and example queries, see [USE_CASES.md](USE_CASES.md).*
*For the product and licensing model, see [PRODUCT_MODEL.md](PRODUCT_MODEL.md).*
