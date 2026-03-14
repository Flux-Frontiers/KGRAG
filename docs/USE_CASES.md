# KGRAG Use Cases: Dev Team Workflows

*Grounded in live queries against the KGRAG codebase itself.*

> **Key fact:** The entire analysis pipeline — build, query, analyze, visualize —
> runs **with zero inference**. No LLM API calls. No token costs. No network
> round-trips after the initial model download. Results are deterministic,
> instant, and completely private. Your code never leaves your machine.

---

## CodeKG Use Cases

CodeKG builds a hybrid structural + semantic knowledge graph from Python source code. The SQLite graph captures every function, class, method, module, call relationship, import, and inheritance edge. LanceDB holds the semantic embeddings. Together they answer questions that previously required reading the code — or asking a senior engineer.

**Graph stats on the KGRAG repo itself (built in 29 seconds):**
```
nodes    1,567   (22 modules, 13 classes, 39 functions, 56 methods, 1,437 symbols)
edges    1,858   (513 CALLS, 568 ATTR_ACCESS, 176 IMPORTS, 108 CONTAINS, 6 INHERITS)
indexed    130   semantic nodes embedded at dim=384
```

---

### Use Case 1: Onboarding — "How does this system actually work?"

A new engineer joins the team. The codebase has 40+ modules, 1,500+ nodes. Reading it top-to-bottom would take days.

**Day 1, first 30 minutes:**

```bash
# What are the most important things in this codebase?
codekg centrality

Rank  Score     Kind      Name         Inbound  XMod  Module
----  --------  --------  -----------  -------  ----  --------------------------
1     0.056306  function  cli          9        8     src/kg_rag/cli/group.py
7     0.036205  method    get          23       19    src/kg_rag/registry.py
8     0.035422  class     KGEntry      15       14    src/kg_rag/primitives.py
9     0.033920  class     KGKind       16       15    src/kg_rag/primitives.py
11    0.013345  class     KGRegistry   14       13    src/kg_rag/registry.py
15    0.012039  class     KGAdapter    9        8     src/kg_rag/adapters/base.py
16    0.011907  class     KGRAG        9        8     src/kg_rag/orchestrator.py
```

In 30 seconds, the new engineer knows: `KGRegistry.get()` is the most-called method in the system (22 callers, 19 cross-module). `KGEntry` and `KGKind` are the core data primitives. `KGAdapter` is the extension point. `KGRAG` is the top-level orchestrator. This is the skeleton of the system — no code read.

```bash
# What is the federation system and how does it work?
codekg query "federated query orchestration"

module   src/kg_rag/orchestrator.py      orchestrator
method   src/kg_rag/orchestrator.py      KGRAG.query      — Federated query across all KGs
method   src/kg_rag/orchestrator.py      KGRAG._get_adapter
method   src/kg_rag/orchestrator.py      KGRAG._resolve_entries — Return filtered registry entries
class    src/kg_rag/orchestrator.py      KGRAG            — Cross-KG orchestrator

EDGES (within returned set):
  KGRAG.query -[CALLS]-> KGRAG._get_adapter
  KGRAG.query -[CALLS]-> KGRAG._resolve_entries
  orchestrator.py -[CONTAINS]-> KGRAG
```

The new engineer now sees exactly which file, which class, and which methods implement federation — with the call graph shown. They can navigate directly to `src/kg_rag/orchestrator.py` and read precisely the right 60 lines.

```bash
# Give me code snippets to read, not just names
codekg pack "how does the KG adapter get loaded and cached"
```

Output includes the actual source of `KGAdapter` (abstract base, lines 15–55), `make_adapter` factory, and `KGRAG._get_adapter` — the three pieces needed to understand the plugin system — with file paths and line numbers.

**Time to productive understanding: 2–3 hours instead of 2–3 days.**

---

### Use Case 2: Code Review — Impact Analysis Before Merging

A PR changes `KGRegistry.get()`. Before merging, the reviewer needs to know: what calls this? What breaks?

```bash
codekg query "registry get lookup"

# Results show 22 callers including:
method   KGRegistry.get          — the method itself
method   KGRAG._get_adapter      — uses get() to load adapter
method   KGRAG._resolve_entries  — uses get() to check entries
function cmd_registry.info       — uses get() for CLI output
function cmd_registry.status     — uses get() for health check
function _tab_registry           — uses get() in Streamlit UI

EDGES:
  KGRAG._get_adapter -[CALLS]-> KGRegistry.get
  cmd_registry.status -[CALLS]-> KGRegistry.get
  _tab_registry -[CALLS]-> KGRegistry.get
  ... (19 more cross-module callers)
```

The reviewer immediately sees the blast radius: 22 callers across 19 modules. The MCP server, CLI, Streamlit app, and orchestrator all depend on this method. A signature change requires coordinated updates in all four subsystems.

**Without CodeKG:** the reviewer reads diffs, searches the codebase manually, hopes they found everything.
**With CodeKG:** the full call graph is computed in under a second, deterministically.

```bash
# Fan-in analysis — what's most fragile to change?
codekg analyze

Most Called Functions (Fan-In):
  get        22 callers
  list        9 callers
  stats       8 callers
  KGRegistry  8 callers
  from_str    7 callers
  pack        6 callers
```

Any change to `get`, `list`, or `stats` on `KGRegistry` requires reviewing all callers. CodeKG makes this a 10-second lookup rather than a manual grep-and-hope exercise.

---

### Use Case 3: Architectural Review — "Is the system healthy?"

Monthly architecture review. Engineering lead wants a full structural health report without scheduling 2 hours of meetings.

```bash
codekg analyze
# Writes to analysis/KGRAG_analysis_20260314.md

✓ Baseline metrics:      1,567 nodes, 1,858 edges
✓ CodeRank computed:     top node _row_to_entry @ 0.001735
✓ Fan-in analysis:       get() has 22 callers — highest coupling point
✓ Fan-out analysis:      1 high-fanout function identified
✓ Public APIs:           22 public functions documented
✓ Docstring coverage:    78.5% (102/130 nodes)
✓ Inheritance:           5 classes, max depth 1, 1 multiple-inheritance, 0 diamond
✓ Module coupling:       22 modules analyzed
✓ Key call chains:       5 identified
✓ Snapshot history:      10 historical snapshots loaded

⚠ Issues Found:
  ⚠ Moderate docstring coverage (78.5%) — semantic retrieval degraded for
    undocumented nodes
  ⚠ 1 orphaned function (main) — consider archiving or documenting
```

The full report (written to a Markdown file) includes: CodeRank top-25 ranking, concern-based hybrid analysis across 5 architectural concerns, module coupling matrix, inheritance diagram, public API inventory, and docstring coverage breakdown.

**This replaces an architecture review meeting.** The report is reproducible, versioned, and can be diffed against the previous month's snapshot.

```bash
# Track architecture evolution across commits
codekg viz-timeline
# Shows: node count, edge count, docstring coverage, top centrality nodes
# plotted across the last 10 commits
```

---

### Use Case 4: Debugging — "Where is this behavior implemented?"

A bug report: "The adapter isn't loading when the KG library is missing." The engineer has never worked in this area.

```bash
codekg query "adapter loading library not installed graceful fallback"

method   CodeKGAdapter.is_available  — Return True if code_kg is installed and DB exists
method   MetaKGAdapter.is_available  — Return True if metakg is installed and DB is built
method   KGAdapter.is_available      — Return True if underlying KG library installed

EDGES:
  KGRAG._get_adapter -[CALLS]-> CodeKGAdapter.is_available
  KGRAG._get_adapter -[CALLS]-> MetaKGAdapter.is_available
```

Two exact files, four exact methods. Navigate to `src/kg_rag/orchestrator.py:KGRAG._get_adapter` and `src/kg_rag/adapters/codekg_adapter.py:CodeKGAdapter.is_available`. Bug found and fixed in minutes.

---

### Use Case 5: Refactoring Safety — Before Touching Shared Infrastructure

A senior engineer wants to change the `KGEntry` dataclass — add a field, rename one.

```bash
codekg query "KGEntry data model construction"

class    KGEntry           — core registry entry dataclass
method   KGEntry.is_built  — True if at least one DB exists
method   KGEntry.label     — human display label
method   KGRegistry._row_to_entry  — constructs KGEntry from SQLite row

EDGES:
  mod:registry.py -[CONTAINS]-> KGRegistry._row_to_entry
  # 15 cross-module callers of KGEntry shown
```

Before making any change: the engineer knows `_row_to_entry` is the only factory, `is_built` and `label` are the two derived properties, and 15 callers across 14 modules will need to be checked. The refactoring checklist writes itself.

---

### Use Case 6: New Feature — Finding Where to Plug In

A developer wants to add a new CLI subcommand. Where does new code go? What patterns to follow?

```bash
codekg query "CLI command registration pattern"

function  cli              — root CLI group (src/kg_rag/cli/group.py)
function  query            — query subcommand (src/kg_rag/cli/cmd_query.py)
function  register         — register subcommand (src/kg_rag/cli/cmd_registry.py)
function  mcp              — mcp subcommand (src/kg_rag/cli/cmd_mcp.py)

EDGES:
  mod:cli/main.py -[IMPORTS]-> fn:group.cli
  mod:cli/cmd_query.py -[CONTAINS]-> fn:query
  mod:cli/cmd_registry.py -[CONTAINS]-> fn:register
```

The engineer sees the pattern: one file per command group in `src/kg_rag/cli/`, each containing a Click-decorated function, all imported into `main.py`. Three files to look at, one pattern to copy. They're writing new code in 10 minutes rather than reading every existing command.

---

## DocKG Use Cases

DocKG builds a semantically searchable knowledge graph from Markdown and text files. It extracts document structure (sections, chunks), semantic nodes (topics, entities, keywords), and relationship edges (CONTAINS, NEXT, REFERENCES, SIMILAR_TO, CO_OCCURS_WITH, HAS_TOPIC, HAS_KEYWORD, MENTIONS_ENTITY).

**Graph stats on the KGRAG docs corpus (built in ~60 seconds):**
```
nodes    2,106   (427 chunks, 341 sections, 12 documents, 534 entities,
                  508 keywords, 284 topics)
edges   13,671   (9,162 CO_OCCURS_WITH, 1,547 HAS_KEYWORD, 1,523 MENTIONS_ENTITY,
                  419 HAS_TOPIC, 768 CONTAINS, 129 SIMILAR_TO, 47 REFERENCES, 76 NEXT)
indexed  2,106   semantic nodes at dim=768
coverage  97.7%  topic coverage, 70.5% entity coverage
```

---

### Use Case 1: Onboarding — "How do I get started?"

A new user has just installed KGRAG. They ask a natural-language question:

```bash
dockg query "how to install and configure KGRAG"

[section]  docs/README.md         — Path 2: Complete Setup
[chunk]    docs/README.md         — 1. Read VISION.md — understand the philosophy
                                   2. Follow INSTALLATION.md — step by step
                                   3. Set up MCP for Claude Code
                                   4. Try workflows in USAGE.md
                                   Time: 30 minutes

[section]  docs/INSTALLATION.md  — Quick Install
[chunk]    docs/INSTALLATION.md  — pip install 'kg-rag @ git+...'

[chunk]    docs/README.md         — Path 3: Mastery
                                   Time: 2 hours
```

The corpus serves as a structured knowledge base that answers natural language questions with exact document sections. New users self-serve — they don't need to read every doc or ask a teammate.

---

### Use Case 2: Documentation Audit — "Is our docs coverage complete?"

A technical writer or engineering lead wants to understand documentation health:

```bash
dockg analyze

Metric           Value
────────────────────────
Total nodes      2,106
Total edges     13,671
Topic coverage   97.7%
Entity coverage  70.5%
Keyword coverage 97.7%
```

97.7% topic coverage means nearly every chunk has been categorized into a searchable topic. 70.5% entity coverage identifies a gap — nearly a third of chunks don't mention recognized named entities. This flags sections that may be too abstract or poorly cross-referenced.

```bash
dockg query "troubleshooting common errors"

[chunk]  docs/TROUBLESHOOTING.md  — "Registry not loading"
[chunk]  docs/TROUBLESHOOTING.md  — "MCP tools fail" with errors
[chunk]  docs/TROUBLESHOOTING.md  — "No KGs registered" or empty registry
[chunk]  docs/TROUBLESHOOTING.md  — "Registry corrupted" or database errors

EDGES:
  chunk:TROUBLESHOOTING.md:0005 -[SIMILAR_TO]-> chunk:TROUBLESHOOTING.md:0008
  chunk:TROUBLESHOOTING.md:0019 -[NEXT]-> chunk:TROUBLESHOOTING.md:0020
```

The SIMILAR_TO edges reveal semantic duplicates — two troubleshooting entries that cover nearly the same ground. The technical writer merges them. **DocKG replaces the manual doc review.**

---

### Use Case 3: Knowledge Base Search — "What did we decide about X?"

A team uses Markdown files for RFCs, ADRs (Architecture Decision Records), and design docs. Over time, these accumulate. Finding a specific decision requires searching across dozens of files.

```bash
dockg query "why does the adapter use graceful degradation not strict mode"

[chunk]  docs/VISION.md  — Resilience: Optional KG libraries (missing libraries
                           don't break KGRAG). Graceful degradation (unavailable
                           KGs are skipped, not fatal). Clear error messages.

[chunk]  docs/USAGE.md   — strict mode: raises ImportError if KG library missing
```

The exact design rationale — stored in VISION.md — is surfaced in under a second. No Confluence search, no Slack archaeology, no asking the original author.

---

### Use Case 4: Cross-Document Discovery — "What topics are related?"

A developer is working on MCP integration and wants to know what documentation sections are semantically related.

```bash
dockg query "MCP server agent integration"

[entity]   MCP
[topic]    topic:registry_mcp      — registry, mcp
[chunk]    docs/MCP.md             — Starting the Server
[chunk]    docs/MCP.md             — kgrag_stats (tool documentation)
[chunk]    docs/INSTALLATION.md    — MCP configuration section
[chunk]    docs/TROUBLESHOOTING.md — "MCP tools fail" with errors

CO_OCCURS_WITH edges:
  entity:registry -[CO_OCCURS_WITH]-> topic:topic-registry-mcp
  entity:mcp -[CO_OCCURS_WITH]-> entity:registry
```

The CO_OCCURS_WITH and HAS_TOPIC edges reveal that MCP always co-occurs with registry concepts — useful signal for a developer writing MCP documentation: they should cross-reference the registry docs.

---

### Use Case 5: Support & Runbooks — "Our system is down, what do we do?"

An on-call engineer gets paged at 2am. The system shows "Registry not loading."

```bash
dockg query "registry not loading database error fix"

[section]  docs/TROUBLESHOOTING.md  — "Registry not loading"
[chunk]    docs/TROUBLESHOOTING.md  — Symptoms: ...
[chunk]    docs/TROUBLESHOOTING.md  — Should match: echo $KGRAG_REGISTRY
[chunk]    docs/TROUBLESHOOTING.md  — Fix: ...
```

The runbook surfaces immediately. No fumbling through a wiki, no waking up a senior engineer. **DocKG turns documentation into a structured, queryable on-call assistant.**

---

### Use Case 6: Compliance & Audit — "Show me everything about data retention"

A compliance officer needs to verify that data handling policies are documented consistently across all specs.

```bash
dockg query "data privacy local storage no data transmitted"

[chunk]  docs/PRODUCT_MODEL.md  — Full data sovereignty: no data leaves the
                                  customer's environment
[chunk]  docs/PRODUCT_MODEL.md  — Optional telemetry is limited to anonymized
                                  usage metrics ... opt-in
[chunk]  docs/INSTALLATION.md   — All databases are local filesystem artifacts
```

Every privacy-relevant statement across all documentation files is surfaced and cross-referenced. The compliance officer can verify consistency without reading every document manually.

---

## Combined CodeKG + DocKG: Federated Use Cases

The real power emerges when both graphs are registered and queried together via `kgrag`.

### Use Case: "Understand a feature end-to-end"

A developer needs to understand how the MCP server works — from the architecture concept through to the implementation.

```bash
# Register both KGs (one-time setup)
kgrag register my-kgrag --kind code --repo /path/to/KGRAG
kgrag register kgrag-docs --kind doc  --repo /path/to/KGRAG

# Single query hits both simultaneously
kgrag query "MCP server tool registration"

[code] src/kg_rag/mcp_server.py     — mcp_server module
[code] src/kg_rag/mcp_server.py     — _make_server() — builds the MCP server instance
[code] src/kg_rag/mcp_server.py     — list_tools() — registers available tools
[code] src/kg_rag/mcp_server.py     — call_tool() — dispatches tool calls
[doc]  docs/MCP.md                  — Starting the Server
[doc]  docs/MCP.md                  — kgrag_stats tool documentation
[doc]  docs/INSTALLATION.md         — MCP configuration section
```

**One query. Code + docs together.** The developer gets the implementation (`_make_server`, `list_tools`, `call_tool` with line numbers) alongside the conceptual documentation (what the tools do, how to configure them). No context switching between code browser and wiki.

```bash
# Extract a snippet pack for an LLM context window
kgrag pack "MCP server tool registration" --out mcp_context.md
```

The pack includes actual source code with line numbers plus the relevant documentation sections, formatted for direct pasting into an LLM prompt — or for a code review document.

---

### Use Case: "New team member — complete system orientation"

Week 1, day 1. The engineering manager runs a single command:

```bash
kgrag init /path/to/repo   # builds CodeKG + DocKG, registers both

kgrag query "system architecture overview"
# → architecture documentation + orchestrator/registry code side by side

kgrag query "how to add a new feature"
# → contribution guide + relevant code patterns

kgrag query "what tests exist and how to run them"
# → test documentation + test file structure from CodeKG
```

The new hire spends day 1 with `kgrag query` as their guide. By end of day they have navigated the full system — code structure, architectural intent, operational patterns — without a single "bother the senior engineer" moment.

---

## MetaKG Use Cases

MetaKG demonstrates KGRAG's domain-agnostic federation with biochemical pathway data. The same adapter pattern that works for code and documentation works for any structured domain knowledge.

### Use Case 1: Scientific Literature + Analysis Code Together

A computational biologist is investigating NADH-dependent reactions. Their team has:
- A Python codebase implementing metabolic simulations
- Research documentation describing the biological context
- MetaKG indexed from pathway databases (KEGG, BiGG, Reactome)

```bash
kgrag query "NADH electron transport glycolysis kinetics"

[code]  analysis/glycolysis.py     — simulate_glycolysis() — implements ODE model
[code]  analysis/electron_chain.py — nadh_flux_rate() — computes NADH flux
[doc]   papers/glycolysis_review.md — NADH regeneration under anaerobic conditions
[meta]  KEGG:M00001                — Glycolysis/Gluconeogenesis pathway
[meta]  KEGG:R00658                — Pyruvate kinase reaction (NADH-producing step)
```

**A single query returns: the code implementing the model, the paper describing the biology, and the pathway database nodes defining the reactions.** This cross-domain retrieval is impossible with any single-domain search tool.

### Use Case 2: Drug Target Discovery

A pharma research team queries across chemical compound databases, protein interaction graphs, and clinical trial documentation simultaneously — all indexed as separate MetaKG, DocKG, and CodeKG instances, all federated under KGRAG.

```bash
kgrag query "BRAF inhibitor resistance mechanism"
# → returns: resistance pathway nodes (MetaKG), clinical trial results (DocKG),
#            analysis scripts (CodeKG)
```

### Use Case 3: Rapid Pathway Comparison

A researcher needs to compare two metabolic pathways structurally. Previously this required custom code or commercial software.

```bash
metakg query "compare glycolysis gluconeogenesis shared enzymes"
# → shared nodes, divergent branches, regulatory edges — all from graph structure
#    No LLM. No inference. Pure graph traversal.
```

---

## The Zero-Inference Advantage

Every result shown above was produced **without a single LLM call**.

| Traditional RAG | KGRAG |
|----------------|-------|
| Requires inference for entity extraction | AST / parser extracts structure directly |
| Requires inference for relationship detection | Graph edges are computed from source |
| Non-deterministic — same query, different answers | Deterministic — same query, same graph, same ranked results |
| Leaks code/docs to external API | All computation local |
| Costs tokens on every query | Zero inference cost |
| Slow (API latency on every query) | Sub-second after initial build |
| Hallucination risk on code content | Zero hallucination — every result cites source + line number |

**The analysis pipeline (build, analyze, centrality, architecture) is pure computation over the graph.** The only inference involved is the one-time embedding of docstrings at build time — a local model, run once, cached permanently.

The viz interface (`kgrag viz`, `codekg viz`) is a Streamlit app that queries the local SQLite and LanceDB directly. No network calls during interactive exploration.

---

## Workflow Summary by Role

| Role | Primary KG | Top Commands | Time to Value |
|------|-----------|-------------|---------------|
| **New hire** | CodeKG + DocKG | `codekg centrality`, `kgrag query` | Day 1 |
| **Code reviewer** | CodeKG | `codekg query <changed fn>`, fan-in from `analyze` | Per PR, 30 seconds |
| **Tech lead** | CodeKG | `codekg analyze`, `codekg viz-timeline` | Monthly, automated |
| **On-call engineer** | DocKG | `dockg query <symptom>` | Per incident, instant |
| **Technical writer** | DocKG | `dockg analyze`, SIMILAR_TO edges | Monthly audit |
| **Data scientist** | MetaKG + DocKG | `kgrag query <hypothesis>` | Per experiment |
| **Platform engineer** | All three | `kgrag init`, `kgrag mcp`, `kgrag viz` | One-time setup |

---

*For the overall impact vision, see [IMPACT.md](IMPACT.md).*
*For the product and licensing model, see [PRODUCT_MODEL.md](PRODUCT_MODEL.md).*
*For command reference, see [USAGE.md](USAGE.md).*
