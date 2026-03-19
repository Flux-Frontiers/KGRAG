# CI Hooks & Quality Gate Flow

*How every commit to KGRAG is validated — from local pre-commit to GitHub Actions.*

---

## Overview

KGRAG uses **three layers** of automated quality gates that run in sequence:

| Layer | Where | Trigger | Tools |
|-------|-------|---------|-------|
| **1. KGRAG git hook** | Local | `git commit` | KG rebuild + snapshot (CodeKG, DocKG, FTreeKG) |
| **2. pre-commit framework** | Local | End of KGRAG hook | ruff, mypy, pytest, pylint, detect-secrets, file checks |
| **3. GitHub Actions** | Remote | Push / PR to `main`, `v*` tags | ruff, mypy, pytest, publish |

Layers 1 and 2 run locally on every commit. Layer 3 runs in CI on every push to
`main` or pull request, and on every version tag for publishing.

---

## Layer 1 — KGRAG Pre-commit Git Hook

Installed once per repository via:

```bash
kgrag install-hooks [--repo .] [--force]
```

This writes `.git/hooks/pre-commit` with the embedded hook script from
`src/kg_rag/cli/cmd_hooks.py`. The hook runs **before** the pre-commit
framework, ensuring KG snapshots are captured and staged as part of the commit.

### What it does

```
git commit
    │
    ▼
.git/hooks/pre-commit
    │
    ├─ 1. Capture git tree hash + branch name (before any tool modifies files)
    │       TREE_HASH=$(git write-tree)
    │       BRANCH=$(git rev-parse --abbrev-ref HEAD)
    │
    ├─ 2. CodeKG  [if $WORKSPACE_ROOT/code_kg/.codekg exists]
    │       codekg build --repo . --wipe
    │       codekg snapshot save --tree-hash $TREE_HASH --branch $BRANCH
    │       git add .codekg/snapshots/
    │
    ├─ 3. DocKG   [if $WORKSPACE_ROOT/doc_kg/.dockg exists]
    │       dockg build --wipe
    │       dockg snapshot save --tree-hash $TREE_HASH --branch $BRANCH
    │       git add .dockg/snapshots/
    │
    ├─ 4. FTreeKG [if $WORKSPACE_ROOT/FTreeKG/.filetreekg exists]
    │       ftreekg build --repo . --wipe
    │       ftreekg snapshot save --tree-hash $TREE_HASH --branch $BRANCH
    │       git add .filetreekg/snapshots/
    │
    └─ 5. Run pre-commit framework (Layer 2) ──────────────────────────────┐
                                                                            │
    Skip everything: KGRAG_SKIP_SNAPSHOT=1 git commit -m "..."             │
```

### Key design decisions

- **Tree hash captured first** — `git write-tree` runs before any tool modifies
  files, so the snapshot key is stable and matches the exact staged content.
- **Snapshots staged atomically** — each KG's `snapshots/` directory is added
  to the index before the pre-commit framework runs, so snapshot files travel
  with the commit.
- **Failures are non-fatal for snapshots** — if a snapshot save fails (e.g. the
  KG library is not installed), a warning is printed to stderr and the hook
  continues. The build step (`codekg build`) is fatal — a broken build blocks
  the commit.
- **FTreeKG build is non-fatal** — uses `|| true` because FTreeKG is optional
  infrastructure; a build failure there should not block a commit.
- **Each KG is presence-checked** — the hook only runs a KG section if the
  corresponding database directory exists. Absent KGs are silently skipped.

### The embedded hook script

The hook is embedded as a string constant `_PRE_COMMIT_HOOK` in
`src/kg_rag/cli/cmd_hooks.py` so the package is self-contained — no external
script files are needed.

```bash
#!/usr/bin/env bash
# KGRAG pre-commit hook — keeps registered KG indices in sync and captures
# metrics snapshots BEFORE quality checks run.
# Installed by: kgrag install-hooks
# Skip with: KGRAG_SKIP_SNAPSHOT=1 git commit ...
set -euo pipefail

[ "${KGRAG_SKIP_SNAPSHOT:-0}" = "1" ] && exit 0

REPO_ROOT="$(git rev-parse --show-toplevel)"
WORKSPACE_ROOT="$(cd "$REPO_ROOT/.." && pwd)"

cd "$REPO_ROOT"

TREE_HASH=$(git write-tree)
BRANCH=$(git rev-parse --abbrev-ref HEAD)

# CodeKG
CODEKG_REPO="${WORKSPACE_ROOT}/code_kg"
if [ -d "$CODEKG_REPO/.codekg" ]; then
    (cd "$CODEKG_REPO" && "$CODEKG_REPO/.venv/bin/codekg" build --repo . --wipe || exit 1)
    (cd "$CODEKG_REPO" && "$CODEKG_REPO/.venv/bin/codekg" snapshot save \
        --repo . --tree-hash "$TREE_HASH" --branch "$BRANCH") \
      || { echo "[kgrag] codekg snapshot skipped" >&2; }
    (cd "$CODEKG_REPO" && git add .codekg/snapshots/ 2>/dev/null || true)
fi

# DocKG
DOCKG_REPO="${WORKSPACE_ROOT}/doc_kg"
if [ -d "$DOCKG_REPO/.dockg" ]; then
    (cd "$DOCKG_REPO" && "$DOCKG_REPO/.venv/bin/dockg" build --wipe || exit 1)
    (cd "$DOCKG_REPO" && "$DOCKG_REPO/.venv/bin/dockg" snapshot save \
        --repo . --tree-hash "$TREE_HASH" --branch "$BRANCH") \
      || { echo "[kgrag] dockg snapshot skipped" >&2; }
    (cd "$DOCKG_REPO" && git add .dockg/snapshots/ 2>/dev/null || true)
fi

# FTreeKG
FTREEKG_REPO="${WORKSPACE_ROOT}/FTreeKG"
if [ -d "$FTREEKG_REPO/.filetreekg" ]; then
    (cd "$FTREEKG_REPO" && "$FTREEKG_REPO/.venv/bin/ftreekg" build --repo . --wipe || true)
    (cd "$FTREEKG_REPO" && "$FTREEKG_REPO/.venv/bin/ftreekg" snapshot save \
        --repo . --tree-hash "$TREE_HASH" --branch "$BRANCH") \
      || { echo "[kgrag] ftreekg snapshot skipped" >&2; }
    (cd "$FTREEKG_REPO" && git add .filetreekg/snapshots/ 2>/dev/null || true)
fi

# Run pre-commit framework
PRECOMMIT="$REPO_ROOT/.venv/bin/pre-commit"
if [ -x "$PRECOMMIT" ]; then
    "$PRECOMMIT" run || exit 1
elif command -v pre-commit &>/dev/null; then
    pre-commit run || exit 1
fi

exit 0
```

---

## Layer 2 — pre-commit Framework (`.pre-commit-config.yaml`)

Invoked as the final step of the KGRAG hook, or standalone via `pre-commit run`.
Configured in `.pre-commit-config.yaml`.

```
pre-commit run
    │
    ├─ pre-commit-hooks  v5.0.0
    │     ├─ trailing-whitespace       — strip trailing spaces
    │     ├─ end-of-file-fixer         — ensure files end with newline
    │     ├─ check-yaml                — validate YAML syntax
    │     ├─ check-toml                — validate TOML syntax
    │     ├─ check-merge-conflict      — block accidental conflict markers
    │     ├─ check-added-large-files   — max 1000 KB
    │     │     (excludes: images, PDFs, .kgrag/ dirs)
    │     └─ debug-statements          — catch leftover breakpoint() / pdb calls
    │
    ├─ pylint  v4.0.4  (src/ only, --rcfile=pyproject.toml)
    │     Enabled checks only:
    │       cyclic-import           (R0401)
    │       broad-exception-caught  (W0718)
    │       cell-var-from-loop      (W0640)
    │       undefined-variable      (E0602)
    │       import-outside-toplevel (C0415)
    │
    ├─ mypy  (local .venv/bin/mypy src/)
    │     always_run: true  — runs even when no Python files are staged
    │     pass_filenames: false  — always checks the full src/ tree
    │     Config: [tool.mypy] in pyproject.toml
    │       python_version = "3.12"
    │       strict = false
    │       ignore_missing_imports = true
    │
    ├─ pytest  (local .venv/bin/pytest --tb=short -q)
    │     always_run: true  — runs on every commit regardless of staged files
    │     testpaths = ["tests"]  (from [tool.pytest.ini_options])
    │
    ├─ detect-secrets  v1.5.0
    │     Baseline: .secrets.baseline
    │     Excludes: .kgrag/, .codekg/, .dockg/ directories
    │
    └─ ruff  v0.9.10
          ├─ ruff check --fix   (rules: E, F, W, I, UP; line-length=100)
          └─ ruff-format        (auto-format)
```

### Pylint configuration (`pyproject.toml`)

```toml
[tool.pylint.messages_control]
disable = ["all"]
enable = [
    "cyclic-import",           # R0401
    "broad-exception-caught",  # W0718
    "cell-var-from-loop",      # W0640
    "undefined-variable",      # E0602
    "import-outside-toplevel", # C0415
]
```

All other pylint checks are disabled — only the five highest-signal issues are
enforced to keep the gate fast and low-noise.

### Ruff configuration (`pyproject.toml`)

```toml
[tool.ruff]
line-length = 100
target-version = "py312"

[tool.ruff.lint]
select = ["E", "F", "W", "I", "UP"]
ignore = ["E501"]   # line-length enforced by formatter, not linter
```

---

## Layer 3 — GitHub Actions (`.github/workflows/`)

### `ci.yml` — Push / PR to `main`

Triggers on every push to `main` and every pull request targeting `main`.
Runs **three parallel jobs** — all must pass for the branch to be mergeable.

```
push or PR → main
    │
    ├─ [lint]        Python 3.12, dev deps only (cached .venv)
    │                  ruff format --check .
    │                  ruff check .
    │
    ├─ [type-check]  Python 3.12, full deps (cached .venv)
    │                  mypy src/
    │
    └─ [test]        Python 3.12, full deps (cached .venv)
                       pytest
```

Each job uses `snok/install-poetry@v1` with `virtualenvs-in-project: true` and
`actions/cache@v4` keyed on `poetry.lock` — so the `.venv` is rebuilt only when
dependencies change.

The `lint` job installs only `--only dev` dependencies (no heavy ML libraries)
to keep it fast. `type-check` and `test` install the full dependency set.

### `publish.yml` — Version tag push (`v*`)

Triggers when a tag matching `v*` is pushed. Runs a single sequential job.

```
git push tag v1.2.3
    │
    └─ [Build & Release]
          ├─ poetry install --no-interaction   (full deps)
          ├─ pytest --tb=short -q              (gate: must pass to continue)
          ├─ poetry build                      (→ dist/*.whl + dist/*.tar.gz)
          └─ gh release create/upload
                title:  "CodeKG v1.2.3"
                notes:  release-notes.md
                assets: dist/*
                (idempotent: uploads to existing release if tag already exists)
```

Requires `permissions: contents: write` (set in the workflow) so the GitHub
Actions bot can create releases and upload assets.

---

## Summary: Full Commit Flow

```
developer runs: git commit -m "feat: ..."
    │
    ▼
[Layer 1] .git/hooks/pre-commit  (KGRAG orchestrator)
    ├─ git write-tree  → stable TREE_HASH
    ├─ CodeKG build + snapshot  → .codekg/snapshots/<hash>.json
    ├─ DocKG  build + snapshot  → .dockg/snapshots/<hash>.json
    ├─ FTreeKG build + snapshot → .filetreekg/snapshots/<hash>.json
    ├─ git add <all snapshot dirs>
    └─ invoke pre-commit framework ──────────────────────────────────┐
                                                                     │
    [Layer 2] pre-commit framework                                   │
        ├─ trailing-whitespace / end-of-file-fixer                   │
        ├─ check-yaml / check-toml / check-merge-conflict            │
        ├─ check-added-large-files (≤1000 KB)                        │
        ├─ debug-statements                                          │
        ├─ pylint (cyclic-import, broad-except, undef-var, …)        │
        ├─ mypy src/  (always_run)                                   │
        ├─ pytest --tb=short -q  (always_run)                        │
        ├─ detect-secrets --baseline .secrets.baseline               │
        ├─ ruff check --fix                                          │
        └─ ruff-format                                               │
                                                                     │
    commit created (with snapshot files included) ◄──────────────────┘
    │
    ▼
git push → main (or PR opened)
    │
    [Layer 3] GitHub Actions: ci.yml
        ├─ [lint]       ruff format --check + ruff check
        ├─ [type-check] mypy src/
        └─ [test]       pytest
    │
    ▼  (all three pass)
merge allowed
    │
    ▼  (maintainer tags: git tag v1.2.3 && git push --tags)
    [Layer 3] GitHub Actions: publish.yml
        ├─ pytest  (gate)
        ├─ poetry build
        └─ gh release create + upload dist/*
```

---

## Skipping the Hook

For commits that don't need KG snapshots (docs-only, CI config changes, etc.):

```bash
KGRAG_SKIP_SNAPSHOT=1 git commit -m "docs: update README"
```

This exits the KGRAG hook immediately and falls through to the pre-commit
framework checks, which still run normally.

---

## Installation

```bash
# Install the KGRAG git hook into the current repo
kgrag install-hooks

# Overwrite an existing hook
kgrag install-hooks --force

# Install into a different repo
kgrag install-hooks --repo /path/to/other/repo

# Install the pre-commit framework hooks (separate step)
pre-commit install
```

Both `kgrag install-hooks` and `pre-commit install` must be run once after
cloning. The KGRAG hook calls the pre-commit framework internally, so only
`.git/hooks/pre-commit` needs to exist — not `.git/hooks/pre-commit` from
pre-commit directly (the KGRAG hook replaces it).

---

## See Also

- `src/kg_rag/cli/cmd_hooks.py` — hook installer and embedded script source
- `.pre-commit-config.yaml` — pre-commit framework configuration
- `.github/workflows/ci.yml` — GitHub Actions CI workflow
- `.github/workflows/publish.yml` — GitHub Actions publish workflow
- `.github/SNAPSHOTS_CI.md` — snapshot system documentation
- [ADAPTER_SPEC.md](ADAPTER_SPEC.md) — snapshot requirements for new KG adapters
