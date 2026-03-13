---
name: codekg
description: Expert knowledge for installing, configuring, and using the CodeKG MCP server — a hybrid semantic + structural knowledge graph for Python codebases. Use this skill when the user asks about: setting up CodeKG in a project, adding code-kg as a Poetry dependency, building the SQLite or LanceDB knowledge graph, configuring .mcp.json for Claude Code or Kilo Code, configuring .vscode/mcp.json for GitHub Copilot, configuring claude_desktop_config.json for Claude Desktop, configuring Cline MCP settings, using the codekg CLI (codekg build-sqlite, codekg build-lancedb, codekg mcp, codekg query, codekg pack, codekg analyze, codekg viz, codekg viz3d, codekg viz-timeline, codekg explain, codekg snapshot, codekg architecture, codekg download-model, codekg install-hooks), using the graph_stats / query_codebase / pack_snippets / get_node / list_nodes / callers / explain / analyze_repo / snapshot_list / snapshot_show / snapshot_diff MCP tools, or troubleshooting CodeKG errors.
---

# CodeKG Skill

> **Use CodeKG first — before grep, Glob, or file reads.**
>
> Grep and file search find text. CodeKG understands code. It knows what calls what, what inherits from what, which modules are imported where, and surfaces the most semantically relevant source snippets in a single query. One `pack_snippets` call replaces five rounds of grep-and-read and gives the agent real structural insight into the codebase — not just line matches.

CodeKG indexes Python repos into a hybrid knowledge graph (SQLite + LanceDB) and exposes it as MCP tools for AI agents.

## Installation (Poetry)

```bash
# With MCP server support
poetry add "code-kg @ git+https://github.com/Flux-Frontiers/code_kg.git"
```

Adds to `pyproject.toml`:
```toml
code-kg = { git = "https://github.com/Flux-Frontiers/code_kg.git", extras = ["viz"] }
```

## Build the Knowledge Graph

```bash
# Step 1 — SQLite graph
codekg build-sqlite --repo .

# Step 2 — LanceDB vector index
codekg build-lancedb --repo .
```

> **Common mistake:** `codekg build-lancedb` uses `--sqlite`, not `--db`, when specifying a non-default path.

Add `--wipe` to either command to rebuild from scratch.

## Rebuilding After Code Changes

The knowledge graph is a snapshot of the codebase at build time. It does **not** update automatically. Stale data causes misleading query results — especially after renames, deletions, or large refactors.

### When to rebuild

| Change | Action |
|---|---|
| Added / renamed / deleted functions, classes, or modules | Full rebuild (`--wipe`) |
| Large refactor touching many files | Full rebuild (`--wipe`) |
| Minor edits within existing functions | Incremental rebuild (no `--wipe`) is usually sufficient |
| New file added to the repo | Incremental rebuild is sufficient |

> **Why `--wipe` matters:** Without it, deleted or renamed nodes remain in the index as phantom entries. LanceDB upserts by node ID so renamed nodes leave behind orphans; `--wipe` clears them.

### Full rebuild (recommended after significant changes)

```bash
codekg build-sqlite  --repo . --wipe
codekg build-lancedb --repo . --wipe
```

### Incremental rebuild (minor additions only)

```bash
# omit --wipe to upsert without clearing
codekg build-sqlite  --repo .
codekg build-lancedb --repo .
```

### Using the installer script

```bash
# Re-run the installer with --wipe from your target repo
bash scripts/install-skill.sh --wipe

# Or via curl if not running from a local clone
curl -fsSL https://raw.githubusercontent.com/Flux-Frontiers/code_kg/main/scripts/install-skill.sh \
  | bash -s -- --wipe
```

---

## Additional CLI Commands

Beyond build/query/viz, the full command set:

| Command | Purpose |
|---|---|
| `codekg explain <NODE_ID>` | Natural-language explanation of a code node by ID |
| `codekg snapshot save <version>` | Capture metrics snapshot (commit, branch, version) |
| `codekg snapshot list` | List all snapshots in reverse chronological order |
| `codekg snapshot show <commit>` | Full details for a single snapshot |
| `codekg snapshot diff <a> <b>` | Compare two snapshots side-by-side |
| `codekg viz-timeline` | Temporal metrics evolution chart (2d or 3d) |
| `codekg architecture [<repo>]` | Generate Markdown/JSON architecture description |
| `codekg download-model` | Pre-download embedding model for offline use |
| `codekg install-hooks` | Install post-commit git hook for automatic snapshots |

## Offline Setup

If you need to use CodeKG without network access (e.g., in CI, air-gapped nets, or to avoid HuggingFace rate limits):

```bash
# Download the embedding model locally
codekg download-model
```

This saves the model to `.codekg/models/microsoft--codebert-base/` (479M). Subsequent runs of `build-lancedb` and `codekg query` will use the cached local copy without any network access.

Alternatively, set `CODEKG_MODEL_DIR` to cache elsewhere:
```bash
export CODEKG_MODEL_DIR=/path/to/shared/models
codekg download-model
```

## Configure Claude Code / Kilo Code (.mcp.json)

Both Claude Code and Kilo Code read per-repo config from `.mcp.json` in the project root.

```json
{
  "mcpServers": {
    "codekg": {
      "command": "codekg",
      "args": [
        "mcp",
        "--repo", "/absolute/path/to/repo",
        "--db",   "/absolute/path/to/repo/.codekg/graph.sqlite"
      ]
    }
  }
}
```

Always use **absolute paths**. Merge into existing `mcpServers` — don't overwrite other entries.

> ⚠️ Do NOT add `codekg` to any global settings file — use per-repo `.mcp.json` only.

## Configure GitHub Copilot (.vscode/mcp.json)

GitHub Copilot uses a different schema — `"servers"` key and `"type": "stdio"` required:

```json
{
  "servers": {
    "codekg": {
      "type": "stdio",
      "command": "codekg",
      "args": [
        "mcp",
        "--repo", "/absolute/path/to/repo",
        "--db",   "/absolute/path/to/repo/.codekg/graph.sqlite"
      ]
    }
  }
}
```

VS Code will prompt you to **Trust** the server on first use.

## Configure Claude Desktop (claude_desktop_config.json)

Claude Desktop has no Poetry on PATH — use the absolute venv binary:

```bash
poetry env info --path
# → /path/to/venv
# binary: /path/to/venv/bin/codekg
```

Config path: `~/Library/Application Support/Claude/claude_desktop_config.json` (macOS)

```json
{
  "mcpServers": {
    "codekg": {
      "command": "/path/to/venv/bin/codekg",
      "args": ["mcp", "--repo", "/abs/path", "--db", "/abs/path/.codekg/graph.sqlite"]
    }
  }
}
```

## Automated Setup

If the project has Claude Copilot installed:
```
/setup-mcp /path/to/repo
```
This installs, builds, smoke-tests, and writes both config files automatically.

## MCP Tools

| Tool | When to use |
|---|---|
| `graph_stats()` | First call — understand codebase size/shape |
| `query_codebase(q)` | Explore graph structure, find relevant nodes; tune precision with `min_score` and result diversity with `max_per_module` |
| `pack_snippets(q)` | Read actual source code (prefer over query_codebase); supports `min_score` and `max_per_module` |
| `get_node(node_id, include_edges)` | Fetch node metadata; `include_edges=True` also returns outgoing edges + incoming callers |
| `list_nodes(module_path, kind)` | List nodes filtered by module path prefix and/or kind |
| `callers(node_id)` | Find all callers of a node — fan-in lookup resolving cross-module sym: stubs with import-aware filtering for ambiguous names |
| `explain(node_id)` | Natural-language explanation of a node: role, docstring, callers, callees |
| `analyze_repo()` | Full architectural analysis — complexity, coupling, coverage, orphans |
| `snapshot_list(limit)` | List saved metric snapshots newest-first (use `limit=0` for all) |
| `snapshot_show(key)` | Full metrics for a snapshot key (tree hash) or `"latest"`; legacy snapshots backfill missing deltas |
| `snapshot_diff(key_a, key_b)` | Compare two snapshots by key — node/edge/coverage/issues delta |

## Query Strategy Guide

### Choosing `k` and `hop`

| Goal | Settings |
|---|---|
| Narrow, precise lookup | `k=4, hop=0` |
| Standard exploration | `k=8, hop=1` (default) |
| Broad context sweep | `k=12, hop=2` |
| Deep dependency trace | `k=8, hop=2, rels="CALLS,IMPORTS"` |

### Choosing `rels`

| Relation | When to include |
|---|---|
| `CONTAINS` | Almost always — structural context |
| `CALLS` | Tracing execution flow |
| `IMPORTS` | Dependency analysis |
| `INHERITS` | OOP hierarchy |
| `RESOLVES_TO` | Connecting `sym:` stubs to definitions | Used internally by `callers()` — include in `query_codebase` rels for graph traversal through import aliases |

### Typical session workflow

```
1. graph_stats()                                         → orientation
2. query_codebase("auth flow", k=8, hop=1)               → find nodes
3. explain("cls:src/auth/jwt.py:JWTValidator")           → understand before reading
4. pack_snippets("JWT validation", k=6, hop=1)           → read source
5. get_node("fn:src/auth/jwt.py:JWTValidator.validate", include_edges=True)
                                                         → node detail + neighborhood in one call
6. pack_snippets("error handling", k=4, hop=2, rels="CALLS")  → deeper
7. snapshot_list() / snapshot_diff("a", "b")             → track codebase evolution
```

## .gitignore Setup

The `.codekg/` directory holds the SQLite graph, LanceDB vector index, and snapshots. All are local artifacts — the graph and index are reproducible, snapshots are captured by the post-commit hook.

```gitignore
.codekg/
```

Add this to `.gitignore` when installing CodeKG in a new repo. Commit snapshots manually at milestones if you want git history.

## Key Defaults

- `k=8, hop=1, rels="CONTAINS,CALLS,IMPORTS,INHERITS"`
- Node ID format: `<kind>:<module_path>:<qualname>` (e.g. `fn:src/auth/jwt.py:JWTValidator.validate`)
- Node ID prefixes: `mod:` module, `cls:` class, `fn:` function/method, `sym:` external symbol
- Transport: `stdio` (Claude Code/Desktop), `sse` (HTTP clients)

## Troubleshooting

| Error | Fix |
|---|---|
| `error: the following arguments are required: --sqlite` | Use `--sqlite`, not `--db`, for `codekg build-lancedb` |
| `ERROR: 'mcp' package not found` | `poetry add mcp` |
| `WARNING: SQLite database not found` | Run both build commands first |
| MCP server not appearing | Use absolute paths; restart Claude Code |
| Empty query results | Run `codekg build-lancedb --wipe` |

## Full Reference

See `references/installation.md` for complete CLI flags, `.mcp.json` templates with full Copilot stack, gitignore recommendations, and query strategy guide.
