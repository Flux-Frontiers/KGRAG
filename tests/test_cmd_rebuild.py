"""
test_cmd_rebuild.py

Tests for ``kgrag rebuild-indices``. The builders are small executable
scripts placed on PATH, so each test runs the real subprocess path against a
temporary registry; nothing is mocked.
"""

from __future__ import annotations

import os
import sqlite3
from pathlib import Path

import pytest
from click.testing import CliRunner

from kg_rag.cli.cmd_rebuild import find_builder, plan
from kg_rag.cli.main import cli
from kg_rag.corpus_registry import CorpusRegistry
from kg_rag.primitives import CorpusEntry, KGEntry, KGKind
from kg_rag.registry import KGRegistry

# A builder that logs its argv and cwd, then stamps a builder version into the
# store under --repo (or the positional root), as a real fleet builder does.
_OK = """#!/bin/sh
echo "$0 $* cwd=$(pwd)" >> "{log}"
root="$3"; [ -z "$root" ] && root="$2"
mkdir -p "$root/{marker}"
sqlite3 "$root/{marker}/graph.sqlite" \
  "CREATE TABLE IF NOT EXISTS _kgrag_meta (key TEXT PRIMARY KEY, value TEXT);
   INSERT OR REPLACE INTO _kgrag_meta VALUES ('builder_version', '9.9.9');"
"""
_FAIL = """#!/bin/sh
echo "$0 $*" >> "{log}"
exit 3
"""


def _script(bin_dir: Path, name: str, body: str, **fmt) -> Path:
    """Write an executable builder script.

    :param bin_dir: Folder to write it in.
    :param name: The CLI name.
    :param body: Script template.
    :return: The script's path.
    """
    bin_dir.mkdir(parents=True, exist_ok=True)
    path = bin_dir / name
    path.write_text(body.format(**fmt))
    path.chmod(0o755)
    return path


def _entry(tmp: Path, name: str, kind: KGKind, marker: str) -> KGEntry:
    """Return a registry entry whose store folder exists under *tmp*.

    :param tmp: Test folder.
    :param name: KG and repo name.
    :param kind: KG kind.
    :param marker: Store folder name, such as ``.pycodekg``.
    :return: The entry (not yet registered).
    """
    repo = tmp / "repos" / name
    (repo / marker).mkdir(parents=True)
    sqlite = repo / marker / "graph.sqlite"
    sqlite3.connect(sqlite).close()
    return KGEntry(
        name=name, kind=kind, repo_path=repo, venv_path=repo / ".venv", sqlite_path=sqlite
    )


@pytest.fixture
def env(tmp_path, monkeypatch):
    """A temp registry with a code, a doc, an agent and a gutenberg KG, and a
    PATH holding only the test's builder scripts plus the system tools.
    """
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    monkeypatch.setenv("PATH", f"{bin_dir}{os.pathsep}/usr/bin{os.pathsep}/bin")
    reg_path = tmp_path / "registry.sqlite"
    entries = {
        "alpha-code": _entry(tmp_path, "alpha-code", KGKind.CODE, ".pycodekg"),
        "beta-doc": _entry(tmp_path, "beta-doc", KGKind.DOC, ".dockg"),
        "gamma-agent": _entry(tmp_path, "gamma-agent", KGKind.AGENT, ".agentkg"),
        "delta-book": _entry(tmp_path, "delta-book", KGKind.GUTENBERG, ".dockg"),
    }
    with KGRegistry(db_path=reg_path) as reg:
        for e in entries.values():
            reg.register(e)
    log = tmp_path / "calls.log"
    return {"tmp": tmp_path, "bin": bin_dir, "reg": reg_path, "log": log, "entries": entries}


def _run(env, *args):
    return CliRunner().invoke(
        cli, ["rebuild-indices", "--registry", str(env["reg"]), *args], catch_exceptions=False
    )


def _calls(env) -> list[str]:
    return env["log"].read_text().splitlines() if env["log"].exists() else []


class TestPlan:
    def test_agent_and_gutenberg_are_skipped_with_reasons(self, env):
        argv, reason = plan(env["entries"]["gamma-agent"])
        assert argv is None and "conversation memory" in reason
        argv, reason = plan(env["entries"]["delta-book"])
        assert argv is None and "static corpus" in reason

    def test_missing_folder_is_skipped(self, tmp_path):
        gone = tmp_path / "gone"
        e = KGEntry(
            name="g",
            kind=KGKind.CODE,
            repo_path=gone,
            venv_path=gone / ".venv",
            sqlite_path=gone / ".pycodekg" / "graph.sqlite",
        )
        argv, reason = plan(e)
        assert argv is None and reason.startswith("folder missing")

    def test_missing_builder_is_skipped(self, env):
        argv, reason = plan(env["entries"]["alpha-code"])
        assert argv is None and "pycodekg not on PATH" in reason

    def test_root_comes_from_the_store_not_repo_path(self, env):
        """A store at <repo>/docs/.dockg builds in <repo>/docs."""
        _script(env["bin"], "dockg", _OK, log=env["log"], marker=".dockg")
        repo = env["tmp"] / "repos" / "withdocs"
        (repo / "docs" / ".dockg").mkdir(parents=True)
        e = KGEntry(
            name="d",
            kind=KGKind.DOC,
            repo_path=repo,
            venv_path=repo / ".venv",
            sqlite_path=repo / "docs" / ".dockg" / "graph.sqlite",
        )
        argv, _ = plan(e)
        assert argv[1:] == ["build", "--repo", str((repo / "docs").resolve())]

    def test_vault_and_diary_take_their_own_root_argument(self, env):
        _script(env["bin"], "vaultkg", _OK, log=env["log"], marker=".vaultkg")
        _script(env["bin"], "diarykg", _OK, log=env["log"], marker=".diarykg")
        vault = _entry(env["tmp"], "v", KGKind.VAULT, ".vaultkg")
        diary = _entry(env["tmp"], "p", KGKind.DIARY, ".diarykg")
        assert plan(vault)[0][1:] == ["build", "--vault", str(vault.repo_path)]
        assert plan(diary)[0][1:] == ["build", str(diary.repo_path)]


class TestFindBuilder:
    def test_path_wins_over_a_venv(self, env):
        on_path = _script(env["bin"], "pycodekg", _OK, log=env["log"], marker=".pycodekg")
        e = env["entries"]["alpha-code"]
        _script(e.repo_path / ".venv" / "bin", "pycodekg", _OK, log=env["log"], marker=".pycodekg")
        assert find_builder("pycodekg", e) == str(on_path)

    def test_falls_back_to_the_nearest_venv_above_the_store(self, tmp_path, monkeypatch):
        """A genealogy corpus entry records a venv inside itself that does not
        exist; the builder is in the repo's .venv two levels up.
        """
        monkeypatch.setenv("PATH", "/usr/bin:/bin")
        repo = tmp_path / "genealogy_kg"
        genkg = _script(repo / ".venv" / "bin", "genkg", _FAIL, log=tmp_path / "log")
        entry_dir = repo / "corpora" / "entries" / "royalty" / "tudor"
        (entry_dir / ".genealogykg").mkdir(parents=True)
        e = KGEntry(
            name="tudor",
            kind=KGKind.GENEALOGY,
            repo_path=entry_dir,
            venv_path=entry_dir / ".venv",
            sqlite_path=entry_dir / ".genealogykg" / "graph.sqlite",
        )
        assert find_builder("genkg", e) == str(genkg.resolve())


class TestRebuildCommand:
    def test_dry_run_builds_nothing(self, env):
        _script(env["bin"], "pycodekg", _OK, log=env["log"], marker=".pycodekg")
        result = _run(env, "--dry-run")
        assert result.exit_code == 0
        assert _calls(env) == []
        assert "would build" in result.output and "skipped" in result.output

    def test_builds_each_kg_in_its_root_and_refreshes_builder_version(self, env):
        _script(env["bin"], "pycodekg", _OK, log=env["log"], marker=".pycodekg")
        _script(env["bin"], "dockg", _OK, log=env["log"], marker=".dockg")
        result = _run(env)
        assert result.exit_code == 0, result.output
        calls = _calls(env)
        code_root = env["entries"]["alpha-code"].repo_path
        doc_root = env["entries"]["beta-doc"].repo_path
        assert f"build --repo {code_root} cwd={code_root}" in calls[0]
        assert f"build --repo {doc_root} cwd={doc_root}" in calls[1]
        assert len(calls) == 2  # agent and gutenberg never run
        with KGRegistry(db_path=env["reg"]) as reg:
            assert reg.get("alpha-code").builder_version == "9.9.9"
            assert reg.get("beta-doc").builder_version == "9.9.9"
            assert reg.get("gamma-agent").builder_version == "unknown"

    def test_a_failed_build_is_reported_and_exits_1(self, env):
        _script(env["bin"], "pycodekg", _OK, log=env["log"], marker=".pycodekg")
        _script(env["bin"], "dockg", _FAIL, log=env["log"])
        result = _run(env)
        assert result.exit_code == 1
        assert "failed" in result.output and "exit 3" in result.output
        assert len(_calls(env)) == 2  # the failure does not stop the others

    def test_kind_filter(self, env):
        _script(env["bin"], "pycodekg", _OK, log=env["log"], marker=".pycodekg")
        _script(env["bin"], "dockg", _OK, log=env["log"], marker=".dockg")
        result = _run(env, "--kind", "doc")
        assert result.exit_code == 0
        calls = _calls(env)
        assert len(calls) == 1 and "dockg" in calls[0]

    def test_corpus_filter(self, env):
        _script(env["bin"], "pycodekg", _OK, log=env["log"], marker=".pycodekg")
        _script(env["bin"], "dockg", _OK, log=env["log"], marker=".dockg")
        with KGRegistry(db_path=env["reg"]) as reg, CorpusRegistry(db_path=env["reg"]) as corp:
            corp.create(CorpusEntry(name="only-code"))
            corp.add_kg("only-code", reg.get("alpha-code").id)
        result = _run(env, "--corpus", "only-code")
        assert result.exit_code == 0
        calls = _calls(env)
        assert len(calls) == 1 and "pycodekg" in calls[0]

    def test_unknown_corpus_is_an_error(self, env):
        result = CliRunner().invoke(
            cli, ["rebuild-indices", "--registry", str(env["reg"]), "--corpus", "nope"]
        )
        assert result.exit_code != 0
        assert "Corpus not found" in result.output
