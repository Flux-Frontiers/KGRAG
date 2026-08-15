"""Tests for ``kgrag install-hooks`` — the generated pre-commit hook.

The hook is an embedded shell string, so nothing type-checks it and nothing
imports it. It had rotted into writing across repository boundaries: it walked
to the parent directory and rebuilt, snapshotted and ``git add``ed inside
sibling checkouts. Committing in one repo silently staged files in others.

Nothing caught it because no test ever ran the hook. These do.
"""

from __future__ import annotations

import os
import shutil
import subprocess
from pathlib import Path

import pytest
from click.testing import CliRunner

from kg_rag.cli.cmd_hooks import _PRE_COMMIT_HOOK
from kg_rag.cli.group import cli

pytestmark = pytest.mark.skipif(
    shutil.which("git") is None or shutil.which("bash") is None,
    reason="hook execution needs git and bash",
)

#: Git environment variables that bind a command to a *specific* repository.
#: ``cwd=`` does not override them — git reads these first — so a test that only
#: sets ``cwd`` still operates on whatever repo the caller was in. That matters
#: here because the pytest pre-commit hook runs these tests *during* a commit.
_GIT_REPO_ENV = (
    "GIT_DIR",
    "GIT_INDEX_FILE",
    "GIT_WORK_TREE",
    "GIT_OBJECT_DIRECTORY",
    "GIT_COMMON_DIR",
    "GIT_ALTERNATE_OBJECT_DIRECTORIES",
)


def _clean_env(**extra: str) -> dict[str, str]:
    env = {k: v for k, v in os.environ.items() if k not in _GIT_REPO_ENV}
    env.update(extra)
    return env


def _git(*args: str, cwd: Path) -> subprocess.CompletedProcess:
    return subprocess.run(
        ["git", *args], cwd=cwd, capture_output=True, text=True, check=False, env=_clean_env()
    )


@pytest.fixture
def repo(tmp_path: Path) -> Path:
    """A real git repository with the hook installed."""
    _git("init", "-q", ".", cwd=tmp_path)
    _git("config", "user.email", "test@example.com", cwd=tmp_path)
    _git("config", "user.name", "Test", cwd=tmp_path)
    result = CliRunner().invoke(cli, ["install-hooks", "--repo", str(tmp_path)])
    assert result.exit_code == 0, result.output
    return tmp_path


def _stage(repo: Path, name: str) -> None:
    (repo / name).write_text("content\n")
    _git("add", name, cwd=repo)


class TestHookContents:
    """What the script says, before worrying about what it does."""

    def test_is_valid_bash(self, tmp_path: Path) -> None:
        script = tmp_path / "hook.sh"
        script.write_text(_PRE_COMMIT_HOOK)
        assert subprocess.run(["bash", "-n", str(script)], check=False).returncode == 0

    def test_does_not_walk_out_of_the_repository(self) -> None:
        """The bug this file exists for: no reaching into sibling checkouts."""
        assert "WORKSPACE_ROOT" not in _PRE_COMMIT_HOOK
        assert "REPO_ROOT/.." not in _PRE_COMMIT_HOOK

    def test_does_not_name_sibling_repositories(self) -> None:
        for sibling in ("pycode_kg", "doc_kg", "FTreeKG", "ftree_kg"):
            assert f"/{sibling}" not in _PRE_COMMIT_HOOK

    def test_does_not_pass_wipe_to_a_full_build(self) -> None:
        """`build` always wipes across the fleet; passing --wipe exits 2."""
        code = [ln for ln in _PRE_COMMIT_HOOK.splitlines() if not ln.lstrip().startswith("#")]
        assert not any("--wipe" in ln for ln in code)

    def test_honours_the_skip_switch(self) -> None:
        assert "KGRAG_SKIP_SNAPSHOT" in _PRE_COMMIT_HOOK


class TestInstall:
    def test_writes_an_executable_hook(self, repo: Path) -> None:
        hook = repo / ".git" / "hooks" / "pre-commit"
        assert hook.is_file()
        assert hook.stat().st_mode & 0o111

    def test_refuses_to_clobber_without_force(self, repo: Path) -> None:
        result = CliRunner().invoke(cli, ["install-hooks", "--repo", str(repo)])
        assert result.exit_code != 0
        assert "--force" in result.output


class TestHookExecution:
    """Does a commit still go through?"""

    def test_first_commit_in_a_fresh_repo_succeeds(self, repo: Path) -> None:
        """Unborn HEAD — `rev-parse --abbrev-ref HEAD` is fatal there."""
        _stage(repo, "a.txt")
        result = _git("commit", "-m", "init", cwd=repo)
        assert result.returncode == 0, result.stderr

    def test_subsequent_commits_succeed(self, repo: Path) -> None:
        _stage(repo, "a.txt")
        _git("commit", "-m", "init", cwd=repo)
        _stage(repo, "b.txt")
        result = _git("commit", "-m", "second", cwd=repo)
        assert result.returncode == 0, result.stderr

    def test_exits_zero_when_no_kg_indices_are_present(self, repo: Path) -> None:
        """A repo with no .pycodekg/.dockg/.filetreekg must commit unimpeded."""
        _stage(repo, "a.txt")
        _git("commit", "-m", "init", cwd=repo)
        result = subprocess.run(
            ["bash", str(repo / ".git" / "hooks" / "pre-commit")],
            cwd=repo,
            capture_output=True,
            text=True,
            env=_clean_env(),
            check=False,
        )
        assert result.returncode == 0, result.stderr

    def test_skip_switch_short_circuits(self, repo: Path) -> None:
        _stage(repo, "a.txt")
        _git("commit", "-m", "init", cwd=repo)
        result = subprocess.run(
            ["bash", str(repo / ".git" / "hooks" / "pre-commit")],
            cwd=repo,
            capture_output=True,
            text=True,
            env={"PATH": "/usr/bin:/bin", "KGRAG_SKIP_SNAPSHOT": "1", "HOME": str(repo)},
            check=False,
        )
        assert result.returncode == 0, result.stderr


class TestRepositoryIsolation:
    """The regression itself: a commit here must not write there."""

    def test_a_sibling_repository_is_left_untouched(self, tmp_path: Path) -> None:
        workspace = tmp_path / "ws"
        workspace.mkdir()

        sibling = workspace / "pycode_kg"
        (sibling / ".pycodekg" / "snapshots").mkdir(parents=True)
        _git("init", "-q", ".", cwd=sibling)
        _git("config", "user.email", "t@e.com", cwd=sibling)
        _git("config", "user.name", "T", cwd=sibling)
        (sibling / ".pycodekg" / "snapshots" / "keep.json").write_text("{}\n")
        _git("add", "-A", cwd=sibling)
        _git("commit", "-q", "-m", "sibling baseline", cwd=sibling)
        before = _git("rev-parse", "HEAD", cwd=sibling).stdout.strip()

        main = workspace / "kgrag"
        main.mkdir()
        _git("init", "-q", ".", cwd=main)
        _git("config", "user.email", "t@e.com", cwd=main)
        _git("config", "user.name", "T", cwd=main)
        assert CliRunner().invoke(cli, ["install-hooks", "--repo", str(main)]).exit_code == 0

        _stage(main, "a.txt")
        assert _git("commit", "-m", "init", cwd=main).returncode == 0

        assert _git("rev-parse", "HEAD", cwd=sibling).stdout.strip() == before
        assert _git("status", "--porcelain", cwd=sibling).stdout == "", (
            "committing in one repository must not stage or modify files in another"
        )
