# KGRAG MCP Reference

**Tool reference and query strategy for the KGRAG federated MCP server**

*Author: Eric G. Suchanek, PhD*

---

## Overview

KGRAG ships a built-in MCP server (`kgrag mcp`) that exposes a **federated cross-KG interface** to any MCP-compatible AI agent — Claude Code, Claude Desktop, Cursor, GitHub Copilot, or Kilo Code. It sits above the individual per-repo KG servers and provides unified query, registry, corpus, and person-corpus tools that span all registered knowledge graphs simultaneously.

Once configured, the agent gains the fleet's five canonical tools -- `stats`,
`query`, `pack`, `get_node`, `neighbors`, the same names as on every KG server --
answered across every registered KG, plus the federation's own: `list_kgs` and
`kg_info` for the registry, and the `corpus_*` and `person_*` tools for named
groups of KGs. The full, generated list is in the [Tool Reference](#tool-reference)
below; `kgrag mcp --manifest` prints it live.

**Federated node ids.** A node id is unique within its KG, not across KGs, so
`query` returns each hit with an `id` of the form `<kg>::<node id>`. Pass it to
`get_node` and `neighbors` unchanged; `neighbors` answers inside that KG and
returns ids in the same form.

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
kgrag mcp                                       # stdio, the default registry
kgrag mcp --transport streamable-http --port 8765
kgrag mcp --manifest                            # the tool list as JSON; opens nothing
```

`kgrag mcp` takes the fleet's standard flags (it is built on `kg_utils.mcp`):

| Flag | Default | Description |
|------|---------|-------------|
| `--db PATH` | `$KGRAG_REGISTRY` or `~/.kgrag/registry.sqlite` | The registry to serve |
| `--repo DIR` | `.` | Where `[tool.kgrag]` (embedder) config is read |
| `--transport` | `stdio` | `stdio` for an agent's MCP config; `streamable-http` to serve over HTTP |
| `--host` / `--port` | `127.0.0.1` / `8765` | Bind address for `streamable-http` |
| `--manifest` | | Print the tool list as JSON and exit |

`--vectors` and `--model` belong to a single KG and are refused; each
registered KG uses its own. `--registry PATH`, the old name for `--db`, is
accepted until 0.19. `kgrag-mcp` is the same command. Each session prints the
registry it serves to stderr.

---

## Configuring Clients

`kgrag` is a global tool (`uv tool install kg-rag`), resolved from `PATH`, as
every fleet server is (FLEET_STANDARDS, "Tools are global"). Claude Desktop does
not inherit the login shell's `PATH`; give it the absolute path that
`command -v kgrag` prints.

### Claude Code / Kilo Code (`.mcp.json`)

Add to the project-root `.mcp.json`:

```json
{
  "mcpServers": {
    "kgrag": {
      "command": "kgrag",
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
      "command": "kgrag",
      "args": ["mcp", "--db", "/abs/path/to/registry.sqlite"]
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
      "command": "kgrag",
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
      "command": "kgrag",
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
    "kgrag":    { "command": "kgrag",    "args": ["mcp"] },
    "pycodekg": { "command": "pycodekg", "args": ["mcp", "--repo", "/abs/path/to/repo"] },
    "dockg":    { "command": "dockg",    "args": ["mcp", "--repo", "/abs/path/to/docs"] }
  }
}
```

| Server | Scope | Best for |
|--------|-------|---------|
| `kgrag` | All registered graphs | Cross-graph federated search, corpus/person registry management |
| `pycodekg` | Single code repo | Deep structural analysis: call chains, AST, centrality, callers |
| `dockg` | Single doc corpus | Document-specific queries, section navigation |

Use `pack` for broad context gathering, then switch to `pack` on the `pycodekg` server or `pack` on the `dockg` server for deep single-source analysis.

---

## KG Kinds

All tools that accept a `kind` filter or `kinds` array support:

`code` · `doc` · `meta` · `diary` · `agent` · `filetree` · `memory` · `gutenberg` · `ia` · `verse` · `disulfide` · `pdbfile` · `legal` · `person`

---

## Tool Reference

<!-- BEGIN GENERATED TOOL REFERENCE (scripts/gen_mcp_reference.py) -->

The server registers **24 tools**. Required parameters are shown in **bold**; the rest show their defaults. Generated from `kgrag mcp --manifest`.

### Canonical tools -- the same five on every fleet server

#### `stats`()

Node and edge counts, in total and by kind and relation, plus the KG's own measures.

Reads the graph only: never loads the embedding model, so it is the
cheap first call of a session.

#### `query`(**q**, k=8, hop=0, max_nodes=25, rels, kinds, min_score=0.0)

Federated semantic search across every registered KG (or the kinds named), ranked together.

Each hit carries a federated `id` ("<kg>::<node id>") for get_node and
neighbors.

- `q` -- Natural-language query.
- `k` -- Hits per KG (default 8).
- `hop` -- Hops to walk from each hit inside its own KG (0-5, default 0: hits only).
- `max_nodes` -- Most results, hits first (default 25).
- `rels` -- Edge types to walk when hop > 0; omit for all.
- `kinds` -- Restrict to these KG kinds, e.g. ["code", "doc"].
- `min_score` -- Drop hits scoring below this (default 0).

#### `pack`(**q**, k=8, hop=0, max_nodes=15, rels, kinds, context=5)

Federated snippet pack: source text from every registered KG, as Markdown ready for a prompt.

- `q` -- Natural-language query.
- `k` -- Snippets per KG (default 8).
- `hop` -- Hops to walk from each snippet (0-5, default 0); what is reached is listed after.
- `max_nodes` -- Most snippets (default 15).
- `rels` -- Edge types to walk when hop > 0; omit for all.
- `kinds` -- Restrict to these KG kinds.
- `context` -- Lines of context around code snippets (default 5).

#### `get_node`(**node_id**)

One node by id, with its kind, location, docstring and metadata.

- `node_id` -- The node's id, as `query`, `pack` or `neighbors` returned it.

#### `neighbors`(**node_id**, rels, direction='both', limit=50)

A node's one-hop neighbourhood: its edges and the nodes at their far ends.

Reads the graph only, so it never loads the embedding model.

- `node_id` -- The node whose neighbours to return.
- `rels` -- Edge types to follow; omit for all of them.
- `direction` -- "out" (edges from the node), "in" (edges to it) or "both".
- `limit` -- Most edges to return (1-500).

### Registry

#### `list_kgs`(kind)

Every registered KG, with its kind, paths and build status.

- `kind` -- Only KGs of this kind, e.g. "code".

#### `kg_info`(**name**)

One registered KG in detail.

- `name` -- KG name or UUID.

### Corpora

#### `corpus_list`()

Every corpus (a named group of KGs) in the registry.

#### `corpus_info`(**name**)

One corpus in detail, with its member KGs.

- `name` -- Corpus name or UUID.

#### `corpus_create`(**name**, kg_names, description='', tags)

Create a corpus grouping registered KGs.

- `name` -- Corpus name.
- `kg_names` -- KG names or UUIDs to include.
- `description` -- What the corpus is for.
- `tags` -- Tags for grouping.

#### `corpus_delete`(**name**)

Delete a corpus; its KGs stay registered.

- `name` -- Corpus name or UUID.

#### `corpus_add`(**corpus**, **kg**)

Add a registered KG to a corpus.

- `corpus` -- Corpus name or UUID.
- `kg` -- KG name or UUID.

#### `corpus_remove`(**corpus**, **kg**)

Remove a KG from a corpus.

- `corpus` -- Corpus name or UUID.
- `kg` -- KG name or UUID.

#### `corpus_query`(**corpus**, **q**, k=8)

Federated semantic search within one corpus.

- `corpus` -- Corpus name or UUID.
- `q` -- Natural-language query.
- `k` -- Hits per KG (default 8).

#### `corpus_pack`(**corpus**, **q**, k=8, context=5)

Federated snippet pack within one corpus, as Markdown.

- `corpus` -- Corpus name or UUID.
- `q` -- Natural-language query.
- `k` -- Snippets per KG (default 8).
- `context` -- Lines of context around code snippets (default 5).

### Person corpora

#### `person_list`()

Every person corpus (the KGs relevant to one individual) in the registry.

#### `person_info`(**name**)

One person corpus in detail: personal metadata and member KGs.

- `name` -- Person name or UUID.

#### `person_create`(**name**, kg_names, birth_year, birth_date, address='', email='', phone='', notes='', tags)

Create a person corpus grouping the KGs relevant to one individual.

- `name` -- The person's full name.
- `kg_names` -- KG names or UUIDs to include.
- `birth_year` -- Year of birth.
- `birth_date` -- Date of birth, YYYY-MM-DD.
- `address` -- Mailing or home address.
- `email` -- Primary email address.
- `phone` -- Primary phone number.
- `notes` -- Free-form notes.
- `tags` -- Tags for grouping.

#### `person_delete`(**name**)

Delete a person corpus; its KGs stay registered.

- `name` -- Person name or UUID.

#### `person_add`(**person**, **kg**)

Add a registered KG to a person corpus.

- `person` -- Person name or UUID.
- `kg` -- KG name or UUID.

#### `person_remove`(**person**, **kg**)

Remove a KG from a person corpus.

- `person` -- Person name or UUID.
- `kg` -- KG name or UUID.

#### `person_update`(**name**, birth_year, birth_date, address, email, phone, notes)

Update a person corpus's personal metadata; omitted fields are left alone.

- `name` -- Person name or UUID.
- `birth_year` -- Year of birth.
- `birth_date` -- Date of birth, YYYY-MM-DD.
- `address` -- Mailing or home address.
- `email` -- Primary email address.
- `phone` -- Primary phone number.
- `notes` -- Free-form notes.

#### `person_query`(**person**, **q**, k=8)

Federated semantic search within one person corpus.

- `person` -- Person name or UUID.
- `q` -- Natural-language query.
- `k` -- Hits per KG (default 8).

#### `person_pack`(**person**, **q**, k=8, context=5)

Federated snippet pack within one person corpus, as Markdown.

- `person` -- Person name or UUID.
- `q` -- Natural-language query.
- `k` -- Snippets per KG (default 8).
- `context` -- Lines of context around code snippets (default 5).

<!-- END GENERATED TOOL REFERENCE -->

---

## Query Strategy Guide

### Typical agent workflow

```
1. stats()
   → confirm KGs are registered and built

2. list_kgs()
   → see names to use in subsequent calls

3. query(q="...", k=8)
   → broad exploration across all registered KGs

4. pack(q="...", k=6, context=5)
   → get source snippets + doc excerpts for LLM context
```

### Focused code-only exploration

```
query(q="database connection pooling", kinds=["code"])
pack(q="connection pool setup", kinds=["code"], k=6)
```

### Cross-source understanding (code + docs)

```
pack(q="user authentication flow", k=8)
# Returns code snippets from PyCodeKG and doc excerpts from DocKG together
```

### Corpus-scoped query

```
corpus_list()
→ see available corpora

corpus_query(corpus="KGRAG_repos", q="MCP server")
→ search within corpus

corpus_pack(corpus="KGRAG_repos", q="MCP server")
→ snippets from corpus
```

### Person corpus

```
person_list()
→ list all persons

person_query(person="Jane Doe", q="research notes")
→ search person's KGs

person_pack(person="Jane Doe", q="project history")
→ snippets from person
```

### Registry inspection

```
list_kgs(kind="code")          → all code KGs
kg_info(name="myrepo-code")   → full paths and timestamps
```

### When to use KGRAG vs. per-repo servers

| Situation | Tool |
|---|---|
| Broad exploration across all code + docs | `pack(q)` |
| Deep call-chain / AST analysis of one repo | `pack(q)` on the `pycodekg` server |
| Document section navigation for one corpus | `pack(q)` on the `dockg` server |
| Scoped query over a curated set of KGs | `corpus_pack(corpus, q)` |
| All knowledge about a specific person | `person_pack(person, q)` |

---

## Troubleshooting

| Symptom | Cause | Fix |
|---|---|---|
| `stats` returns `total: 0` | No KGs registered | Run `kgrag register --name <n> --kind <k> --repo <path>` |
| `query` returns no hits | KG not built or LanceDB index missing | Rebuild the KG (`pycodekg build` / `dockg build`), re-register if needed |
| `kg_info` returns `{"error": "Not found: ..."}` | Name/UUID mismatch | Check exact name with `list_kgs()` |
| MCP server not appearing in agent | Wrong/relative paths in MCP config, or agent not restarted | Use absolute venv path from `poetry env info --path`; restart the agent |
| `kgrag` command not found | Not installed as a global tool | `uv tool install kg-rag`; in Claude Desktop, use the path `command -v kgrag` prints |
| `corpus_query` raises KeyError | Corpus name doesn't exist | Check with `corpus_list()` first |
| Registry path mismatch | `$KGRAG_REGISTRY` not set consistently | Pass `--db` explicitly, or set `KGRAG_REGISTRY` in your shell and MCP config env |

---

## Environment Variables

| Variable | Description |
|----------|-------------|
| `KGRAG_REGISTRY` | Path to the registry SQLite file. Overrides the default `~/.kgrag/registry.sqlite`. Equivalent to `kgrag mcp --db`. |

---

## Summary

| Concern | Answer |
|---|---|
| What does the MCP server expose? | 24 tools: the five canonical (`stats`, `query`, `pack`, `get_node`, `neighbors`) across every registered KG, `list_kgs` and `kg_info`, 8 corpus tools and 9 person-corpus tools. `kgrag mcp --manifest` lists them. |
| What must exist before starting? | At least one KG registered via `kgrag register`; KG must be built |
| How do I start the server? | `kgrag mcp` — spawned automatically by the MCP client |
| Which tool should I call first? | `stats()` for orientation |
| Can it modify the registry? | Yes — corpus and person tools write to the registry SQLite |
| Can it modify KG graphs? | No — KG query/pack tools are strictly read-only |
| Default registry location | `~/.kgrag/registry.sqlite` (override with `KGRAG_REGISTRY`, or `kgrag mcp --db`) |
