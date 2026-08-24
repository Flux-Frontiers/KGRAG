"""
test_cmd_init.py

Tests for ``kgrag init`` -- auto-detect, build, and register all applicable
KG layers for a repository in one shot.
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

from click.testing import CliRunner

from kg_rag.cli.cmd_init import _detect_layers
from kg_rag.cli.main import cli
from kg_rag.corpus_registry import CorpusRegistry
from kg_rag.primitives import CorpusEntry
from kg_rag.registry import KGRegistry

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _reg_opt(tmp_path: Path) -> list[str]:
    return ["--registry", str(tmp_path / "registry.sqlite")]


def _fake_run_factory(marker_dirname: str = ".pycodekg"):
    """Return a subprocess.run stand-in that creates a graph.sqlite next to
    ``--repo`` under the given marker directory, mimicking a real build tool.
    """

    def _fake_run(cmd, check=True, cwd=None, **kwargs):
        repo_idx = cmd.index("--repo") + 1
        repo = Path(cmd[repo_idx])
        kg_dir = repo / marker_dirname
        kg_dir.mkdir(parents=True, exist_ok=True)
        (kg_dir / "graph.sqlite").touch()
        return MagicMock(returncode=0)

    return _fake_run


def _which_for(*tool_names: str):
    """Return a shutil.which stand-in that reports the given tools as present."""

    def _which(name):
        return f"/usr/bin/{name}" if name in tool_names else None

    return _which


# ---------------------------------------------------------------------------
# _detect_layers
# ---------------------------------------------------------------------------


class TestDetectLayers:
    def test_python_only(self, tmp_path):
        (tmp_path / "mod.py").write_text("x = 1\n")
        assert _detect_layers(tmp_path) == ["code"]

    def test_docs_only(self, tmp_path):
        (tmp_path / "README.md").write_text("# hi\n")
        assert _detect_layers(tmp_path) == ["doc"]

    def test_both(self, tmp_path):
        (tmp_path / "mod.py").write_text("x = 1\n")
        (tmp_path / "notes.txt").write_text("hi\n")
        assert _detect_layers(tmp_path) == ["code", "doc"]

    def test_neither(self, tmp_path):
        (tmp_path / "data.json").write_text("{}\n")
        assert _detect_layers(tmp_path) == []

    def test_prunes_venv_directory(self, tmp_path):
        """A .py file that only exists inside .venv must not count as source."""
        venv = tmp_path / ".venv"
        venv.mkdir()
        (venv / "lib.py").write_text("x = 1\n")
        assert _detect_layers(tmp_path) == []

    def test_prunes_hidden_directories(self, tmp_path):
        """A .py file inside a hidden directory (e.g. .git) must not count."""
        hidden = tmp_path / ".git"
        hidden.mkdir()
        (hidden / "hooks.py").write_text("x = 1\n")
        assert _detect_layers(tmp_path) == []


# ---------------------------------------------------------------------------
# init CLI -- detection / no-op path
# ---------------------------------------------------------------------------


class TestInitDetection:
    def test_no_layers_detected(self, tmp_path):
        repo = tmp_path / "empty-repo"
        repo.mkdir()
        (repo / "data.json").write_text("{}\n")

        result = CliRunner().invoke(cli, ["init", str(repo)] + _reg_opt(tmp_path))
        assert result.exit_code == 0, result.output
        assert "No applicable KG layers detected" in result.output

    def test_auto_detects_and_announces(self, tmp_path):
        repo = tmp_path / "auto-repo"
        repo.mkdir()
        (repo / "mod.py").write_text("x = 1\n")

        with (
            patch("shutil.which", side_effect=_which_for()),
        ):
            result = CliRunner().invoke(cli, ["init", str(repo)] + _reg_opt(tmp_path))
        assert result.exit_code == 0, result.output
        assert "Auto-detecting applicable KG layers" in result.output
        assert "Detected:" in result.output
        assert "code" in result.output

    def test_explicit_layers_skip_detection(self, tmp_path):
        repo = tmp_path / "explicit-repo"
        repo.mkdir()

        with patch("shutil.which", side_effect=_which_for()):
            result = CliRunner().invoke(
                cli, ["init", str(repo), "--layer", "doc"] + _reg_opt(tmp_path)
            )
        assert result.exit_code == 0, result.output
        assert "Auto-detecting" not in result.output


# ---------------------------------------------------------------------------
# init CLI -- build tool availability
# ---------------------------------------------------------------------------


class TestInitBuildToolMissing:
    def test_skips_when_tool_not_on_path(self, tmp_path):
        repo = tmp_path / "no-tool-repo"
        repo.mkdir()

        with patch("shutil.which", return_value=None):
            result = CliRunner().invoke(
                cli, ["init", str(repo), "--layer", "code"] + _reg_opt(tmp_path)
            )
        assert result.exit_code == 0, result.output
        assert "Skipping code layer" in result.output
        assert "pycodekg" in result.output
        assert "not found on PATH" in result.output
        assert "skipped" in result.output

        with KGRegistry(db_path=tmp_path / "registry.sqlite") as reg:
            assert reg.get(f"{repo.name}-code") is None


# ---------------------------------------------------------------------------
# init CLI -- build success / failure
# ---------------------------------------------------------------------------


class TestInitBuild:
    def test_successful_build_registers_entry(self, tmp_path):
        repo = tmp_path / "good-repo"
        repo.mkdir()

        with (
            patch("shutil.which", side_effect=_which_for("pycodekg")),
            patch("subprocess.run", side_effect=_fake_run_factory(".pycodekg")),
        ):
            result = CliRunner().invoke(
                cli, ["init", str(repo), "--layer", "code"] + _reg_opt(tmp_path)
            )
        assert result.exit_code == 0, result.output
        assert "Registered" in result.output
        assert f"{repo.name}-code" in result.output

        with KGRegistry(db_path=tmp_path / "registry.sqlite") as reg:
            entry = reg.get(f"{repo.name}-code")
            assert entry is not None
            assert entry.sqlite_path is not None
            assert entry.sqlite_path.exists()

    def test_build_failure_recorded_and_not_registered(self, tmp_path):
        import subprocess

        repo = tmp_path / "bad-repo"
        repo.mkdir()

        def _fail(cmd, check=True, cwd=None, **kwargs):
            raise subprocess.CalledProcessError(1, cmd)

        with (
            patch("shutil.which", side_effect=_which_for("pycodekg")),
            patch("subprocess.run", side_effect=_fail),
        ):
            result = CliRunner().invoke(
                cli, ["init", str(repo), "--layer", "code"] + _reg_opt(tmp_path)
            )
        assert result.exit_code == 0, result.output
        assert "Build failed" in result.output
        assert "build failed" in result.output  # status column in summary table

        with KGRegistry(db_path=tmp_path / "registry.sqlite") as reg:
            assert reg.get(f"{repo.name}-code") is None

    def test_unbuilt_paths_render_as_dash(self, tmp_path):
        """A build that reports success but leaves no sqlite file behind should
        still register (build tool's own contract), with size shown as '-'."""
        repo = tmp_path / "noop-repo"
        repo.mkdir()

        with (
            patch("shutil.which", side_effect=_which_for("pycodekg")),
            patch("subprocess.run", return_value=MagicMock(returncode=0)),
        ):
            result = CliRunner().invoke(
                cli, ["init", str(repo), "--layer", "code"] + _reg_opt(tmp_path)
            )
        assert result.exit_code == 0, result.output
        with KGRegistry(db_path=tmp_path / "registry.sqlite") as reg:
            entry = reg.get(f"{repo.name}-code")
            assert entry is not None
            assert entry.sqlite_path is None  # file never existed on disk


# ---------------------------------------------------------------------------
# init CLI -- options: --wipe, --name
# ---------------------------------------------------------------------------


class TestInitOptions:
    def test_wipe_flag_passed_for_code_not_doc(self, tmp_path):
        repo = tmp_path / "wipe-repo"
        repo.mkdir()
        calls: list[list[str]] = []

        def _record_run(cmd, check=True, cwd=None, **kwargs):
            calls.append(cmd)
            return _fake_run_factory(".pycodekg" if "pycodekg" in cmd[0] else ".dockg")(
                cmd, check=check, cwd=cwd
            )

        with (
            patch("shutil.which", side_effect=_which_for("pycodekg", "dockg")),
            patch("subprocess.run", side_effect=_record_run),
        ):
            result = CliRunner().invoke(
                cli,
                ["init", str(repo), "--layer", "code", "--layer", "doc", "--wipe"]
                + _reg_opt(tmp_path),
            )
        assert result.exit_code == 0, result.output
        code_cmd = next(c for c in calls if c[0] == "pycodekg")
        doc_cmd = next(c for c in calls if c[0] == "dockg")
        assert "--wipe" in code_cmd
        assert "--wipe" not in doc_cmd

    def test_name_prefix_used_for_registered_names(self, tmp_path):
        repo = tmp_path / "prefix-repo"
        repo.mkdir()

        with (
            patch("shutil.which", side_effect=_which_for("pycodekg")),
            patch("subprocess.run", side_effect=_fake_run_factory(".pycodekg")),
        ):
            result = CliRunner().invoke(
                cli,
                ["init", str(repo), "--layer", "code", "--name", "custom"] + _reg_opt(tmp_path),
            )
        assert result.exit_code == 0, result.output
        assert "custom-code" in result.output

        with KGRegistry(db_path=tmp_path / "registry.sqlite") as reg:
            assert reg.get("custom-code") is not None
            assert reg.get(f"{repo.name}-code") is None


# ---------------------------------------------------------------------------
# init CLI -- --corpus
# ---------------------------------------------------------------------------


class TestInitCorpus:
    def test_no_kgs_registered_skips_corpus_add(self, tmp_path):
        repo = tmp_path / "skip-corpus-repo"
        repo.mkdir()

        with patch("shutil.which", return_value=None):
            result = CliRunner().invoke(
                cli,
                ["init", str(repo), "--layer", "code", "--corpus", "somecorpus"]
                + _reg_opt(tmp_path),
            )
        assert result.exit_code == 0, result.output
        assert "No KGs were registered; skipping corpus add" in result.output

    def test_missing_corpus_reports_error(self, tmp_path):
        repo = tmp_path / "missing-corpus-repo"
        repo.mkdir()

        with (
            patch("shutil.which", side_effect=_which_for("pycodekg")),
            patch("subprocess.run", side_effect=_fake_run_factory(".pycodekg")),
        ):
            result = CliRunner().invoke(
                cli,
                ["init", str(repo), "--layer", "code", "--corpus", "ghost-corpus"]
                + _reg_opt(tmp_path),
            )
        assert result.exit_code == 0, result.output
        assert "Corpus not found" in result.output
        assert "ghost-corpus" in result.output

    def test_successful_corpus_add(self, tmp_path):
        repo = tmp_path / "corpus-repo"
        repo.mkdir()
        db = tmp_path / "registry.sqlite"
        with CorpusRegistry(db_path=db) as creg:
            creg.create(CorpusEntry(name="mycorpus", kg_ids=[]))

        with (
            patch("shutil.which", side_effect=_which_for("pycodekg")),
            patch("subprocess.run", side_effect=_fake_run_factory(".pycodekg")),
        ):
            result = CliRunner().invoke(
                cli,
                ["init", str(repo), "--layer", "code", "--corpus", "mycorpus"] + _reg_opt(tmp_path),
            )
        assert result.exit_code == 0, result.output
        assert "Added" in result.output
        assert f"{repo.name}-code" in result.output

        with KGRegistry(db_path=db) as kg_reg, CorpusRegistry(db_path=db) as corp_reg:
            entry = kg_reg.get(f"{repo.name}-code")
            corpus = corp_reg.get("mycorpus")
            assert entry.id in corpus.kg_ids


# ---------------------------------------------------------------------------
# init CLI -- summary table rendering
# ---------------------------------------------------------------------------


class TestInitSummaryTable:
    def test_doc_layer_lancedb_dir_size_summed(self, tmp_path):
        """Non-code layers report a lancedb *directory* -- exercise the
        directory-size-summing branch of the table's size formatter, not just
        the single-file branch the other tests hit via graph.sqlite."""
        repo = tmp_path / "doc-size-repo"
        repo.mkdir()

        def _fake_doc_run(cmd, check=True, cwd=None, **kwargs):
            repo_idx = cmd.index("--repo") + 1
            r = Path(cmd[repo_idx])
            kg_dir = r / ".dockg"
            kg_dir.mkdir(parents=True, exist_ok=True)
            (kg_dir / "graph.sqlite").touch()
            lancedb = kg_dir / "lancedb"
            lancedb.mkdir()
            (lancedb / "data.lance").write_bytes(b"x" * 100)
            return MagicMock(returncode=0)

        with (
            patch("shutil.which", side_effect=_which_for("dockg")),
            patch("subprocess.run", side_effect=_fake_doc_run),
        ):
            result = CliRunner().invoke(
                cli,
                ["init", str(repo), "--layer", "doc"] + _reg_opt(tmp_path),
                env={"COLUMNS": "200"},
            )
        assert result.exit_code == 0, result.output
        assert "100 B" in result.output

    def test_mixed_results_all_shown_in_summary(self, tmp_path):
        """One layer builds fine (registered) and one has no tool on PATH
        (skipped) -- exercise both summary-row status labels together."""
        repo = tmp_path / "mixed-repo"
        repo.mkdir()

        with (
            patch("shutil.which", side_effect=_which_for("pycodekg")),
            patch("subprocess.run", side_effect=_fake_run_factory(".pycodekg")),
        ):
            result = CliRunner().invoke(
                cli,
                ["init", str(repo), "--layer", "code", "--layer", "doc"] + _reg_opt(tmp_path),
                env={"COLUMNS": "200"},
            )
        assert result.exit_code == 0, result.output
        assert "registered" in result.output
        assert "skipped" in result.output
        assert "KG Init" in result.output
