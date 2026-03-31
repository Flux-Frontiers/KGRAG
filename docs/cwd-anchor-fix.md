# CWD-Anchor Bug Fix — KG Build CLIs

**Date:** 2026-03-30
**Affects:** `doc_kg`, `ftreekg`, `kgrag`
**Status:** Fixed

---

## The Bug

When a KG build CLI accepts a `--repo /some/path` argument but its output
path options (`--sqlite`, `--lancedb`, `--db`) default to bare relative
strings like `".dockg/graph.sqlite"`, those paths resolve against the
**current working directory** of the shell — not against `--repo`.

This means running:

```bash
kgrag init ~/repos/Dracula          # or
dockg build --repo ~/repos/Dracula  # from any other directory
```

silently wrote the SQLite/LanceDB output into `$CWD/.dockg/` instead of
`~/repos/Dracula/.dockg/`.  The build appeared to succeed, but the files
landed in the wrong place, and subsequent queries (which look under the
repo directory) found nothing.

---

## Root Cause

### `doc_kg` — `options.py`

```python
# BEFORE (CWD-relative)
sqlite_option  = click.option("--sqlite",  default=".dockg/graph.sqlite", ...)
lancedb_option = click.option("--lancedb", default=".dockg/lancedb",      ...)
```

These bare string defaults were passed straight to `Path(sqlite)` /
`Path(lancedb)` in every build/query/snapshot command body, with no
anchoring to `--repo`.

### `ftreekg` — `options.py`

Same pattern:

```python
# BEFORE (CWD-relative)
db_option      = click.option("--db",      default=".filetreekg/graph.sqlite", ...)
lancedb_option = click.option("--lancedb", default=".filetreekg/lancedb",      ...)
```

### `kgrag` — `cmd_init.py`

`kgrag init` calls `dockg build --repo <repo>` via `subprocess.run(cmd,
check=True)` without setting `cwd`, so the subprocess inherited the shell's
CWD and `dockg`'s relative defaults resolved there.

### `code_kg` — **not affected**

`codekg` already used `default=None` and resolved output paths as
`repo_root / ".codekg" / ...` inside the function body.

---

## Fix

### Pattern (matches `code_kg`)

1. Set the option default to `None` in `options.py`.
2. In every command function body, resolve the path explicitly:

```python
repo_root = Path(repo).resolve()
db_path   = Path(sqlite) if sqlite else repo_root / ".dockg" / "graph.sqlite"
lancedb_dir = Path(lancedb) if lancedb else repo_root / ".dockg" / "lancedb"
```

This preserves explicit overrides (`--sqlite /abs/path` or `--sqlite
./rel/path` are used as-is) while anchoring the default to `--repo`.

---

## Files Changed

### `kgrag/src/kg_rag/cli/cmd_init.py`

```python
# BEFORE
subprocess.run(cmd, check=True)

# AFTER
subprocess.run(cmd, check=True, cwd=repo)
```

Ensures `dockg build` (and any future layer tool) runs with CWD = the repo
being initialised, so its own CWD-relative defaults land in the right place
even before the per-tool fix.

---

### `doc_kg/src/doc_kg/cli/options.py`

| Option | Before | After |
|---|---|---|
| `--sqlite` | `default=".dockg/graph.sqlite"` | `default=None` |
| `--lancedb` | `default=".dockg/lancedb"` | `default=None` |

Help text updated to `(default: <repo>/.dockg/...)`.

### `doc_kg/src/doc_kg/cli/cmd_build.py`

All three subcommands fixed:

| Command | Variables added |
|---|---|
| `build` | `repo_root`, `db_path`, `lancedb_dir` |
| `build-graph` | `repo_root`, `db_path` |
| `build-index` | `repo_root`, `db_path`, `lancedb_dir` |

Print lines updated to show resolved paths.

### `doc_kg/src/doc_kg/cli/cmd_query.py`

| Command | Variables added |
|---|---|
| `query` | `repo_root`, `db_path`, `lancedb_dir` |
| `pack`  | `repo_root`, `db_path`, `lancedb_dir` |

### `doc_kg/src/doc_kg/cli/cmd_snapshot.py`

| Command | Variables added |
|---|---|
| `snapshot save` | `db_path` resolved via `repo_root` |

---

### `ftreekg/src/ftree_kg/cli/options.py`

| Option | Before | After |
|---|---|---|
| `--db`      | `default=".filetreekg/graph.sqlite"` | `default=None` |
| `--lancedb` | `default=".filetreekg/lancedb"` | `default=None` |

Help text updated to `(default: <repo>/.filetreekg/...)`.

### `ftreekg/src/ftree_kg/cli/cmd_build.py`

| Command | Change |
|---|---|
| `build` | `db_path`, `lancedb_path` resolved via `repo_root` |

### `ftreekg/src/ftree_kg/cli/cmd_analyze.py`

| Command | Change |
|---|---|
| `analyze` | `db_path`, `lancedb_path` resolved via `repo_root` |

### `ftreekg/src/ftree_kg/cli/cmd_query.py`

| Command | Change |
|---|---|
| `query` | `db_path`, `lancedb_path` resolved via `repo_root` |
| `pack`  | `db_path`, `lancedb_path` resolved via `repo_root` |

### `ftreekg/src/ftree_kg/cli/cmd_snapshot.py`

| Command | Change |
|---|---|
| `snapshot save` | `db_path`, `lancedb_path` resolved via `repo_root` |

---

## Projects Not Affected

| Project | Reason |
|---|---|
| `code_kg` | Already used `default=None` + `repo_root` resolution — clean |
| `meta_kg` | No `--repo` concept; `--data` is required; CWD-relative output is intentional |

---

## Testing Checklist

### `doc_kg`

```bash
# From a directory other than the corpus root:
cd /tmp
dockg build --repo ~/repos/Dracula --wipe
# Verify: ~/repos/Dracula/.dockg/graph.sqlite exists
# Verify: ~/repos/Dracula/.dockg/lancedb/ exists

dockg query "vampire" --repo ~/repos/Dracula
dockg pack  "Mina"    --repo ~/repos/Dracula
dockg snapshot save 0.1.0 --repo ~/repos/Dracula
```

### `ftreekg`

```bash
cd /tmp
ftreekg build   --repo ~/repos/myproject --wipe
# Verify: ~/repos/myproject/.filetreekg/graph.sqlite exists
# Verify: ~/repos/myproject/.filetreekg/lancedb/ exists

ftreekg query   "Python source files" --repo ~/repos/myproject
ftreekg pack    "config files"        --repo ~/repos/myproject
ftreekg analyze --repo ~/repos/myproject
ftreekg snapshot save 0.1.0 --repo ~/repos/myproject
```

### `kgrag init`

```bash
cd /tmp
kgrag init ~/repos/Dracula --layer doc --wipe
# Verify: ~/repos/Dracula/.dockg/graph.sqlite exists (not /tmp/.dockg/)
```
