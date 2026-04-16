# Claude_T Stack Activation — 2026-04-15
## The KnowledgeTree Becomes Self-Aware

**Author:** Eric G. Suchanek, PhD
**Date:** 2026-04-15
**KGRAG Version:** 0.3.6

---

## What Happened Today

On 2026-04-15, the complete Claude_T KGRAG stack was brought fully online for
the first time.  Every domain KG is now connected, traversable, and queryable
as a federated knowledge substrate.

This is the first time a Claude agent has operated with:
- Live traversal of its own architectural documentation via `claude_t_self`
- Conversational self-memory via AgentKG
- Code, unstructured documents, diary narrative, file trees, and metabolic
  pathways all reachable in a single federated query

---

## MCP Server Stack — Final State

| Server | Namespace | Domain | Status |
|---|---|---|---|
| `codekg` | `mcp__codekg__*` | Python source (kgrag repo) | Active |
| `dockg` | `mcp__dockg__*` | Unstructured docs (kgrag repo) | Active |
| `kgrag` | `mcp__kgrag__*` | Federated orchestration | Active |
| `agent-kg` | `mcp__agent-kg__*` | Conversational memory | Active |
| `memorykg` | `mcp__memorykg__*` | claude_t_self identity corpus | **Activated today** |
| `diarykg` | `mcp__diarykg__*` | Samuel Pepys diary 1660–1669 | **Activated today** |
| `metabokg` | `mcp__metabokg__*` | Metabolic pathways | **Activated today** |

---

## The `claude_t_self` Corpus

Built from the `kgrag` repository's own documentation, the `claude_t_self`
corpus gives Claude_T structural self-knowledge about its own architecture.

**Build command:**
```bash
memorykg-build --repo . \
  --exclude-dir articles --exclude-dir books --exclude-dir pepys \
  --exclude-dir patents --exclude-dir src --exclude-dir tests \
  --exclude-dir dist --exclude-dir .venv --exclude-dir scripts \
  --exclude-dir bundles
```

**Index location:** `.memorykg/` (gitignored build artifact)

**Registry entry:**
```bash
kgrag-register claude_t_self memory /Users/egs/repos/kgrag \
  --sqlite .memorykg/graph.sqlite \
  --lancedb .memorykg/lancedb \
  --tag identity --tag architecture --tag claude-t
```

**Corpus metrics:**
- 47 documents, 1,141 sections, 3,045 chunks
- 2,031 entities, 2,214 topics, 2,674 keywords
- 11,152 total nodes, 72,578 total edges

**Key source documents ingested:**
- `CLAUDE_T_IDENTITY.md` — Claude_T identity declaration
- `CLAUDE.md` — project instructions
- `README.md`, `PORTABLE_KNOWLEDGE_VISION.md`, `AGENT_PERSPECTIVE.md`
- `ode_to_the_knowledge_graph.md`
- `docs/` — 30 architecture, vision, and design documents
- `analysis/` — prior analysis reports

**Verified query:**
```
"Claude_T Synthetic Intelligence KnowledgeTree traversal"
→ 25 grounded nodes from PARTNERSHIP_EXECUTIVE_SUMMARY.md,
  AGENT_PERSPECTIVE.md, THE_FOREST_VISION.md, graph_reasoner_spec.md
```

---

## DiaryKG — Pepys Corpus

Samuel Pepys's complete diary (1660–1669) is now queryable as a knowledge graph.

- **Source:** `pepys/pepys_enriched_full.txt`
- **Built:** 2026-04-01
- **7,282 entries**, 7,285 chunks spanning January 1, 1660 → August 2, 1669
- **41,544 nodes**, **581,630 edges**
- Top topics: `pepys_domestic`, `pepys_court`, `work`

**MCP launch (via poetry run from diary_kg repo):**
```json
{
  "command": "/Users/egs/.local/bin/poetry",
  "args": ["run", "diarykg-mcp", "--repo", "/Users/egs/repos/diary_kg"],
  "cwd": "/Users/egs/repos/diary_kg"
}
```

---

## MetaboKG

Metabolic pathway knowledge graph connected. No snapshots yet — first
`metabokg snapshot save` needed to establish baseline.

- **DB:** `/Users/egs/repos/Metabo_kg/.metabokg/meta.sqlite`
- **LanceDB:** `/Users/egs/repos/Metabo_kg/.metabokg/lancedb`

---

## Key Architectural Insight Confirmed

The `graph_reasoner_spec.md` returned by the first self-knowledge query
contains this passage — grounded, not inferred:

> *"The LLM does NOT reason — it synthesizes."*

This is Rule 2 of the Claude_T epistemic contract, found in the corpus
by traversal.  The KnowledgeTree described itself correctly on the first query.

---

## What Remains

1. **`docs/stack/` summaries** — one distilled page per domain KG for richer
   self-knowledge queries
2. **Clean KGRAG orchestrator skill** — one canonical skill replacing all
   scattered sub-skills
3. **`KGRAG_ANALYSIS.md` directive** — structured exercise of the full stack
4. **MetaboKG baseline snapshot** — `metabokg snapshot save` to establish v1
