# KGRAG Full Stack Assessment
**Generated:** 2026-04-16
**KGRAG Version:** 0.3.6
**Assessor:** Claude_T (KnowledgeTree-backed SI instance)
**Registry:** `/Users/egs/.kgrag/registry.sqlite`

---

## Phase 1 — Stack Inventory

### Active MCP Servers

| Server | Tool Called | Nodes | Edges | Index Path | Build Date | Status |
|--------|-------------|------:|------:|------------|------------|--------|
| codekg | `graph_stats()` | 4,017 (324 meaningful) | 5,437 | `.codekg/graph.sqlite` | unknown | OK* |
| dockg | `graph_stats()` | 9,529 | 77,578 | `.dockg/graph.sqlite` | unknown | OK* |
| memorykg | `graph_stats()` | 11,663 | 76,477 | `.memorykg/graph.sqlite` | unknown | OK* |
| diarykg | `diary_stats()` | 41,544 | 581,630 | `pepys/pepys_enriched_full.txt` | 2026-04-01 | OK |
| metabokg | `snapshot_list()` | — | — | `/Users/egs/repos/Metabo_kg/...` | — | ⚠️ NO_SNAPSHOT |
| agent-kg | `agent_kg_stats()` | 309 | 810 | `.agentkg/graph.sqlite` | live | OK |
| kgrag | `kgrag_list()` + `kgrag_stats()` | 91 KGs total | — | registry.sqlite | — | OK |

> \* codekg, dockg, and memorykg LanceDB indices were **stale at session start** — MCP servers held references to old `.lance` data files after a rebuild. Required manual MCP server restart. See Phase 5 for full details.

### CodeKG Node Breakdown (kgrag repo)

| Kind | Count |
|------|------:|
| symbol (stubs) | 3,693 |
| method | 180 |
| function | 69 |
| module | 40 |
| class | 35 |
| **meaningful total** | **324** |

### DocKG Node Breakdown (kgrag repo)

| Kind | Count |
|------|------:|
| chunk | 2,221 |
| entity | 2,280 |
| keyword | 2,082 |
| section | 1,225 |
| topic | 1,668 |
| document | 53 |

### MemoryKG Node Breakdown

| Kind | Count |
|------|------:|
| chunk | 3,224 |
| keyword | 2,740 |
| topic | 2,327 |
| entity | 2,075 |
| section | 1,240 |
| document | 57 |

### DiaryKG Summary

- **Source:** Pepys diary (`pepys/pepys_enriched_full.txt`)
- **Chunks / Entries:** 7,285 / 7,282
- **Temporal span:** 1660-01-01 → 1669-08-02
- **Top topic:** pepys_domestic (3,136), pepys_court (1,884), work (1,268)
- **Nodes / Edges:** 41,544 / 581,630

### AgentKG Summary (growth since 2026-04-15)

| Metric | 2026-04-15 | 2026-04-16 | Delta |
|--------|----------:|----------:|------:|
| Nodes | 279 | 309 | +30 |
| Edges | 733 | 810 | +77 |
| Sessions (turns) | 21 | 29 | +8 |
| Entity nodes | 33 | 35 | +2 |
| Intent nodes | 21 | 28 | +7 |
| Summary nodes | 19 | 21 | +2 |
| Topic nodes | 180 | 191 | +11 |

### KGRAG Registry Summary

| Kind | Count | Built | Unbuilt |
|------|------:|------:|--------:|
| code | 6 | 6 | 0 |
| doc | 84 | 84 | 0 |
| memory | 1 | 1 | 0 |
| **Total** | **91** | **91** | **0** |

**Improvement from 2026-04-15:** All 3 previously unbuilt code KGs (`FTreeKG-code`, `doc_kg-code`, `proteusPy-code`) are now built. Two new KGs registered: `numpy-code`, `numpy-doc`.

---

## Phase 2 — Federated Health Check

| Query | Target KG | Hit Count | Top Result | Source File | Result |
|-------|-----------|----------:|------------|-------------|--------|
| `"hybrid semantic graph retrieval"` | codekg | 16 nodes | `AgentKGAdapter.assemble_context` (0.627) | `src/kg_rag/adapters/agent_adapter.py` | ✅ PASS |
| `"KnowledgeTree traversal epistemic"` | memorykg | 25 nodes | "The Knowledge Tree" entity | `docs/PARTNERSHIP_EXECUTIVE_SUMMARY.md` | ✅ PASS |
| `"Pepys naval fleet battle"` | diarykg | 5 entries | entry_4607 1665-11-27 (0.796) | `pepys/pepys_enriched_full.txt` | ✅ PASS |
| `"metabolic pathway glycolysis"` | metabokg | 3 pathways | Glycolysis/Gluconeogenesis (hsa00010) | `Metabo_kg/data/hsa_pathways/hsa00010.kgml` | ✅ PASS |
| `"KGRAG MCP tool surface"` | dockg | 25 nodes | "MCP Tool Surface (Claude_T Interface)" | `CLAUDE_T_IDENTITY.md` + `docs/ADAPTER_SPEC.md` | ✅ PASS |

**All 5 health checks PASS** (compared to 5/5 on 2026-04-15 — maintained after MCP restart).

### Detail Notes

- **codekg** top hits: `assemble_context`, `query` (cmd_query), `KGAdapter._graph_stats`, `AgentKGAdapter.query`, `KGKind` — correct structural coverage.
- **memorykg** top entity "The Knowledge Tree" + chunk from `PARTNERSHIP_EXECUTIVE_SUMMARY.md` — KnowledgeTree vision concept properly indexed.
- **diarykg** all 5 hits categorized `pepys_naval` — semantic routing to topic cluster confirmed. Scores 0.773–0.796.
- **metabokg** Glycolysis/Gluconeogenesis (hsa00010, 61 members) as top hit — semantic index intact.
- **dockg** hit `CLAUDE_T_IDENTITY.md` section "MCP Tool Surface (Claude_T Interface)" as second result, `docs/ADAPTER_SPEC.md` section "MCP Tool Surface" as third — high precision routing confirmed.

---

## Phase 3 — Cross-Domain Traversal

### Query 1: `kgrag_query("knowledge graph registry federated")`

- **Total hits:** 440
- **KGs queried:** 89
- **Top contributing KGs:** `doc_kg-code` (`DocKG.__init__`, score 0.617), `proteusPy-code` (`KnowledgeGraph` class, 0.608), `proteusPy-code` (`GraphReasoner`, 0.601)
- **Assessment:** Wide multi-KG hit span across ≥5 KG kinds (code, doc, memory). ✅ PASS

### Query 2: `kgrag_corpus_query("claude_t_self", "inference optional synthesis")`

- **Result:** `{"total_hits": 0, "kgs_queried": 1, "hits": []}`
- **Assessment:** 0 hits despite corpus existing and memorykg being rebuilt. Root cause: the **kgrag MCP orchestrator** cached the stale adapter for `claude_t_self` at startup and did not pick up the rebuilt LanceDB after restart. The kgrag server itself needs a restart to reconnect its adapter to the fresh index. ❌ FAIL — kgrag adapter cache stale.

### Routing Gap Summary

| Gap | Severity | Impact |
|-----|----------|--------|
| kgrag MCP adapter stale for `claude_t_self` | HIGH | `kgrag_corpus_query` returns 0 hits even after memorykg rebuild |
| MetaboKG no snapshot | HIGH | No temporal baseline for delta tracking |

---

## Phase 4 — Self-Knowledge Probe

### AgentKG Statistics

| Metric | Value |
|--------|------:|
| Total nodes | 309 |
| Total edges | 810 |
| Sessions (turns) | 29 |
| Person ID | egs |
| Entity nodes | 35 |
| Intent nodes | 28 |
| Summary nodes | 21 |
| Task nodes | 5 |
| Topic nodes | 191 |

### Top 10 Topics (by recency, 2026-04-16)

1. `memory`
2. `query`
3. `repo`
4. `codebase`
5. `test`
6. `fix`
7. `module`
8. `python`
9. `check your` / `repos kgrag`
10. `inference kgrag` → `federated knowledge` → `knowledge substrate`

Notable new topic chains (since 2026-04-15): `inference optional`, `correction both documents`, `distinction matters`, `knowledgetree`, `userpromptsubmit`, `precompact`, `diarykg with poetry`.

### Identity Profile (agent_kg_profile)

**User:** Eric G. Suchanek, PhD
**Expertise:** platform architecture, abstraction, optimization, physics, biophysics, chemistry, ML, AI
**Interests:** embedding spaces, knowledge representation, knowledge graphs
**Style:** concise, `:param:` docstrings, comprehensive
**Key commitments tracked:** no hallucinations, no sycophancy, write pytest tests, never simplify without permission, `:param:` style docstrings.

**Profile noise detected:** Several commitment entries contain scraped/garbage text (e.g. `"never committed. : Skip to content..."`, `"never share or sell your email..."`, `"avoid unnecessary retracing..."`). These are low-quality ingestion artifacts.

### MemoryKG Identity Corpus Check

Query: `"Claude_T Synthetic Intelligence identity"` → 15 nodes, seeds from `CHANGELOG.md` and `CLAUDE_T_IDENTITY.md`.

**Key identity chunks indexed:**

> **Claude_T** is the first instantiation of a **Synthetic Intelligence (SI)** agent — `CLAUDE_T_IDENTITY.md` — Technical identity declaration... documents the KnowledgeTree (T) architecture, epistemic contract, stack components, and Claude_T vs Claude_H distinction.

> `feat(identity): Claude_T SI identity, full stack activation, self-knowledge corpus` — Bring all seven MCP servers online and establish Claude_T as the first Synthetic Intelligence agent with a traversable KnowledgeTree substrate.

**Coverage:** `CLAUDE_T_IDENTITY.md` indexed via dockg chunks; `CHANGELOG.md` identity section indexed with SIMILAR_TO links to commit.txt. ✅ PASS (memorykg direct access — kgrag corpus route still stale).

---

## Phase 5 — Gap Analysis

### 1. LanceDB Stale Index Files — NEW CRITICAL FINDING

**Affects:** codekg, dockg, memorykg (all three MCP servers on this session start)

**Root cause:** After a `codekg build` / `dockg build` / `memorykg-build`, LanceDB replaces the old `.lance` data files with new ones. MCP servers **hold open file handles** to the old data files. Queries fail with:
```
lance error: Not found: Users/egs/repos/kgrag/.codekg/lancedb/codekg_nodes.lance/data/<hash>.lance
```
The registry shows `built=true` (SQLite file exists) but the vector search layer is broken until the MCP server process is restarted.

**Impact:** All semantic queries to affected KGs fail. `kgrag_corpus_query` returns 0 hits. Health command's current `stale_lancedb` check only verifies the **directory** exists — it does not detect stale internal file references.

**Remediation:**
- **Immediate:** Always restart MCP servers after any KG build (`codekg build`, `dockg build`, `memorykg-build`). Lance holds exclusive locks on data files.
- **Tooling:** The health command should add a lightweight probe check — attempt a 1-hit query via the adapter and flag it as `stale_lancedb_probe` if it throws a lance `Not found` error.

### 2. kgrag_corpus_query Returns 0 Hits for claude_t_self

Even after memorykg was rebuilt and its MCP server restarted, `kgrag_corpus_query("claude_t_self", ...)` returns 0 hits. The kgrag MCP orchestrator instantiates KGAdapters at startup and caches them — it does not reload when the underlying LanceDB is replaced. Requires a kgrag MCP server restart to pick up the new index.

### 3. MetaboKG No Snapshot Baseline

`snapshot_list()` → `[]`. Unchanged since 2026-04-15. Temporal metrics unavailable.

### 4. AgentKG Profile Noise

Several commitment entries contain raw scraped text rather than clean policy statements. Entries like `"never committed. : Skip to content..."` are ingestion artifacts from web pages that were accidentally ingested as commitments.

### 5. numpy-doc Missing LanceDB

`numpy-doc` is registered with `lancedb_path: null`. Semantic queries against numpy-doc will fall back to SQLite-only and miss vector search. Needs a `dockg build --repo /Users/egs/repos/numpy` to generate the LanceDB index.

### 6. Version Tags

87 of 91 KGs show `version: "unknown"`. Only `claude_t_self` (0.3.6), `FTreeKG-*` (0.2.0), `proteusPy-*` (0.99.50) carry version strings. Low priority but makes temporal tracking harder.

---

## Phase 6 — Coverage Matrix

| Domain | KG | MCP Active | Nodes | Edges | Last Build | Status |
|--------|-----|:----------:|------:|------:|------------|--------|
| Python source (kgrag) | kgrag-code | ✅ | 324 meaningful | 5,437 | unknown | OK |
| Unstructured docs (kgrag) | kgrag-doc | ✅ | 9,529 | 77,578 | unknown | OK |
| Self-knowledge / identity | memorykg (claude_t_self) | ✅ | 11,663 | 76,477 | unknown | OK |
| Diary narrative (Pepys) | diarykg | ✅ | 41,544 | 581,630 | 2026-04-01 | OK |
| File tree | FTreeKG-doc | ✅ | built | — | 2026-03-19 | OK |
| File tree code | FTreeKG-code | ✅ | built | — | 2026-03-19 | OK ✓ (was UNBUILT) |
| Session memory | agent-kg | ✅ | 309 | 810 | live | OK |
| Metabolic | metabokg | ✅ | active | — | — | ⚠️ NO_SNAPSHOT |
| Python source (code_kg) | code_kg-code | ✅ | built | — | unknown | OK ✓ (was UNBUILT) |
| Docs (code_kg) | code_kg-doc | ✅ | built | — | unknown | OK |
| Python source (doc_kg) | doc_kg-code | ✅ | built | — | unknown | OK ✓ (was UNBUILT) |
| Docs (doc_kg) | doc_kg-doc | ✅ | built | — | unknown | OK |
| Python source (proteusPy) | proteusPy-code | ✅ | built | — | 2026-03-24 | OK ✓ (was UNBUILT) |
| Docs (proteusPy) | proteusPy-doc | ✅ | built | — | 2026-03-24 | OK |
| NumPy source | numpy-code | ✅ | built | — | — | OK (NEW) |
| NumPy docs | numpy-doc | ✅ | built | — | — | ⚠️ NO_LANCEDB (NEW) |
| Literature (Gutenberg) | 75 doc KGs | ✅ | built | — | 2026-03-30/31 | OK |
| Corpus: KGRAG_repos | corpus | ✅ | — | — | — | OK (verify) |
| Corpus: claude_t_self | corpus | ✅ created | — | — | — | ⚠️ kgrag adapter stale |

---

## Phase 7 — Recommendations

| # | Issue | Severity | Remediation |
|---|-------|----------|-------------|
| 1 | MCP servers not restarted after builds | **CRITICAL** | Always restart codekg/dockg/memorykg/kgrag MCP servers after any build — LanceDB holds file locks on old data files |
| 2 | `kgrag_corpus_query` stale for `claude_t_self` | HIGH | Restart kgrag MCP server; verify with `kgrag_corpus_query("claude_t_self", "inference optional synthesis")` |
| 3 | MetaboKG no snapshot baseline | HIGH | `cd /Users/egs/repos/Metabo_kg && metabokg snapshot save` (check exact CLI) |
| 4 | Health command: probe LanceDB liveness | HIGH | Add a `stale_lancedb_probe` check — attempt a 1-hit semantic query; catch lance `Not found` errors as a new critical issue |
| 5 | numpy-doc missing LanceDB | MEDIUM | `cd /Users/egs/repos/numpy && dockg build --repo .` then restart dockg MCP |
| 6 | AgentKG profile noise | LOW | `agent_kg_prune` — remove commitment entries that contain raw scraped web content |
| 7 | Version tags `unknown` in registry | LOW | Re-register KGs with explicit `--version` to enable temporal tracking |

---

## Summary

| Metric | 2026-04-15 | 2026-04-16 | Delta |
|--------|----------:|----------:|-------|
| KGRAG version | 0.3.6 | 0.3.6 | — |
| Total KGs registered | 91 | 91 | 0 |
| KGs built | 88 | **91** | +3 ✓ |
| Unbuilt KGs | 3 | **0** | -3 ✓ |
| MCP servers responding | 7/7 | 7/7 | — |
| Phase 2 health checks | 5/5 | **5/5** | maintained |
| Phase 3 federated query | 1/2 | **1/2** | unchanged |
| AgentKG nodes | 279 | **309** | +30 |
| AgentKG sessions (turns) | 21 | **29** | +8 |
| New KGs | — | numpy-code, numpy-doc | +2 |

### Critical Gaps (Priority Order)

1. **MCP restart after builds** — LanceDB file locking makes this a hard requirement; a health check probe would catch it automatically
2. **kgrag corpus adapter cache** — `claude_t_self` corpus unreachable via kgrag MCP until kgrag server is restarted
3. **MetaboKG snapshot** — no temporal baseline; run snapshot save immediately
4. **Health command liveness probe** — current `stale_lancedb` check is path-exists only; needs a query-probe to catch stale file handles

### Progress vs. 2026-04-15

- ✅ `claude_t_self` corpus created (was missing)
- ✅ 3 unbuilt code KGs now built (FTreeKG-code, doc_kg-code, proteusPy-code)
- ✅ `kgrag health` command implemented with `--fix` executing build commands
- ✅ All 5 Phase 2 health queries passing
- ❌ MetaboKG snapshot still missing
- ❌ kgrag corpus query for claude_t_self still returns 0 hits (new root cause identified: kgrag adapter cache)

---

*Report generated by Claude_T (Synthetic Intelligence, KnowledgeTree-backed) — 2026-04-16*
