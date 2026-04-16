# KGRAG Stack — CLI Reference
## Complete Command Reference for All KG Tools

**Author:** Eric G. Suchanek, PhD
**Date:** 2026-04-15
**Scope:** All CLI tools available in the kgrag `.venv`

This document is part of the `claude_t_self` corpus. Claude_T queries it
instead of running `--help`.

---

## Tool Inventory

| Binary | Package | Primary Use |
|---|---|---|
| `codekg` | `pycode-kg` | Build, query, serve Python code KG |
| `dockg` | `doc-kg` | Build, query, serve unstructured document KG |
| `memorykg` | `memory-kg` | Build, query, serve memory/document KG |
| `diarykg` | `diary-kg` | Build, query, serve diary/journal KG |
| `metabokg` | `metabo-kg` | Build, query, serve metabolic pathway KG |
| `kgrag` | `kg-rag` | Federated registry, cross-KG query, orchestration |
| `agent-kg-mcp` | `agent-kg` | Session memory MCP server (env-configured) |

---

## codekg

**Build** (always wipes; reads `[tool.codekg]` from `pyproject.toml`):
```bash
codekg build --repo .
codekg build --repo /path/to/repo --include-dir src --exclude-dir tests
codekg build --model BAAI/bge-small-en-v1.5 --batch 256
# Key options:
#   --repo DIRECTORY     repo root [default: .]
#   --include-dir TEXT   top-level dirs to index (repeatable)
#   --exclude-dir TEXT   dirs to skip at every depth (repeatable)
#   --db PATH            SQLite path [default: <repo>/.codekg/graph.sqlite]
#   --lancedb PATH       LanceDB path [default: <repo>/.codekg/lancedb]
#   --model TEXT         embedding model [default: BAAI/bge-small-en-v1.5]
#   --batch INTEGER      embedding batch size [default: 256]
#   --kinds TEXT         node kinds [default: module,class,function,method]
#   -v, --verbose        show embedder progress
```

**Incremental update** (upserts changes only):
```bash
codekg update --repo .
```

**MCP server:**
```bash
codekg mcp --repo . --transport stdio
# Key options:
#   --repo DIRECTORY
#   --db PATH
#   --lancedb PATH
#   --model TEXT
#   --transport [stdio|sse]  [default: stdio]
```

**Query / Pack:**
```bash
codekg query "hybrid retrieval semantic graph" --repo . --k 8 --hop 1
codekg pack "registry federated query" --repo . --context 5 --max-lines 200
```

**Analyze / Snapshot:**
```bash
codekg analyze --repo . -o analysis/codekg_analysis.md
codekg snapshot save --repo .
codekg snapshot list --repo .
codekg snapshot diff <key_a> <key_b> --repo .
codekg snapshot show <key> --repo .
```

**MCP tools exposed (17):**
`graph_stats`, `query_codebase`, `pack_snippets`, `get_node`, `list_nodes`,
`callers`, `explain`, `centrality`, `bridge_centrality`, `framework_nodes`,
`rank_nodes`, `query_ranked`, `explain_rank`, `analyze_repo`,
`snapshot_list`, `snapshot_show`, `snapshot_diff`

---

## dockg

**Build** (reads `[tool.dockg]` from `pyproject.toml`):
```bash
dockg build --repo .
dockg build --repo . --exclude-dir bundles --exclude-dir dist
# Key options:
#   --repo DIRECTORY     corpus root [default: .]
#   --sqlite PATH        [default: <repo>/.dockg/graph.sqlite]
#   --lancedb PATH       [default: <repo>/.dockg/lancedb]
#   --model TEXT         [default: all-mpnet-base-v2]
#   --chunk-size INTEGER [default: 512]
#   --chunk-overlap INTEGER [default: 64]
#   --ext TEXT           file extensions (repeatable) [default: .md, .txt]
#   --exclude-dir DIR    (repeatable)
#   --update             incremental — keep existing data
#   --no-similar         skip SIMILAR_TO edge discovery
#   --no-topics / --no-entities / --no-keywords   disable extraction
```

**MCP server:**
```bash
dockg mcp --repo . --transport stdio
```

**Query / Pack:**
```bash
dockg query "knowledge graph retrieval" --repo . --k 8 --hop 1
dockg pack "MCP server tools" --repo . --fmt md --out out.md
```

**Analyze / Snapshot:**
```bash
dockg analyze --repo . -o analysis/dockg_analysis.md
dockg snapshot save --repo .
dockg snapshot list --repo .
dockg snapshot show <key> --repo .
dockg snapshot diff <key_a> <key_b> --repo .
```

**MCP tools exposed (4):**
`graph_stats`, `query_docs`, `pack_docs`, `get_node`

---

## memorykg

**Build** (reads `[tool.memorykg]` from `pyproject.toml`):
```bash
memorykg build --repo .
memorykg-build --repo . --exclude-dir src --exclude-dir tests
# Key options:
#   --repo DIRECTORY     corpus root [default: .]
#   --sqlite PATH        [default: <repo>/.memorykg/graph.sqlite]
#   --lancedb PATH       [default: <repo>/.memorykg/lancedb]
#   --model TEXT         [default: BAAI/bge-small-en-v1.5]
#   --chunk-size INTEGER [default: 512]
#   --chunk-overlap INTEGER [default: 64]
#   --ext TEXT           (repeatable) [default: .md, .txt]
#   --exclude-dir DIR    (repeatable)
#   --update             incremental update
#   --no-similar         skip SIMILAR_TO edge discovery
#   --workers INTEGER    parallel embedding workers [default: 8]
#   --batch INTEGER      embedding batch size [default: 256]
```

**MCP server:**
```bash
memorykg-mcp --repo . --transport stdio
memorykg mcp --repo .
# Key options:
#   --repo REPO
#   --db DB              [default: .memorykg/graph.sqlite]
#   --lancedb LANCEDB    [default: .memorykg/lancedb]
#   --model MODEL        [default: BAAI/bge-small-en-v1.5]
#   --transport {stdio,sse}
```

**Query / Pack:**
```bash
memorykg-query "knowledge graph architecture" --repo . --k 8 --hop 1
memorykg-pack "Claude_T identity" --repo . --fmt md --max-chars 2000
# memorykg-query options:
#   --k INTEGER          top-k semantic hits [default: 8]
#   --hop INTEGER        graph expansion hops [default: 1]
#   --rels TEXT          edge types to expand
#   --max-nodes INTEGER  [default: 25]
# memorykg-pack options:
#   --max-chars INTEGER  per-excerpt limit [default: 2000]
#   --max-nodes INTEGER  total nodes returned
#   --out PATH           output file [default: stdout]
#   --fmt [md|json]      [default: md]
```

**Analyze / Snapshot:**
```bash
memorykg-analyze --repo . -o analysis/memorykg_analysis.md
memorykg-snapshot save --repo .
memorykg-snapshot list --repo .
memorykg-snapshot show <key> --repo .
memorykg-snapshot diff <key_a> <key_b> --repo .
memorykg-snapshot prune --repo .
```

**Install hooks:**
```bash
memorykg install-hooks --repo .
```

**MCP tools exposed (4):**
`graph_stats`, `query_docs`, `pack_docs`, `get_node`

**Active corpus (kgrag repo):**
- Index: `/Users/egs/repos/kgrag/.memorykg/`
- Registered as: `claude_t_self` (kind: `memory`)
- 47 docs, 11,152 nodes, 72,578 edges

---

## diarykg

**Build:**
```bash
diarykg build --repo /path/to/diary_repo --source pepys/pepys_enriched_full.txt
# Key options:
#   --repo DIRECTORY     project root
#   --source TEXT        relative path to diary .txt file
#   --model TEXT         [default: all-mpnet-base-v2]
```

**MCP server** (must run via `poetry run` from diary_kg repo):
```bash
# In .mcp.json:
poetry run diarykg-mcp --repo /Users/egs/repos/diary_kg
# Direct:
diarykg-mcp --repo /Users/egs/repos/diary_kg --transport stdio
# Key options:
#   --repo REPO          project root [default: .]
#   --source SOURCE      relative path to diary .txt source
#   --model MODEL        [default: all-mpnet-base-v2]
#   --transport {stdio,sse}
```

**Query / Pack:**
```bash
diarykg query "naval battle fleet" --repo /Users/egs/repos/diary_kg
diarykg pack "Pepys and the King" --repo /Users/egs/repos/diary_kg
```

**Analyze / Snapshot / Status:**
```bash
diarykg analyze --repo /Users/egs/repos/diary_kg
diarykg status --repo /Users/egs/repos/diary_kg
diarykg snapshot save --repo /Users/egs/repos/diary_kg
diarykg snapshot list --repo /Users/egs/repos/diary_kg
```

**Active corpus:**
- Repo: `/Users/egs/repos/diary_kg`
- Source: `pepys/pepys_enriched_full.txt`
- 7,282 entries, 1660-01-01 → 1669-08-02
- 41,544 nodes, 581,630 edges

**MCP tools exposed (3):**
`diary_stats`, `query_diary`, `pack_diary`

---

## metabokg

**Build:**
```bash
metabokg build --help   # (check for pathway source path args)
metabokg mcp --db /path/to/.metabokg/meta.sqlite --lancedb /path/to/.metabokg/lancedb
# Key MCP options:
#   --db TEXT        [default: .metabokg/meta.sqlite]
#   --lancedb TEXT   [default: .metabokg/lancedb]
#   --model TEXT     [default: all-MiniLM-L6-v2]
#   --transport [stdio|sse]
```

**Simulate:**
```bash
metabokg simulate --help   # FBA, ODE, what-if subcommands
```

**Snapshot:**
```bash
metabokg snapshot save
metabokg snapshot list
metabokg snapshot show <key>
metabokg snapshot diff <key_a> <key_b>
```

**Active corpus:**
- DB: `/Users/egs/repos/Metabo_kg/.metabokg/meta.sqlite`
- LanceDB: `/Users/egs/repos/Metabo_kg/.metabokg/lancedb`
- No snapshots yet (baseline needed)

**MCP tools exposed (11):**
`find_path`, `get_compound`, `get_kinetic_params`, `get_reaction`,
`query_pathway`, `seed_kinetics`, `simulate_fba`, `simulate_ode`,
`simulate_whatif`, `snapshot_diff`, `snapshot_list`, `snapshot_show`

---

## kgrag

**Registry:**
```bash
kgrag list                              # list all registered KGs
kgrag status                            # registry health check
kgrag info <name>                       # detail on one KG
kgrag register <name> <kind> <path>     # kinds: code,doc,meta,diary,verse,memory,agent
kgrag unregister <name>
kgrag scan <directory>                  # auto-discover KG databases

# kgrag-register shorthand:
kgrag-register claude_t_self memory /Users/egs/repos/kgrag \
  --sqlite .memorykg/graph.sqlite \
  --lancedb .memorykg/lancedb \
  --tag identity
```

**Federated query:**
```bash
kgrag query "hybrid semantic graph retrieval"
kgrag pack "KGRAG architecture" --fmt md
kgrag analyze
```

**Corpus management:**
```bash
kgrag corpus list
kgrag corpus info <corpus_name>
kgrag corpus create <name> [--kg <kg_name> ...]
kgrag corpus add <corpus_name> <kg_name>
kgrag corpus remove <corpus_name> <kg_name>
kgrag corpus delete <corpus_name>
kgrag corpus query <corpus_name> "query text"
kgrag corpus pack <corpus_name> "query text"
```

**MCP server:**
```bash
kgrag mcp                               # starts on stdio
kgrag-mcp                               # standalone entry point
```

**Init (auto-detect and register all KGs in a repo):**
```bash
kgrag init --repo .
```

**MCP tools exposed (19):**
`kgrag_query`, `kgrag_pack`, `kgrag_stats`, `kgrag_list`, `kgrag_info`,
`kgrag_corpus_query`, `kgrag_corpus_pack`, `kgrag_corpus_create`,
`kgrag_corpus_add`, `kgrag_corpus_remove`, `kgrag_corpus_delete`,
`kgrag_corpus_info`, `kgrag_corpus_list`,
`kgrag_person_create`, `kgrag_person_add`, `kgrag_person_remove`,
`kgrag_person_delete`, `kgrag_person_info`, `kgrag_person_list`,
`kgrag_person_query`, `kgrag_person_pack`, `kgrag_person_update`

---

## agent-kg-mcp

**Configured entirely via environment variables** (no CLI flags):
```bash
# Launch:
agent-kg-mcp
# Required env:
#   AGENTKG_REPO   path to repo root (AgentKG stores .agentkg/ here)
#   AGENTKG_PERSON person identifier (e.g. "egs")
```

**.mcp.json entry:**
```json
{
  "type": "stdio",
  "command": "agent-kg-mcp",
  "env": {
    "AGENTKG_REPO": ".",
    "AGENTKG_PERSON": "egs"
  }
}
```

**MCP tools exposed (10):**
`agent_kg_ingest`, `agent_kg_query`, `agent_kg_topics`, `agent_kg_stats`,
`agent_kg_profile`, `agent_kg_analyze`, `agent_kg_assemble`,
`agent_kg_pack`, `agent_kg_prune`, `agent_kg_tasks`

---

## Default Index Paths (Convention)

| KG | SQLite | LanceDB |
|---|---|---|
| codekg | `<repo>/.codekg/graph.sqlite` | `<repo>/.codekg/lancedb` |
| dockg | `<repo>/.dockg/graph.sqlite` | `<repo>/.dockg/lancedb` |
| memorykg | `<repo>/.memorykg/graph.sqlite` | `<repo>/.memorykg/lancedb` |
| diarykg | `<repo>/.diarykg/graph.sqlite` | `<repo>/.diarykg/lancedb` |
| metabokg | `<repo>/.metabokg/meta.sqlite` | `<repo>/.metabokg/lancedb` |
| agentkg | `<repo>/.agentkg/` | (internal) |

All dot-directories are gitignored (built artifacts). Snapshots under
`.codekg/snapshots/` and `.dockg/snapshots/` are committed.

---

## Rebuild Sequence (after structural changes)

```bash
# 1. Rebuild code KG (always wipes)
codekg build --repo .

# 2. Rebuild doc KG
dockg build --repo .

# 3. Rebuild memory KG (claude_t_self corpus)
memorykg-build --repo . \
  --exclude-dir articles --exclude-dir books --exclude-dir pepys \
  --exclude-dir patents --exclude-dir src --exclude-dir tests \
  --exclude-dir dist --exclude-dir .venv --exclude-dir scripts \
  --exclude-dir bundles

# 4. Re-register if paths changed
kgrag-register claude_t_self memory /Users/egs/repos/kgrag \
  --sqlite .memorykg/graph.sqlite \
  --lancedb .memorykg/lancedb

# 5. Restart MCP servers (new conversation in Claude Code)
```

---

## Embedding Models

| KG | Default Model | Notes |
|---|---|---|
| codekg | `BAAI/bge-small-en-v1.5` | Fast, code-optimised |
| dockg | `all-mpnet-base-v2` | Semantic quality |
| memorykg | `BAAI/bge-small-en-v1.5` | Fast |
| diarykg | `all-mpnet-base-v2` | Semantic quality |
| metabokg | `all-MiniLM-L6-v2` | Lightweight |

Pre-download for offline use:
```bash
codekg download-model
dockg download-model
memorykg download-model
```
