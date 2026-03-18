> **Analysis Report Metadata**
> - **Generated:** 2026-03-18T03:51:48Z
> - **Version:** code-kg 0.9.0
> - **Commit:** 6a49352 (main)
> - **Platform:** Darwin arm64 | Python 3.12.13
> - **Graph:** 3723 nodes · 4929 edges (299 meaningful)
> - **Included directories:** src
> - **Excluded directories:** none
> - **Elapsed time:** 3s

# kgrag Analysis

**Generated:** 2026-03-18 03:51:48 UTC

---

## Executive Summary

This report provides a comprehensive architectural analysis of the **kgrag** repository using CodeKG's knowledge graph. The analysis covers complexity hotspots, module coupling, key call chains, and code quality signals to guide refactoring and architecture decisions.

| Overall Quality | Grade | Score |
|----------------|-------|-------|
| [C] **Fair** | **C** | 72 / 100 |

---

## Baseline Metrics

| Metric | Value |
|--------|-------|
| **Total Nodes** | 3723 |
| **Total Edges** | 4929 |
| **Modules** | 36 (of 36 total) |
| **Functions** | 63 |
| **Classes** | 34 |
| **Methods** | 166 |

### Edge Distribution

| Relationship Type | Count |
|-------------------|-------|
| CALLS | 1311 |
| CONTAINS | 263 |
| IMPORTS | 337 |
| ATTR_ACCESS | 1357 |
| INHERITS | 19 |

---

## Fan-In Ranking

Most-called functions are potential bottlenecks or core functionality. These functions are heavily depended upon across the codebase.

| # | Function | Module | Callers |
|---|----------|--------|---------|
| 1 | `get()` | src/kg_rag/corpus_registry.py | **51** |
| 2 | `get()` | src/kg_rag/person_registry.py | **51** |
| 3 | `get()` | src/kg_rag/registry.py | **49** |
| 4 | `stats()` | src/kg_rag/adapters/base.py | **16** |
| 5 | `stats()` | src/kg_rag/adapters/_stub_adapter.py | **16** |
| 6 | `stats()` | src/kg_rag/adapters/metakg_adapter.py | **16** |
| 7 | `list()` | src/kg_rag/corpus_registry.py | **15** |
| 8 | `list()` | src/kg_rag/person_registry.py | **15** |
| 9 | `list()` | src/kg_rag/registry.py | **15** |
| 10 | `__init__()` | src/kg_rag/adapters/_stub_adapter.py | **15** |
| 11 | `__init__()` | src/kg_rag/adapters/base.py | **15** |
| 12 | `__init__()` | src/kg_rag/adapters/codekg_adapter.py | **15** |
| 13 | `stats()` | src/kg_rag/adapters/codekg_adapter.py | **15** |
| 14 | `__init__()` | src/kg_rag/adapters/diary_adapter.py | **15** |
| 15 | `is_available()` | src/kg_rag/adapters/_stub_adapter.py | **11** |


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
| `src/kg_rag/viz_qt.py` | 4 | 4 | 0 | 1 | 0.50 |
| `src/kg_rag/orchestrator.py` | 0 | 1 | 4 | 6 | 0.55 |
| `src/kg_rag/cli/cmd_corpus.py` | 18 | 0 | 1 | 5 | 0.71 |
| `src/kg_rag/corpus_registry.py` | 0 | 1 | 4 | 2 | 0.29 |
| `src/kg_rag/person_registry.py` | 0 | 1 | 4 | 2 | 0.29 |
| `src/kg_rag/primitives.py` | 0 | 11 | 26 | 0 | 0.00 |
| `src/kg_rag/registry.py` | 1 | 1 | 9 | 1 | 0.09 |
| `src/kg_rag/adapters/base.py` | 1 | 1 | 7 | 2 | 0.20 |
| `src/kg_rag/app.py` | 13 | 0 | 0 | 2 | 0.67 |
| `src/kg_rag/adapters/_stub_adapter.py` | 0 | 1 | 7 | 2 | 0.20 |

---

## Key Call Chains

Deepest call chains in the codebase.

**Chain 1** (depth: 4)

```
add_kg → get → _row_to_entry → CorpusEntry
```

**Chain 2** (depth: 4)

```
add_kg → get → _row_to_entry → PersonCorpusEntry
```

**Chain 3** (depth: 4)

```
update → get → _row_to_entry → KGEntry
```

**Chain 4** (depth: 4)

```
analyze → stats → _load → _try_load
```

---

## Public API Surface

Identified public APIs (module-level functions with high usage).

| Function | Module | Fan-In | Type |
|----------|--------|--------|------|
| `KGRegistry()` | src/kg_rag/registry.py | 16 | class |
| `pack()` | src/kg_rag/cli/cmd_query.py | 10 | function |
| `PersonCorpusRegistry()` | src/kg_rag/person_registry.py | 8 | class |
| `CorpusRegistry()` | src/kg_rag/corpus_registry.py | 7 | class |
| `KGRAG()` | src/kg_rag/orchestrator.py | 7 | class |
| `info()` | src/kg_rag/cli/cmd_registry.py | 5 | function |
| `CrossHit()` | src/kg_rag/primitives.py | 5 | class |
| `CrossSnippet()` | src/kg_rag/primitives.py | 5 | class |
| `KGEntry()` | src/kg_rag/primitives.py | 5 | class |
| `register()` | src/kg_rag/cli/cmd_registry.py | 3 | function |
---

## Docstring Coverage

Docstring coverage directly determines semantic retrieval quality. Nodes without
docstrings embed only structured identifiers (`KIND/NAME/QUALNAME/MODULE`), where
keyword search is as effective as vector embeddings. The semantic model earns its
value only when a docstring is present.

| Kind | Documented | Total | Coverage |
|------|-----------|-------|----------|
| `function` | 50 | 63 | [WARN] 79.4% |
| `method` | 114 | 166 | [WARN] 68.7% |
| `class` | 34 | 34 | [OK] 100.0% |
| `module` | 36 | 36 | [OK] 100.0% |
| **total** | **234** | **299** | **[WARN] 78.3%** |

> **Recommendation:** 65 nodes lack docstrings. Prioritize documenting high-fan-in functions and public API surface first — these have the highest impact on query accuracy.

---

## Structural Importance Ranking (SIR)

Weighted PageRank aggregated by module — reveals architectural spine. Cross-module edges boosted 1.5×; private symbols penalized 0.85×. Node-level detail: `codekg centrality --top 25`

| Rank | Score | Members | Module |
|------|-------|---------|--------|
| 1 | 0.211135 | 19 | `src/kg_rag/primitives.py` |
| 2 | 0.099107 | 18 | `src/kg_rag/registry.py` |
| 3 | 0.092591 | 19 | `src/kg_rag/person_registry.py` |
| 4 | 0.092393 | 19 | `src/kg_rag/corpus_registry.py` |
| 5 | 0.080374 | 33 | `src/kg_rag/viz_qt.py` |
| 6 | 0.067360 | 2 | `src/kg_rag/cli/group.py` |
| 7 | 0.060396 | 23 | `src/kg_rag/orchestrator.py` |
| 8 | 0.052905 | 16 | `src/kg_rag/adapters/base.py` |
| 9 | 0.039234 | 11 | `src/kg_rag/adapters/_stub_adapter.py` |
| 10 | 0.025762 | 11 | `src/kg_rag/adapters/diary_adapter.py` |
| 11 | 0.023388 | 10 | `src/kg_rag/adapters/metakg_adapter.py` |
| 12 | 0.023147 | 10 | `src/kg_rag/adapters/dockg_adapter.py` |
| 13 | 0.022911 | 10 | `src/kg_rag/adapters/codekg_adapter.py` |
| 14 | 0.021687 | 19 | `src/kg_rag/cli/cmd_corpus.py` |
| 15 | 0.015834 | 14 | `src/kg_rag/app.py` |



---

## Code Quality Issues

- [WARN] Moderate docstring coverage (78.3%) — semantic retrieval quality is degraded for undocumented nodes; BM25 is as effective as embeddings without docstrings
- [WARN] 1 functions with high fan-out -- potential orchestrators or god objects

---

## Architectural Strengths

- Well-structured with 15 core functions identified
- No obvious dead code detected

---

## Recommendations

### Immediate Actions
1. **Improve docstring coverage** — 65 nodes lack docstrings; prioritize high-fan-in functions and public APIs first for maximum semantic retrieval gain
2. **Refactor high fan-out orchestrators** — `init` calls 30 functions; consider splitting into smaller, focused coordinators

### Medium-term Refactoring
1. **Harden high fan-in functions** — `get`, `get`, `get` are widely depended upon; review for thread safety, clear contracts, and stable interfaces
2. **Reduce module coupling** — consider splitting tightly coupled modules or introducing interface boundaries
3. **Add tests for key call chains** — the identified call chains represent well-traveled execution paths that benefit most from regression coverage

### Long-term Architecture
1. **Version and stabilize the public API** — document breaking-change policies for `KGRegistry`, `pack`, `PersonCorpusRegistry`
2. **Enforce layer boundaries** — add linting or CI checks to prevent unexpected cross-module dependencies as the codebase grows
3. **Monitor hot paths** — instrument the high fan-in functions identified here to catch performance regressions early

---

## Inheritance Hierarchy

**19** INHERITS edges across **19** classes. Max depth: **2**.

| Class | Module | Depth | Parents | Children |
|-------|--------|-------|---------|----------|
| `DisulfideKGAdapter` | src/kg_rag/adapters/disulfide_adapter.py | 2 | 1 | 0 |
| `LegalKGAdapter` | src/kg_rag/adapters/legal_adapter.py | 2 | 1 | 0 |
| `MemoryKGAdapter` | src/kg_rag/adapters/memory_adapter.py | 2 | 1 | 0 |
| `PDBFileKGAdapter` | src/kg_rag/adapters/pdbfile_adapter.py | 2 | 1 | 0 |
| `PersonKGAdapter` | src/kg_rag/adapters/person_adapter.py | 2 | 1 | 0 |
| `VerseKGAdapter` | src/kg_rag/adapters/verse_adapter.py | 2 | 1 | 0 |
| `StubKGAdapter` | src/kg_rag/adapters/_stub_adapter.py | 1 | 1 | 6 |
| `CodeKGAdapter` | src/kg_rag/adapters/codekg_adapter.py | 1 | 1 | 0 |
| `DiaryKGAdapter` | src/kg_rag/adapters/diary_adapter.py | 1 | 1 | 0 |
| `DocKGAdapter` | src/kg_rag/adapters/dockg_adapter.py | 1 | 1 | 0 |
| `MetaKGAdapter` | src/kg_rag/adapters/metakg_adapter.py | 1 | 1 | 0 |
| `KGAdapter` | src/kg_rag/adapters/base.py | 0 | 1 | 5 |
| `KGKind` | src/kg_rag/primitives.py | 0 | 1 | 0 |
| `DisplayMode` | src/kg_rag/viz.py | 0 | 1 | 0 |
| `RenderBackend` | src/kg_rag/viz.py | 0 | 1 | 0 |
| `KGGraphView` | src/kg_rag/viz_qt.py | 0 | 1 | 0 |
| `KGRAGViz2DWindow` | src/kg_rag/viz_qt.py | 0 | 1 | 0 |
| `KGViewportWidget` | src/kg_rag/viz_qt.py | 0 | 1 | 0 |
| `_CanvasWidget` | src/kg_rag/viz_qt.py | 0 | 1 | 0 |


---

## Snapshot History

Recent snapshots in reverse chronological order. Δ columns show change vs. the immediately preceding snapshot.

| # | Timestamp | Branch | Version | Nodes | Edges | Coverage | Δ Nodes | Δ Edges | Δ Coverage |
|---|-----------|--------|---------|-------|-------|----------|---------|---------|------------|
| 1 | 2026-03-17 01:35:05 | main | 0.3.0 | 2859 | 4120 | 81.3% | +177 | +368 | +0.4% |
| 2 | 2026-03-15 17:16:53 | claude/add-corpus-abstraction-KXiKg | stub-adapters-all-kinds | 2682 | 3752 | 80.9% | +1055 | +1792 | +2.1% |
| 3 | 2026-03-15 02:59:34 | main | 0.3.0 | 1627 | 1960 | 78.8% | +2 | +2 | +0.0% |
| 4 | 2026-03-15 02:50:21 | main | 0.2.0 | 1625 | 1958 | 78.8% | +51 | +93 | +0.3% |
| 5 | 2026-03-14 23:56:47 | main | 0.2.0 | 1574 | 1865 | 78.5% | +48 | +72 | +0.7% |
| 6 | 2026-03-14 05:28:35 | main | 0.2.0 | 1526 | 1793 | 77.8% | +0 | +0 | +0.0% |
| 7 | 2026-03-14 05:27:56 | main | 0.2.0 | 1526 | 1793 | 77.8% | +0 | +0 | +0.0% |
| 8 | 2026-03-14 05:22:41 | main | 0.2.0 | 1526 | 1793 | 77.8% | +0 | +0 | +0.0% |
| 9 | 2026-03-14 05:03:46 | main | 0.2.0 | 1526 | 1793 | 77.8% | +0 | +0 | +0.0% |
| 10 | 2026-03-14 04:53:15 | main | 0.2.0 | 1526 | 1793 | 77.8% | +393 | +447 | -2.0% |


---

## Appendix: Orphaned Code

Functions with zero callers (potential dead code):

No orphaned functions detected.
---

## CodeRank -- Global Structural Importance

Weighted PageRank over CALLS + IMPORTS + INHERITS edges (test paths excluded). Scores are normalized to sum to 1.0. This ranking seeds Phase 2 fan-in discovery and Phase 15 concern queries.

| Rank | Score | Kind | Name | Module |
|------|-------|------|------|--------|
| 1 | 0.000864 | method | `DiaryKGAdapter._load` | src/kg_rag/adapters/diary_adapter.py |
| 2 | 0.000864 | method | `CorpusRegistry._row_to_entry` | src/kg_rag/corpus_registry.py |
| 3 | 0.000864 | method | `PersonCorpusRegistry._row_to_entry` | src/kg_rag/person_registry.py |
| 4 | 0.000831 | method | `KGRAG._get_adapter` | src/kg_rag/orchestrator.py |
| 5 | 0.000727 | method | `KGRegistry._row_to_entry` | src/kg_rag/registry.py |
| 6 | 0.000654 | method | `CodeKGAdapter._load` | src/kg_rag/adapters/codekg_adapter.py |
| 7 | 0.000653 | method | `StubKGAdapter._try_load` | src/kg_rag/adapters/_stub_adapter.py |
| 8 | 0.000562 | method | `DocKGAdapter._load` | src/kg_rag/adapters/dockg_adapter.py |
| 9 | 0.000554 | method | `CorpusRegistry.get` | src/kg_rag/corpus_registry.py |
| 10 | 0.000554 | method | `PersonCorpusRegistry.get` | src/kg_rag/person_registry.py |
| 11 | 0.000551 | method | `KGRegistry.list` | src/kg_rag/registry.py |
| 12 | 0.000551 | method | `CorpusRegistry.list` | src/kg_rag/corpus_registry.py |
| 13 | 0.000551 | method | `PersonCorpusRegistry.list` | src/kg_rag/person_registry.py |
| 14 | 0.000535 | method | `KGAdapter.is_available` | src/kg_rag/adapters/base.py |
| 15 | 0.000526 | method | `KGViewportWidget._render` | src/kg_rag/viz_qt.py |
| 16 | 0.000485 | method | `MetaKGAdapter._load` | src/kg_rag/adapters/metakg_adapter.py |
| 17 | 0.000483 | function | `_load_kgrag` | src/kg_rag/app.py |
| 18 | 0.000472 | method | `StubKGAdapter._load` | src/kg_rag/adapters/_stub_adapter.py |
| 19 | 0.000472 | method | `StubKGAdapter.is_available` | src/kg_rag/adapters/_stub_adapter.py |
| 20 | 0.000465 | method | `KGRegistry.close` | src/kg_rag/registry.py |

---

## Concern-Based Hybrid Ranking

Top structurally-dominant nodes per architectural concern (0.60 × semantic + 0.25 × CodeRank + 0.15 × graph proximity).

### Configuration Loading Initialization Setup

| Rank | Score | Kind | Name | Module |
|------|-------|------|------|--------|
| 1 | 0.8097 | method | `CodeKGAdapter._load` | src/kg_rag/adapters/codekg_adapter.py |
| 2 | 0.7966 | method | `DocKGAdapter._load` | src/kg_rag/adapters/dockg_adapter.py |
| 3 | 0.7883 | method | `MetaKGAdapter._load` | src/kg_rag/adapters/metakg_adapter.py |
| 4 | 0.7484 | method | `KGRAGViz2DWindow._load_registry` | src/kg_rag/viz_qt.py |
| 5 | 0.7484 | function | `_init_state` | src/kg_rag/app.py |

### Data Persistence Storage Database

| Rank | Score | Kind | Name | Module |
|------|-------|------|------|--------|
| 1 | 0.8038 | method | `KGAdapter.is_available` | src/kg_rag/adapters/base.py |
| 2 | 0.7895 | method | `StubKGAdapter.is_available` | src/kg_rag/adapters/_stub_adapter.py |
| 3 | 0.7483 | method | `KGEntry.is_built` | src/kg_rag/primitives.py |
| 4 | 0.7438 | method | `KGAdapter.snapshot` | src/kg_rag/adapters/base.py |
| 5 | 0.7349 | method | `DocKGAdapter.is_available` | src/kg_rag/adapters/dockg_adapter.py |

### Query Search Retrieval Semantic

| Rank | Score | Kind | Name | Module |
|------|-------|------|------|--------|
| 1 | 0.75 | function | `query` | src/kg_rag/cli/cmd_query.py |
| 2 | 0.7115 | function | `_tab_query` | src/kg_rag/app.py |
| 3 | 0.7084 | function | `_parse_kinds` | src/kg_rag/cli/cmd_query.py |
| 4 | 0.706 | function | `person_query` | src/kg_rag/cli/cmd_corpus.py |
| 5 | 0.7053 | function | `corpus_query` | src/kg_rag/cli/cmd_corpus.py |

### Graph Traversal Node Edge

| Rank | Score | Kind | Name | Module |
|------|-------|------|------|--------|
| 1 | 0.7628 | method | `KGAdapter._graph_stats` | src/kg_rag/adapters/base.py |
| 2 | 0.7265 | function | `draw_stub_ontological` | src/kg_rag/viz_qt.py |
| 3 | 0.7232 | function | `draw_stub_semantic` | src/kg_rag/viz_qt.py |
| 4 | 0.7203 | method | `MetaKGAdapter.stats` | src/kg_rag/adapters/metakg_adapter.py |
| 5 | 0.7074 | method | `CodeKGAdapter.stats` | src/kg_rag/adapters/codekg_adapter.py |



---

*Report generated by CodeKG Thorough Analysis Tool — analysis completed in 3.5s*
