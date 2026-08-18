"""
cmd_hooks.py

CLI command for installing KGRAG git hooks:

  install-hooks — install the pre-commit snapshot hook into .git/hooks/

The KGRAG hook orchestrates snapshots for all registered KGs (PyCodeKG, DocKG,
etc.) that live in the workspace, then runs quality checks.

  Author: Eric G. Suchanek, PhD
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
# KGRAG pre-commit hook — rebuilds this repository's KG indices and captures
# metrics snapshots BEFORE quality checks run.
# Installed by: kgrag install-hooks
# Skip with: KGRAG_SKIP_SNAPSHOT=1 git commit ...
#
# This hook touches THIS repository and nothing else. An earlier version walked
# to the parent directory and rebuilt, snapshotted and `git add`ed inside
# sibling checkouts (pycode_kg, doc_kg, FTreeKG). That is not a hook's business:
# committing in one repo silently wrote into others, staged files there, and
# tagged their snapshots with this repo's tree hash and branch name — so a
# pycode_kg snapshot would claim to describe pycode_kg at a kgrag commit. It
# also raced pre-commit's own git plumbing and aborted commits outright.
#
# Snapshots are opt-in and OFF by default (2026-08-18):
#
#   KGRAG_SNAPSHOT=1 git commit ...        opt in to per-commit snapshots
#   KGRAG_SKIP_SNAPSHOT=1 git commit ...   force snapshots off (wins)
#
# KGRAG_SKIP_SNAPSHOT no longer skips the quality checks. It used to
# short-circuit the whole hook, so a variable named "skip snapshot" also
# silently skipped ruff, ty and pytest. It now gates only what it names.
#
# A per-commit snapshot records `git write-tree` and is then staged into that
# same commit, so the recorded hash can never equal the tree it names — an
# audit of 605 fleet snapshots found only 63 (10.4%) keyed to a real commit
# tree. The fix is to snapshot at release, keyed on the tag; until that lands
# this hook runs quality checks only.
# See kgrag_priv/docs/SNAPSHOT_STRATEGY.md.
set -euo pipefail

REPO_ROOT="$(git rev-parse --show-toplevel)"
cd "$REPO_ROOT"

# ---------------------------------------------------------------------------
# Quality checks FIRST. This used to run last, after the snapshots were built
# and staged, which meant `pre-commit run`'s stash/restore window contained
# freshly-rewritten snapshot files, and a rejected commit had already paid for
# three index rebuilds.
# ---------------------------------------------------------------------------
# The config gate is load-bearing: `pre-commit run` exits non-zero with
# "InvalidConfigError: .pre-commit-config.yaml is not a file" when there is no
# config, so without it this hook blocks every commit in any repo that
# installed it without also adopting pre-commit. Metabo_kg fixed the same
# defect in its own hook.
if [ -f "$REPO_ROOT/.pre-commit-config.yaml" ]; then
    PRECOMMIT="$REPO_ROOT/.venv/bin/pre-commit"
    if [ -x "$PRECOMMIT" ]; then
        "$PRECOMMIT" run || exit 1
    elif command -v pre-commit &>/dev/null; then
        pre-commit run || exit 1
    fi
fi

# ---------------------------------------------------------------------------
# Opt-in index rebuilds + snapshots. Everything below is skipped unless
# KGRAG_SNAPSHOT=1 is set, and is skipped regardless if KGRAG_SKIP_SNAPSHOT=1.
# ---------------------------------------------------------------------------
[ "${KGRAG_SNAPSHOT:-0}" = "1" ] || exit 0
[ "${KGRAG_SKIP_SNAPSHOT:-0}" = "1" ] && exit 0

# Captured after the checks so nothing further modifies the working tree. Note
# the caveat above: this still cannot match the committed tree, because the
# `git add` calls below change the index after this point.
TREE_HASH=$(git write-tree)
BRANCH=$(git rev-parse --abbrev-ref HEAD 2>/dev/null || echo "HEAD")

# Resolve a CLI from this repo's venv first, then PATH. Absent is fine: a repo
# that does not carry a given index simply skips it.
_kg_bin() {
    if [ -x "$REPO_ROOT/.venv/bin/$1" ]; then
        echo "$REPO_ROOT/.venv/bin/$1"
    elif command -v "$1" >/dev/null 2>&1; then
        command -v "$1"
    fi
}

# build + snapshot + stage one index, all inside this repo.
#   $1 CLI name   $2 index directory   $3 snapshot path to stage
_kg_refresh() {
    local cli="$1" dir="$2" staged="$3" bin
    [ -d "$REPO_ROOT/$dir" ] || return 0
    bin="$(_kg_bin "$cli")"
    [ -n "$bin" ] || return 0

    # No --wipe on any of these: a bare `build` rebuilds in full across the
    # fleet, and passing the flag exits 2.
    "$bin" build --repo "$REPO_ROOT" \
      || { echo "[kgrag] $cli build failed — snapshot skipped" >&2; return 0; }
    "$bin" snapshot save --repo "$REPO_ROOT" --tree-hash "$TREE_HASH" --branch "$BRANCH" \
      || { echo "[kgrag] $cli snapshot skipped" >&2; return 0; }
    git add "$staged" 2>/dev/null || true
}

_kg_refresh pycodekg .pycodekg .pycodekg/snapshots/
_kg_refresh dockg    .dockg    .dockg/snapshots/
_kg_refresh ftreekg  .filetreekg .filetreekg/snapshots/

# Quality checks already ran, before any of the above.

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

    After installation, before each commit the hook will, **for this
    repository only**:
      1. Rebuild + snapshot PyCodeKG   (if ./.pycodekg exists)
      2. Rebuild + snapshot DocKG      (if ./.dockg exists)
      3. Rebuild + snapshot FTreeKG    (if ./.filetreekg exists)
      4. Stage the snapshot directories it wrote
      5. Run pre-commit framework checks (ruff, ty, etc.)

    Each step is skipped when the index directory or the CLI is absent, so a
    repo that carries only one of the three works unchanged. The hook never
    touches a repository other than the one being committed to.

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
    click.echo("  Refreshes this repo's PyCodeKG / DocKG / FTreeKG indices, if present.")
