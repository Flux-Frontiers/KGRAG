> **Analysis Report Metadata**  
> - **Generated:** 2026-03-15T16:46:11Z  
> - **Version:** code-kg 0.9.0  
> - **Commit:** 9091d4f (claude/add-corpus-abstraction-KXiKg)  
> - **Platform:** Linux x86_64 | Python 3.12.3  
> - **Graph:** 2071 nodes · 2632 edges (169 meaningful)  
> - **Included directories:** src  
> - **Excluded directories:** none  
> - **Elapsed time:** 8s  

# KGRAG Analysis

**Generated:** 2026-03-15 16:46:11 UTC

---

## Executive Summary

This report provides a comprehensive architectural analysis of the **KGRAG** repository using CodeKG's knowledge graph. The analysis covers complexity hotspots, module coupling, key call chains, and code quality signals to guide refactoring and architecture decisions.

| Overall Quality | Grade | Score |
|----------------|-------|-------|
| [B] **Good** | **B** | 82 / 100 |

---

## Baseline Metrics

| Metric | Value |
|--------|-------|
| **Total Nodes** | 2071 |
| **Total Edges** | 2632 |
| **Modules** | 24 (of 24 total) |
| **Functions** | 48 |
| **Classes** | 16 |
| **Methods** | 81 |

### Edge Distribution

| Relationship Type | Count |
|-------------------|-------|
| CALLS | 714 |
| CONTAINS | 145 |
| IMPORTS | 211 |
| ATTR_ACCESS | 770 |
| INHERITS | 5 |

---

## Fan-In Ranking

Most-called functions are potential bottlenecks or core functionality. These functions are heavily depended upon across the codebase.

| # | Function | Module | Callers |
|---|----------|--------|---------|
| 1 | `get()` | src/kg_rag/corpus_registry.py | **33** |
| 2 | `get()` | src/kg_rag/registry.py | **31** |
| 3 | `stats()` | src/kg_rag/adapters/metakg_adapter.py | **12** |
| 4 | `list()` | src/kg_rag/corpus_registry.py | **11** |
| 5 | `list()` | src/kg_rag/registry.py | **11** |
| 6 | `stats()` | src/kg_rag/adapters/base.py | **11** |
| 7 | `stats()` | src/kg_rag/adapters/codekg_adapter.py | **11** |
| 8 | `stats()` | src/kg_rag/adapters/dockg_adapter.py | **11** |
| 9 | `_get_adapter()` | src/kg_rag/orchestrator.py | **7** |
| 10 | `from_str()` | src/kg_rag/primitives.py | **7** |
| 11 | `pack()` | src/kg_rag/adapters/base.py | **7** |
| 12 | `query()` | src/kg_rag/adapters/base.py | **7** |
| 13 | `pack()` | src/kg_rag/adapters/codekg_adapter.py | **7** |
| 14 | `query()` | src/kg_rag/adapters/codekg_adapter.py | **7** |
| 15 | `pack()` | src/kg_rag/adapters/dockg_adapter.py | **7** |


**Insight:** Functions with high fan-in are either core APIs or bottlenecks. Review these for:
- Thread safety and performance
- Clear documentation and contracts
- Potential for breaking changes

---

## High Fan-Out Functions (Orchestrators)

Functions that call many others may indicate complex orchestration logic or poor separation of concerns.

| # | Function | Module | Calls | Type |
|---|----------|--------|-------|------|
| 1 | `init()` | src/kg_rag/cli/cmd_init.py | **30** | Coordinator |

---

## Module Architecture

Top modules by dependency coupling and cohesion (showing up to 10 with activity).
Cohesion = incoming / (incoming + outgoing + 1); higher = more internally focused.

| Module | Functions | Classes | Incoming | Outgoing | Cohesion |
|--------|-----------|---------|----------|----------|----------|
| `src/kg_rag/corpus_registry.py` | 0 | 1 | 4 | 2 | 0.29 |
| `src/kg_rag/orchestrator.py` | 0 | 1 | 4 | 5 | 0.50 |
| `src/kg_rag/registry.py` | 1 | 1 | 8 | 1 | 0.10 |
| `src/kg_rag/primitives.py` | 0 | 9 | 17 | 0 | 0.00 |
| `src/kg_rag/app.py` | 13 | 0 | 0 | 2 | 0.67 |
| `src/kg_rag/cli/cmd_corpus.py` | 9 | 0 | 1 | 4 | 0.67 |
| `src/kg_rag/adapters/codekg_adapter.py` | 0 | 1 | 1 | 2 | 0.50 |
| `src/kg_rag/adapters/dockg_adapter.py` | 0 | 1 | 1 | 2 | 0.50 |
| `src/kg_rag/adapters/metakg_adapter.py` | 0 | 1 | 1 | 2 | 0.50 |
| `src/kg_rag/adapters/base.py` | 0 | 1 | 5 | 1 | 0.14 |

---

## Key Call Chains

Deepest call chains in the codebase.

**Chain 1** (depth: 4)

```
add_kg → get → _row_to_entry → CorpusEntry
```

**Chain 2** (depth: 4)

```
update → get → _row_to_entry → KGEntry
```

**Chain 3** (depth: 4)

```
stats → list → _row_to_entry → CorpusEntry
```

**Chain 4** (depth: 4)

```
stats → list → _row_to_entry → KGEntry
```

---

## Public API Surface

Identified public APIs (module-level functions with high usage).

| Function | Module | Fan-In | Type |
|----------|--------|--------|------|
| `KGRegistry()` | src/kg_rag/registry.py | 12 | class |
| `pack()` | src/kg_rag/cli/cmd_query.py | 7 | function |
| `CorpusRegistry()` | src/kg_rag/corpus_registry.py | 7 | class |
| `KGEntry()` | src/kg_rag/primitives.py | 5 | class |
| `KGRAG()` | src/kg_rag/orchestrator.py | 5 | class |
| `info()` | src/kg_rag/cli/cmd_registry.py | 4 | function |
| `register()` | src/kg_rag/cli/cmd_registry.py | 3 | function |
| `CrossSnippet()` | src/kg_rag/primitives.py | 3 | class |
| `CrossHit()` | src/kg_rag/primitives.py | 3 | class |
| `CorpusEntry()` | src/kg_rag/primitives.py | 3 | class |
---

## Docstring Coverage

Docstring coverage directly determines semantic retrieval quality. Nodes without
docstrings embed only structured identifiers (`KIND/NAME/QUALNAME/MODULE`), where
keyword search is as effective as vector embeddings. The semantic model earns its
value only when a docstring is present.

| Kind | Documented | Total | Coverage |
|------|-----------|-------|----------|
| `function` | 37 | 48 | [WARN] 77.1% |
| `method` | 60 | 81 | [WARN] 74.1% |
| `class` | 16 | 16 | [OK] 100.0% |
| `module` | 24 | 24 | [OK] 100.0% |
| **total** | **137** | **169** | **[OK] 81.1%** |

---

## Structural Importance Ranking (SIR)

Weighted PageRank aggregated by module — reveals architectural spine. Cross-module edges boosted 1.5×; private symbols penalized 0.85×. Node-level detail: `codekg centrality --top 25`

| Rank | Score | Members | Module |
|------|-------|---------|--------|
| 1 | 0.242769 | 16 | `src/kg_rag/primitives.py` |
| 2 | 0.155892 | 18 | `src/kg_rag/registry.py` |
| 3 | 0.154099 | 19 | `src/kg_rag/corpus_registry.py` |
| 4 | 0.094001 | 18 | `src/kg_rag/orchestrator.py` |
| 5 | 0.090297 | 2 | `src/kg_rag/cli/group.py` |
| 6 | 0.043598 | 8 | `src/kg_rag/adapters/base.py` |
| 7 | 0.034790 | 9 | `src/kg_rag/adapters/metakg_adapter.py` |
| 8 | 0.034585 | 9 | `src/kg_rag/adapters/dockg_adapter.py` |
| 9 | 0.034043 | 9 | `src/kg_rag/adapters/codekg_adapter.py` |
| 10 | 0.029044 | 14 | `src/kg_rag/app.py` |
| 11 | 0.021458 | 10 | `src/kg_rag/cli/cmd_corpus.py` |
| 12 | 0.018139 | 8 | `src/kg_rag/cli/cmd_registry.py` |
| 13 | 0.017131 | 6 | `src/kg_rag/mcp_server.py` |
| 14 | 0.014955 | 4 | `src/kg_rag/cli/cmd_query.py` |
| 15 | 0.011860 | 4 | `src/kg_rag/config.py` |



---

## Code Quality Issues

- [WARN] 1 orphaned functions found (`main`) -- consider archiving or documenting
- [WARN] 1 functions with high fan-out -- potential orchestrators or god objects

---

## Architectural Strengths

- Well-structured with 15 core functions identified
- Good docstring coverage: 81.1% of functions/methods/classes/modules documented

---

## Recommendations

### Immediate Actions
1. **Remove or archive orphaned functions** — `main` have zero callers and add maintenance burden
2. **Refactor high fan-out orchestrators** — `init` calls 30 functions; consider splitting into smaller, focused coordinators

### Medium-term Refactoring
1. **Harden high fan-in functions** — `get`, `get`, `stats` are widely depended upon; review for thread safety, clear contracts, and stable interfaces
2. **Reduce module coupling** — consider splitting tightly coupled modules or introducing interface boundaries
3. **Add tests for key call chains** — the identified call chains represent well-traveled execution paths that benefit most from regression coverage

### Long-term Architecture
1. **Version and stabilize the public API** — document breaking-change policies for `KGRegistry`, `pack`, `CorpusRegistry`
2. **Enforce layer boundaries** — add linting or CI checks to prevent unexpected cross-module dependencies as the codebase grows
3. **Monitor hot paths** — instrument the high fan-in functions identified here to catch performance regressions early

---

## Inheritance Hierarchy

**5** INHERITS edges across **5** classes. Max depth: **1**.

| Class | Module | Depth | Parents | Children |
|-------|--------|-------|---------|----------|
| `CodeKGAdapter` | src/kg_rag/adapters/codekg_adapter.py | 1 | 1 | 0 |
| `DocKGAdapter` | src/kg_rag/adapters/dockg_adapter.py | 1 | 1 | 0 |
| `MetaKGAdapter` | src/kg_rag/adapters/metakg_adapter.py | 1 | 1 | 0 |
| `KGAdapter` | src/kg_rag/adapters/base.py | 0 | 1 | 3 |
| `KGKind` | src/kg_rag/primitives.py | 0 | 1 | 0 |


---

## Snapshot History

Recent snapshots in reverse chronological order. Δ columns show change vs. the immediately preceding snapshot.

| # | Timestamp | Branch | Version | Nodes | Edges | Coverage | Δ Nodes | Δ Edges | Δ Coverage |
|---|-----------|--------|---------|-------|-------|----------|---------|---------|------------|
| 1 | 2026-03-15 02:59:34 | main | 0.3.0 | 1627 | 1960 | 78.8% | +2 | +2 | +0.0% |
| 2 | 2026-03-15 02:50:21 | main | 0.2.0 | 1625 | 1958 | 78.8% | +51 | +93 | +0.3% |
| 3 | 2026-03-14 23:56:47 | main | 0.2.0 | 1574 | 1865 | 78.5% | +48 | +72 | +0.7% |
| 4 | 2026-03-14 05:28:35 | main | 0.2.0 | 1526 | 1793 | 77.8% | +0 | +0 | +0.0% |
| 5 | 2026-03-14 05:27:56 | main | 0.2.0 | 1526 | 1793 | 77.8% | +0 | +0 | +0.0% |
| 6 | 2026-03-14 05:22:41 | main | 0.2.0 | 1526 | 1793 | 77.8% | +0 | +0 | +0.0% |
| 7 | 2026-03-14 05:03:46 | main | 0.2.0 | 1526 | 1793 | 77.8% | +0 | +0 | +0.0% |
| 8 | 2026-03-14 04:53:15 | main | 0.2.0 | 1526 | 1793 | 77.8% | +393 | +447 | -2.0% |
| 9 | 2026-03-13 03:56:03 | main | 0.2.0 | 1133 | 1346 | 79.8% | +108 | +103 | +0.8% |
| 10 | 2026-03-12 23:11:06 | main | 0.1.0 | 1025 | 1243 | 79.0% | +2 | +4 | +0.2% |


---

## Appendix: Orphaned Code

Functions with zero callers (potential dead code):

| Function | Module | Lines |
|----------|--------|-------|
| `main()` | src/kg_rag/app.py | 30 |
---

## CodeRank -- Global Structural Importance

Weighted PageRank over CALLS + IMPORTS + INHERITS edges (test paths excluded). Scores are normalized to sum to 1.0. This ranking seeds Phase 2 fan-in discovery and Phase 15 concern queries.

| Rank | Score | Kind | Name | Module |
|------|-------|------|------|--------|
| 1 | 0.001557 | method | `CorpusRegistry._row_to_entry` | src/kg_rag/corpus_registry.py |
| 2 | 0.001310 | method | `KGRegistry._row_to_entry` | src/kg_rag/registry.py |
| 3 | 0.001214 | method | `KGRAG._get_adapter` | src/kg_rag/orchestrator.py |
| 4 | 0.001109 | method | `CodeKGAdapter._load` | src/kg_rag/adapters/codekg_adapter.py |
| 5 | 0.000999 | method | `CorpusRegistry.get` | src/kg_rag/corpus_registry.py |
| 6 | 0.000992 | method | `CorpusRegistry.list` | src/kg_rag/corpus_registry.py |
| 7 | 0.000992 | method | `KGRegistry.list` | src/kg_rag/registry.py |
| 8 | 0.000943 | method | `DocKGAdapter._load` | src/kg_rag/adapters/dockg_adapter.py |
| 9 | 0.000870 | function | `_load_kgrag` | src/kg_rag/app.py |
| 10 | 0.000838 | method | `CorpusRegistry.close` | src/kg_rag/corpus_registry.py |
| 11 | 0.000838 | method | `KGRegistry.close` | src/kg_rag/registry.py |
| 12 | 0.000838 | method | `KGRAG.close` | src/kg_rag/orchestrator.py |
| 13 | 0.000816 | method | `MetaKGAdapter._load` | src/kg_rag/adapters/metakg_adapter.py |
| 14 | 0.000806 | method | `CorpusRegistry.create` | src/kg_rag/corpus_registry.py |
| 15 | 0.000737 | method | `KGRAG._resolve_entries` | src/kg_rag/orchestrator.py |
| 16 | 0.000737 | method | `KGRAG._resolve_corpus_entries` | src/kg_rag/orchestrator.py |
| 17 | 0.000646 | function | `_make_server` | src/kg_rag/mcp_server.py |
| 18 | 0.000639 | function | `_resolve_kg_id` | src/kg_rag/cli/cmd_corpus.py |
| 19 | 0.000635 | function | `_load_toml` | src/kg_rag/config.py |
| 20 | 0.000609 | method | `MetaKGAdapter.is_available` | src/kg_rag/adapters/metakg_adapter.py |

---

## Concern-Based Hybrid Ranking

Top structurally-dominant nodes per architectural concern (0.60 × semantic + 0.25 × CodeRank + 0.15 × graph proximity).

### Configuration Loading Initialization Setup

| Rank | Score | Kind | Name | Module |
|------|-------|------|------|--------|
| 1 | 0.816 | method | `CodeKGAdapter._load` | src/kg_rag/adapters/codekg_adapter.py |
| 2 | 0.8 | method | `DocKGAdapter._load` | src/kg_rag/adapters/dockg_adapter.py |
| 3 | 0.7897 | method | `MetaKGAdapter._load` | src/kg_rag/adapters/metakg_adapter.py |
| 4 | 0.7516 | function | `_init_state` | src/kg_rag/app.py |
| 5 | 0.7485 | method | `DocKGAdapter.__init__` | src/kg_rag/adapters/dockg_adapter.py |

### Data Persistence Storage Database

| Rank | Score | Kind | Name | Module |
|------|-------|------|------|--------|
| 1 | 0.8291 | method | `MetaKGAdapter.is_available` | src/kg_rag/adapters/metakg_adapter.py |
| 2 | 0.75 | method | `KGEntry.is_built` | src/kg_rag/primitives.py |
| 3 | 0.7382 | method | `KGAdapter.is_available` | src/kg_rag/adapters/base.py |
| 4 | 0.7359 | method | `DocKGAdapter.is_available` | src/kg_rag/adapters/dockg_adapter.py |
| 5 | 0.7342 | method | `CorpusRegistry.db_path` | src/kg_rag/corpus_registry.py |

### Query Search Retrieval Semantic

| Rank | Score | Kind | Name | Module |
|------|-------|------|------|--------|
| 1 | 0.75 | function | `query` | src/kg_rag/cli/cmd_query.py |
| 2 | 0.7125 | function | `_tab_query` | src/kg_rag/app.py |
| 3 | 0.7103 | function | `_parse_kinds` | src/kg_rag/cli/cmd_query.py |
| 4 | 0.7055 | function | `corpus_query` | src/kg_rag/cli/cmd_corpus.py |
| 5 | 0.6899 | method | `KGRAG.query` | src/kg_rag/orchestrator.py |

### Graph Traversal Node Edge

| Rank | Score | Kind | Name | Module |
|------|-------|------|------|--------|
| 1 | 0.7565 | method | `MetaKGAdapter.stats` | src/kg_rag/adapters/metakg_adapter.py |
| 2 | 0.7433 | method | `CodeKGAdapter.stats` | src/kg_rag/adapters/codekg_adapter.py |
| 3 | 0.7265 | method | `DocKGAdapter.stats` | src/kg_rag/adapters/dockg_adapter.py |
| 4 | 0.7212 | function | `_tab_snippets` | src/kg_rag/app.py |
| 5 | 0.7212 | function | `pack` | src/kg_rag/cli/cmd_query.py |



---

*Report generated by CodeKG Thorough Analysis Tool — analysis completed in 8.3s*
