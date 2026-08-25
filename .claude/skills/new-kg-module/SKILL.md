---
name: new-kg-module
description: Scaffold a complete new KGModule package for any knowledge domain. Use when the user wants to build a new domain knowledge graph using the KGModule SDK (e.g. "build a file tree KG", "create a TypeScript KG module", "scaffold a new KG for genomics data"). Invoked as "/new-kg-module NAME" where NAME is the snake_case package name (e.g. filetreekg, tskg, genomicskg).
---

# new-kg-module

Scaffold a complete KGModule package into a `<name>/` directory.

## Usage

```
/new-kg-module <name>
```

- `<name>` — snake_case package name, e.g. `filetreekg`, `tskg`, `legalkg`
- Derive `ClassName` = PascalCase, e.g. `FileTreeKG`
- Derive `ExtractorName` = `<ClassName>Extractor`, e.g. `FileTreeKGExtractor`
- Derive `AdapterName` = `<ClassName>Adapter`, e.g. `FileTreeKGAdapter`

## Step 1 — Ask four questions before writing

1. **Domain** — what kind of source does it parse? (file tree, TypeScript AST, genomics, etc.)
2. **Node kinds** — what node types? (e.g. `["file", "directory"]`)
3. **Edge kinds** — what relations? (e.g. `["CONTAINS", "REFERENCES"]`)
4. **KGKind** — `"code"`, `"doc"`, or `"meta"`?

Use answers to fill in stubs with real content rather than generic TODOs.

## Step 2 — Write these files

```
<name>/
├── __init__.py
├── extractor.py
├── module.py
├── adapter.py
└── tests/
    ├── __init__.py
    ├── test_extractor.py
    └── test_query.py
```

Read templates from `assets/` and substitute:
- `{{name}}` → snake_case name
- `{{ClassName}}` → PascalCase KG class
- `{{ExtractorName}}` → extractor class
- `{{AdapterName}}` → adapter class
- `{{node_kinds}}` → list from user answer
- `{{edge_kinds}}` → list from user answer
- `{{kg_kind}}` → `"code"` / `"doc"` / `"meta"`

## Key patterns (enforce strictly)

| Pattern | Rule |
|---------|------|
| Lazy init | `if self._kg is not None: return` |
| `is_available()` | import guard + `self.entry.is_built`, never raise |
| `query/pack/stats/analyze` | never raise — return `[]` or error Markdown |
| `stats()` | must include `"kind"` key |
| `node_id` | `'<kind>:<source_path>:<qualname>'` |
| `analyze()` | Markdown, first line `# <Name> Analysis` |
| `extract()` | yields `NodeSpec` and `EdgeSpec` in any order |

## Step 3 — Add CLI Integration (Optional but recommended)

Create a click-based CLI following the pycode_kg pattern:

```
<name>/cli/
├── __init__.py          # imports subcommand modules
├── main.py              # root Click group: @click.group() def cli()
├── options.py           # shared @click.option decorators
├── __main__.py          # entry point: if __name__ == "__main__": cli()
├── cmd_build.py         # @cli.command("build")
├── cmd_query.py         # @cli.command("query"), @cli.command("pack")
└── cmd_analyze.py       # @cli.command("analyze")
```

Add to `pyproject.toml`:

```toml
[tool.poetry.dependencies]
click = "^8.1.0"

[tool.poetry.scripts]
<name>            = "<name>.cli:cli"
<name>-build      = "<name>.cli.cmd_build:build"
<name>-query      = "<name>.cli.cmd_query:query"
<name>-pack       = "<name>.cli.cmd_query:pack"
<name>-analyze    = "<name>.cli.cmd_analyze:analyze"
<name>-snapshot   = "<name>.cli.cmd_snapshot:snapshot"
```

**CRITICAL:** Register EACH command individually in `[tool.poetry.scripts]`, not just the group.
This allows users to call:
- `<name>` — main group with all subcommands
- `<name>-build` — extract and build indices
- `<name>-query` — semantic search
- `<name>-pack` — get metadata snippets
- `<name>-analyze` — full analysis report
- `<name>-snapshot` — domain-appropriate snapshot management

Follow the pycode_kg pattern: prefix each script with `<name>-` and point to the function in the appropriate `cmd_*.py` module.

Key patterns:
- Use `@repo_option`, `@db_option`, `@include_option`, `@exclude_option` decorators
- Load config from `[tool.<name>]` in pyproject.toml using `load_include_dirs()`, `load_exclude_dirs()`
- CLI options override pyproject.toml settings
- Don't hardcode directory exclusions—let users configure via pyproject.toml

### Snapshot Command (CRITICAL)

Create `<name>/cli/cmd_snapshot.py` with domain-appropriate snapshot management:

```python
@cli.command("snapshot")
@repo_option
@db_option
@vectors_option
@click.option("--list", is_flag=True, help="List saved snapshots.")
@click.option("--show", type=str, help="Show specific snapshot details.")
@click.option("--diff", nargs=2, help="Compare two snapshots.")
def snapshot(repo, db, vectors, list, show, diff):
    """Manage and analyze domain-specific snapshots.

    For a filesystem tree KG: track file structure changes over time
    For a code KG: track architecture evolution, complexity trends
    For a document KG: track content updates, coverage metrics
    """
    # Implement domain-specific snapshot logic
    # Show: node/edge counts, metadata changes, domain metrics
    # Diff: track what changed between snapshots
    pass
```

Snapshots enable temporal analysis—comparing KG state across time to reveal trends, growth patterns, and structural evolution specific to your domain.

## Step 4 — Add Configuration Support

Create `<name>/config.py` for loading settings from `[tool.<name>]` in pyproject.toml:

```python
from pathlib import Path
import tomllib

def load_include_dirs(repo_root: Path | str) -> set[str]:
    """Load [tool.<name>].include from pyproject.toml."""
    # Use tomllib to parse; return set of directory names

def load_exclude_dirs(repo_root: Path | str) -> set[str]:
    """Load [tool.<name>].exclude from pyproject.toml."""
    # Use tomllib to parse; return set of directory names
```

Pass these to the extractor:

```python
def make_extractor(self) -> KGExtractor:
    return YourExtractor(
        self.repo_root,
        include_dirs=load_include_dirs(self.repo_root),
        exclude_dirs=load_exclude_dirs(self.repo_root),
    )
```

Add example config to `pyproject.toml`:

```toml
[tool.<name>]
# include = ["src", "docs"]  # only index these dirs
# exclude = ["archives"]     # exclude these dirs (in addition to defaults)
```

## Templates

- `assets/extractor.py.tpl` — KGExtractor subclass
- `assets/module.py.tpl` — KGModule subclass
- `assets/adapter.py.tpl` — KGAdapter shim
- `assets/init.py.tpl` — package `__init__`
- `assets/test_extractor.py.tpl` — extractor tests
- `assets/test_query.py.tpl` — query/pack tests
