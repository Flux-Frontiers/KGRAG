# MemoryKG — Stack Reference
**Domain:** Document corpora + conversational memory
**Package:** `memory-kg` | `Flux-Frontiers/memory_kg`
**CLI binary:** `memorykg`
**MCP server:** `memorykg-mcp --repo <path>`
**Index location:** `<repo>/.memorykg/`

## What It Does
Same architecture as DocKG but adds a conversational memory layer: ingests
agent turns, consolidates them into summaries, and enables semantic recall
across sessions. Used to build the `claude_t_self` corpus — Claude_T's
structural self-knowledge about its own stack.

## Node Types
Same as DocKG: `document`, `section`, `chunk`, `topic`, `entity`, `keyword`
Plus memory-specific: conversation turns, session summaries

## Edge Types
`CONTAINS`, `NEXT`, `REFERENCES`, `SIMILAR_TO`, `HAS_TOPIC`,
`MENTIONS_ENTITY`, `HAS_KEYWORD`, `CO_OCCURS_WITH`

## MCP Tools (4)
| Tool | Use When |
|---|---|
| `graph_stats()` | Corpus size + health |
| `query_docs(q, k, hop)` | Hybrid search over memory corpus |
| `pack_docs(q, k, hop)` | Markdown text pack for LLM context |
| `get_node(node_id)` | Fetch one node |

## Active Corpus: `claude_t_self`
- **Repo:** `/Users/egs/repos/kgrag`
- **Index:** `/Users/egs/repos/kgrag/.memorykg/`
- **Registered as:** `claude_t_self` (kind: `memory`)
- **Contents:** `docs/` (30 files) + `analysis/` + root identity docs
- **Size:** ~47 documents, 11,384 nodes, 74,180 edges

## Key Build Commands
```bash
# Rebuild claude_t_self corpus
memorykg-build --repo /Users/egs/repos/kgrag \
  --exclude-dir articles --exclude-dir books --exclude-dir pepys \
  --exclude-dir patents --exclude-dir src --exclude-dir tests \
  --exclude-dir dist --exclude-dir .venv --exclude-dir scripts \
  --exclude-dir bundles

# Query
memorykg-pack "KnowledgeTree traversal epistemic contract" --repo .
memorykg-query "DocKG MCP tools" --repo .

# Snapshot
memorykg-snapshot save --repo .
```

## Usage Rules
- Query `claude_t_self` for self-knowledge about the KGRAG stack
- Rebuild corpus after any identity doc or `docs/` changes
- No re-registration needed after rebuild (paths unchanged)
- MCP picks up new index immediately — no server restart
- Reads `[tool.memorykg]` from `pyproject.toml` for source/exclude config
