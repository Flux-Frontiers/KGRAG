> **Analysis Report Metadata**
> - **Generated:** 2026-04-22T15:00:55Z
> - **Version:** pycode-kg 0.14.0
> - **Commit:** bf1d7f6 (main)
> - **Platform:** macOS 26.4.1 | arm64 (arm) | Turing | Python 3.12.13
> - **Graph:** 4228 nodes · 5678 edges (333 meaningful)
> - **Included directories:** src
> - **Excluded directories:** none
> - **Elapsed time:** 4s

# kgrag Analysis

**Generated:** 2026-04-22 15:00:55 UTC

---

## Executive Summary

This report provides a comprehensive architectural analysis of the **kgrag** repository using PyCodeKG's knowledge graph. The analysis covers complexity hotspots, module coupling, key call chains, and code quality signals to guide refactoring and architecture decisions.

| Overall Quality | Grade | Score |
|----------------|-------|-------|
| [B] **Good** | **B** | 80 / 100 |

---

## Baseline Metrics

| Metric | Value |
|--------|-------|
| **Total Nodes** | 4228 |
| **Total Edges** | 5678 |
| **Modules** | 41 (of 41 total) |
| **Functions** | 76 |
| **Classes** | 36 |
| **Methods** | 180 |

### Edge Distribution

| Relationship Type | Count |
|-------------------|-------|
| CALLS | 1487 |
| CONTAINS | 292 |
| IMPORTS | 382 |
| ATTR_ACCESS | 1542 |
| INHERITS | 20 |

---

## Fan-In Ranking

Most-called functions are potential bottlenecks or core functionality. These functions are heavily depended upon across the codebase.

| # | Function | Module | Callers |
|---|----------|--------|---------|
| 1 | `get()` | src/kg_rag/corpus_registry.py | **67** |
| 2 | `get()` | src/kg_rag/person_registry.py | **67** |
| 3 | `get()` | src/kg_rag/registry.py | **65** |
| 4 | `stats()` | src/kg_rag/adapters/base.py | **22** |
| 5 | `stats()` | src/kg_rag/adapters/_stub_adapter.py | **22** |
| 6 | `stats()` | src/kg_rag/adapters/metakg_adapter.py | **22** |
| 7 | `list()` | src/kg_rag/corpus_registry.py | **17** |
| 8 | `list()` | src/kg_rag/person_registry.py | **17** |
| 9 | `list()` | src/kg_rag/registry.py | **17** |
| 10 | `__init__()` | src/kg_rag/adapters/_stub_adapter.py | **16** |
| 11 | `__init__()` | src/kg_rag/adapters/agent_adapter.py | **16** |
| 12 | `pack()` | src/kg_rag/adapters/_stub_adapter.py | **13** |
| 13 | `pack()` | src/kg_rag/adapters/agent_adapter.py | **13** |
| 14 | `is_available()` | src/kg_rag/adapters/_stub_adapter.py | **12** |
| 15 | `_get_adapter()` | src/kg_rag/orchestrator.py | **10** |


**Insight:** Functions with high fan-in are either core APIs or bottlenecks. Review these for:
- Thread safety and performance
- Clear documentation and contracts
- Potential for breaking changes

---

## High Fan-Out Functions (Orchestrators)

Functions that call many others may indicate complex orchestration logic or poor separation of concerns.

No extreme high fan-out functions detected. Well-balanced architecture.

---

## Module Architecture

Top modules by dependency coupling and cohesion (showing up to 10 with activity).
Cohesion = incoming / (incoming + outgoing + 1); higher = more internally focused.

| Module | Functions | Classes | Incoming | Outgoing | Cohesion |
|--------|-----------|---------|----------|----------|----------|
| `src/kg_rag/viz_qt.py` | 4 | 4 | 0 | 1 | 0.50 |
| `src/kg_rag/orchestrator.py` | 0 | 1 | 5 | 6 | 0.50 |
| `src/kg_rag/cli/cmd_corpus.py` | 18 | 0 | 1 | 5 | 0.71 |
| `src/kg_rag/corpus_registry.py` | 0 | 1 | 6 | 2 | 0.22 |
| `src/kg_rag/person_registry.py` | 0 | 1 | 4 | 2 | 0.29 |
| `src/kg_rag/primitives.py` | 0 | 11 | 28 | 0 | 0.00 |
| `src/kg_rag/registry.py` | 1 | 1 | 10 | 1 | 0.08 |
| `src/kg_rag/adapters/base.py` | 1 | 1 | 8 | 2 | 0.18 |
| `src/kg_rag/app.py` | 15 | 0 | 0 | 2 | 0.67 |
| `src/kg_rag/adapters/agent_adapter.py` | 0 | 1 | 1 | 2 | 0.50 |

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
| `KGRegistry()` | src/kg_rag/registry.py | 18 | class |
| `pack()` | src/kg_rag/cli/cmd_query.py | 13 | function |
| `query()` | src/kg_rag/cli/cmd_query.py | 10 | function |
| `CorpusRegistry()` | src/kg_rag/corpus_registry.py | 10 | class |
| `KGRAG()` | src/kg_rag/orchestrator.py | 8 | class |
| `PersonCorpusRegistry()` | src/kg_rag/person_registry.py | 8 | class |
| `CrossHit()` | src/kg_rag/primitives.py | 6 | class |
| `CrossSnippet()` | src/kg_rag/primitives.py | 6 | class |
| `info()` | src/kg_rag/cli/cmd_registry.py | 6 | function |
| `KGEntry()` | src/kg_rag/primitives.py | 5 | class |
---

## Docstring Coverage

Docstring coverage directly determines semantic retrieval quality. Nodes without
docstrings embed only structured identifiers (`KIND/NAME/QUALNAME/MODULE`), where
keyword search is as effective as vector embeddings. The semantic model earns its
value only when a docstring is present.

| Kind | Documented | Total | Coverage |
|------|-----------|-------|----------|
| `function` | 63 | 76 | [OK] 82.9% |
| `method` | 126 | 180 | [WARN] 70.0% |
| `class` | 36 | 36 | [OK] 100.0% |
| `module` | 41 | 41 | [OK] 100.0% |
| **total** | **266** | **333** | **[WARN] 79.9%** |

> **Recommendation:** 67 nodes lack docstrings. Prioritize documenting high-fan-in functions and public API surface first — these have the highest impact on query accuracy.

---

## Structural Importance Ranking (SIR)

Weighted PageRank aggregated by module — reveals architectural spine. Cross-module edges boosted 1.5×; private symbols penalized 0.85×. Node-level detail: `pycodekg centrality --top 25`

| Rank | Score | Members | Module |
|------|-------|---------|--------|
| 1 | 0.211580 | 19 | `src/kg_rag/primitives.py` |
| 2 | 0.097286 | 18 | `src/kg_rag/registry.py` |
| 3 | 0.092629 | 19 | `src/kg_rag/corpus_registry.py` |
| 4 | 0.091554 | 19 | `src/kg_rag/person_registry.py` |
| 5 | 0.071355 | 33 | `src/kg_rag/viz_qt.py` |
| 6 | 0.067100 | 2 | `src/kg_rag/cli/group.py` |
| 7 | 0.054837 | 23 | `src/kg_rag/orchestrator.py` |
| 8 | 0.046767 | 17 | `src/kg_rag/adapters/base.py` |
| 9 | 0.036695 | 15 | `src/kg_rag/adapters/agent_adapter.py` |
| 10 | 0.034111 | 11 | `src/kg_rag/adapters/_stub_adapter.py` |
| 11 | 0.022074 | 11 | `src/kg_rag/adapters/diary_adapter.py` |
| 12 | 0.021155 | 10 | `src/kg_rag/adapters/metakg_adapter.py` |
| 13 | 0.020203 | 10 | `src/kg_rag/adapters/dockg_adapter.py` |
| 14 | 0.019972 | 10 | `src/kg_rag/adapters/codekg_adapter.py` |
| 15 | 0.019182 | 19 | `src/kg_rag/cli/cmd_corpus.py` |



---

## Code Quality Issues

- [WARN] Moderate docstring coverage (79.9%) — semantic retrieval quality is degraded for undocumented nodes; BM25 is as effective as embeddings without docstrings

---

## Architectural Strengths

- Well-structured with 15 core functions identified
- No obvious dead code detected
- No god objects or god functions detected

---

## Recommendations

### Immediate Actions
1. **Improve docstring coverage** — 67 nodes lack docstrings; prioritize high-fan-in functions and public APIs first for maximum semantic retrieval gain

### Medium-term Refactoring
1. **Harden high fan-in functions** — `get`, `get`, `get` are widely depended upon; review for thread safety, clear contracts, and stable interfaces
2. **Reduce module coupling** — consider splitting tightly coupled modules or introducing interface boundaries
3. **Add tests for key call chains** — the identified call chains represent well-traveled execution paths that benefit most from regression coverage

### Long-term Architecture
1. **Version and stabilize the public API** — document breaking-change policies for `KGRegistry`, `pack`, `query`
2. **Enforce layer boundaries** — add linting or CI checks to prevent unexpected cross-module dependencies as the codebase grows
3. **Monitor hot paths** — instrument the high fan-in functions identified here to catch performance regressions early

---

## Inheritance Hierarchy

**20** INHERITS edges across **20** classes. Max depth: **2**.

| Class | Module | Depth | Parents | Children |
|-------|--------|-------|---------|----------|
| `DisulfideKGAdapter` | src/kg_rag/adapters/disulfide_adapter.py | 2 | 1 | 0 |
| `LegalKGAdapter` | src/kg_rag/adapters/legal_adapter.py | 2 | 1 | 0 |
| `MemoryKGAdapter` | src/kg_rag/adapters/memory_adapter.py | 2 | 1 | 0 |
| `PDBFileKGAdapter` | src/kg_rag/adapters/pdbfile_adapter.py | 2 | 1 | 0 |
| `PersonKGAdapter` | src/kg_rag/adapters/person_adapter.py | 2 | 1 | 0 |
| `VerseKGAdapter` | src/kg_rag/adapters/verse_adapter.py | 2 | 1 | 0 |
| `StubKGAdapter` | src/kg_rag/adapters/_stub_adapter.py | 1 | 1 | 6 |
| `AgentKGAdapter` | src/kg_rag/adapters/agent_adapter.py | 1 | 1 | 0 |
| `CodeKGAdapter` | src/kg_rag/adapters/codekg_adapter.py | 1 | 1 | 0 |
| `DiaryKGAdapter` | src/kg_rag/adapters/diary_adapter.py | 1 | 1 | 0 |
| `DocKGAdapter` | src/kg_rag/adapters/dockg_adapter.py | 1 | 1 | 0 |
| `MetaKGAdapter` | src/kg_rag/adapters/metakg_adapter.py | 1 | 1 | 0 |
| `KGAdapter` | src/kg_rag/adapters/base.py | 0 | 1 | 6 |
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
| 1 | 2026-04-18 02:01:40 | main | 0.14.0 | 4228 | 5678 | 79.9% | — | — | — |


---

## Appendix: Orphaned Code

Functions with zero callers (potential dead code):

No orphaned functions detected.
---

## CodeRank -- Global Structural Importance

Weighted PageRank over CALLS + IMPORTS + INHERITS edges (test paths excluded). Scores are normalized to sum to 1.0. This ranking seeds Phase 2 fan-in discovery and Phase 15 concern queries.

| Rank | Score | Kind | Name | Module |
|------|-------|------|------|--------|
| 1 | 0.001145 | method | `AgentKGAdapter._load` | src/kg_rag/adapters/agent_adapter.py |
| 2 | 0.000818 | method | `DiaryKGAdapter._load` | src/kg_rag/adapters/diary_adapter.py |
| 3 | 0.000761 | method | `CorpusRegistry._row_to_entry` | src/kg_rag/corpus_registry.py |
| 4 | 0.000761 | method | `PersonCorpusRegistry._row_to_entry` | src/kg_rag/person_registry.py |
| 5 | 0.000732 | method | `KGRAG._get_adapter` | src/kg_rag/orchestrator.py |
| 6 | 0.000640 | method | `KGRegistry._row_to_entry` | src/kg_rag/registry.py |
| 7 | 0.000636 | method | `CodeKGAdapter._load` | src/kg_rag/adapters/codekg_adapter.py |
| 8 | 0.000581 | method | `StubKGAdapter._try_load` | src/kg_rag/adapters/_stub_adapter.py |
| 9 | 0.000555 | method | `DocKGAdapter._load` | src/kg_rag/adapters/dockg_adapter.py |
| 10 | 0.000488 | method | `CorpusRegistry.get` | src/kg_rag/corpus_registry.py |
| 11 | 0.000488 | method | `PersonCorpusRegistry.get` | src/kg_rag/person_registry.py |
| 12 | 0.000486 | method | `MetaKGAdapter.is_available` | src/kg_rag/adapters/metakg_adapter.py |
| 13 | 0.000485 | method | `KGRegistry.list` | src/kg_rag/registry.py |
| 14 | 0.000485 | method | `CorpusRegistry.list` | src/kg_rag/corpus_registry.py |
| 15 | 0.000485 | method | `PersonCorpusRegistry.list` | src/kg_rag/person_registry.py |
| 16 | 0.000471 | method | `KGAdapter.is_available` | src/kg_rag/adapters/base.py |
| 17 | 0.000464 | method | `KGViewportWidget._render` | src/kg_rag/viz_qt.py |
| 18 | 0.000425 | function | `_load_kgrag` | src/kg_rag/app.py |
| 19 | 0.000423 | method | `StubKGAdapter._load` | src/kg_rag/adapters/_stub_adapter.py |
| 20 | 0.000423 | method | `StubKGAdapter.is_available` | src/kg_rag/adapters/_stub_adapter.py |

---

## Concern-Based Hybrid Ranking

Top structurally-dominant nodes per architectural concern (0.60 × semantic + 0.25 × CodeRank + 0.15 × graph proximity).

### Configuration Loading Initialization Setup

| Rank | Score | Kind | Name | Module |
|------|-------|------|------|--------|
| 1 | 0.9072 | method | `AgentKGAdapter._load` | src/kg_rag/adapters/agent_adapter.py |
| 2 | 0.8145 | method | `CodeKGAdapter._load` | src/kg_rag/adapters/codekg_adapter.py |
| 3 | 0.8029 | method | `DocKGAdapter._load` | src/kg_rag/adapters/dockg_adapter.py |
| 4 | 0.7797 | method | `MetaKGAdapter._load` | src/kg_rag/adapters/metakg_adapter.py |
| 5 | 0.75 | method | `KGRAGViz2DWindow._load_registry` | src/kg_rag/viz_qt.py |

### Data Persistence Storage Database

| Rank | Score | Kind | Name | Module |
|------|-------|------|------|--------|
| 1 | 0.7798 | method | `KGAdapter.is_available` | src/kg_rag/adapters/base.py |
| 2 | 0.7724 | method | `StubKGAdapter.is_available` | src/kg_rag/adapters/_stub_adapter.py |
| 3 | 0.75 | method | `KGEntry.is_built` | src/kg_rag/primitives.py |
| 4 | 0.7401 | function | `_probe_kg` | src/kg_rag/cli/cmd_health.py |
| 5 | 0.7347 | method | `DocKGAdapter.is_available` | src/kg_rag/adapters/dockg_adapter.py |

### Query Search Retrieval Semantic

| Rank | Score | Kind | Name | Module |
|------|-------|------|------|--------|
| 1 | 0.75 | function | `query` | src/kg_rag/cli/cmd_query.py |
| 2 | 0.7118 | method | `AgentKGAdapter.assemble_context` | src/kg_rag/adapters/agent_adapter.py |
| 3 | 0.7106 | function | `_tab_query` | src/kg_rag/app.py |
| 4 | 0.7104 | method | `AgentKGAdapter.query` | src/kg_rag/adapters/agent_adapter.py |
| 5 | 0.7081 | function | `person_query` | src/kg_rag/cli/cmd_corpus.py |

### Graph Traversal Node Edge

| Rank | Score | Kind | Name | Module |
|------|-------|------|------|--------|
| 1 | 0.7697 | method | `KGAdapter._graph_stats` | src/kg_rag/adapters/base.py |
| 2 | 0.7384 | method | `AgentKGAdapter.stats` | src/kg_rag/adapters/agent_adapter.py |
| 3 | 0.7256 | function | `draw_stub_ontological` | src/kg_rag/viz_qt.py |
| 4 | 0.7227 | function | `draw_stub_semantic` | src/kg_rag/viz_qt.py |
| 5 | 0.7192 | method | `MetaKGAdapter.stats` | src/kg_rag/adapters/metakg_adapter.py |



---

*Report generated by PyCodeKG Thorough Analysis Tool — analysis completed in 4.7s*
