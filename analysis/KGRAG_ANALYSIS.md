# KGRAG_ANALYSIS — Claude_T Full Stack Assessment Directive

When invoked, execute this analysis completely and produce a structured
Markdown report in `analysis/kgrag_analysis_<YYYYMMDD>.md`.

---

## Phase 1 — Stack Inventory

For each active MCP server, call the stats tool:

```
codekg:    graph_stats()
dockg:     graph_stats()
memorykg:  graph_stats()
diarykg:   diary_stats()
metabokg:  snapshot_list()
agent-kg:  agent_kg_stats()
kgrag:     kgrag_list() + kgrag_stats()
```

Report: server name, node count, edge count, index path, build date (if available).
Flag any server that returns zero nodes or an error.

---

## Phase 2 — Federated Health Check

Run these known-good queries and verify each returns grounded hits:

| Query | Expected KG | Pass Condition |
|---|---|---|
| `"hybrid semantic graph retrieval"` | codekg | ≥3 chunk hits |
| `"KnowledgeTree traversal epistemic"` | memorykg | ≥3 chunk hits |
| `"Pepys naval fleet battle"` | diarykg | ≥3 entry hits |
| `"metabolic pathway glycolysis"` | metabokg | ≥1 pathway hit |
| `"KGRAG MCP tool surface"` | memorykg/dockg | ≥3 chunk hits |

For each: report hit count, top result title, source file.
Mark PASS / FAIL / NO_COVERAGE.

---

## Phase 3 — Cross-Domain Traversal

Run federated queries that must span ≥2 KGs:

```
kgrag_query("knowledge graph registry federated")
kgrag_corpus_query("claude_t_self", "inference optional synthesis")
```

Verify results include hits from multiple distinct KGs.
Report: which KGs contributed, total hits, any routing gaps.

---

## Phase 4 — Self-Knowledge Probe

```
agent_kg_stats()           → session count, entity count, topic count
agent_kg_topics()          → top 10 topics by frequency
agent_kg_profile()         → current identity summary
memorykg: pack_docs("Claude_T Synthetic Intelligence identity")
```

Report: sessions recorded, top topics, identity summary excerpt,
self-knowledge corpus coverage of identity concepts.

---

## Phase 5 — Gap Analysis

Identify and report:

1. **KGs with zero nodes** — index not built or stale
2. **Registered KGs not reachable** — path missing or MCP server down
3. **Domains with no KG coverage** — e.g. if ftreekg has no MCP
4. **Tools in MCP but missing from skill** — compare active tool list
   to `~/.claude/skills/kgrag/SKILL.md`
5. **MetaboKG snapshot status** — flag if no baseline snapshot exists

---

## Phase 6 — Coverage Matrix

Produce a table:

| Domain | KG | MCP Active | Nodes | Edges | Last Build | Status |
|---|---|---|---|---|---|---|
| Python source | codekg | ✓/✗ | N | N | date | OK/STALE |
| Unstructured docs | dockg | ✓/✗ | N | N | date | OK/STALE |
| Self-knowledge | memorykg | ✓/✗ | N | N | date | OK/STALE |
| Diary narrative | diarykg | ✓/✗ | N | N | date | OK/STALE |
| File tree | ftreekg | ✓/✗ | — | — | — | NO_MCP |
| Session memory | agentkg | ✓/✗ | N | N | live | OK/STALE |
| Metabolic | metabokg | ✓/✗ | N | N | date | OK/STALE |

---

## Phase 7 — Recommendations

For each gap or failure, produce a one-line remediation:

- STALE index → rebuild command
- Missing snapshot → `<tool> snapshot save` command
- NO_MCP → note that CLI-only access is the current state
- Federated routing gap → `kgrag register` command

---

## Output

Write the full report to:
```
analysis/kgrag_analysis_<YYYYMMDD>.md
```

Include:
- Timestamp and KGRAG version at top
- All six phases with pass/fail/gap markers
- Coverage matrix
- Recommendations section
- Summary: total KGs live, total nodes across stack, critical gaps

After writing, rebuild the `claude_t_self` corpus to index the new report:
```bash
memorykg-build --repo /Users/egs/repos/kgrag \
  --exclude-dir articles --exclude-dir books --exclude-dir pepys \
  --exclude-dir patents --exclude-dir src --exclude-dir tests \
  --exclude-dir dist --exclude-dir .venv --exclude-dir scripts \
  --exclude-dir bundles
```
