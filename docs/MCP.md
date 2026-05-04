# KGRAG MCP Reference

**Tool reference and query strategy for the KGRAG federated MCP server**

*Author: Eric G. Suchanek, PhD*

---

## Overview

KGRAG ships a built-in MCP server (`kgrag mcp`) that exposes a **federated cross-KG interface** to any MCP-compatible AI agent — Claude Code, Claude Desktop, Cursor, GitHub Copilot, or Kilo Code. It sits above the individual per-repo KG servers and provides unified query, registry, corpus, and person-corpus tools that span all registered knowledge graphs simultaneously.

Once configured, the agent gains **22 tools**, grouped by purpose:

**Core KG tools** — registry inspection and federated query

| Tool | Purpose |
|---|---|
| `kgrag_stats()` | Registry summary: total KGs, per-kind counts, built status |
| `kgrag_list(kind)` | List all registered KG instances with paths and build status |
| `kgrag_info(name)` | Detailed info for a single registered KG |
| `kgrag_query(q, k, kinds)` | Federated semantic query across all (or filtered) registered KGs |
| `kgrag_pack(q, k, context, kinds)` | Federated snippet pack — source code + doc excerpts for LLM context |

**Corpus tools** — named groupings of KGs

| Tool | Purpose |
|---|---|
| `kgrag_corpus_list()` | List all corpora with size and member KG IDs |
| `kgrag_corpus_info(name)` | Detailed info about a corpus and its member KGs |
| `kgrag_corpus_create(name, ...)` | Create a named corpus grouping one or more KGs |
| `kgrag_corpus_delete(name)` | Delete a corpus (KGs are not removed) |
| `kgrag_corpus_add(corpus, kg)` | Add a KG to an existing corpus |
| `kgrag_corpus_remove(corpus, kg)` | Remove a KG from a corpus |
| `kgrag_corpus_query(corpus, q, k)` | Federated query scoped to a named corpus |
| `kgrag_corpus_pack(corpus, q, k, context)` | Snippet pack scoped to a named corpus |

**Person corpus tools** — per-person KG groupings with personal metadata

| Tool | Purpose |
|---|---|
| `kgrag_person_list()` | List all person corpus entries |
| `kgrag_person_info(name)` | Detailed info including personal metadata and member KGs |
| `kgrag_person_create(name, ...)` | Create a person corpus entry |
| `kgrag_person_delete(name)` | Delete a person corpus entry (KGs are not removed) |
| `kgrag_person_add(person, kg)` | Add a KG to a person corpus |
| `kgrag_person_remove(person, kg)` | Remove a KG from a person corpus |
| `kgrag_person_update(name, ...)` | Update personal metadata fields |
| `kgrag_person_query(person, q, k)` | Federated query scoped to a person corpus |
| `kgrag_person_pack(person, q, k, context)` | Snippet pack scoped to a person corpus |

> The KGRAG MCP server does not replace per-repo CodeKG/DocKG servers — it **orchestrates across them**. For deep structural analysis of a single codebase (call chains, AST, centrality), use the dedicated `pycodekg mcp` server directly.

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
      ┌──────┼──────────────┐
      ▼      ▼              ▼
   KG      Corpus       Person
 entries  Registry      Registry
 (per KG) (named sets)  (per-person sets)
      │
  ┌───┴───┐
  ▼       ▼
PyCodeKG  DocKG / MemoryKG / DiaryKG / FTreeKG / …
```

---

## Smoke Test

Verify the server and registry are working before wiring into an agent:

```bash
# Confirm the kgrag command is reachable
kgrag --version

# Check what KGs are registered
kgrag list

# Run a query against the registry
kgrag query "authentication middleware"
```

Or check from Python:

```python
from kg_rag.registry import KGRegistry, default_registry_path
import json

with KGRegistry(db_path=default_registry_path()) as reg:
    stats = reg.stats()
    print(json.dumps({
        "total": stats.total,
        "by_kind": stats.by_kind,
        "built": stats.built,
        "registry_path": str(stats.registry_path),
    }, indent=2))
```

Expected output shape:

```json
{
  "total": 6,
  "by_kind": {"code": 2, "doc": 2, "memory": 1, "diary": 1},
  "built": 6,
  "registry_path": "/Users/you/.kgrag/registry.sqlite"
}
```

If this succeeds, the MCP server will work correctly.

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

Always use the **absolute path** to the venv binary. Find it with:

```bash
poetry env info --path
# → /Users/you/repos/kgrag/.venv
# binary: /Users/you/repos/kgrag/.venv/bin/kgrag
```

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

### Running alongside per-repo servers

A typical `.mcp.json` runs all three servers simultaneously:

```json
{
  "mcpServers": {
    "kgrag":    { "command": "/venv/bin/kgrag",    "args": ["mcp"] },
    "pycodekg": { "command": "/venv/bin/pycodekg", "args": ["mcp", "--repo", "/abs/path/to/repo"] },
    "dockg":    { "command": "/venv/bin/dockg",    "args": ["mcp", "--repo", "/abs/path/to/docs"] }
  }
}
```

| Server | Scope | Best for |
|--------|-------|---------|
| `kgrag` | All registered graphs | Cross-graph federated search, corpus/person registry management |
| `pycodekg` | Single code repo | Deep structural analysis: call chains, AST, centrality, callers |
| `dockg` | Single doc corpus | Document-specific queries, section navigation |

Use `kgrag_pack` for broad context gathering, then switch to `pack_snippets` (pycodekg) or `pack_docs` (dockg) for deep single-source analysis.

---

## KG Kinds

All tools that accept a `kind` filter or `kinds` array support:

`code` · `doc` · `meta` · `diary` · `agent` · `filetree` · `memory` · `gutenberg` · `ia` · `verse` · `disulfide` · `pdbfile` · `legal` · `person`

---

## Tool Reference

### `kgrag_stats()`

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

### `kgrag_list(kind)`

List all registered KG instances with paths and build status.

**Parameters:**

| Name | Type | Required | Description |
|------|------|----------|-------------|
| `kind` | string (KG kind) | No | Filter results to a single KG kind |

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
    "sqlite_path": "/Users/you/repos/myproject/.pycodekg/graph.sqlite",
    "lancedb_path": "/Users/you/repos/myproject/.pycodekg/lancedb",
    "tags": []
  }
]
```

**When to use:** Discovering what is registered before querying; confirming paths after `kgrag init`.

---

### `kgrag_info(name)`

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
  "sqlite_path": "/Users/you/repos/myproject/.pycodekg/graph.sqlite",
  "lancedb_path": "/Users/you/repos/myproject/.pycodekg/lancedb",
  "tags": [],
  "metadata": {},
  "created_at": "2026-03-12T10:00:00",
  "updated_at": "2026-03-12T10:05:00"
}
```

Returns `{"error": "Not found: <name>"}` if the name is unknown.

---

### `kgrag_query(q, k, kinds)`

Federated semantic query across all (or a filtered subset of) registered KGs. Returns ranked hits from every queried graph, merged into a single result.

**Parameters:**

| Name | Type | Required | Default | Description |
|------|------|----------|---------|-------------|
| `q` | string | Yes | — | Natural-language query |
| `k` | integer | No | `8` | Hits to retrieve per KG |
| `kinds` | array of KG kind strings | No | all | Restrict to these KG kinds |

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

### `kgrag_pack(q, k, context, kinds)`

Federated snippet pack across all registered KGs. Returns source code snippets and document excerpts suitable for direct inclusion in LLM context.

**Parameters:**

| Name | Type | Required | Default | Description |
|------|------|----------|---------|-------------|
| `q` | string | Yes | — | Natural-language query |
| `k` | integer | No | `8` | Snippets to retrieve per KG |
| `context` | integer | No | `5` | Lines of context around code snippets |
| `kinds` | array of KG kind strings | No | all | Restrict to these KG kinds |

**Returns:** Markdown-formatted context pack (plain text)

**When to use:** Feeding grounded context into an LLM prompt; understanding how something works across both code and docs simultaneously.

---

## Corpus Tools

A **corpus** is a named, persistent grouping of one or more registered KGs. Use corpora to scope queries to a logical project or topic without touching the underlying KG registrations.

---

### `kgrag_corpus_list()`

List all corpora with their size and member KG IDs.

**Parameters:** none

**Returns:** JSON object

```json
{
  "total": 2,
  "total_kg_refs": 5,
  "corpora": [
    {
      "id": "abc123...",
      "name": "KGRAG_repos",
      "description": "All KGRAG-family repos",
      "size": 3,
      "kg_ids": ["id1", "id2", "id3"],
      "tags": [],
      "updated_at": "2026-04-01T09:00:00"
    }
  ]
}
```

---

### `kgrag_corpus_info(name)`

Detailed information about a corpus, including the name and kind of each member KG.

**Parameters:**

| Name | Type | Required | Description |
|------|------|----------|-------------|
| `name` | string | Yes | Corpus name or UUID |

**Returns:** JSON object with `id`, `name`, `description`, `size`, `kgs` (array of `{id, name, kind, built}`), `tags`, `metadata`, `created_at`, `updated_at`.

---

### `kgrag_corpus_create(name, kg_names, description, tags)`

Create a new corpus grouping one or more registered KGs.

**Parameters:**

| Name | Type | Required | Description |
|------|------|----------|-------------|
| `name` | string | Yes | Corpus name |
| `kg_names` | array of strings | No | KG names or UUIDs to include |
| `description` | string | No | Optional description |
| `tags` | array of strings | No | Optional tags |

**Returns:** `{"created": "<name>", "size": <n>}`

---

### `kgrag_corpus_delete(name)`

Delete a corpus from the registry. The underlying KGs are **not** removed.

**Parameters:**

| Name | Type | Required | Description |
|------|------|----------|-------------|
| `name` | string | Yes | Corpus name or UUID |

**Returns:** `{"deleted": "<name>"}` or `{"error": "Corpus not found: <name>"}`

---

### `kgrag_corpus_add(corpus, kg)`

Add a KG to an existing corpus.

**Parameters:**

| Name | Type | Required | Description |
|------|------|----------|-------------|
| `corpus` | string | Yes | Corpus name or UUID |
| `kg` | string | Yes | KG name or UUID to add |

**Returns:** `{"corpus": "<name>", "added": "<kg>", "size": <n>}`

---

### `kgrag_corpus_remove(corpus, kg)`

Remove a KG from a corpus.

**Parameters:**

| Name | Type | Required | Description |
|------|------|----------|-------------|
| `corpus` | string | Yes | Corpus name or UUID |
| `kg` | string | Yes | KG name or UUID to remove |

**Returns:** `{"corpus": "<name>", "removed": "<kg>", "size": <n>}`

---

### `kgrag_corpus_query(corpus, q, k)`

Federated semantic query scoped to a named corpus.

**Parameters:**

| Name | Type | Required | Default | Description |
|------|------|----------|---------|-------------|
| `corpus` | string | Yes | — | Corpus name or UUID |
| `q` | string | Yes | — | Natural-language query |
| `k` | integer | No | `8` | Hits per KG |

**Returns:** Same structure as `kgrag_query` with an added `"corpus"` field.

---

### `kgrag_corpus_pack(corpus, q, k, context)`

Federated snippet pack scoped to a named corpus.

**Parameters:**

| Name | Type | Required | Default | Description |
|------|------|----------|---------|-------------|
| `corpus` | string | Yes | — | Corpus name or UUID |
| `q` | string | Yes | — | Natural-language query |
| `k` | integer | No | `8` | Snippets per KG |
| `context` | integer | No | `5` | Lines of context |

**Returns:** Markdown context pack (same format as `kgrag_pack`).

---

## Person Corpus Tools

A **person corpus** is a named grouping of KGs associated with an individual, plus optional personal metadata (birth date, email, address, phone, notes). Use person corpora to query across all knowledge sources relevant to one person.

---

### `kgrag_person_list()`

List all person corpus entries.

**Parameters:** none

**Returns:** JSON object with `total`, `total_kg_refs`, and `persons` array; each entry includes `id`, `name`, `birth_year`, `birth_date`, `email`, `size`, `tags`, `updated_at`.

---

### `kgrag_person_info(name)`

Detailed info about a person corpus entry, including personal metadata and all member KGs.

**Parameters:**

| Name | Type | Required | Description |
|------|------|----------|-------------|
| `name` | string | Yes | Person name or UUID |

**Returns:** JSON object with `id`, `name`, `birth_year`, `birth_date`, `address`, `email`, `phone`, `notes`, `size`, `kgs`, `tags`, `metadata`, `created_at`, `updated_at`.

---

### `kgrag_person_create(name, ...)`

Create a person corpus entry.

**Parameters:**

| Name | Type | Required | Description |
|------|------|----------|-------------|
| `name` | string | Yes | Full name of the person |
| `kg_names` | array of strings | No | KG names or UUIDs to include |
| `birth_year` | integer | No | Year of birth |
| `birth_date` | string | No | Full birth date (`YYYY-MM-DD`) |
| `address` | string | No | Mailing/home address |
| `email` | string | No | Primary email address |
| `phone` | string | No | Primary phone number |
| `notes` | string | No | Free-form notes |
| `tags` | array of strings | No | Optional tags |

**Returns:** `{"created": "<name>", "size": <n>}`

---

### `kgrag_person_delete(name)`

Delete a person corpus entry. The underlying KGs are **not** removed.

**Parameters:**

| Name | Type | Required | Description |
|------|------|----------|-------------|
| `name` | string | Yes | Person name or UUID |

**Returns:** `{"deleted": "<name>"}` or `{"error": "Person not found: <name>"}`

---

### `kgrag_person_add(person, kg)`

Add a KG to an existing person corpus.

**Parameters:**

| Name | Type | Required | Description |
|------|------|----------|-------------|
| `person` | string | Yes | Person name or UUID |
| `kg` | string | Yes | KG name or UUID to add |

**Returns:** `{"person": "<name>", "added": "<kg>", "size": <n>}`

---

### `kgrag_person_remove(person, kg)`

Remove a KG from a person corpus.

**Parameters:**

| Name | Type | Required | Description |
|------|------|----------|-------------|
| `person` | string | Yes | Person name or UUID |
| `kg` | string | Yes | KG name or UUID to remove |

**Returns:** `{"person": "<name>", "removed": "<kg>", "size": <n>}`

---

### `kgrag_person_update(name, ...)`

Update personal metadata for an existing person corpus entry. Only supplied fields are changed.

**Parameters:**

| Name | Type | Required | Description |
|------|------|----------|-------------|
| `name` | string | Yes | Person name or UUID |
| `birth_year` | integer | No | Year of birth |
| `birth_date` | string | No | Full birth date (`YYYY-MM-DD`) |
| `address` | string | No | Mailing/home address |
| `email` | string | No | Primary email address |
| `phone` | string | No | Primary phone number |
| `notes` | string | No | Free-form notes |

**Returns:** `{"updated": "<name>", "fields": [<changed fields>]}`

---

### `kgrag_person_query(person, q, k)`

Federated semantic query scoped to a person corpus.

**Parameters:**

| Name | Type | Required | Default | Description |
|------|------|----------|---------|-------------|
| `person` | string | Yes | — | Person name or UUID |
| `q` | string | Yes | — | Natural-language query |
| `k` | integer | No | `8` | Hits per KG |

**Returns:** Same structure as `kgrag_query` with an added `"person"` field.

---

### `kgrag_person_pack(person, q, k, context)`

Federated snippet pack scoped to a person corpus.

**Parameters:**

| Name | Type | Required | Default | Description |
|------|------|----------|---------|-------------|
| `person` | string | Yes | — | Person name or UUID |
| `q` | string | Yes | — | Natural-language query |
| `k` | integer | No | `8` | Snippets per KG |
| `context` | integer | No | `5` | Lines of context |

**Returns:** Markdown context pack (same format as `kgrag_pack`).

---

## Query Strategy Guide

### Typical agent workflow

```
1. kgrag_stats()
   → confirm KGs are registered and built

2. kgrag_list()
   → see names to use in subsequent calls

3. kgrag_query(q="...", k=8)
   → broad exploration across all registered KGs

4. kgrag_pack(q="...", k=6, context=5)
   → get source snippets + doc excerpts for LLM context
```

### Focused code-only exploration

```
kgrag_query(q="database connection pooling", kinds=["code"])
kgrag_pack(q="connection pool setup", kinds=["code"], k=6)
```

### Cross-source understanding (code + docs)

```
kgrag_pack(q="user authentication flow", k=8)
# Returns code snippets from PyCodeKG and doc excerpts from DocKG together
```

### Corpus-scoped query

```
kgrag_corpus_list()
→ see available corpora

kgrag_corpus_query(corpus="KGRAG_repos", q="MCP server")
→ search within corpus

kgrag_corpus_pack(corpus="KGRAG_repos", q="MCP server")
→ snippets from corpus
```

### Person corpus

```
kgrag_person_list()
→ list all persons

kgrag_person_query(person="Jane Doe", q="research notes")
→ search person's KGs

kgrag_person_pack(person="Jane Doe", q="project history")
→ snippets from person
```

### Registry inspection

```
kgrag_list(kind="code")          → all code KGs
kgrag_info(name="myrepo-code")   → full paths and timestamps
```

### When to use KGRAG vs. per-repo servers

| Situation | Tool |
|---|---|
| Broad exploration across all code + docs | `kgrag_pack(q)` |
| Deep call-chain / AST analysis of one repo | `pycodekg pack_snippets(q)` |
| Document section navigation for one corpus | `dockg pack_docs(q)` |
| Scoped query over a curated set of KGs | `kgrag_corpus_pack(corpus, q)` |
| All knowledge about a specific person | `kgrag_person_pack(person, q)` |

---

## Troubleshooting

| Symptom | Cause | Fix |
|---|---|---|
| `kgrag_stats` returns `total: 0` | No KGs registered | Run `kgrag register --name <n> --kind <k> --repo <path>` |
| `kgrag_query` returns no hits | KG not built or LanceDB index missing | Rebuild the KG (`pycodekg build` / `dockg build`), re-register if needed |
| `kgrag_info` returns `{"error": "Not found: ..."}` | Name/UUID mismatch | Check exact name with `kgrag_list()` |
| MCP server not appearing in agent | Wrong/relative paths in MCP config, or agent not restarted | Use absolute venv path from `poetry env info --path`; restart the agent |
| `kgrag` command not found | Package not installed or venv not active | `poetry install`, or use absolute path `/path/to/.venv/bin/kgrag` |
| `corpus_query` raises KeyError | Corpus name doesn't exist | Check with `kgrag_corpus_list()` first |
| Registry path mismatch | `$KGRAG_REGISTRY` not set consistently | Pass `--registry` explicitly, or set `KGRAG_REGISTRY` in your shell and MCP config env |

---

## Environment Variables

| Variable | Description |
|----------|-------------|
| `KGRAG_REGISTRY` | Path to the registry SQLite file. Overrides the default `~/.kgrag/registry.sqlite`. Equivalent to `--registry`. |

---

## Summary

| Concern | Answer |
|---|---|
| What does the MCP server expose? | 22 tools across core KG (`kgrag_stats`, `kgrag_list`, `kgrag_info`, `kgrag_query`, `kgrag_pack`), corpus (8 tools), and person corpus (9 tools) |
| What must exist before starting? | At least one KG registered via `kgrag register`; KG must be built |
| How do I start the server? | `kgrag mcp` — spawned automatically by the MCP client |
| Which tool should I call first? | `kgrag_stats()` for orientation |
| Can it modify the registry? | Yes — corpus and person tools write to the registry SQLite |
| Can it modify KG graphs? | No — KG query/pack tools are strictly read-only |
| Default registry location | `~/.kgrag/registry.sqlite` (override with `KGRAG_REGISTRY` or `--registry`) |
