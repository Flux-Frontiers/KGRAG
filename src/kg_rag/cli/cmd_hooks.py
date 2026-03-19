"""
cmd_hooks.py

CLI command for installing KGRAG git hooks:

  install-hooks — install the pre-commit snapshot hook into .git/hooks/

The KGRAG hook orchestrates snapshots for all registered KGs (CodeKG, DocKG,
etc.) that live in the workspace, then runs quality checks.

  Author: Eric G. Suchanek, PhD
  Last Revision: 2026-03-18
"""

from __future__ import annotations

import stat
from pathlib import Path

import click

from kg_rag.cli.group import cli

# ---------------------------------------------------------------------------
# Hook script content (embedded so this module is self-contained when
# installed as a package in any repo, not just kgrag itself)
# ---------------------------------------------------------------------------

_PRE_COMMIT_HOOK = """\
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

# Capture the tree hash of the staged index NOW — before any tool modifies files.
TREE_HASH=$(git write-tree)
BRANCH=$(git rev-parse --abbrev-ref HEAD)

# ---------------------------------------------------------------------------
# CodeKG — rebuild + snapshot if present in workspace
# ---------------------------------------------------------------------------
CODEKG_REPO="${WORKSPACE_ROOT}/code_kg"
if [ -d "$CODEKG_REPO/.codekg" ]; then
    (cd "$CODEKG_REPO" && "$CODEKG_REPO/.venv/bin/codekg" build --repo . --wipe || exit 1)
    (cd "$CODEKG_REPO" && "$CODEKG_REPO/.venv/bin/codekg" snapshot save \\
        --repo . \\
        --tree-hash "$TREE_HASH" \\
        --branch "$BRANCH") \\
      || { echo "[kgrag] codekg snapshot skipped" >&2; }
    (cd "$CODEKG_REPO" && git add .codekg/snapshots/ 2>/dev/null || true)
fi

# ---------------------------------------------------------------------------
# DocKG — rebuild + snapshot if present in workspace
# ---------------------------------------------------------------------------
DOCKG_REPO="${WORKSPACE_ROOT}/doc_kg"
if [ -d "$DOCKG_REPO/.dockg" ]; then
    (cd "$DOCKG_REPO" && "$DOCKG_REPO/.venv/bin/dockg" build --wipe || exit 1)
    (cd "$DOCKG_REPO" && "$DOCKG_REPO/.venv/bin/dockg" snapshot save \\
        --repo . \\
        --tree-hash "$TREE_HASH" \\
        --branch "$BRANCH") \\
      || { echo "[kgrag] dockg snapshot skipped" >&2; }
    (cd "$DOCKG_REPO" && git add .dockg/snapshots/ 2>/dev/null || true)
fi

# ---------------------------------------------------------------------------
# FTreeKG — rebuild + snapshot if present in workspace
# ---------------------------------------------------------------------------
FTREEKG_REPO="${WORKSPACE_ROOT}/FTreeKG"
if [ -d "$FTREEKG_REPO/.filetreekg" ]; then
    (cd "$FTREEKG_REPO" && "$FTREEKG_REPO/.venv/bin/ftreekg" build --repo . --wipe || true)
    (cd "$FTREEKG_REPO" && "$FTREEKG_REPO/.venv/bin/ftreekg" snapshot save \\
        --repo . \\
        --tree-hash "$TREE_HASH" \\
        --branch "$BRANCH") \\
      || { echo "[kgrag] ftreekg snapshot skipped" >&2; }
    (cd "$FTREEKG_REPO" && git add .filetreekg/snapshots/ 2>/dev/null || true)
fi

# ---------------------------------------------------------------------------
# DiaryKG — snapshot if present in workspace
# ---------------------------------------------------------------------------
DIARYKG_REPO="${WORKSPACE_ROOT}/diary_kg"
if [ -d "$DIARYKG_REPO/.diarykg" ]; then
    (cd "$DIARYKG_REPO" && "$DIARYKG_REPO/.venv/bin/diarykg" snapshot save .) \\
      || { echo "[kgrag] diarykg snapshot skipped" >&2; }
    (cd "$DIARYKG_REPO" && git add .diarykg/snapshots/ 2>/dev/null || true)
fi

# ---------------------------------------------------------------------------
# Run pre-commit framework checks AFTER all snapshots are captured and staged.
# ---------------------------------------------------------------------------
PRECOMMIT="$REPO_ROOT/.venv/bin/pre-commit"
if [ -x "$PRECOMMIT" ]; then
    "$PRECOMMIT" run || exit 1
elif command -v pre-commit &>/dev/null; then
    pre-commit run || exit 1
fi

exit 0
"""


@cli.command("install-hooks")
@click.option(
    "--repo",
    default=".",
    type=click.Path(exists=True),
    show_default=True,
    help="Repository root.",
)
@click.option(
    "--force",
    is_flag=True,
    help="Overwrite an existing pre-commit hook.",
)
def install_hooks(repo: str, force: bool) -> None:
    """Install the KGRAG pre-commit git hook.

    After installation, before each commit the hook will:
      1. Rebuild + snapshot CodeKG (if workspace/code_kg is built)
      2. Rebuild + snapshot DocKG (if workspace/doc_kg is built)
      3. Rebuild + snapshot FTreeKG (if workspace/FTreeKG is built)
      4. Snapshot DiaryKG (if workspace/diary_kg is built)
      5. Stage all snapshot directories atomically
      6. Run pre-commit framework checks (ruff, mypy, etc.)

    Skip with: KGRAG_SKIP_SNAPSHOT=1 git commit ...

    Example:
        kgrag install-hooks --repo .
    """
    repo_root = Path(repo).resolve()
    git_dir = repo_root / ".git"

    if not git_dir.is_dir():
        click.echo(f"Error: {repo_root} is not a git repository.", err=True)
        raise SystemExit(1)

    hooks_dir = git_dir / "hooks"
    hooks_dir.mkdir(exist_ok=True)
    hook_path = hooks_dir / "pre-commit"

    if hook_path.exists() and not force:
        click.echo(f"Hook already exists: {hook_path}")
        click.echo("Use --force to overwrite.")
        raise SystemExit(1)

    hook_path.write_text(_PRE_COMMIT_HOOK)
    mode = hook_path.stat().st_mode | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH
    hook_path.chmod(mode)

    click.echo(f"OK Installed pre-commit hook: {hook_path}")
    click.echo("  Snapshots will be captured automatically before each commit.")
    click.echo("  Orchestrates: CodeKG, DocKG, FTreeKG, DiaryKG (if built).")
