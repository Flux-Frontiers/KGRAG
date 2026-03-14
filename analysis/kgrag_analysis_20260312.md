> **Analysis Report Metadata**
> - **Generated:** 2026-03-12T22:51:27Z
> - **Version:** code-kg 0.8.0
> - **Commit:** 053fbd5 (main)
> - **Platform:** Darwin arm64 | Python 3.12.13
> - **Graph:** 1023 nodes · 1239 edges (104 meaningful)
> - **Included directories:** src
> - **Excluded directories:** none
> - **Elapsed time:** 4s

# kgrag Analysis

**Generated:** 2026-03-12 22:51:27 UTC

---

## 📊 Executive Summary

This report provides a comprehensive architectural analysis of the **kgrag** repository using CodeKG's knowledge graph. The analysis covers complexity hotspots, module coupling, key call chains, and code quality signals to guide refactoring and architecture decisions.

| Overall Quality | Grade | Score |
|----------------|-------|-------|
| 🟢 **Good** | **B** | 80 / 100 |

---

## 📈 Baseline Metrics

| Metric | Value |
|--------|-------|
| **Total Nodes** | 1023 |
| **Total Edges** | 1239 |
| **Modules** | 18 (of 18 total) |
| **Functions** | 20 |
| **Classes** | 13 |
| **Methods** | 53 |

### Edge Distribution

| Relationship Type | Count |
|-------------------|-------|
| CALLS | 306 |
| CONTAINS | 86 |
| IMPORTS | 136 |
| ATTR_ACCESS | 365 |
| INHERITS | 6 |

---

## 🔥 Fan-In Ranking

Most-called functions are potential bottlenecks or core functionality. These functions are heavily depended upon across the codebase.

| # | Function | Module | Callers |
|---|----------|--------|---------|
| 1 | `list()` | src/kg_rag/registry.py | **7** |
| 2 | `get()` | src/kg_rag/registry.py | **7** |
| 3 | `KGRegistry()` | src/kg_rag/registry.py | **7** |
| 4 | `from_str()` | src/kg_rag/primitives.py | **6** |
| 5 | `pack()` | src/kg_rag/adapters/base.py | **5** |
| 6 | `query()` | src/kg_rag/adapters/base.py | **5** |
| 7 | `pack()` | src/kg_rag/adapters/codekg_adapter.py | **5** |
| 8 | `query()` | src/kg_rag/adapters/codekg_adapter.py | **5** |
| 9 | `pack()` | src/kg_rag/adapters/dockg_adapter.py | **5** |
| 10 | `query()` | src/kg_rag/adapters/dockg_adapter.py | **5** |
| 11 | `pack()` | src/kg_rag/adapters/metakg_adapter.py | **5** |
| 12 | `query()` | src/kg_rag/adapters/metakg_adapter.py | **5** |
| 13 | `pack()` | src/kg_rag/cli/cmd_query.py | **5** |
| 14 | `query()` | src/kg_rag/cli/cmd_query.py | **5** |
| 15 | `pack()` | src/kg_rag/orchestrator.py | **5** |


**Insight:** Functions with high fan-in are either core APIs or bottlenecks. Review these for:
- Thread safety and performance
- Clear documentation and contracts
- Potential for breaking changes

---

## 🔗 High Fan-Out Functions (Orchestrators)

Functions that call many others may indicate complex orchestration logic or poor separation of concerns.

✓ No extreme high fan-out functions detected. Well-balanced architecture.

---

## 📦 Module Architecture

Top modules by dependency coupling and cohesion (showing up to 10 with activity).
Cohesion = incoming / (incoming + outgoing + 1); higher = more internally focused.

| Module | Functions | Classes | Incoming | Outgoing | Cohesion |
|--------|-----------|---------|----------|----------|----------|
| `src/kg_rag/registry.py` | 1 | 1 | 4 | 1 | 0.17 |
| `src/kg_rag/primitives.py` | 0 | 7 | 11 | 0 | 0.00 |
| `src/kg_rag/orchestrator.py` | 0 | 1 | 4 | 4 | 0.44 |
| `src/kg_rag/adapters/codekg_adapter.py` | 0 | 1 | 1 | 2 | 0.50 |
| `src/kg_rag/adapters/dockg_adapter.py` | 0 | 1 | 1 | 2 | 0.50 |
| `src/kg_rag/adapters/metakg_adapter.py` | 0 | 1 | 1 | 2 | 0.50 |
| `src/kg_rag/adapters/base.py` | 0 | 1 | 5 | 1 | 0.14 |
| `src/kg_rag/cli/cmd_registry.py` | 6 | 0 | 1 | 3 | 0.60 |
| `src/kg_rag/mcp_server.py` | 5 | 0 | 0 | 2 | 0.67 |
| `src/kg_rag/cli/cmd_query.py` | 3 | 0 | 1 | 3 | 0.60 |

---

## 🔗 Key Call Chains

Deepest call chains in the codebase.

**Chain 1** (depth: 4)

```
iter → list → _row_to_entry → KGEntry
```

**Chain 2** (depth: 4)

```
update → get → _row_to_entry → KGEntry
```

**Chain 3** (depth: 2)

```
__init__ → KGRegistry
```

**Chain 4** (depth: 2)

```
pack → pack
```

---

## 🔓 Public API Surface

Identified public APIs (module-level functions with high usage).

| Function | Module | Fan-In | Type |
|----------|--------|--------|------|
| `KGRegistry()` | src/kg_rag/registry.py | 7 | class |
| `pack()` | src/kg_rag/cli/cmd_query.py | 5 | function |
| `query()` | src/kg_rag/cli/cmd_query.py | 5 | function |
| `KGEntry()` | src/kg_rag/primitives.py | 4 | class |
| `CrossHit()` | src/kg_rag/primitives.py | 3 | class |
| `KGRAG()` | src/kg_rag/orchestrator.py | 3 | class |
| `CrossSnippet()` | src/kg_rag/primitives.py | 3 | class |
| `register()` | src/kg_rag/cli/cmd_registry.py | 2 | function |
| `main()` | src/kg_rag/mcp_server.py | 1 | function |
| `CrossSnippetPack()` | src/kg_rag/primitives.py | 1 | class |
---

## 📝 Docstring Coverage

Docstring coverage directly determines semantic retrieval quality. Nodes without
docstrings embed only structured identifiers (`KIND/NAME/QUALNAME/MODULE`), where
keyword search is as effective as vector embeddings. The semantic model earns its
value only when a docstring is present.

| Kind | Documented | Total | Coverage |
|------|-----------|-------|----------|
| `function` | 15 | 20 | 🟡 75.0% |
| `method` | 36 | 53 | 🟡 67.9% |
| `class` | 13 | 13 | 🟢 100.0% |
| `module` | 18 | 18 | 🟢 100.0% |
| **total** | **82** | **104** | **🟡 78.8%** |

> **Recommendation:** 22 nodes lack docstrings. Prioritize documenting high-fan-in functions and public API surface first — these have the highest impact on query accuracy.

---

## 🏆 Structural Importance Ranking (SIR)

Weighted PageRank aggregated by module — reveals architectural spine. Cross-module edges boosted 1.5×; private symbols penalized 0.85×. Node-level detail: `codekg centrality --top 25`

| Rank | Score | Members | Module |
|------|-------|---------|--------|
| 1 | 0.258511 | 18 | `src/kg_rag/registry.py` |
| 2 | 0.253323 | 13 | `src/kg_rag/primitives.py` |
| 3 | 0.128204 | 12 | `src/kg_rag/orchestrator.py` |
| 4 | 0.070423 | 7 | `src/kg_rag/adapters/base.py` |
| 5 | 0.055631 | 8 | `src/kg_rag/adapters/metakg_adapter.py` |
| 6 | 0.054856 | 8 | `src/kg_rag/adapters/dockg_adapter.py` |
| 7 | 0.054856 | 8 | `src/kg_rag/adapters/codekg_adapter.py` |
| 8 | 0.032805 | 6 | `src/kg_rag/mcp_server.py` |
| 9 | 0.030109 | 7 | `src/kg_rag/cli/cmd_registry.py` |
| 10 | 0.026790 | 4 | `src/kg_rag/cli/cmd_query.py` |
| 11 | 0.018616 | 2 | `src/kg_rag/cli/main.py` |
| 12 | 0.010917 | 2 | `src/kg_rag/config.py` |
| 13 | 0.010176 | 2 | `src/kg_rag/adapters/__init__.py` |
| 14 | 0.009143 | 2 | `src/kg_rag/cli/cmd_mcp.py` |
| 15 | 0.008702 | 2 | `src/kg_rag/cli/cmd_analyze.py` |



---

## ⚠️  Code Quality Issues

- ⚠️  Moderate docstring coverage (78.8%) — semantic retrieval quality is degraded for undocumented nodes; BM25 is as effective as embeddings without docstrings

---

## ✅ Architectural Strengths

- ✓ Well-structured with 15 core functions identified
- ✓ No obvious dead code detected
- ✓ No god objects or god functions detected
- ✓ Multiple inheritance used in 1 class(es) without diamond patterns

---

## 💡 Recommendations

### Immediate Actions
1. **Improve docstring coverage** — 22 nodes lack docstrings; prioritize high-fan-in functions and public APIs first for maximum semantic retrieval gain

### Medium-term Refactoring
1. **Harden high fan-in functions** — `list`, `get`, `KGRegistry` are widely depended upon; review for thread safety, clear contracts, and stable interfaces
2. **Reduce module coupling** — consider splitting tightly coupled modules or introducing interface boundaries
3. **Add tests for key call chains** — the identified call chains represent well-traveled execution paths that benefit most from regression coverage

### Long-term Architecture
1. **Version and stabilize the public API** — document breaking-change policies for `KGRegistry`, `pack`, `query`
2. **Enforce layer boundaries** — add linting or CI checks to prevent unexpected cross-module dependencies as the codebase grows
3. **Monitor hot paths** — instrument the high fan-in functions identified here to catch performance regressions early

---

## 🧬 Inheritance Hierarchy

**6** INHERITS edges across **5** classes. Max depth: **1**.

| Class | Module | Depth | Parents | Children |
|-------|--------|-------|---------|----------|
| `CodeKGAdapter` | src/kg_rag/adapters/codekg_adapter.py | 1 | 1 | 0 |
| `DocKGAdapter` | src/kg_rag/adapters/dockg_adapter.py | 1 | 1 | 0 |
| `MetaKGAdapter` | src/kg_rag/adapters/metakg_adapter.py | 1 | 1 | 0 |
| `KGAdapter` | src/kg_rag/adapters/base.py | 0 | 1 | 3 |
| `KGKind` | src/kg_rag/primitives.py | 0 | 2 | 0 |

### Multiple Inheritance (1 classes)

- `KGKind` (src/kg_rag/primitives.py) inherits from `Enum`, `str`


---

## 📸 Snapshot History

Recent snapshots in reverse chronological order. Δ columns show change vs. the immediately preceding snapshot.

| # | Timestamp | Branch | Version | Nodes | Edges | Coverage | Δ Nodes | Δ Edges | Δ Coverage |
|---|-----------|--------|---------|-------|-------|----------|---------|---------|------------|
| 1 | 2026-03-12 22:50:19 | main | 0.1.0 | 1023 | 1239 | 78.8% | +0 | +0 | +0.0% |
| 2 | 2026-03-12 22:50:03 | main | 0.1.0 | 1023 | 1239 | 78.8% | +0 | +0 | +0.0% |
| 3 | 2026-03-12 22:47:53 | main | 0.1.0 | 1023 | 1239 | 78.8% | — | — | — |


---

## 📋 Appendix: Orphaned Code

Functions with zero callers (potential dead code):

✓ No orphaned functions detected.
---

## 📐 CodeRank — Global Structural Importance

Weighted PageRank over CALLS + IMPORTS + INHERITS edges (test paths excluded). Scores are normalized to sum to 1.0. This ranking seeds Phase 2 fan-in discovery and Phase 15 concern queries.

| Rank | Score | Kind | Name | Module |
|------|-------|------|------|--------|
| 1 | 0.002629 | method | `KGRegistry._row_to_entry` | src/kg_rag/registry.py |
| 2 | 0.001991 | method | `KGRegistry.list` | src/kg_rag/registry.py |
| 3 | 0.001914 | method | `CodeKGAdapter._load` | src/kg_rag/adapters/codekg_adapter.py |
| 4 | 0.001697 | method | `DocKGAdapter._load` | src/kg_rag/adapters/dockg_adapter.py |
| 5 | 0.001682 | method | `KGRegistry.close` | src/kg_rag/registry.py |
| 6 | 0.001682 | method | `KGRAG.close` | src/kg_rag/orchestrator.py |
| 7 | 0.001682 | method | `MetaKGAdapter.is_available` | src/kg_rag/adapters/metakg_adapter.py |
| 8 | 0.001479 | method | `KGRAG._get_adapter` | src/kg_rag/orchestrator.py |
| 9 | 0.001479 | method | `KGRAG._resolve_entries` | src/kg_rag/orchestrator.py |
| 10 | 0.001323 | method | `MetaKGAdapter._load` | src/kg_rag/adapters/metakg_adapter.py |
| 11 | 0.001296 | function | `_make_server` | src/kg_rag/mcp_server.py |
| 12 | 0.001218 | method | `KGKind.from_str` | src/kg_rag/primitives.py |
| 13 | 0.001119 | function | `_parse_kinds` | src/kg_rag/cli/cmd_query.py |
| 14 | 0.001103 | method | `KGRegistry.register` | src/kg_rag/registry.py |
| 15 | 0.001103 | method | `KGRegistry.get` | src/kg_rag/registry.py |
| 16 | 0.001097 | method | `KGRegistry.find_by_name` | src/kg_rag/registry.py |
| 17 | 0.001081 | function | `default_registry_path` | src/kg_rag/registry.py |
| 18 | 0.000909 | module | `config` | src/kg_rag/config.py |
| 19 | 0.000909 | function | `load_kgrag_config` | src/kg_rag/config.py |
| 20 | 0.000909 | module | `primitives` | src/kg_rag/primitives.py |

---

## 🔎 Concern-Based Hybrid Ranking

Top structurally-dominant nodes per architectural concern (0.60 × semantic + 0.25 × CodeRank + 0.15 × graph proximity).

### Error Handling Exception Recovery

| Rank | Score | Kind | Name | Module |
|------|-------|------|------|--------|
| 1 | 0.8719 | method | `KGRegistry._row_to_entry` | src/kg_rag/registry.py |
| 2 | 0.8118 | method | `CodeKGAdapter._load` | src/kg_rag/adapters/codekg_adapter.py |
| 3 | 0.7948 | method | `KGRegistry.close` | src/kg_rag/registry.py |
| 4 | 0.75 | method | `KGRegistry.__exit__` | src/kg_rag/registry.py |
| 5 | 0.7346 | method | `KGRegistry.__enter__` | src/kg_rag/registry.py |

### Configuration Loading Initialization Setup

| Rank | Score | Kind | Name | Module |
|------|-------|------|------|--------|
| 1 | 0.8279 | method | `CodeKGAdapter._load` | src/kg_rag/adapters/codekg_adapter.py |
| 2 | 0.8119 | method | `DocKGAdapter._load` | src/kg_rag/adapters/dockg_adapter.py |
| 3 | 0.7846 | method | `MetaKGAdapter._load` | src/kg_rag/adapters/metakg_adapter.py |
| 4 | 0.7499 | method | `DocKGAdapter.__init__` | src/kg_rag/adapters/dockg_adapter.py |
| 5 | 0.7432 | method | `MetaKGAdapter.__init__` | src/kg_rag/adapters/metakg_adapter.py |

### Data Persistence Storage Database

| Rank | Score | Kind | Name | Module |
|------|-------|------|------|--------|
| 1 | 0.7973 | method | `MetaKGAdapter.is_available` | src/kg_rag/adapters/metakg_adapter.py |
| 2 | 0.75 | method | `KGEntry.is_built` | src/kg_rag/primitives.py |
| 3 | 0.7377 | method | `KGAdapter.is_available` | src/kg_rag/adapters/base.py |
| 4 | 0.7358 | method | `DocKGAdapter.is_available` | src/kg_rag/adapters/dockg_adapter.py |
| 5 | 0.7325 | method | `CodeKGAdapter.is_available` | src/kg_rag/adapters/codekg_adapter.py |

### Query Search Retrieval Semantic

| Rank | Score | Kind | Name | Module |
|------|-------|------|------|--------|
| 1 | 0.75 | function | `query` | src/kg_rag/cli/cmd_query.py |
| 2 | 0.7139 | function | `_parse_kinds` | src/kg_rag/cli/cmd_query.py |
| 3 | 0.6899 | method | `KGRAG.query` | src/kg_rag/orchestrator.py |
| 4 | 0.6879 | method | `DocKGAdapter.query` | src/kg_rag/adapters/dockg_adapter.py |
| 5 | 0.6837 | function | `pack` | src/kg_rag/cli/cmd_query.py |

### Graph Traversal Node Edge

| Rank | Score | Kind | Name | Module |
|------|-------|------|------|--------|
| 1 | 0.75 | method | `CodeKGAdapter.stats` | src/kg_rag/adapters/codekg_adapter.py |
| 2 | 0.7343 | method | `DocKGAdapter.stats` | src/kg_rag/adapters/dockg_adapter.py |
| 3 | 0.7276 | function | `pack` | src/kg_rag/cli/cmd_query.py |
| 4 | 0.7267 | function | `query` | src/kg_rag/cli/cmd_query.py |
| 5 | 0.7229 | method | `KGAdapter.stats` | src/kg_rag/adapters/base.py |



---

*Report generated by CodeKG Thorough Analysis Tool — analysis completed in 4.1s*
