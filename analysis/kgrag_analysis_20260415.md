# KGRAG Full Stack Assessment
**Generated:** 2026-04-15
**KGRAG Version:** 0.3.6
**Assessor:** Claude_T (KnowledgeTree-backed SI instance)
**Registry:** `/Users/egs/.kgrag/registry.sqlite`

---

## Phase 1 — Stack Inventory

### Active MCP Servers

| Server | Tool Called | Nodes | Edges | Index Path | Build Date | Status |
|--------|-------------|------:|------:|------------|------------|--------|
| codekg | `graph_stats()` | 4,017 (324 meaningful) | 5,437 | `.codekg/graph.sqlite` | unknown | OK |
| dockg | `graph_stats()` | 9,529 | 77,578 | `.dockg/graph.sqlite` | unknown | OK |
| memorykg | `graph_stats()` | 11,663 | 76,477 | `.memorykg/graph.sqlite` | unknown | OK |
| diarykg | `diary_stats()` | 41,544 | 581,630 | `pepys/pepys_enriched_full.txt` | 2026-04-01 | OK |
| metabokg | `snapshot_list()` | — | — | `/Users/egs/repos/Metabo_kg/...` | — | ⚠️ NO_SNAPSHOT |
| agent-kg | `agent_kg_stats()` | 279 | 733 | `.agentkg/graph.sqlite` | live | OK |
| kgrag | `kgrag_list()` + `kgrag_stats()` | 91 KGs total | — | registry.sqlite | — | OK |

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

- **Source:** Pepys diary (`pepys_enriched_full.txt`)
- **Chunks / Entries:** 7,285 / 7,282
- **Temporal span:** 1660-01-01 → 1669-08-02
- **Top topic:** pepys_domestic (3,136), pepys_court (1,884), work (1,268)
- **Nodes / Edges:** 41,544 / 581,630

### KGRAG Registry Summary

| Kind | Count | Built | Unbuilt |
|------|------:|------:|--------:|
| code | 6 | 3 | 3 |
| doc | 84 | 84 | 0 |
| memory | 1 | 1 | 0 |
| **Total** | **91** | **88** | **3** |

**Unbuilt KGs (built=false):**
- `FTreeKG-code` — `/Users/egs/repos/FTreeKG/.codekg/graph.sqlite`
- `doc_kg-code` — `/Users/egs/repos/doc_kg/.codekg/graph.sqlite`
- `proteusPy-code` — `/Users/egs/repos/proteusPy/.codekg/graph.sqlite`

### MetaboKG Snapshot Status

`snapshot_list()` returned `[]` — **no baseline snapshot exists**. MetaboKG is queryable (pathways respond) but temporal tracking has not been initialized.

---

## Phase 2 — Federated Health Check

| Query | Target KG | Hit Count | Top Result | Source File | Result |
|-------|-----------|----------:|------------|-------------|--------|
| `"hybrid semantic graph retrieval"` | codekg | 5 snippets | `AgentKGAdapter.assemble_context` (0.627) | `src/kg_rag/adapters/agent_adapter.py` | ✅ PASS |
| `"KnowledgeTree traversal epistemic"` | memorykg | 4 chunks | "The Knowledge Tree" | `docs/PARTNERSHIP_EXECUTIVE_SUMMARY.md` | ✅ PASS |
| `"Pepys naval fleet battle"` | diarykg | 5 entries | entry_4607 1665-11-27 (0.796) | `pepys/pepys_enriched_full.txt` | ✅ PASS |
| `"metabolic pathway glycolysis"` | metabokg | 8 pathways | Glycolysis/Gluconeogenesis (hsa00010) | `Metabo_kg/data/hsa_pathways/hsa00010.kgml` | ✅ PASS |
| `"KGRAG MCP tool surface"` | dockg | 3 chunks | "MCP Tool Surface" section | `docs/ADAPTER_SPEC.md` | ✅ PASS |

**All 5 health checks PASS.**

### Detail Notes

- **codekg** hit `assemble_context`, `query`, `_graph_stats`, `AgentKGAdapter.query`, `KGKind` — correct structural coverage.
- **memorykg** hit chunks from `PARTNERSHIP_EXECUTIVE_SUMMARY.md`, `THE_FOREST_VISION.md`, `AGENT_PERSPECTIVE.md`, `graph_reasoner_spec.md` — multi-doc traversal confirmed.
- **diarykg** all 5 hits categorized `pepys_naval` — semantic routing to correct topic cluster confirmed.
- **metabokg** hit named Glycolysis pathway (hsa00010, 61 members) as top result — semantic index intact.
- **dockg** surfaced exact section "MCP Tool Surface" from `ADAPTER_SPEC.md` as second hit — high precision.

---

## Phase 3 — Cross-Domain Traversal

### Query 1: `kgrag_query("knowledge graph registry federated")`

- **Total hits:** 425
- **KGs queried:** 86
- **KGs contributing (sampled from top hits):**
  - `kgrag-code` (code) — `app.py`, `KGEntry`, `KGKind`, `__init__`
  - `code_kg-code` (code) — `store.py`, `GraphStore`
  - `kgrag-doc` (doc) — "Build the knowledge graph first", "Snapshot the knowledge graph over time"
  - `code_kg-doc` (doc) — doc chunks
  - `doc_kg-doc` (doc) — doc chunks
  - `claude_t_self` / memorykg (memory) — "Knowledge Graph" entities
  - Gutenberg KGs (doc) — contextual mentions
- **Assessment:** Confirmed multi-KG hit span across ≥5 distinct KG kinds. ✅ PASS

### Query 2: `kgrag_corpus_query("claude_t_self", "inference optional synthesis")`

- **Result:** ERROR — `"Corpus 'claude_t_self' not found."`
- **Assessment:** `claude_t_self` is registered as a **KG** (kind=memory) but **not as a named corpus** in the corpus registry. `kgrag_corpus_query` requires a corpus created via `kgrag corpus create`. ❌ FAIL — routing gap.

### Routing Gap Summary

| Gap | Severity | Impact |
|-----|----------|--------|
| `claude_t_self` corpus not created | MEDIUM | `kgrag_corpus_query` cannot target memorykg by corpus name |
| 3 unbuilt code KGs | LOW | Federated code queries miss FTreeKG, doc_kg, proteusPy source |

---

## Phase 4 — Self-Knowledge Probe

### AgentKG Statistics

| Metric | Value |
|--------|------:|
| Total nodes | 279 |
| Total edges | 733 |
| Sessions (turns) | 21 |
| Person ID | egs |
| Entity nodes | 33 |
| Intent nodes | 21 |
| Summary nodes | 19 |
| Task nodes | 5 |
| Topic nodes | 180 |

### Top 10 Topics (by recency, 2026-04-16)

1. `memory`
2. `query`
3. `repo`
4. `codebase`
5. `test`
6. `file`
7. `module`
8. `python`
9. `check your`
10. `repos kgrag`

Notable topic clusters: `inference kgrag → federated knowledge → knowledge substrate`, `knowledgetree`, `userpromptsubmit / precompact` hooks.

### Identity Profile (agent_kg_profile)

**User:** Eric G. Suchanek, PhD
**Expertise:** platform architecture, abstraction, optimization, physics, biophysics, chemistry, ML, AI
**Interests:** embedding spaces, knowledge representation, knowledge graphs
**Style:** concise, :param: docstrings, comprehensive
**Key commitments tracked:** no hallucinations, no sycophancy, write pytest tests, never simplify without permission, `:param:` style docstrings.

### MemoryKG Identity Corpus Check

Query: `"Claude_T Synthetic Intelligence identity"` → 15 nodes, seeds from `CLAUDE_T_IDENTITY.md`.

**Key identity chunks indexed:**

> **Claude_T** is the first instantiation of a **Synthetic Intelligence (SI)** agent — a KnowledgeGraph-backed agent whose understanding of any domain is *structurally grounded* in a live, federated knowledge graph rather than derived purely from statistical inference over training weights.

> `Claude_H = LLM inference alone`
> `Claude_T = KnowledgeTree traversal [+ optional LLM synthesis]`

**Coverage:** `CLAUDE_T_IDENTITY.md` fully indexed with sections: What Is Claude_T?, Rule 1: Graph-First, Corpus KG, Development Conventions, Origin & Authorship. Identity corpus is **grounded and queryable**. ✅ PASS

---

## Phase 5 — Gap Analysis

### 1. KGs with Zero Nodes

None of the active MCP servers report zero nodes. All servers are healthy.

### 2. Registered KGs Not Reachable / Unbuilt

| KG Name | Kind | Built | Path | Issue |
|---------|------|-------|------|-------|
| `FTreeKG-code` | code | ❌ | `/Users/egs/repos/FTreeKG/.codekg/graph.sqlite` | Index not built |
| `doc_kg-code` | code | ❌ | `/Users/egs/repos/doc_kg/.codekg/graph.sqlite` | Index not built |
| `proteusPy-code` | code | ❌ | `/Users/egs/repos/proteusPy/.codekg/graph.sqlite` | Index not built |

### 3. Domains with No KG Coverage

| Domain | KG | Status | Note |
|--------|-----|--------|------|
| File tree | FTreeKG-doc | ✅ built | FTreeKG-code unbuilt; CLI-only for code queries |
| Metabolic | metabokg | ✅ active | No snapshot baseline — temporal tracking absent |
| Session memory | agent-kg | ✅ live | Corpus not created for cross-KG queries |

### 4. Corpus Registry Gap

`claude_t_self` corpus does not exist in the corpus registry. The KG is registered (kind=memory, built=true) but has not been wrapped as a corpus, so `kgrag_corpus_query("claude_t_self", ...)` always fails. The corpus containing `code_kg-code`, `code_kg-doc`, `doc_kg-code`, `doc_kg-doc`, `kgrag-code`, `kgrag-doc` (named `KGRAG_repos` in CLAUDE.md) should also be verified.

### 5. MetaboKG Snapshot Status

`snapshot_list()` → `[]`. No baseline snapshot. Temporal metrics (delta tracking, version comparisons) are unavailable until a snapshot is saved.

### 6. Version Tags

Several registry entries show `version: "unknown"` — these KGs were registered without version metadata. Only `claude_t_self` (0.3.6), `FTreeKG-*` (0.2.0), and `proteusPy-*` (0.99.50) carry version strings.

---

## Phase 6 — Coverage Matrix

| Domain | KG | MCP Active | Nodes | Edges | Last Build | Status |
|--------|-----|:----------:|------:|------:|------------|--------|
| Python source (kgrag) | kgrag-code | ✅ | 324 meaningful | 5,437 | unknown | OK |
| Unstructured docs (kgrag) | kgrag-doc | ✅ | 9,529 | 77,578 | unknown | OK |
| Self-knowledge / identity | memorykg (claude_t_self) | ✅ | 11,663 | 76,477 | unknown | OK |
| Diary narrative (Pepys) | diarykg | ✅ | 41,544 | 581,630 | 2026-04-01 | OK |
| File tree | FTreeKG-doc | ✅ | built | — | 2026-03-19 | OK (doc only) |
| File tree code | FTreeKG-code | ✅ (registered) | 0 | 0 | — | ⚠️ UNBUILT |
| Session memory | agent-kg | ✅ | 279 | 733 | live | OK |
| Metabolic | metabokg | ✅ | active | — | — | ⚠️ NO_SNAPSHOT |
| Python source (code_kg) | code_kg-code | ✅ | built | — | unknown | OK |
| Docs (code_kg) | code_kg-doc | ✅ | built | — | unknown | OK |
| Python source (doc_kg) | doc_kg-code | ✅ (registered) | 0 | 0 | — | ⚠️ UNBUILT |
| Docs (doc_kg) | doc_kg-doc | ✅ | built | — | unknown | OK |
| Python source (proteusPy) | proteusPy-code | ✅ (registered) | 0 | 0 | 2026-03-24 | ⚠️ UNBUILT |
| Docs (proteusPy) | proteusPy-doc | ✅ | built | — | 2026-03-24 | OK |
| Literature (Gutenberg) | gutenberg-*-doc (75 KGs) | ✅ | built | — | 2026-03-30/31 | OK |
| Corpus: KGRAG_repos | corpus | ✅ in CLAUDE.md | — | — | — | ⚠️ VERIFY |
| Corpus: claude_t_self | corpus | ❌ not created | — | — | — | ❌ MISSING |

---

## Phase 7 — Recommendations

| # | Issue | Severity | Remediation |
|---|-------|----------|-------------|
| 1 | `FTreeKG-code` index unbuilt | MEDIUM | `cd /Users/egs/repos/FTreeKG && codekg build --repo .` |
| 2 | `doc_kg-code` index unbuilt | MEDIUM | `cd /Users/egs/repos/doc_kg && codekg build --repo .` |
| 3 | `proteusPy-code` index unbuilt | MEDIUM | `cd /Users/egs/repos/proteusPy && codekg build --repo .` |
| 4 | MetaboKG — no baseline snapshot | HIGH | `kgrag snapshot save` (or metabokg equivalent) from `/Users/egs/repos/Metabo_kg` |
| 5 | `claude_t_self` corpus missing | HIGH | `kgrag corpus create claude_t_self --add claude_t_self` |
| 6 | Version tags `unknown` in registry | LOW | Re-register KGs with version: `kgrag register --repo <path> --version <ver>` |
| 7 | `kgrag_corpus_query` routing gap | HIGH | After fix #5: verify with `kgrag_corpus_query("claude_t_self", "inference optional synthesis")` |
| 8 | KGRAG_repos corpus — verify | MEDIUM | `kgrag corpus info KGRAG_repos` — confirm all 6 KGs are present |
| 9 | AgentKG profile has noise entries | LOW | `agent_kg_prune` — several commitment entries appear to contain raw scraped text |

---

## Summary

| Metric | Value |
|--------|-------|
| KGRAG version | 0.3.6 |
| Total KGs registered | 91 |
| KGs built and healthy | 88 |
| KGs unbuilt | 3 (FTreeKG-code, doc_kg-code, proteusPy-code) |
| MCP servers responding | 7 (codekg, dockg, memorykg, diarykg, metabokg, agent-kg, kgrag) |
| Phase 2 health checks passed | 5/5 |
| Phase 3 cross-domain traversal | 1/2 PASS (claude_t_self corpus missing) |
| Phase 4 identity corpus | GROUNDED — CLAUDE_T_IDENTITY.md indexed |
| Total nodes across stack (active servers) | ~59,000+ |
| Critical gaps | MetaboKG no snapshot; claude_t_self corpus not created; 3 code KGs unbuilt |

### Critical Gaps (Priority Order)

1. **MetaboKG snapshot missing** — no temporal baseline; run snapshot save immediately
2. **`claude_t_self` corpus not created** — `kgrag_corpus_query` always fails for this target
3. **3 code KGs unbuilt** — FTreeKG, doc_kg, proteusPy source queries unavailable

---

*Report generated by Claude_T (Synthetic Intelligence, KnowledgeTree-backed) — 2026-04-15*
