# KGRAG Usage Guide

## Quick Start (5 minutes)

```bash
# 1. Initialize KGRAG for a project
cd ~/repos/myproject
kgrag init

# 2. Query all registered KGs
kgrag query "database connection setup"

# 3. Launch interactive visualizer
kgrag viz
# Open http://localhost:8501 in browser
```

That's it! KGRAG is now managing your KGs and you can start querying.

---

## KG Types

KGRAG supports the following knowledge graph kinds. Only `code` and `doc` have
fully-built backends today; the remaining kinds are **stubbed** — they can be
registered and queried, but return empty results until their backing library is
released.

| Kind | Status | Backing library | Description |
|------|--------|-----------------|-------------|
| `code` | **Available** | `code-kg` | Python source code: functions, classes, call graph |
| `doc` | **Available** | `doc-kg` | Markdown / RST documentation |
| `meta` | **Available** | `metakg` | Metabolic pathway graphs |
| `diary` | *Stubbed* | `diary_kg` *(unreleased)* | Personal diary / journal entries |
| `verse` | *Stubbed* | `verse_kg` *(unreleased)* | Poetry and verse |
| `memory` | *Stubbed* | `memory_kg` *(unreleased)* | Episodic / long-term memory |
| `disulfide` | *Stubbed* | `disulfide_kg` *(unreleased)* | Protein disulfide bond data |
| `pdbfile` | *Stubbed* | `pdbfile_kg` *(unreleased)* | Protein Data Bank (PDB) files |
| `legal` | *Stubbed* | `legal_kg` *(unreleased)* | US code, case law, legal corpus |
| `person` | *Stubbed* | `person_kg` *(unreleased)* | Individual-scoped knowledge graph |

Stubbed adapters still participate in the registry — you can register,
list, and inspect them — but `query` and `pack` return empty results until
the backing library is installed.

---

## Core Workflows

### Workflow 1: Federated Search

Query across all registered KGs simultaneously:

```bash
# Search all KGs
kgrag query "authentication flow"

# Search code KGs only
kgrag query "error handling" --kind code -k 5

# Search documentation only
kgrag query "REST API" --kind doc

# Get more results
kgrag query "transaction patterns" -k 12
```

**What happens:**
1. KGRAG searches all matching KGs
2. Results are ranked globally by relevance
3. Output shows KG source + node details + score

### Workflow 2: Extracting Context for LLM

Prepare markdown snippets for LLM analysis:

```bash
# Extract snippets across all KGs
kgrag pack "database transaction patterns"

# Extract to file
kgrag pack "error handling" --out context.md

# Code only, with minimal context
kgrag pack "API design" --kind code --context 2 -k 5

# High volume for comprehensive context
kgrag pack "authentication" -k 12 --context 10 --out auth_context.md
```

**Output:** Markdown file with:
- Source code snippets with line numbers
- File paths and KG names
- Relevance scores
- Ready to paste into LLM prompts

### Workflow 3: Setting Up Multiple Projects

Federate multiple projects under one registry:

```bash
# Initialize each project
kgrag init ~/repos/backend --name backend
kgrag init ~/repos/frontend --name frontend
kgrag init ~/repos/docs --name docs

# Verify all registered
kgrag status
kgrag list

# Now queries search all projects
kgrag query "caching strategy"
```

**Result:** All projects are federated. One query searches all.

### Workflow 4: Grouping KGs into a Corpus

A **corpus** is a named collection of KG instances that can be queried as a
unit:

```bash
# Create a corpus
kgrag corpus create my-project --kg my-codekg --kg my-dockg

# Query the corpus
kgrag corpus query my-project "how is authentication handled"

# Add / remove KGs later
kgrag corpus add my-project another-kg
kgrag corpus remove my-project old-kg

# List all corpora
kgrag corpus list

# Inspect a corpus
kgrag corpus info my-project
```

### Workflow 5: Person Corpora

A **person corpus** groups all KGs relevant to an individual (diary, memory,
doc, verse, code, etc.) alongside personal metadata:

```bash
# Create a person corpus
kgrag corpus person create "Jane Doe" \
    --kg jane-diary --kg jane-memories \
    --birth-year 1985 --email jane@example.com

# Query across all of Jane's KGs
kgrag corpus person query "Jane Doe" "childhood memories in Ohio"

# Update personal metadata
kgrag corpus person update "Jane Doe" --address "123 Main St, Springfield"

# List all people
kgrag corpus person list

# Inspect a person entry
kgrag corpus person info "Jane Doe"

# Add / remove a KG
kgrag corpus person add "Jane Doe" jane-legal-docs
kgrag corpus person remove "Jane Doe" old-kg
```

> **Note:** Queries against `diary`, `memory`, `verse`, and `person`-kind KGs
> return empty results today — those adapters are stubbed pending library release.

### Workflow 6: Interactive Exploration with Visualizer

```bash
kgrag viz
# Open http://localhost:8501
```

**Features:**
- **Registry tab** — Browse all KGs, view metadata, check build status
- **Federated Query** — Search all KGs, display results ranked or by KG
- **Analysis** — Run architectural analysis on CodeKGs
- **Snippet Pack** — Extract snippets with configurable parameters

### Workflow 7: Architectural Analysis

```bash
# Quick overview
kgrag analyze

# Or use visualizer → Analysis tab
```

---

## Command Reference

### Registry Commands

| Command | Description |
|---------|-------------|
| `kgrag list [--kind KIND]` | List registered KG instances, optionally filtered by kind |
| `kgrag status` | Registry health: counts, built/unbuilt, missing paths |
| `kgrag info NAME_OR_ID` | Detailed info for a specific KG |
| `kgrag analyze` | Statistics across all registered KGs |
| `kgrag register NAME KIND REPO_PATH` | Manually register a KG |
| `kgrag unregister NAME_OR_ID` | Remove a KG from the registry |
| `kgrag scan [ROOT_PATH]` | Discover existing KG databases in a directory tree |
| `kgrag init [REPO_PATH]` | Detect, build, and register KG layers for a repo |

#### `kgrag register`

```bash
kgrag register NAME KIND REPO_PATH [OPTIONS]

# Examples
kgrag register my-code code ~/repos/myproject
kgrag register my-docs doc ~/repos/myproject \
    --sqlite ~/repos/myproject/.dockg/graph.sqlite

# All supported kinds (stubbed ones can be registered but won't query)
kgrag register my-diary  diary  ~/data/journal
kgrag register case-law  legal  ~/data/legal
```

Options: `--venv`, `--sqlite`, `--lancedb`, `--version`, `--tag`

#### `kgrag scan`

```bash
kgrag scan [ROOT_PATH] [--auto-register]
```

Discovers `.codekg/`, `.dockg/`, `.metakg/`, `.diarykg/`, `.versekg/`,
`.memorykg/`, `.disulfidekg/`, `.pdbfilekg/`, `.legalkg/`, `.personkg/`
directories. Pass `--auto-register` to add them to the registry automatically.

#### `kgrag init`

```bash
kgrag init [REPO_PATH] [--wipe] [--name PREFIX] [--layer code|doc]
```

Detects applicable layers (`code`, `doc`), builds each, and registers them.
Layers other than `code`/`doc` must be registered manually via `kgrag register`.

---

### Query Commands

```bash
kgrag query QUERY_TEXT [-k N] [--kind KIND] [--json]
kgrag pack  QUERY_TEXT [-k N] [--kind KIND] [--context N] [--out FILE]
```

`--kind` accepts any of the 10 KG types. Queries against stubbed kinds
(diary, verse, memory, disulfide, pdbfile, legal, person) return no hits
until the backing library is installed.

---

### Corpus Commands

#### Generic corpus

| Command | Description |
|---------|-------------|
| `kgrag corpus create NAME [--kg KG]... [--desc TEXT] [--tag TAG]` | Create a corpus |
| `kgrag corpus delete NAME_OR_ID` | Delete a corpus |
| `kgrag corpus add CORPUS_NAME KG_REF` | Add a KG to a corpus |
| `kgrag corpus remove CORPUS_NAME KG_REF` | Remove a KG from a corpus |
| `kgrag corpus list` | List all corpora |
| `kgrag corpus info NAME_OR_ID` | Inspect a corpus |
| `kgrag corpus query CORPUS_NAME QUERY_TEXT [-k N] [--json]` | Federated query scoped to a corpus |

```bash
# Full example
kgrag corpus create law-library \
    --kg us-code --kg supremecourt --desc "US legal corpus"
kgrag corpus query law-library "first amendment protections" -k 10
```

#### Person corpus

| Command | Description |
|---------|-------------|
| `kgrag corpus person create NAME [--kg KG]... [OPTIONS]` | Create a person entry |
| `kgrag corpus person delete NAME_OR_ID` | Delete a person entry |
| `kgrag corpus person add PERSON KG_REF` | Add a KG to a person |
| `kgrag corpus person remove PERSON KG_REF` | Remove a KG from a person |
| `kgrag corpus person update NAME_OR_ID [OPTIONS]` | Update personal metadata |
| `kgrag corpus person list` | List all person entries |
| `kgrag corpus person info NAME_OR_ID` | Inspect a person entry |
| `kgrag corpus person query PERSON_NAME QUERY_TEXT [-k N] [--json]` | Federated query scoped to a person |

`kgrag corpus person create` options:

| Option | Type | Description |
|--------|------|-------------|
| `--kg TEXT` | repeatable | KG name or ID to include |
| `--birth-year INTEGER` | optional | Year of birth |
| `--birth-date TEXT` | optional | Full birth date (YYYY-MM-DD) |
| `--address TEXT` | optional | Mailing/home address |
| `--email TEXT` | optional | Primary email address |
| `--phone TEXT` | optional | Primary phone number |
| `--notes TEXT` | optional | Free-form notes |
| `--tag TEXT` | repeatable | Tags |

`kgrag corpus person update` accepts the same metadata options (omit any you
don't want to change).

---

### Integration Commands

```bash
kgrag viz [--port PORT]    # Launch Streamlit visualizer (default port 8501)
kgrag mcp                  # Start MCP server for Claude Code / Kilo Code
```

---

## Environment & Configuration

### Registry Path

```bash
export KGRAG_REGISTRY=/custom/path/registry.sqlite
# or pass per-command:
kgrag list --registry /custom/path/registry.sqlite
```

Default: `~/.kgrag/registry.sqlite`

### Rebuilding KGs

```bash
# After large refactors: full rebuild
kgrag init --wipe

# Minor additions: incremental
kgrag init
```

---

## Stubbed KG Types — What to Expect

When a KG is registered with a stubbed kind:

- `kgrag list` — shows the entry normally
- `kgrag info NAME` — shows full metadata
- `kgrag query` / `kgrag pack` — returns **0 results** (no error)
- `kgrag analyze` — reports `status: unavailable`
- `kgrag corpus query` / `kgrag corpus person query` — silently skips the stub KG

This allows you to register future KG instances now and start building corpora.
Results will appear automatically once the backing library (`diary_kg`,
`legal_kg`, etc.) is installed.

---

## Tips & Best Practices

### Querying Effectively

- Use specific terms: `"JWT validation"` not `"auth"`
- Filter by kind when appropriate: `--kind code`
- Start small: `-k 3` for focused, `-k 12` for surveys

### Managing Corpora

- Group related KGs at project creation: `--kg` is repeatable
- Use corpora to scope queries by domain (legal, personal, scientific)
- Person corpora naturally pair with `diary`, `memory`, and `doc` kinds

### MCP Integration

- Use absolute paths in `.mcp.json` (machine-specific — never commit it)
- Restart Claude Code after editing `.mcp.json`
- Test: `kgrag mcp --help`

---

## Troubleshooting Common Issues

### "No results found"

```bash
kgrag status                        # check health
kgrag info NAME                     # check is_built + kind
kgrag init ~/repos/myproject --wipe # rebuild if stale
```

If the KG kind is stubbed (diary, verse, memory, etc.), results will always
be empty until the backing library is released.

### "Registry not loading" in visualizer

Click **Refresh Registry** in the sidebar, or restart the visualizer.

### "MCP tools not appearing" in Claude Code

Verify `.mcp.json` uses absolute paths, then fully restart Claude Code.

For more, see [TROUBLESHOOTING.md](TROUBLESHOOTING.md).

---

## See Also

- [INSTALLATION.md](INSTALLATION.md) — Setup and configuration
- [TROUBLESHOOTING.md](TROUBLESHOOTING.md) — Issues and solutions
- [VISION.md](VISION.md) — Philosophy and design
- [MCP.md](MCP.md) — MCP server configuration and tools
