# CodeKG Installation Reference

## Table of Contents
1. [CLI Flags Reference](#cli-flags-reference)
2. [Agent Config Matrix](#agent-config-matrix)
3. [MCP Config Templates](#mcp-config-templates)
4. [Query Strategy Guide](#query-strategy-guide)
5. [Gitignore Recommendations](#gitignore-recommendations)
6. [Smoke-Test Commands](#smoke-test-commands)
7. [Full Troubleshooting Table](#full-troubleshooting-table)

---

## CLI Flags Reference

### `codekg-build-sqlite`

| Flag | Required | Default | Description |
|---|---|---|---|
| `--repo` | | `.` | Repository root path |
| `--db` | | `.codekg/graph.sqlite` | SQLite output path |
| `--wipe` | | false | Delete existing graph first |

### `codekg-build-lancedb`

| Flag | Required | Default | Description |
|---|---|---|---|
| `--repo` | | `.` | Repository root (anchors default paths) |
| `--sqlite` | | `<repo>/.codekg/graph.sqlite` | Path to SQLite graph (**not** `--db`) |
| `--lancedb` | | `<repo>/.codekg/lancedb` | LanceDB output directory |
| `--table` | | `codekg_nodes` | LanceDB table name |
| `--model` | | `microsoft/codebert-base` | Sentence-transformer model |
| `--wipe` | | false | Delete existing vectors first |
| `--kinds` | | `module,class,function,method` | Node kinds to embed |
| `--batch` | | `256` | Embedding batch size |

### `codekg-mcp`

| Flag | Default | Description |
|---|---|---|
| `--repo` | `.` | Repository root |
| `--db` | `.codekg/graph.sqlite` | SQLite path |
| `--lancedb` | `.codekg/lancedb` | LanceDB directory |
| `--model` | `microsoft/codebert-base` | Embedding model |
| `--transport` | `stdio` | `stdio` or `sse` |

### `codekg-query`

```bash
poetry run codekg-query \
  --sqlite .codekg/graph.sqlite \
  --lancedb .codekg/lancedb \
  --q "your query here"
```

---

## Agent Config Matrix

| Agent | Config file | Key | Per-repo? |
|---|---|---|---|
| **Claude Code** | `.mcp.json` (project root) | `"mcpServers"` | ✅ Yes |
| **Kilo Code** | `.mcp.json` (project root) | `"mcpServers"` | ✅ Yes |
| **GitHub Copilot** | `.vscode/mcp.json` (workspace root) | `"servers"` | ✅ Yes |
| **Claude Desktop** | `~/Library/Application Support/Claude/claude_desktop_config.json` | `"mcpServers"` | ❌ Global |
| **Cline** | `~/...saoudrizwan.claude-dev/settings/cline_mcp_settings.json` | `"mcpServers"` | ❌ Global only |

> ⚠️ **Do NOT add `codekg` to any global settings file** (Claude Code `~/.claude/settings.json`, Kilo Code `mcp_settings.json`, Cline `cline_mcp_settings.json`).
> Use per-repo config files instead. For Cline, use a uniquely-named entry per repo (e.g. `codekg-myproject`).

---

## MCP Config Templates

### Claude Code `.mcp.json`

```json
{
  "mcpServers": {
    "codekg": {
      "command": "codekg",
      "args": [
        "mcp",
        "--repo",    "/absolute/path/to/repo",
        "--db",      "/absolute/path/to/repo/.codekg/graph.sqlite"
      ]
    }
  }
}
```

### Kilo Code `.mcp.json` with Copilot servers (no CodeKG)

```json
{
  "mcpServers": {
    "copilot-memory": {
      "command": "node",
      "args": ["/Users/YOU/.claude/copilot/mcp-servers/copilot-memory/dist/index.js"],
      "env": {
        "MEMORY_PATH": "/Users/YOU/.claude/memory",
        "WORKSPACE_ID": "your-project"
      }
    },
    "skills-copilot": {
      "command": "node",
      "args": ["/Users/YOU/.claude/copilot/mcp-servers/skills-copilot/dist/index.js"],
      "env": {
        "LOCAL_SKILLS_PATH": "./.claude/skills"
      }
    },
    "task-copilot": {
      "command": "node",
      "args": ["/Users/YOU/.claude/copilot/mcp-servers/task-copilot/dist/index.js"],
      "env": {
        "TASK_DB_PATH": "/Users/YOU/.claude/tasks",
        "WORKSPACE_ID": "your-project"
      }
    }
  }
}
```

### Full setup: `.mcp.json` with all servers

If you want Claude Code / Kilo Code to also have access to Copilot servers:

```json
{
  "mcpServers": {
    "copilot-memory": {
      "command": "node",
      "args": ["/Users/YOU/.claude/copilot/mcp-servers/copilot-memory/dist/index.js"],
      "env": {
        "MEMORY_PATH": "/Users/YOU/.claude/memory",
        "WORKSPACE_ID": "your-project"
      }
    },
    "skills-copilot": {
      "command": "node",
      "args": ["/Users/YOU/.claude/copilot/mcp-servers/skills-copilot/dist/index.js"],
      "env": {
        "LOCAL_SKILLS_PATH": "./.claude/skills"
      }
    },
    "task-copilot": {
      "command": "node",
      "args": ["/Users/YOU/.claude/copilot/mcp-servers/task-copilot/dist/index.js"],
      "env": {
        "TASK_DB_PATH": "/Users/YOU/.claude/tasks",
        "WORKSPACE_ID": "your-project"
      }
    },
    "codekg": {
      "command": "codekg",
      "args": [
        "mcp",
        "--repo",    "/absolute/path/to/repo",
        "--db",      "/absolute/path/to/repo/.codekg/graph.sqlite"
      ]
    }
  }
}
```

### GitHub Copilot (.vscode/mcp.json)

GitHub Copilot uses a different schema — `"servers"` key (not `"mcpServers"`) and requires `"type": "stdio"`:

```json
{
  "servers": {
    "codekg": {
      "type": "stdio",
      "command": "/absolute/path/to/venv/bin/codekg",
      "args": [
        "mcp",
        "--repo",    "/absolute/path/to/repo",
        "--db",      "/absolute/path/to/repo/.codekg/graph.sqlite"
      ]
    }
  }
}
```

Get venv path: `poetry env info --path`

VS Code will prompt you to **Trust** the server on first use.

### Claude Desktop (absolute venv path)

```json
{
  "mcpServers": {
    "codekg": {
      "command": "/absolute/path/to/venv/bin/codekg",
      "args": [
        "mcp",
        "--repo",    "/absolute/path/to/repo",
        "--db",      "/absolute/path/to/repo/.codekg/graph.sqlite"
      ]
    }
  }
}
```

Get venv path: `poetry env info --path`

---

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

### Typical session workflow

```
1. graph_stats()                                    → orientation
2. query_codebase("auth flow", k=8, hop=1)          → find nodes
3. pack_snippets("JWT validation", k=6, hop=1)      → read source
4. get_node("fn:src/auth/jwt.py:JWTValidator.validate")  → node detail
5. pack_snippets("error handling", k=4, hop=2, rels="CALLS")  → deeper
```

### Node ID format

`<kind>:<module_path>:<qualname>`

| Prefix | Kind |
|---|---|
| `mod:` | module |
| `cls:` | class |
| `fn:` | function / method |
| `sym:` | unresolved external symbol |

---

## Gitignore Recommendations

```gitignore
.codekg/
```

---

## Smoke-Test Commands

```bash
# Graph stats (Python API)
poetry run python -c "
from code_kg import CodeKG
import json
kg = CodeKG(repo_root='.', db_path='.codekg/graph.sqlite', lancedb_dir='.codekg/lancedb')
print(json.dumps(kg.stats(), indent=2))
"

# Sample query (CLI)
poetry run codekg-query --sqlite .codekg/graph.sqlite --lancedb .codekg/lancedb --q "module structure"

# Verify SQLite row counts
sqlite3 .codekg/graph.sqlite "SELECT COUNT(*) FROM nodes; SELECT COUNT(*) FROM edges;"
```

---

## Full Troubleshooting Table

| Symptom | Cause | Fix |
|---|---|---|
| `error: the following arguments are required: --sqlite` | Wrong flag for lancedb builder | Use `--sqlite`, not `--db` |
| `ERROR: 'mcp' package not found` | Optional dep missing | `poetry add mcp` |
| `WARNING: SQLite database not found` | Graph not built | Run `codekg-build-sqlite` first |
| Empty results from `query_codebase` | LanceDB stale or missing | `codekg-build-lancedb --wipe` |
| `RuntimeError: CodeKG not initialised` | Server not started via CLI | Always use `codekg-mcp` CLI |
| Snippets show wrong line numbers | Source changed since build | `codekg-build-sqlite --wipe` |
| MCP server not in Claude Code / Kilo Code | Relative paths or wrong location | Absolute paths in `.mcp.json` (project root); restart |
| MCP server not in GitHub Copilot | Missing `"type": "stdio"` or wrong key | Use `"servers"` key with `"type": "stdio"` in `.vscode/mcp.json`; click Trust |
| MCP server not in Claude Desktop | Wrong binary path | `poetry env info --path` for absolute path |
| Cline shows all repos pointing to same path | Global config used | Use unique entry name per repo (e.g. `codekg-myproject`) |
| `poetry run which codekg-mcp` empty | `mcp` extra not installed | `poetry add "code-kg[mcp]"` |
| `Command not found: codekg-mcp` in VS Code MCP log | VS Code extension host doesn't inherit shell PATH; bare `"poetry"` not found | Use absolute path: `"command": "/Users/you/.local/bin/poetry"` (get it with `which poetry`) |
