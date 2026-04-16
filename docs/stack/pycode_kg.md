# PyCodeKG — Stack Reference
**Domain:** Python source code
**Package:** `pycode-kg` | `Flux-Frontiers/pycode_kg`
**CLI binary:** `codekg`
**MCP server:** `codekg mcp --repo <path>`
**Index location:** `<repo>/.codekg/`

## What It Does
Builds a hybrid semantic + structural knowledge graph from a Python codebase.
Extracts every module, class, function, and method as a node. Edges encode
CALLS, IMPORTS, CONTAINS, and INHERITS relationships. Hybrid retrieval: vector
similarity seeds, graph hop expansion ranks.

## Node Types
| Kind | Description |
|---|---|
| `module` | Python file (`*.py`) |
| `class` | Class definition |
| `function` | Top-level function |
| `method` | Class method |
| `sym:*` | Symbol stubs (imports, unresolved references) |

## Edge Types
`CALLS`, `IMPORTS`, `CONTAINS`, `INHERITS`

## MCP Tools (17)
| Tool | Use When |
|---|---|
| `graph_stats()` | First call in any session — size/shape of codebase |
| `query_codebase(q, k, hop, rels)` | Find code by description |
| `pack_snippets(q, k, hop, context)` | Get source with surrounding lines |
| `get_node(node_id, include_edges)` | Fetch one node by ID |
| `list_nodes(module_path, kind)` | Enumerate nodes in a module |
| `callers(node_id)` | Find all callers — never grep for this |
| `explain(node_id)` | Natural-language role + callers + callees |
| `centrality(top, kinds)` | PageRank — most structurally important nodes |
| `bridge_centrality()` | Betweenness — architectural bridges |
| `framework_nodes()` | High-degree dependency nodes |
| `rank_nodes()` | Custom ranking by configurable signals |
| `query_ranked()` | Query + ranking combined |
| `explain_rank()` | Why a node ranked highly |
| `analyze_repo()` | Full architectural analysis |
| `snapshot_list(limit)` | List metric snapshots |
| `snapshot_show(key)` | Metrics for a snapshot |
| `snapshot_diff(key_a, key_b)` | Structural delta between versions |

## Node ID Format
`<kind>:<module_path>:<qualname>`
Examples: `function:src/kg_rag/registry:register_kg`, `class:src/kg_rag/mcp_server:KGRAGMCPServer`

## Key Build Commands
```bash
codekg build --repo .                          # full wipe + rebuild
codekg build --repo . --include-dir src        # scope to src/
codekg update --repo .                         # incremental upsert
codekg snapshot save --repo .
```

## Usage Rules
- Always `graph_stats()` first in a new session
- `pack_snippets` before `Read` for code understanding
- `callers(node_id)` instead of grep for call sites
- `explain(node_id)` before `pack_snippets` for single nodes
- Rebuild after structural changes: `codekg build --repo .`
