# KGModule Developer Guide

*Build a production-grade knowledge graph for any domain in two classes.*

---

## Overview

`pycode_kg.module` is an SDK base layer that lets you build a full-featured knowledge graph
for **any domain** — TypeScript code, genomics data, legal text, infrastructure graphs — by
implementing a single extraction class.  You get SQLite persistence, LanceDB vector indexing,
hybrid semantic + structural query, snapshot management, and an MCP server, identical in
capability to PyCodeKG, without reimplementing any infrastructure.

```
Your domain:
  MyExtractor(KGExtractor)   ← the only thing you write
       │
       ▼
  KGModule (this package)    ← provides everything below automatically
  ├── GraphStore (SQLite)
  ├── SemanticIndex (LanceDB)
  ├── HybridQueryEngine
  ├── SnapshotManager
  └── MCP server via FastMCP
```

---

## Quick Start

```python
from pycode_kg.module import KGModule, KGExtractor, NodeSpec, EdgeSpec
from pathlib import Path
from typing import Iterator


# Step 1 — teach the infrastructure how to parse your domain
class MyExtractor(KGExtractor):

    def node_kinds(self) -> list[str]:
        return ["document", "section"]

    def edge_kinds(self) -> list[str]:
        return ["CONTAINS", "REFERENCES"]

    def extract(self) -> Iterator[NodeSpec | EdgeSpec]:
        for path in self.repo_path.rglob("*.txt"):
            yield NodeSpec(
                node_id=f"document:{path.name}",
                kind="document",
                name=path.stem,
                qualname=path.stem,
                source_path=str(path.relative_to(self.repo_path)),
                docstring=path.read_text()[:500],
            )


# Step 2 — wire the extractor into the KGModule
class MyKG(KGModule):

    def make_extractor(self) -> MyExtractor:
        return MyExtractor(self.repo_root)

    def kind(self) -> str:
        return "doc"    # or register a new KGKind

    def analyze(self) -> str:
        stats = self.stats()
        return f"# MyKG Analysis\n\n{stats.node_count} nodes, {stats.edge_count} edges.\n"


# Step 3 — use it
kg = MyKG(
    repo_root=Path("/path/to/data"),
    db_path=Path(".mykg/graph.sqlite"),
    lancedb_path=Path(".mykg/lancedb"),
)
kg.build(wipe=True)

result = kg.query("search term")
pack   = kg.pack("search term", context=3)
```

---

## API Reference

### `KGExtractor` — domain extraction protocol

```python
from pycode_kg.module import KGExtractor, NodeSpec, EdgeSpec
```

**Abstract methods (must implement):**

| Method | Returns | Description |
|--------|---------|-------------|
| `node_kinds()` | `list[str]` | Canonical node type names your extractor emits |
| `edge_kinds()` | `list[str]` | Canonical edge relation strings your extractor emits |
| `extract()` | `Iterator[NodeSpec \| EdgeSpec]` | Parse source, yield nodes and edges |

**Optional overrides:**

| Method | Default | When to override |
|--------|---------|-----------------|
| `meaningful_node_kinds()` | all `node_kinds()` | Exclude structural stubs from the vector index and coverage metrics |
| `coverage_metric(nodes)` | fraction with non-empty docstring | Domain-appropriate quality signal for snapshots |
| `source_text(node)` | reads `lineno:end_lineno` from `source_path` | Override if content isn't in flat files (DB, parsed object model, etc.) |

---

### `NodeSpec` — intermediate node representation

```python
@dataclass
class NodeSpec:
    node_id: str           # stable unique ID  (e.g. 'fn:src/foo.py:bar')
    kind: str              # domain type ('function', 'gene', 'statute', …)
    name: str              # human-readable short name
    qualname: str          # fully-qualified name within its source
    source_path: str       # repo-relative path to source file or document
    lineno: int | None     # 1-based start line (None for doc/domain KGs)
    end_lineno: int | None # 1-based end line (None if not applicable)
    docstring: str         # text embedded in the vector index
    metadata: dict         # domain extension data (stored as JSON)
```

`node_id` format convention: `'<kind>:<source_path>:<qualname>'`, e.g.
`'function:src/app.py:MyClass.my_method'`.  Must be stable across builds for
snapshot deltas to be meaningful.

---

### `EdgeSpec` — intermediate edge representation

```python
@dataclass
class EdgeSpec:
    source_id: str     # node_id of the source node
    target_id: str     # node_id of the target (may be unresolved at extract time)
    relation: str      # edge type ('CALLS', 'IMPORTS', 'LINKED_TO', …)
    weight: float      # PageRank edge weight (default 1.0)
    metadata: dict     # domain extension data (stored as evidence JSON)
```

Forward references are allowed: `target_id` may reference a node that has not
been yielded yet.  The build pipeline processes all `NodeSpec` objects first,
then all `EdgeSpec` objects, so cross-file references are resolved correctly.

---

### `KGModule` — infrastructure base class

```python
from pycode_kg.module import KGModule
```

**Constructor:**

```python
KGModule(
    repo_root: Path,
    db_path: Path,
    lancedb_path: Path,
    embed_model: str = "all-MiniLM-L6-v2",
    config: dict | None = None,
)
```

**Abstract methods (must implement):**

| Method | Returns | Description |
|--------|---------|-------------|
| `make_extractor()` | `KGExtractor` | Factory: return the extractor for this module |
| `kind()` | `str` | KGKind string: `'code'`, `'doc'`, `'meta'`, or custom |
| `analyze()` | `str` | Full Markdown analysis report |

**Concrete methods (provided):**

| Method | Description |
|--------|-------------|
| `build(wipe=False)` | Full build pipeline: extract → SQLite → LanceDB. Returns `BuildStats`. |
| `query(q, k=8, hop=1, rels=None, min_score=0.0, rerank_mode="hybrid")` | Hybrid semantic + structural query. Returns `QueryResult`. |
| `pack(q, k=8, hop=1, context=5, max_lines=200)` | Query + source snippets for LLM context. Returns `SnippetPack`. |
| `stats()` | Node/edge counts by kind and relation. |
| `get_node(node_id, include_edges=False)` | Single node lookup by stable ID. |
| `list_nodes(module_path="", kind="")` | Enumerate nodes filtered by path prefix or kind. |
| `callers(node_id, rel=None)` | All nodes with an edge pointing to `node_id`. |
| `centrality(top=20, kinds=None, group_by="node")` | PageRank structural importance ranking. |
| `snapshot_save(version)` | Capture current metrics as a snapshot. |
| `snapshot_list(limit=10, branch="")` | List snapshots newest-first. |
| `snapshot_show(key="latest")` | Full snapshot detail. |
| `snapshot_diff(key_a, key_b)` | Side-by-side snapshot comparison. |

**Optional overrides:**

| Method | Description |
|--------|-------------|
| `_kind_priority()` | Return `dict[str, int]` to control node ordering in results. |
| `_post_build_hook(nodes, edges)` | Called after the build pipeline; used by `PyCodeKG` for symbol resolution. |

---

## Result Types

```python
from pycode_kg.module import BuildStats, QueryResult, Snippet, SnippetPack
```

| Type | Fields |
|------|--------|
| `BuildStats` | `node_count`, `edge_count`, `duration_s`, `wipe` |
| `QueryResult` | `nodes: list[dict]`, `edges: list[dict]`, `query`, `elapsed_s` |
| `Snippet` | `node_id`, `kind`, `name`, `source_path`, `lineno`, `end_lineno`, `content`, `score` |
| `SnippetPack` | `snippets: list[Snippet]`, `query`, `total_lines`, `warnings: list[str]` |

---

## Reference Implementation: `PyCodeKG`

`PyCodeKG` (`src/pycode_kg/kg.py`) is a `KGModule` subclass and the reference
implementation for code-domain KG modules.  Read it to understand how the
hooks work:

- `make_extractor()` → returns `PyCodeKGExtractor` (Python AST)
- `kind()` → `"code"`
- `_kind_priority()` → deprioritizes `symbol` stubs
- `_post_build_hook()` → calls `resolve_symbols()` for cross-module call resolution
- `analyze()` → delegates to `PyCodeKGThoroughAnalysis`

---

## KGRAG Integration

A `KGModule` instance integrates with the KGRAG federation layer via a
`KGAdapter` shim.  The adapter wraps the 5-method `KGAdapter` contract
(`is_available`, `query`, `pack`, `stats`, `analyze`) and delegates to this
module.

```python
# In src/kg_rag/adapters/my_adapter.py
from kg_rag.adapters.base import KGAdapter
from kg_rag.primitives import CrossHit, CrossSnippet, KGEntry, KGKind
from my_kg import MyKG


class MyKGAdapter(KGAdapter):

    def __init__(self, entry: KGEntry) -> None:
        super().__init__(entry)
        self._kg: MyKG | None = None

    def _load(self) -> None:
        if self._kg is not None:
            return
        self._kg = MyKG(
            repo_root=self.entry.repo_path,
            db_path=self.entry.sqlite_path,
            lancedb_path=self.entry.lancedb_path,
        )

    def is_available(self) -> bool:
        try:
            import my_kg  # noqa: F401
            return self.entry.is_built
        except ImportError:
            return False

    def query(self, q: str, k: int = 8) -> list[CrossHit]:
        self._load()
        result = self._kg.query(q, k=k)
        return [
            CrossHit(
                kg_name=self.entry.name,
                kg_kind=KGKind.DOC,
                node_id=n["node_id"],
                name=n["name"],
                kind=n["kind"],
                score=n["score"],
                summary=n.get("docstring", ""),
                source_path=n.get("source_path", ""),
            )
            for n in result.nodes
        ]

    def pack(self, q: str, k: int = 8, context: int = 5) -> list[CrossSnippet]:
        self._load()
        pack = self._kg.pack(q, k=k, context=context)
        return [
            CrossSnippet(
                kg_name=self.entry.name,
                kg_kind=KGKind.DOC,
                node_id=s.node_id,
                source_path=s.source_path,
                content=s.content,
                score=s.score,
                lineno=s.lineno,
                end_lineno=s.end_lineno,
            )
            for s in pack.snippets
        ]

    def stats(self) -> dict:
        self._load()
        s = self._kg.stats()
        return {"kind": self._kg.kind(), "node_count": s.node_count, "edge_count": s.edge_count}

    def analyze(self) -> str:
        self._load()
        return self._kg.analyze()
```

See [ADAPTER_SPEC.md](ADAPTER_SPEC.md) (in the KGRAG repo) for the full adapter
contract and checklist.

---

## Checklist: New KG Module

- [ ] Implement `KGExtractor` subclass:
  - [ ] `node_kinds()` — list your node types
  - [ ] `edge_kinds()` — list your edge relations
  - [ ] `extract()` — parse source, yield `NodeSpec` / `EdgeSpec`
  - [ ] `source_text()` — override if content isn't in flat files *(optional)*
  - [ ] `meaningful_node_kinds()` — exclude structural stubs *(optional)*
  - [ ] `coverage_metric()` — domain-appropriate quality signal *(optional)*
- [ ] Implement `KGModule` subclass:
  - [ ] `make_extractor()` — return your extractor
  - [ ] `kind()` — return KGKind string
  - [ ] `analyze()` — Markdown analysis report
- [ ] Write tests:
  - [ ] `test_extractor.py` — node/edge counts, schema correctness
  - [ ] `test_query.py` — semantic and structural query results
  - [ ] `test_pack.py` — snippet content and line numbers
  - [ ] `test_snapshots.py` — save, list, diff round-trip
- [ ] Create `KGAdapter` shim in KGRAG (or use `module.make_adapter()` when available)
- [ ] Register in `make_adapter()` factory (`adapters/__init__.py`)
- [ ] Document in KGRAG `docs/ADAPTER_SPEC.md` KG Module Catalog table

---

*See [KGMODULE_SPEC.md](../kg_rag/docs/KGMODULE_SPEC.md) for architecture rationale.*
*See [ADAPTER_SPEC.md](https://github.com/Flux-Frontiers/kgrag/blob/main/docs/ADAPTER_SPEC.md) for the KGRAG integration contract.*
