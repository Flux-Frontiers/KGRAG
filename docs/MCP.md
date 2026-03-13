# KGRAG MCP Server

The KGRAG MCP server exposes a **federated cross-KG interface** to AI agents via the [Model Context Protocol](https://modelcontextprotocol.io/). It sits above the individual CodeKG and DocKG MCP servers and provides unified query, registry, and snippet tools that span all registered knowledge graphs simultaneously.

---

## Architecture

```
AI Agent (Claude Code / Cursor / Copilot)
         │
         │  MCP (stdio)
         ▼
  ┌─────────────────────┐
  │   KGRAG MCP Server  │   ← kgrag mcp
  │  (mcp_server.py)    │
  └──────────┬──────────┘
             │  reads
             ▼
      KGRegistry (SQLite)
             │
      ┌──────┴──────┐
      ▼             ▼
   CodeKG        DocKG
  adapters      adapters
  (per repo)   (per corpus)
```

The KGRAG MCP server does not replace the per-repo CodeKG/DocKG servers — it **orchestrates across them**. For deep structural analysis of a single codebase (call chains, AST, centrality), use the dedicated `codekg` MCP server directly.

---

## Starting the Server

```bash
kgrag mcp
```

Options:

| Flag | Default | Description |
|------|---------|-------------|
| `--host` | `localhost` | Server host (informational; stdio transport is used) |
| `--port` | `8765` | Server port (informational; stdio transport is used) |
| `--registry PATH` | `$KGRAG_REGISTRY` or `~/.kgrag/registry.sqlite` | Registry database to use |

The server uses **stdio transport** — the AI agent's MCP client spawns it as a subprocess. No network socket is opened.

---

## Configuring Clients

### Claude Code / Kilo Code (`.mcp.json`)

Add to the project-root `.mcp.json`:

```json
{
  "mcpServers": {
    "kgrag": {
      "command": "/path/to/venv/bin/kgrag",
      "args": ["mcp"]
    }
  }
}
```

To point at a non-default registry:

```json
{
  "mcpServers": {
    "kgrag": {
      "command": "/path/to/venv/bin/kgrag",
      "args": ["mcp", "--registry", "/abs/path/to/registry.sqlite"]
    }
  }
}
```

> Always use the **absolute path** to the venv binary. Find it with:
> ```bash
> poetry env info --path
> # → /Users/you/repos/myproject/.venv
> # binary: /Users/you/repos/myproject/.venv/bin/kgrag
> ```

### GitHub Copilot (`.vscode/mcp.json`)

```json
{
  "servers": {
    "kgrag": {
      "type": "stdio",
      "command": "/path/to/venv/bin/kgrag",
      "args": ["mcp"]
    }
  }
}
```

### Claude Desktop (`claude_desktop_config.json`)

macOS: `~/Library/Application Support/Claude/claude_desktop_config.json`

```json
{
  "mcpServers": {
    "kgrag": {
      "command": "/path/to/venv/bin/kgrag",
      "args": ["mcp"]
    }
  }
}
```

---

## Tools Reference

The server exposes five tools under the server name `kgrag`.

---

### `kgrag_stats`

Registry summary: total registered KGs, per-kind counts, and how many are built.

**Parameters:** none

**Returns:** JSON object

```json
{
  "total": 3,
  "by_kind": {"code": 2, "doc": 1},
  "built": 3,
  "registry_path": "/Users/you/.kgrag/registry.sqlite"
}
```

**When to use:** First call in any session — confirms which KGs are available and built.

---

### `kgrag_list`

List all registered KG instances with paths and build status.

**Parameters:**

| Name | Type | Required | Description |
|------|------|----------|-------------|
| `kind` | `"code" \| "doc" \| "meta"` | No | Filter results to a single KG kind |

**Returns:** JSON array of entry objects

```json
[
  {
    "name": "myproject-code",
    "kind": "code",
    "built": true,
    "version": null,
    "repo_path": "/Users/you/repos/myproject",
    "venv_path": "/Users/you/repos/myproject/.venv",
    "sqlite_path": "/Users/you/repos/myproject/.codekg/graph.sqlite",
    "lancedb_path": "/Users/you/repos/myproject/.codekg/lancedb",
    "tags": []
  }
]
```

**When to use:** Discovering what is registered before querying; confirming paths after `kgrag init`.

---

### `kgrag_info`

Detailed information about a single registered KG, including creation/update timestamps and metadata.

**Parameters:**

| Name | Type | Required | Description |
|------|------|----------|-------------|
| `name` | string | Yes | KG name or UUID |

**Returns:** JSON object with full entry detail

```json
{
  "id": "3f2a1b...",
  "name": "myproject-code",
  "kind": "code",
  "built": true,
  "version": null,
  "repo_path": "/Users/you/repos/myproject",
  "venv_path": "/Users/you/repos/myproject/.venv",
  "sqlite_path": "/Users/you/repos/myproject/.codekg/graph.sqlite",
  "lancedb_path": "/Users/you/repos/myproject/.codekg/lancedb",
  "tags": [],
  "metadata": {},
  "created_at": "2026-03-12T10:00:00",
  "updated_at": "2026-03-12T10:05:00"
}
```

Returns `{"error": "Not found: <name>"}` if the name is unknown.

---

### `kgrag_query`

Federated semantic query across all (or a filtered subset of) registered KGs. Returns ranked hits from every queried graph, merged into a single result.

**Parameters:**

| Name | Type | Required | Default | Description |
|------|------|----------|---------|-------------|
| `q` | string | Yes | — | Natural-language query |
| `k` | integer | No | `8` | Hits to retrieve per KG |
| `kinds` | `["code" \| "doc" \| "meta"]` | No | all | Restrict to these KG kinds |

**Returns:** JSON object

```json
{
  "query": "authentication middleware",
  "total_hits": 16,
  "kgs_queried": 2,
  "hits": [
    {
      "kg": "myproject-code",
      "kind": "code",
      "node_id": "fn:src/auth/middleware.py:AuthMiddleware.process_request",
      "name": "process_request",
      "node_kind": "function",
      "score": 0.8912,
      "summary": "Validates JWT token and attaches user to request context.",
      "source_path": "src/auth/middleware.py"
    }
  ]
}
```

**When to use:** Broad exploration — finding relevant nodes across code and docs before drilling in with `kgrag_pack`.

---

### `kgrag_pack`

Federated snippet pack across all registered KGs. Returns source code snippets and document excerpts suitable for direct inclusion in LLM context.

**Parameters:**

| Name | Type | Required | Default | Description |
|------|------|----------|---------|-------------|
| `q` | string | Yes | — | Natural-language query |
| `k` | integer | No | `8` | Snippets to retrieve per KG |
| `context` | integer | No | `5` | Lines of context around code snippets |
| `kinds` | `["code" \| "doc" \| "meta"]` | No | all | Restrict to these KG kinds |

**Returns:** Markdown-formatted context pack (plain text)

```markdown
# KGRAG Context Pack — "authentication middleware"

## [myproject-code] fn:src/auth/middleware.py:AuthMiddleware.process_request
*Score: 0.89 | src/auth/middleware.py:42–67*

```python
def process_request(self, request):
    """Validates JWT token and attaches user to request context."""
    token = request.headers.get("Authorization", "").removeprefix("Bearer ")
    ...
```

## [myproject-docs] Authentication Guide
*Score: 0.81 | docs/auth.md:15–40*

JWT tokens are issued on login and must be included in every request...
```

**When to use:** Feeding grounded context into an LLM prompt; understanding how something works across both code and docs simultaneously.

---

## Recommended Workflows

### Starting a session

```
1. kgrag_stats()                          → confirm graphs are registered and built
2. kgrag_list()                           → see names to use in subsequent calls
3. kgrag_query(q="...", k=8)              → broad exploration
4. kgrag_pack(q="...", k=6, context=5)   → get source for context
```

### Focused code-only exploration

```
kgrag_query(q="database connection pooling", kinds=["code"])
kgrag_pack(q="connection pool setup",        kinds=["code"], k=6)
```

### Cross-source understanding (code + docs)

```
kgrag_pack(q="user authentication flow", k=8)
# Returns code snippets from CodeKG and doc excerpts from DocKG together
```

### Registry inspection

```
kgrag_list(kind="code")          → all code KGs
kgrag_info(name="myrepo-code")   → full paths and timestamps
```

---

## Environment Variables

| Variable | Description |
|----------|-------------|
| `KGRAG_REGISTRY` | Path to the registry SQLite file. Overrides the default `~/.kgrag/registry.sqlite`. Equivalent to `--registry`. |

---

## Relationship to CodeKG / DocKG MCP Servers

KGRAG, CodeKG, and DocKG can run as separate MCP servers simultaneously. They serve different scopes:

| Server | Scope | Best for |
|--------|-------|---------|
| `kgrag` | All registered graphs | Cross-graph federated search, registry management |
| `codekg` | Single code repo | Deep structural analysis: call chains, AST, centrality, callers |
| `dockg` | Single doc corpus | Document-specific queries, section navigation |

A typical `.mcp.json` runs all three:

```json
{
  "mcpServers": {
    "kgrag":  { "command": "/venv/bin/kgrag",  "args": ["mcp"] },
    "codekg": { "command": "/venv/bin/codekg", "args": ["mcp", "--repo", "/abs/path"] },
    "dockg":  { "command": "/venv/bin/dockg",  "args": ["mcp", "--repo", "/abs/path"] }
  }
}
```

Use `kgrag_pack` for broad context gathering, then switch to `pack_snippets` (codekg) or `pack_docs` (dockg) for deep single-source analysis.
