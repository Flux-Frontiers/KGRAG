"""
test_cli.py

Unit tests for the KGRAG CLI using Click's CliRunner.
Each test creates an isolated registry via --registry so it never
touches ~/.kgrag.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from unittest.mock import patch

from click.testing import CliRunner

from kg_rag.cli.main import cli
from kg_rag.orchestrator import KGRAG
from kg_rag.registry import KGRegistry

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _runner():
    return CliRunner()


def _reg_opt(tmp_path: Path) -> list[str]:
    """Return --registry <tmp_path/reg.sqlite> args."""
    return ["--registry", str(tmp_path / "registry.sqlite")]


def _json_runner():
    """A CliRunner that keeps stderr out of the stdout stream.

    click >= 8.2 always captures the two separately; 8.1 (still allowed by
    our floor) merges them unless told not to.
    """
    try:
        return CliRunner(mix_stderr=False)  # click < 8.2
    except TypeError:
        return CliRunner()


def _json_stdout(result):
    """Parse a CliRunner result's *stdout* as JSON.

    Deliberately not ``result.output``: on click >= 8.2 that is stdout and
    stderr combined. ``status --stats`` builds a KGRAG orchestrator, which
    eagerly loads an embedder, and on a cold model cache (every CI run)
    huggingface_hub writes a download progress bar to stderr. Real stdout
    stays clean JSON -- only the merged view does not.
    """
    return json.loads(result.stdout)


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
        runner.invoke(
            cli,
            [
                "register",
                "mykg",
                "code",
                str(repo),
            ]
            + _reg_opt(tmp_path),
        )
        # Then list
        result = runner.invoke(cli, ["list"] + _reg_opt(tmp_path))
        assert result.exit_code == 0
        assert "mykg" in result.output


# ---------------------------------------------------------------------------
# kgrag status --json
# ---------------------------------------------------------------------------


class TestCLIStatusJson:
    def test_status_json_shape(self, tmp_path):
        repo = tmp_path / "repo"
        repo.mkdir()
        _runner().invoke(cli, ["register", "mykg", "code", str(repo)] + _reg_opt(tmp_path))

        result = _json_runner().invoke(cli, ["status", "--json"] + _reg_opt(tmp_path))
        assert result.exit_code == 0, result.output
        data = _json_stdout(result)
        assert data["total"] == 1
        assert data["by_kind"] == {"code": 1}
        assert data["built"] == 0
        assert data["issues"][0]["name"] == "mykg"
        assert data["issues"][0]["reason"] == "not built"

    def test_status_json_flags_missing_repo(self, tmp_path):
        repo = tmp_path / "gone"
        repo.mkdir()
        _runner().invoke(cli, ["register", "vanished", "code", str(repo)] + _reg_opt(tmp_path))
        repo.rmdir()

        result = _json_runner().invoke(cli, ["status", "--json"] + _reg_opt(tmp_path))
        assert result.exit_code == 0, result.output
        data = _json_stdout(result)
        assert data["issues"][0] == {
            "name": "vanished",
            "reason": "missing",
            "repo_path": str(repo),
        }

    def test_status_json_is_valid_with_no_registry(self, tmp_path):
        """An empty/nonexistent registry must still emit parseable JSON."""
        result = _json_runner().invoke(cli, ["status", "--json"] + _reg_opt(tmp_path))
        assert result.exit_code == 0, result.output
        data = _json_stdout(result)
        assert data["total"] == 0
        assert data["issues"] == []

    def test_status_stats_json_no_matching_kgs(self, tmp_path):
        """--stats --json with nothing to show is an empty JSON array, not text."""
        result = _json_runner().invoke(
            cli, ["status", "--stats", "--json", "--kind", "code"] + _reg_opt(tmp_path)
        )
        assert result.exit_code == 0, result.output
        assert _json_stdout(result) == []

    def test_status_stats_json_reports_unbuilt(self, tmp_path):
        repo = tmp_path / "repo"
        repo.mkdir()
        _runner().invoke(cli, ["register", "mykg", "code", str(repo)] + _reg_opt(tmp_path))

        result = _json_runner().invoke(cli, ["status", "--stats", "--json"] + _reg_opt(tmp_path))
        assert result.exit_code == 0, result.output
        data = _json_stdout(result)
        assert data == [
            {"name": "mykg", "kind": "code", "builder_version": "unknown", "status": "not built"}
        ]

    def test_status_stats_json_survives_stderr_noise(self, tmp_path):
        """Stdout stays parseable when a library scribbles on stderr.

        This is the CI failure mode reproduced without the network: on a cold
        model cache huggingface_hub draws a download progress bar while the
        orchestrator is being built. It goes to stderr, so stdout is still
        clean JSON -- but click's ``result.output`` merges the two streams.
        """
        repo = tmp_path / "repo"
        repo.mkdir()
        _runner().invoke(cli, ["register", "mykg", "code", str(repo)] + _reg_opt(tmp_path))

        class _NoisyKGRAG(KGRAG):
            def __init__(self, *args, **kwargs):
                print("Fetching 3 files:   0%|          | 0/3", end="\r", file=sys.stderr)
                super().__init__(*args, **kwargs)

        with patch("kg_rag.orchestrator.KGRAG", _NoisyKGRAG):
            result = _json_runner().invoke(
                cli, ["status", "--stats", "--json"] + _reg_opt(tmp_path)
            )

        assert result.exit_code == 0, result.output
        assert "Fetching" in result.stderr
        assert _json_stdout(result) == [
            {"name": "mykg", "kind": "code", "builder_version": "unknown", "status": "not built"}
        ]


# ---------------------------------------------------------------------------
# kgrag register
# ---------------------------------------------------------------------------


class TestCLIRegister:
    def test_register_basic(self, tmp_path):
        repo = tmp_path / "repo"
        repo.mkdir()
        result = _runner().invoke(
            cli,
            [
                "register",
                "mykg",
                "code",
                str(repo),
            ]
            + _reg_opt(tmp_path),
        )
        assert result.exit_code == 0
        assert "Registered" in result.output
        assert "mykg" in result.output

    def test_register_with_tags(self, tmp_path):
        repo = tmp_path / "repo"
        repo.mkdir()
        result = _runner().invoke(
            cli,
            [
                "register",
                "taggedkg",
                "doc",
                str(repo),
                "--tag",
                "alpha",
                "--tag",
                "beta",
            ]
            + _reg_opt(tmp_path),
        )
        assert result.exit_code == 0

    def test_register_autodetects_vectors_store(self, tmp_path):
        """A default-layout vectors.sqlite is discovered without --vectors."""
        repo = tmp_path / "repo"
        (repo / ".pycodekg").mkdir(parents=True)
        vectors = repo / ".pycodekg" / "vectors.sqlite"
        vectors.touch()

        result = _runner().invoke(
            cli, ["register", "veckg", "code", str(repo)] + _reg_opt(tmp_path)
        )
        assert result.exit_code == 0, result.output

        with KGRegistry(db_path=tmp_path / "registry.sqlite") as reg:
            entry = reg.get("veckg")
        assert entry.vectors_path == vectors.resolve()

    def test_register_explicit_vectors_option(self, tmp_path):
        """--vectors accepts a store outside the default layout."""
        repo = tmp_path / "repo"
        repo.mkdir()
        vectors = tmp_path / "shared" / "vectors.sqlite"
        vectors.parent.mkdir()
        vectors.touch()

        result = _runner().invoke(
            cli,
            ["register", "custom-vec", "code", str(repo), "--vectors", str(vectors)]
            + _reg_opt(tmp_path),
        )
        assert result.exit_code == 0, result.output

        with KGRegistry(db_path=tmp_path / "registry.sqlite") as reg:
            entry = reg.get("custom-vec")
        assert entry.vectors_path == vectors.resolve()

    def test_register_code_kind_ignores_stale_lancedb_dir(self, tmp_path):
        """Code KGs are sqlite-vec only; a leftover lancedb/ must not be recorded."""
        repo = tmp_path / "repo"
        kg_dir = repo / ".pycodekg"
        kg_dir.mkdir(parents=True)
        (kg_dir / "lancedb").mkdir()
        (kg_dir / "vectors.sqlite").touch()

        result = _runner().invoke(
            cli, ["register", "codekg", "code", str(repo)] + _reg_opt(tmp_path)
        )
        assert result.exit_code == 0, result.output

        with KGRegistry(db_path=tmp_path / "registry.sqlite") as reg:
            entry = reg.get("codekg")
        assert entry.lancedb_path is None
        assert entry.vectors_path is not None

    def test_register_doc_kind_still_detects_lancedb(self, tmp_path):
        """Doc corpora still ship LanceDB, so detection must remain for them."""
        repo = tmp_path / "docrepo"
        kg_dir = repo / ".dockg"
        kg_dir.mkdir(parents=True)
        lancedb = kg_dir / "lancedb"
        lancedb.mkdir()

        result = _runner().invoke(
            cli, ["register", "docskg", "doc", str(repo)] + _reg_opt(tmp_path)
        )
        assert result.exit_code == 0, result.output

        with KGRegistry(db_path=tmp_path / "registry.sqlite") as reg:
            entry = reg.get("docskg")
        assert entry.lancedb_path == lancedb.resolve()

    def test_register_nonexistent_repo_fails(self, tmp_path):
        result = _runner().invoke(
            cli,
            [
                "register",
                "bad",
                "code",
                str(tmp_path / "no_such_dir"),
            ]
            + _reg_opt(tmp_path),
        )
        # Click's path validation should reject it
        assert result.exit_code != 0

    def test_register_invalid_kind_fails(self, tmp_path):
        repo = tmp_path / "repo"
        repo.mkdir()
        result = _runner().invoke(
            cli,
            [
                "register",
                "bad",
                "invalid_kind",
                str(repo),
            ]
            + _reg_opt(tmp_path),
        )
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
        codekg_dir = repo / ".pycodekg"
        codekg_dir.mkdir()
        (codekg_dir / "graph.sqlite").touch()

        result = _runner().invoke(cli, ["scan", str(tmp_path)] + _reg_opt(tmp_path))
        assert result.exit_code == 0
        assert "code" in result.output

    def test_scan_auto_register_records_vectors(self, tmp_path):
        repo = tmp_path / "vecrepo"
        codekg_dir = repo / ".pycodekg"
        codekg_dir.mkdir(parents=True)
        (codekg_dir / "graph.sqlite").touch()
        (codekg_dir / "vectors.sqlite").touch()

        _runner().invoke(cli, ["scan", str(tmp_path), "--auto-register"] + _reg_opt(tmp_path))

        with KGRegistry(db_path=tmp_path / "registry.sqlite") as reg:
            entry = reg.get("vecrepo-code")
        assert entry is not None
        assert entry.vectors_path == (codekg_dir / "vectors.sqlite").resolve()

    def test_scan_auto_register(self, tmp_path):
        repo = tmp_path / "myrepo"
        repo.mkdir()
        codekg_dir = repo / ".pycodekg"
        codekg_dir.mkdir()
        (codekg_dir / "graph.sqlite").touch()

        runner = _runner()
        runner.invoke(cli, ["scan", str(tmp_path), "--auto-register"] + _reg_opt(tmp_path))

        # Verify it was registered
        result = runner.invoke(cli, ["list"] + _reg_opt(tmp_path))
        assert "myrepo-code" in result.output

    def test_scan_finds_filetreekg(self, tmp_path):
        """Regression: .filetreekg was missing from _KG_MARKERS entirely, so
        scan silently skipped every FTreeKG instance on disk.

        Asserts on registry state, not printed output: pytest names tmp_path
        after the test function, so a naive `"filetree" in result.output`
        check passes on the echoed *path* alone (it contains
        "test_scan_finds_filetreekg0") regardless of whether scan found
        anything at all.
        """
        repo = tmp_path / "myrepo"
        repo.mkdir()
        marker_dir = repo / ".filetreekg"
        marker_dir.mkdir()
        (marker_dir / "graph.sqlite").touch()

        _runner().invoke(cli, ["scan", str(tmp_path), "--auto-register"] + _reg_opt(tmp_path))

        with KGRegistry(db_path=tmp_path / "registry.sqlite") as reg:
            entry = reg.get("myrepo-filetree")
        assert entry is not None
        assert entry.kind.value == "filetree"

    def test_scan_finds_agentkg(self, tmp_path):
        """Regression: .agentkg had the same gap as .filetreekg."""
        repo = tmp_path / "myrepo"
        repo.mkdir()
        marker_dir = repo / ".agentkg"
        marker_dir.mkdir()
        (marker_dir / "graph.sqlite").touch()

        _runner().invoke(cli, ["scan", str(tmp_path), "--auto-register"] + _reg_opt(tmp_path))

        with KGRegistry(db_path=tmp_path / "registry.sqlite") as reg:
            entry = reg.get("myrepo-agent")
        assert entry is not None
        assert entry.kind.value == "agent"
