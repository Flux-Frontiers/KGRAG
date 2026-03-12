"""
test_cli.py

Unit tests for the KGRAG CLI using Click's CliRunner.
Each test creates an isolated registry via --registry so it never
touches ~/.kgrag.
"""
from __future__ import annotations

import os
from pathlib import Path

import pytest
from click.testing import CliRunner

from kg_rag.cli.main import cli


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _runner():
    return CliRunner()


def _reg_opt(tmp_path: Path) -> list[str]:
    """Return --registry <tmp_path/reg.sqlite> args."""
    return ["--registry", str(tmp_path / "registry.sqlite")]


# ---------------------------------------------------------------------------
# Top-level CLI
# ---------------------------------------------------------------------------

class TestCLITopLevel:
    def test_help(self):
        result = _runner().invoke(cli, ["--help"])
        assert result.exit_code == 0
        assert "KGRAG" in result.output

    def test_version(self):
        result = _runner().invoke(cli, ["--version"])
        assert result.exit_code == 0
        assert "version" in result.output.lower() or "0." in result.output

    def test_no_args_shows_help(self):
        result = _runner().invoke(cli, [])
        # Click exits 0 or 2 depending on version when no subcommand given; either is fine
        assert "KGRAG" in result.output or result.exit_code in (0, 2)


# ---------------------------------------------------------------------------
# kgrag list
# ---------------------------------------------------------------------------

class TestCLIList:
    def test_list_empty(self, tmp_path):
        result = _runner().invoke(cli, ["list"] + _reg_opt(tmp_path))
        assert result.exit_code == 0
        assert "No KG instances" in result.output

    def test_list_shows_registered(self, tmp_path):
        runner = _runner()
        repo = tmp_path / "repo"
        repo.mkdir()
        # Register first
        runner.invoke(cli, [
            "register", "mykg", "code", str(repo),
        ] + _reg_opt(tmp_path))
        # Then list
        result = runner.invoke(cli, ["list"] + _reg_opt(tmp_path))
        assert result.exit_code == 0
        assert "mykg" in result.output


# ---------------------------------------------------------------------------
# kgrag register
# ---------------------------------------------------------------------------

class TestCLIRegister:
    def test_register_basic(self, tmp_path):
        repo = tmp_path / "repo"
        repo.mkdir()
        result = _runner().invoke(cli, [
            "register", "mykg", "code", str(repo),
        ] + _reg_opt(tmp_path))
        assert result.exit_code == 0
        assert "Registered" in result.output
        assert "mykg" in result.output

    def test_register_with_tags(self, tmp_path):
        repo = tmp_path / "repo"
        repo.mkdir()
        result = _runner().invoke(cli, [
            "register", "taggedkg", "doc", str(repo),
            "--tag", "alpha", "--tag", "beta",
        ] + _reg_opt(tmp_path))
        assert result.exit_code == 0

    def test_register_nonexistent_repo_fails(self, tmp_path):
        result = _runner().invoke(cli, [
            "register", "bad", "code", str(tmp_path / "no_such_dir"),
        ] + _reg_opt(tmp_path))
        # Click's path validation should reject it
        assert result.exit_code != 0

    def test_register_invalid_kind_fails(self, tmp_path):
        repo = tmp_path / "repo"
        repo.mkdir()
        result = _runner().invoke(cli, [
            "register", "bad", "invalid_kind", str(repo),
        ] + _reg_opt(tmp_path))
        assert result.exit_code != 0


# ---------------------------------------------------------------------------
# kgrag unregister
# ---------------------------------------------------------------------------

class TestCLIUnregister:
    def _register(self, runner, tmp_path, name="mykg"):
        repo = tmp_path / "repo"
        repo.mkdir(exist_ok=True)
        runner.invoke(cli, ["register", name, "code", str(repo)] + _reg_opt(tmp_path))

    def test_unregister_existing(self, tmp_path):
        runner = _runner()
        self._register(runner, tmp_path)
        result = runner.invoke(cli, ["unregister", "mykg", "--yes"] + _reg_opt(tmp_path))
        assert result.exit_code == 0
        assert "Unregistered" in result.output

    def test_unregister_not_found(self, tmp_path):
        result = _runner().invoke(cli, ["unregister", "ghost", "--yes"] + _reg_opt(tmp_path))
        assert result.exit_code != 0
        assert "Not found" in result.output


# ---------------------------------------------------------------------------
# kgrag info
# ---------------------------------------------------------------------------

class TestCLIInfo:
    def test_info_existing(self, tmp_path):
        runner = _runner()
        repo = tmp_path / "repo"
        repo.mkdir()
        runner.invoke(cli, ["register", "mykg", "code", str(repo)] + _reg_opt(tmp_path))
        result = runner.invoke(cli, ["info", "mykg"] + _reg_opt(tmp_path))
        assert result.exit_code == 0
        assert "mykg" in result.output
        assert "code" in result.output

    def test_info_not_found(self, tmp_path):
        result = _runner().invoke(cli, ["info", "ghost"] + _reg_opt(tmp_path))
        assert result.exit_code != 0
        assert "Not found" in result.output


# ---------------------------------------------------------------------------
# kgrag status
# ---------------------------------------------------------------------------

class TestCLIStatus:
    def test_status_empty_registry(self, tmp_path):
        result = _runner().invoke(cli, ["status"] + _reg_opt(tmp_path))
        assert result.exit_code == 0
        assert "Total KGs" in result.output

    def test_status_shows_counts(self, tmp_path):
        runner = _runner()
        for name in ("a", "b"):
            repo = tmp_path / name
            repo.mkdir()
            runner.invoke(cli, ["register", name, "code", str(repo)] + _reg_opt(tmp_path))
        result = runner.invoke(cli, ["status"] + _reg_opt(tmp_path))
        assert result.exit_code == 0
        assert "2" in result.output  # total count


# ---------------------------------------------------------------------------
# kgrag scan
# ---------------------------------------------------------------------------

class TestCLIScan:
    def test_scan_no_kgs(self, tmp_path):
        result = _runner().invoke(cli, ["scan", str(tmp_path)] + _reg_opt(tmp_path))
        assert result.exit_code == 0
        assert "No KG databases found" in result.output

    def test_scan_finds_codekg(self, tmp_path):
        repo = tmp_path / "myrepo"
        repo.mkdir()
        codekg_dir = repo / ".codekg"
        codekg_dir.mkdir()
        (codekg_dir / "graph.sqlite").touch()

        result = _runner().invoke(cli, ["scan", str(tmp_path)] + _reg_opt(tmp_path))
        assert result.exit_code == 0
        assert "code" in result.output

    def test_scan_auto_register(self, tmp_path):
        repo = tmp_path / "myrepo"
        repo.mkdir()
        codekg_dir = repo / ".codekg"
        codekg_dir.mkdir()
        (codekg_dir / "graph.sqlite").touch()

        runner = _runner()
        runner.invoke(cli, ["scan", str(tmp_path), "--auto-register"] + _reg_opt(tmp_path))

        # Verify it was registered
        result = runner.invoke(cli, ["list"] + _reg_opt(tmp_path))
        assert "myrepo-code" in result.output
