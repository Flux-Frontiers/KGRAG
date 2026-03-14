> **Analysis Report Metadata**  
> - **Generated:** 2026-03-14T17:46:51Z  
> - **Version:** code-kg 0.8.1  
> - **Commit:** fc7533c (main)  
> - **Platform:** Darwin arm64 | Python 3.12.13  
> - **Graph:** 1574 nodes · 1865 edges (130 meaningful)  
> - **Included directories:** src  
> - **Excluded directories:** none  
> - **Elapsed time:** 4s  

# kgrag Analysis

**Generated:** 2026-03-14 17:46:51 UTC

---

## 📊 Executive Summary

This report provides a comprehensive architectural analysis of the **kgrag** repository using CodeKG's knowledge graph. The analysis covers complexity hotspots, module coupling, key call chains, and code quality signals to guide refactoring and architecture decisions.

| Overall Quality | Grade | Score |
|----------------|-------|-------|
| 🟡 **Fair** | **C** | 62 / 100 |

---

## 📈 Baseline Metrics

| Metric | Value |
|--------|-------|
| **Total Nodes** | 1574 |
| **Total Edges** | 1865 |
| **Modules** | 22 (of 22 total) |
| **Functions** | 39 |
| **Classes** | 13 |
| **Methods** | 56 |

### Edge Distribution

| Relationship Type | Count |
|-------------------|-------|
| CALLS | 514 |
| CONTAINS | 108 |
| IMPORTS | 180 |
| ATTR_ACCESS | 570 |
| INHERITS | 6 |

---

## 🔥 Fan-In Ranking

Most-called functions are potential bottlenecks or core functionality. These functions are heavily depended upon across the codebase.

| # | Function | Module | Callers |
|---|----------|--------|---------|
| 1 | `get()` | src/kg_rag/registry.py | **22** |
| 2 | `list()` | src/kg_rag/registry.py | **9** |
| 3 | `stats()` | src/kg_rag/adapters/base.py | **8** |
| 4 | `stats()` | src/kg_rag/adapters/codekg_adapter.py | **8** |
| 5 | `stats()` | src/kg_rag/adapters/dockg_adapter.py | **8** |
| 6 | `stats()` | src/kg_rag/adapters/metakg_adapter.py | **8** |
| 7 | `stats()` | src/kg_rag/orchestrator.py | **8** |
| 8 | `KGRegistry()` | src/kg_rag/registry.py | **8** |
| 9 | `from_str()` | src/kg_rag/primitives.py | **7** |
| 10 | `pack()` | src/kg_rag/adapters/base.py | **6** |
| 11 | `query()` | src/kg_rag/adapters/base.py | **6** |
| 12 | `pack()` | src/kg_rag/adapters/codekg_adapter.py | **6** |
| 13 | `query()` | src/kg_rag/adapters/codekg_adapter.py | **6** |
| 14 | `pack()` | src/kg_rag/adapters/dockg_adapter.py | **6** |
| 15 | `query()` | src/kg_rag/adapters/dockg_adapter.py | **6** |


**Insight:** Functions with high fan-in are either core APIs or bottlenecks. Review these for:
- Thread safety and performance
- Clear documentation and contracts
- Potential for breaking changes

---

## 🔗 High Fan-Out Functions (Orchestrators)

Functions that call many others may indicate complex orchestration logic or poor separation of concerns.

| # | Function | Module | Calls | Type |
|---|----------|--------|-------|------|
| 1 | `init()` | src/kg_rag/cli/cmd_init.py | **30** | Coordinator |

---

## 📦 Module Architecture

Top modules by dependency coupling and cohesion (showing up to 10 with activity).
Cohesion = incoming / (incoming + outgoing + 1); higher = more internally focused.

| Module | Functions | Classes | Incoming | Outgoing | Cohesion |
|--------|-----------|---------|----------|----------|----------|
| `src/kg_rag/registry.py` | 1 | 1 | 6 | 1 | 0.12 |
| `src/kg_rag/app.py` | 13 | 0 | 0 | 2 | 0.67 |
| `src/kg_rag/orchestrator.py` | 0 | 1 | 4 | 4 | 0.44 |
| `src/kg_rag/primitives.py` | 0 | 7 | 14 | 0 | 0.00 |
| `src/kg_rag/adapters/codekg_adapter.py` | 0 | 1 | 1 | 2 | 0.50 |
| `src/kg_rag/adapters/base.py` | 0 | 1 | 5 | 1 | 0.14 |
| `src/kg_rag/adapters/dockg_adapter.py` | 0 | 1 | 1 | 2 | 0.50 |
| `src/kg_rag/adapters/metakg_adapter.py` | 0 | 1 | 1 | 2 | 0.50 |
| `src/kg_rag/cli/cmd_registry.py` | 7 | 0 | 1 | 4 | 0.67 |
| `src/kg_rag/mcp_server.py` | 5 | 0 | 0 | 3 | 0.75 |

---

## 🔗 Key Call Chains

Deepest call chains in the codebase.

**Chain 1** (depth: 4)

```
update → get → _row_to_entry → KGEntry
```

**Chain 2** (depth: 4)

```
iter → list → _row_to_entry → KGEntry
```

**Chain 3** (depth: 2)

```
stats → stats
```

**Chain 4** (depth: 3)

```
stats → stats → _load
```

**Chain 5** (depth: 3)

```
stats → stats → _load
```

---

## 🔓 Public API Surface

Identified public APIs (module-level functions with high usage).

| Function | Module | Fan-In | Type |
|----------|--------|--------|------|
| `KGRegistry()` | src/kg_rag/registry.py | 8 | class |
| `pack()` | src/kg_rag/cli/cmd_query.py | 6 | function |
| `KGEntry()` | src/kg_rag/primitives.py | 5 | class |
| `info()` | src/kg_rag/cli/cmd_registry.py | 4 | function |
| `KGRAG()` | src/kg_rag/orchestrator.py | 4 | class |
| `register()` | src/kg_rag/cli/cmd_registry.py | 3 | function |
| `CrossHit()` | src/kg_rag/primitives.py | 3 | class |
| `CrossSnippet()` | src/kg_rag/primitives.py | 3 | class |
| `KGKind()` | src/kg_rag/primitives.py | 2 | class |
| `make_adapter()` | src/kg_rag/adapters/__init__.py | 2 | function |
---

## 📝 Docstring Coverage

Docstring coverage directly determines semantic retrieval quality. Nodes without
docstrings embed only structured identifiers (`KIND/NAME/QUALNAME/MODULE`), where
keyword search is as effective as vector embeddings. The semantic model earns its
value only when a docstring is present.

| Kind | Documented | Total | Coverage |
|------|-----------|-------|----------|
| `function` | 28 | 39 | 🟡 71.8% |
| `method` | 39 | 56 | 🟡 69.6% |
| `class` | 13 | 13 | 🟢 100.0% |
| `module` | 22 | 22 | 🟢 100.0% |
| **total** | **102** | **130** | **🟡 78.5%** |

> **Recommendation:** 28 nodes lack docstrings. Prioritize documenting high-fan-in functions and public API surface first — these have the highest impact on query accuracy.

---

## 🏆 Structural Importance Ranking (SIR)

Weighted PageRank aggregated by module — reveals architectural spine. Cross-module edges boosted 1.5×; private symbols penalized 0.85×. Node-level detail: `codekg centrality --top 25`

| Rank | Score | Members | Module |
|------|-------|---------|--------|
| 1 | 0.223417 | 18 | `src/kg_rag/registry.py` |
| 2 | 0.216305 | 13 | `src/kg_rag/primitives.py` |
| 3 | 0.113681 | 13 | `src/kg_rag/orchestrator.py` |
| 4 | 0.106951 | 2 | `src/kg_rag/cli/group.py` |
| 5 | 0.060070 | 8 | `src/kg_rag/adapters/base.py` |
| 6 | 0.046476 | 8 | `src/kg_rag/adapters/metakg_adapter.py` |
| 7 | 0.046203 | 9 | `src/kg_rag/adapters/codekg_adapter.py` |
| 8 | 0.040629 | 8 | `src/kg_rag/adapters/dockg_adapter.py` |
| 9 | 0.040124 | 14 | `src/kg_rag/app.py` |
| 10 | 0.025572 | 8 | `src/kg_rag/cli/cmd_registry.py` |
| 11 | 0.023700 | 6 | `src/kg_rag/mcp_server.py` |
| 12 | 0.019794 | 4 | `src/kg_rag/cli/cmd_query.py` |
| 13 | 0.017587 | 4 | `src/kg_rag/config.py` |
| 14 | 0.008635 | 3 | `src/kg_rag/cli/cmd_init.py` |
| 15 | 0.008485 | 2 | `src/kg_rag/cli/cmd_analyze.py` |



---

## ⚠️  Code Quality Issues

- ⚠️  Moderate docstring coverage (78.5%) — semantic retrieval quality is degraded for undocumented nodes; BM25 is as effective as embeddings without docstrings
- ⚠️  1 orphaned functions found (`main`) — consider archiving or documenting
- ⚠️  1 functions with high fan-out — potential orchestrators or god objects

---

## ✅ Architectural Strengths

- ✓ Well-structured with 15 core functions identified
- ✓ Multiple inheritance used in 1 class(es) without diamond patterns

---

## 💡 Recommendations

### Immediate Actions
1. **Improve docstring coverage** — 28 nodes lack docstrings; prioritize high-fan-in functions and public APIs first for maximum semantic retrieval gain
2. **Remove or archive orphaned functions** — `main` have zero callers and add maintenance burden
3. **Refactor high fan-out orchestrators** — `init` calls 30 functions; consider splitting into smaller, focused coordinators

### Medium-term Refactoring
1. **Harden high fan-in functions** — `get`, `list`, `stats` are widely depended upon; review for thread safety, clear contracts, and stable interfaces
2. **Reduce module coupling** — consider splitting tightly coupled modules or introducing interface boundaries
3. **Add tests for key call chains** — the identified call chains represent well-traveled execution paths that benefit most from regression coverage

### Long-term Architecture
1. **Version and stabilize the public API** — document breaking-change policies for `KGRegistry`, `pack`, `KGEntry`
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
| 1 | 2026-03-14 05:28:35 | main | 0.2.0 | 1526 | 1793 | 77.8% | +0 | +0 | +0.0% |
| 2 | 2026-03-14 05:27:56 | main | 0.2.0 | 1526 | 1793 | 77.8% | +0 | +0 | +0.0% |
| 3 | 2026-03-14 05:22:41 | main | 0.2.0 | 1526 | 1793 | 77.8% | +0 | +0 | +0.0% |
| 4 | 2026-03-14 05:03:46 | main | 0.2.0 | 1526 | 1793 | 77.8% | +0 | +0 | +0.0% |
| 5 | 2026-03-14 04:53:15 | main | 0.2.0 | 1526 | 1793 | 77.8% | +393 | +447 | -2.0% |
| 6 | 2026-03-13 03:56:03 | main | 0.2.0 | 1133 | 1346 | 79.8% | +108 | +103 | +0.8% |
| 7 | 2026-03-12 23:11:06 | main | 0.1.0 | 1025 | 1243 | 79.0% | +2 | +4 | +0.2% |
| 8 | 2026-03-12 22:50:19 | main | 0.1.0 | 1023 | 1239 | 78.8% | +0 | +0 | +0.0% |
| 9 | 2026-03-12 22:50:03 | main | 0.1.0 | 1023 | 1239 | 78.8% | +0 | +0 | +0.0% |
| 10 | 2026-03-12 22:47:53 | main | 0.1.0 | 1023 | 1239 | 78.8% | — | — | — |


---

## 📋 Appendix: Orphaned Code

Functions with zero callers (potential dead code):

| Function | Module | Lines |
|----------|--------|-------|
| `main()` | src/kg_rag/app.py | 30 |
---

## 📐 CodeRank — Global Structural Importance

Weighted PageRank over CALLS + IMPORTS + INHERITS edges (test paths excluded). Scores are normalized to sum to 1.0. This ranking seeds Phase 2 fan-in discovery and Phase 15 concern queries.

| Rank | Score | Kind | Name | Module |
|------|-------|------|------|--------|
| 1 | 0.001727 | method | `KGRegistry._row_to_entry` | src/kg_rag/registry.py |
| 2 | 0.001462 | method | `CodeKGAdapter._load` | src/kg_rag/adapters/codekg_adapter.py |
| 3 | 0.001308 | method | `KGRegistry.list` | src/kg_rag/registry.py |
| 4 | 0.001226 | method | `KGRAG._get_adapter` | src/kg_rag/orchestrator.py |
| 5 | 0.001147 | function | `_load_kgrag` | src/kg_rag/app.py |
| 6 | 0.001142 | method | `DocKGAdapter._load` | src/kg_rag/adapters/dockg_adapter.py |
| 7 | 0.001105 | method | `KGRegistry.close` | src/kg_rag/registry.py |
| 8 | 0.001105 | method | `KGRAG.close` | src/kg_rag/orchestrator.py |
| 9 | 0.001105 | method | `MetaKGAdapter.is_available` | src/kg_rag/adapters/metakg_adapter.py |
| 10 | 0.000972 | method | `KGRAG._resolve_entries` | src/kg_rag/orchestrator.py |
| 11 | 0.000869 | method | `MetaKGAdapter._load` | src/kg_rag/adapters/metakg_adapter.py |
| 12 | 0.000851 | function | `_make_server` | src/kg_rag/mcp_server.py |
| 13 | 0.000837 | function | `_load_toml` | src/kg_rag/config.py |
| 14 | 0.000801 | method | `KGKind.from_str` | src/kg_rag/primitives.py |
| 15 | 0.000735 | function | `_parse_kinds` | src/kg_rag/cli/cmd_query.py |
| 16 | 0.000724 | method | `KGRegistry.register` | src/kg_rag/registry.py |
| 17 | 0.000724 | method | `KGRegistry.get` | src/kg_rag/registry.py |
| 18 | 0.000721 | method | `KGRegistry.find_by_name` | src/kg_rag/registry.py |
| 19 | 0.000710 | function | `default_registry_path` | src/kg_rag/registry.py |
| 20 | 0.000665 | function | `_init_state` | src/kg_rag/app.py |

---

## 🔎 Concern-Based Hybrid Ranking

Top structurally-dominant nodes per architectural concern (0.60 × semantic + 0.25 × CodeRank + 0.15 × graph proximity).

### Error Handling Exception Recovery

| Rank | Score | Kind | Name | Module |
|------|-------|------|------|--------|
| 1 | 0.8352 | method | `KGRegistry._row_to_entry` | src/kg_rag/registry.py |
| 2 | 0.8115 | method | `CodeKGAdapter._load` | src/kg_rag/adapters/codekg_adapter.py |
| 3 | 0.7783 | method | `KGRegistry.close` | src/kg_rag/registry.py |
| 4 | 0.75 | method | `KGRegistry.__exit__` | src/kg_rag/registry.py |
| 5 | 0.731 | method | `KGRegistry.__enter__` | src/kg_rag/registry.py |

### Configuration Loading Initialization Setup

| Rank | Score | Kind | Name | Module |
|------|-------|------|------|--------|
| 1 | 0.8278 | method | `CodeKGAdapter._load` | src/kg_rag/adapters/codekg_adapter.py |
| 2 | 0.799 | method | `DocKGAdapter._load` | src/kg_rag/adapters/dockg_adapter.py |
| 3 | 0.7763 | method | `MetaKGAdapter._load` | src/kg_rag/adapters/metakg_adapter.py |
| 4 | 0.7526 | function | `_init_state` | src/kg_rag/app.py |
| 5 | 0.7485 | method | `DocKGAdapter.__init__` | src/kg_rag/adapters/dockg_adapter.py |

### Data Persistence Storage Database

| Rank | Score | Kind | Name | Module |
|------|-------|------|------|--------|
| 1 | 0.7818 | method | `MetaKGAdapter.is_available` | src/kg_rag/adapters/metakg_adapter.py |
| 2 | 0.75 | method | `KGEntry.is_built` | src/kg_rag/primitives.py |
| 3 | 0.739 | method | `KGAdapter.is_available` | src/kg_rag/adapters/base.py |
| 4 | 0.7367 | method | `DocKGAdapter.is_available` | src/kg_rag/adapters/dockg_adapter.py |
| 5 | 0.7331 | method | `CodeKGAdapter.is_available` | src/kg_rag/adapters/codekg_adapter.py |

### Query Search Retrieval Semantic

| Rank | Score | Kind | Name | Module |
|------|-------|------|------|--------|
| 1 | 0.75 | function | `query` | src/kg_rag/cli/cmd_query.py |
| 2 | 0.7134 | function | `_tab_query` | src/kg_rag/app.py |
| 3 | 0.7122 | function | `_parse_kinds` | src/kg_rag/cli/cmd_query.py |
| 4 | 0.69 | method | `KGRAG.query` | src/kg_rag/orchestrator.py |
| 5 | 0.6879 | method | `DocKGAdapter.query` | src/kg_rag/adapters/dockg_adapter.py |

### Graph Traversal Node Edge

| Rank | Score | Kind | Name | Module |
|------|-------|------|------|--------|
| 1 | 0.75 | method | `CodeKGAdapter.stats` | src/kg_rag/adapters/codekg_adapter.py |
| 2 | 0.733 | method | `DocKGAdapter.stats` | src/kg_rag/adapters/dockg_adapter.py |
| 3 | 0.7285 | function | `_tab_snippets` | src/kg_rag/app.py |
| 4 | 0.7276 | function | `pack` | src/kg_rag/cli/cmd_query.py |
| 5 | 0.7261 | function | `query` | src/kg_rag/cli/cmd_query.py |



---

*Report generated by CodeKG Thorough Analysis Tool — analysis completed in 4.8s*
