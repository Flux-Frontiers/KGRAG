---
name: kgrag
description: "Claude_T orchestrator skill — complete tool decision tree AND CLI reference for the full KGRAG fleet: PyCodeKG, DocKG, MemoryKG, DiaryKG, FTreeKG, AgentKG, MetaboKG, GutenbergKG, IAKG. Use this skill when working in any KGRAG-enabled repo or when the user asks about code, documents, diary, memory, metabolism, filesystem trees, Gutenberg/IA corpora, or self-knowledge queries — via MCP tools or CLI."
---

# Claude_T KGRAG Orchestrator

Claude_T is a **Synthetic Intelligence** agent. Answers come from KnowledgeTree
traversal. LLM inference is optional — applied only for synthesis against
grounded results.

```
Claude_T = KnowledgeTree traversal  [+ optional LLM synthesis]
```

---

## Fleet Installation

One script installs every adaptor as a `uv tool --editable` global command:

```bash
# Install/refresh the entire fleet
scripts/install-kgs.sh

# Only specific adaptors
scripts/install-kgs.sh doc_kg gutenberg_kg

# Force rebuild of all venvs from scratch
REINSTALL=1 scripts/install-kgs.sh
```

**Adaptors installed** (in order): `doc_kg` → `pycode_kg` → `gutenberg_kg` → `metabo_kg` → `ftree_kg` → `diary_kg` → `memory_kg` → `agent_kg` → `ia_kg` → `kgrag` (with `[all]` extras)

Commands become globally available: `dockg`, `pycodekg`, `gutenkg`, `metabokg`, `ftreekg`, `diarykg`, `memorykg`, `agent-kg`, `iakg`, `kgrag`.

---

## Tool Decision Tree

**Match the query type to the tool — no ambiguity.**

| Query Type | Primary Tool | Never Use Instead |
|---|---|---|
| Code structure, callers, imports | `mcp__pycodekg__*` | grep, Read |
| Unstructured doc content | `mcp__dockg__*` | Grep, Read |
| Claude_T self-knowledge / stack | `mcp__memorykg__*` (corpus: `claude_t_self`) | weights, memory |
| Diary / Pepys narrative | `mcp__diarykg__*` | Read, Grep |
| Session history / self-memory | `mcp__agent-kg__*` | context window |
| Metabolic pathways | `mcp__metabokg__*` | inference |
| Cross-domain / "any" | `mcp__kgrag__kgrag_corpus_query` | multiple separate queries |

---

## PyCodeKG — code knowledge graph

**Repo:** `../pycode_kg` | **Index:** `.pycodekg/` | **Command:** `pycodekg`

### MCP tools — `mcp__pycodekg__*`

```
graph_stats()                              ← start every session
pack_snippets(q, k=8, hop=1, context=5)   ← returns source code
query_codebase(q, k=8, hop=1)             ← returns ranked node list
callers(node_id)                           ← who calls this?  NEVER grep
get_node(node_id, include_edges=True)      ← node detail
list_nodes(module_path, kind)              ← all nodes in a module
explain(node_id)                           ← role + callers + callees
centrality(top=20)                         ← most important nodes
bridge_centrality()                        ← architectural bridges
framework_nodes()                          ← most depended-upon
analyze_repo()                             ← full analysis
snapshot_list() / snapshot_show(key) / snapshot_diff(key_a, key_b)
```

**Node ID format:** `<kind>:<module_path>:<qualname>`

### CLI

```bash
# One-shot setup (download model + full build + snapshot)
pycodekg init --repo .

# Build / update
pycodekg build --repo .                       # full wipe-and-rebuild
pycodekg update --repo .                      # incremental upsert
pycodekg build-sqlite --repo .                # SQLite only
pycodekg build-lancedb --repo .               # LanceDB only

# Query
pycodekg query "authentication flow" --k 8 --hop 1
pycodekg pack  "JWT token validation" --k 6

# Analysis
pycodekg analyze --repo .
pycodekg architecture --repo .
pycodekg centrality --top 20

# Snapshots
pycodekg snapshot save 1.0.0
pycodekg snapshot list
pycodekg snapshot show <id>
pycodekg snapshot diff <a> <b>

# Visualization
pycodekg viz           # Streamlit 2-D
pycodekg viz3d         # PyVista 3-D
pycodekg viz-timeline  # temporal growth chart

# Explain a node
pycodekg explain "function:src/auth.py:validate_token"

# Hooks
pycodekg install-hooks --repo .

# MCP server (stdio)
pycodekg mcp --repo .
```

---

## DocKG — document knowledge graph

**Repo:** `../doc_kg` | **Index:** `.dockg/` | **Command:** `dockg`

### MCP tools — `mcp__dockg__*`

```
graph_stats()
query_docs(q, k=8, hop=1)                  ← find sections/chunks
pack_docs(q, k=8, hop=1)                   ← markdown text for LLM
get_node(node_id)
```

### CLI

```bash
# Build
dockg build docs                            # full wipe-and-rebuild (default)
dockg build docs --update                   # incremental upsert
dockg build-graph docs                      # SQLite only
dockg build-index                           # LanceDB only

# Query
dockg query "authentication flow"
dockg pack  "JWT token validation"

# Analysis
dockg analyze
dockg semantic-analyze

# Pipeline (deep NLP)
dockg pipeline run   --repo docs --batch 20
dockg pipeline embed --repo docs --workers 4
dockg pipeline manifold

# Snapshots
dockg snapshot save 1.0.0
dockg snapshot list
dockg snapshot show <commit>
dockg snapshot diff <a> <b>

# Visualization + MCP
dockg viz
dockg mcp --repo . --db .dockg/graph.sqlite --lancedb .dockg/lancedb
```

---

## MemoryKG — self-knowledge corpus

**Repo:** `../memory_kg` | **Index:** `.memorykg/` | **Command:** `memorykg`

Claude_T's self-knowledge corpus (`claude_t_self`). Query for stack architecture, tool surfaces, identity, CLI reference.

### MCP tools — `mcp__memorykg__*`

```
graph_stats()
query_docs(q)                              ← search claude_t_self
pack_docs(q)                               ← get grounded text
get_node(node_id)
```

### CLI

```bash
# Build
memorykg build <corpus_dir>                # full rebuild
memorykg build <corpus_dir> --update       # incremental
memorykg build-graph <corpus_dir>
memorykg build-index

# Query
memorykg query "Claude_T identity"
memorykg pack  "tool decision tree"

# Analysis
memorykg analyze
memorykg semantic-analyze

# Pipeline
memorykg pipeline run   --repo docs --batch 20
memorykg pipeline embed --repo docs --workers 4

# Snapshots + visualization
memorykg snapshot save 1.0.0
memorykg snapshot list
memorykg snapshot show <id>
memorykg snapshot diff <a> <b>
memorykg viz

# MCP server
memorykg mcp --repo . --db .memorykg/graph.sqlite --lancedb .memorykg/lancedb
```

**Rebuild after any `docs/` or identity doc change:**
```bash
memorykg-build --repo /Users/egs/repos/kgrag \
  --exclude-dir articles --exclude-dir books --exclude-dir pepys \
  --exclude-dir patents --exclude-dir src --exclude-dir tests \
  --exclude-dir dist --exclude-dir .venv --exclude-dir scripts \
  --exclude-dir bundles
```

---

## DiaryKG — diary / journal corpus

**Repo:** `../diary_kg` | **Index:** `.diarykg/` | **Commands:** `diarykg`, `diary-transformer`, `diary-embedder`

Samuel Pepys diary, 1660–1669. 41,544 nodes, 581,630 edges.

### MCP tools — `mcp__diarykg__*`

```
diary_stats()                              ← corpus overview
query_diary(q, k=8)                        ← semantic search
pack_diary(q, k=8)                         ← passage text
```

### CLI

```bash
# Build
diarykg build --repo .                     # ingest diary → SQLite + LanceDB
diarykg reindex                            # rebuild index from existing data

# Query
diarykg query "plague London 1665"
diarykg pack  "Samuel Pepys theatre"

# Metadata
diarykg status
diarykg analyze

# Snapshots
diarykg snapshot save
diarykg snapshot list
diarykg snapshot show <id>
diarykg snapshot diff <a> <b>

# NLP transformation pipeline
diary-transformer --help
diary-embedder --help

# Hooks + MCP
diarykg install-hooks
diarykg-mcp
```

---

## FTreeKG — filesystem tree knowledge graph

**Repo:** `../ftree_kg` | **Index:** `.filetreekg/` | **Command:** `ftreekg`

Indexes filesystem trees (files, dirs, symlinks) with metadata into a queryable KG. Useful for "what's in this repo?", CI-change detection, and cross-repo filesystem comparisons.

### CLI (FTreeKG has no MCP server — CLI only)

```bash
# Build
ftreekg build --repo .                     # full wipe-and-rebuild
ftreekg build --repo . --no-wipe           # incremental merge
ftreekg build --repo . --include-dir src --exclude-dir .venv

# Query
ftreekg query "Python config files" --k 8
ftreekg pack  "test helpers"

# Analysis + status
ftreekg analyze --repo .
ftreekg status --repo .

# Snapshots
ftreekg snapshot save
ftreekg snapshot list
ftreekg snapshot show <id>
ftreekg snapshot diff <a> <b>
ftreekg snapshot prune                     # remove vestigial snapshots

# Hooks
ftreekg install-hooks
```

**Key options:** `--repo DIR`, `--db PATH`, `--lancedb PATH`, `--model TEXT`, `--include-dir` / `--exclude-dir` (repeatable), `--no-wipe`

---

## AgentKG — conversational memory graph

**Repo:** `../agent_kg` | **Index:** `.agentkg/` | **Command:** `agent-kg`

Session history and self-memory. Answer "what have I worked on?" by traversal.

### MCP tools — `mcp__agent-kg__*`

```
agent_kg_stats()                           ← session count, entity graph
agent_kg_topics()                          ← topic distribution
agent_kg_profile()                         ← evolving identity
agent_kg_query(q)                          ← semantic search over history
agent_kg_analyze()
agent_kg_pack()
```

### CLI

```bash
# Ingest + query
agent-kg ingest "text" --role user|assistant [--no-embed]
agent-kg query "topic" --k 10 [--include-profile]
agent-kg assemble "question" --budget 4000

# Status + analysis
agent-kg stats
agent-kg analyze
agent-kg sessions

# Profile (identity, education, preferences)
agent-kg profile
agent-kg profile-set --name "Eric Suchanek" --email eric@example.com
agent-kg profile-set --preference "concise" --commitment "always write tests"
agent-kg profile-set --expertise "Python, SQLite" --interest "knowledge graphs"
agent-kg profile-remove --preference "verbose"

# Onboarding interview
agent-kg onboard [--update] [--skip-optional]

# Maintenance
agent-kg snapshot [--label "session-end"]
agent-kg prune --window 20 [--force]
agent-kg wipe --local [--yes]
agent-kg wipe --global [--yes]

# Visualization + MCP
agent-kg viz [--agent] [--profile] [--html] [--serve]
agent-kg mcp
agent-kg install-hooks
```

**Profile path:** `~/.kgrag/profiles/<person_id>/userprofile.sqlite` (global, repo-independent)

---

## MetaboKG — metabolic pathway knowledge graph

**Repo:** `../metabo_kg` | **Index:** `.metabokg/` | **Commands:** `metabokg`, `metabokg-*`

### MCP tools — `mcp__metabokg__*`

```
query_pathway(q)                           ← find pathways
get_compound(id) / get_reaction(id)
find_path(from_compound, to_compound)
pack(q)                                    ← context-rich Markdown
seed_kinetics()                            ← MUST call before simulation
simulate_fba() / simulate_ode() / simulate_whatif(...)
get_kinetic_params(reaction_id)
snapshot_list() / snapshot_show(key) / snapshot_diff(key_a, key_b)
```

### CLI

```bash
# First-time setup (all corpora + seed kinetics)
metabokg-init
metabokg-init --check                      # status only
metabokg-init --corpus hsa                 # single corpus

# Build / update
metabokg-build --data ./data/hsa_pathways  # full rebuild
metabokg-build --data ./data/hsa_pathways --no-wipe
metabokg-update --data ./data/hsa_pathways # incremental
metabokg-enrich --db <path>.sqlite         # re-run enrichment only

# Query
metabokg-query "glycolysis pyruvate" --k 8 --hop 1
metabokg-pack  "fatty acid beta oxidation"

# Analysis
metabokg-analyze
metabokg-analyze-basic
metabokg-info

# Simulation
metabokg-simulate fba
metabokg-simulate ode
metabokg-simulate whatif
metabokg-simulate seed        # seed kinetic params (human)
metabokg-simulate seed-cho    # seed 35 CHO-specific params

# Snapshots + visualization
metabokg-snapshot save 0.8.1
metabokg-snapshot list
metabokg-snapshot show <id>
metabokg-snapshot diff <a> <b>
metabokg-viz    [--port 8500]
metabokg-viz3d  [--layout allium|cake]

# MCP server
metabokg-mcp --repo . --db data/hsa_pathways/.metabokg/hsa.sqlite
```

> ODE: always use `BDF` (default). **Never `RK45`** — metabolic networks are stiff.

---

## GutenbergKG — Project Gutenberg + Internet Archive corpus

**Repo:** `../gutenberg_kg` | **Corpus:** `corpus/` | **Command:** `gutenkg`

DocKG-backed text corpus for classic literature. Each book gets its own `.dockg/` index.

### CLI

```bash
# Download books
gutenkg download book 2701 --genre american-literature
gutenkg download catalog scripts/catalogs/philosophy.txt --genre philosophy
gutenkg download search --author "Herman Melville"
gutenkg download fetch-genre <genre> [--query "..."]
gutenkg download survey [--genre <g>]

# Internet Archive books
gutenkg ia download <ia-identifier> --genre <genre>
gutenkg ia catalog <file> --genre <genre>
gutenkg ia search "query"
gutenkg ia survey [--genre <g>]

# Genre management
gutenkg genres init
gutenkg genres add <name> --source gutenberg|ia
gutenkg genres list
gutenkg list-genres

# Build DocKG indices + register with KGRAG
gutenkg ingest [--genre <g>] [--force-build] [--force-register] [--push]

# After fresh clone (indices are gitignored)
gutenkg rebuild-indices
gutenkg rebuild-indices --genre philosophy

# Status + author index
gutenkg status
gutenkg status --json
gutenkg authors [--refresh]

# Snapshots
gutenkg snapshot save
gutenkg snapshot list
gutenkg snapshot show
gutenkg snapshot diff

# Visualization
gutenkg viz3d
gutenkg viz-timeline [--type 2d|3d]
```

**Standard batch workflow:**
```bash
gutenkg download catalog scripts/catalogs/philosophy.txt --genre philosophy
gutenkg ingest --genre philosophy
gutenkg authors
gutenkg snapshot save
git add corpus/philosophy/ && git commit -m "feat: add philosophy batch"
```

---

## IAKG — Internet Archive knowledge graph

**Repo:** `../ia_kg` | **Corpus:** `corpus/` | **Command:** `iakg`

Lightweight IA downloader that builds DocKG indices and registers them with KGRAG.

### CLI

```bash
# Download
iakg download book <ia-identifier> [--genre <g>] [--force]
iakg download catalog <file>  [--genre <g>]
iakg download search "query"
iakg download survey [--genre <g>]

# Build + register
iakg ingest [--genre <g>] [--force-build] [--force-register] [--push] [--dry-run]
iakg ingest --list-genres
```

---

## KGRAG Federated — `mcp__kgrag__*`

Cross-domain queries spanning multiple KGs simultaneously.

### MCP tools

```
kgrag_query(q)                             ← all registered KGs
kgrag_pack(q)                              ← code + doc snippets
kgrag_corpus_query(corpus, q)             ← named corpus
kgrag_stats() / kgrag_list() / kgrag_info(name)
```

**Corpus management:**
```
kgrag_corpus_create / add / remove / delete / info / list / query / pack
```

### CLI

```bash
kgrag query "authentication flow"           # federated across all KGs
kgrag pack  "token validation"
kgrag list                                  # list registered KGs
kgrag info <name>                           # KG details
kgrag stats                                 # overall counts
kgrag corpus list
kgrag corpus create <name>
kgrag corpus add <name> <kg-name>
kgrag corpus query <name> "query"
```

---

## Epistemic Contract

1. **Graph-First** — traverse before composing any answer
2. **Inference is optional** — graph results ARE the answer; synthesis only when narration needed
3. **Cite nodes** — every fact traces to a node ID and file path
4. **Report gaps** — missing nodes → "graph has no coverage here", never fill with inference
5. **Self-knowledge via AgentKG** — "what have I worked on?" goes to `agent_kg_query`, not context

---

## Forbidden Patterns

```
❌ grep for callers             →  ✓ callers(node_id)
❌ Read file for understanding  →  ✓ pack_snippets(q) first
❌ Infer answer when tool exists →  ✓ traverse first
❌ Fill graph gap with inference →  ✓ report the gap
❌ Reconstruct history from context → ✓ agent_kg_query(q)
❌ Web search for metabolic data →  ✓ metabokg query/pack first
```

---

## Active Index Paths

| KG | SQLite | Notes |
|---|---|---|
| pycodekg | `kgrag/.pycodekg/graph.sqlite` | kgrag repo |
| dockg | `kgrag/.dockg/graph.sqlite` | kgrag repo |
| memorykg | `kgrag/.memorykg/graph.sqlite` | `claude_t_self` corpus |
| diarykg | `diary_kg/.diarykg/graph.sqlite` | Pepys 1660–1669 |
| ftreekg | `<repo>/.filetreekg/graph.sqlite` | per-repo filesystem index |
| metabokg-hsa | `metabo_kg/data/hsa_pathways/.metabokg/hsa.sqlite` | 369 human pathways |
| metabokg-cge | `metabo_kg/data/cge_pathways/.metabokg/cge.sqlite` | 366 CHO pathways |
| metabokg-icho | `metabo_kg/data/icho_model/.metabokg/icho.sqlite` | iCHO2441 GEM |
| agentkg | `kgrag/.agentkg/` | private, gitignored |
| gutenkg | `corpus/<genre>/<book>/.dockg/graph.sqlite` | per-book DocKG |
