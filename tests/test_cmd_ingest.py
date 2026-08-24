"""
test_cmd_ingest.py

Tests for ``kgrag ingest`` — the document-ingestion pipeline command
(stage -> build -> register).

The CLI tests mock ``kg_utils.ingest.IngestPipeline`` and ``subprocess.run``
so no real document conversion or ``dockg`` invocation happens. The
``_register`` / ``_add_to_corpus`` / ``_print_problems`` / ``_print_summary``
helpers are also exercised directly, the same way ``test_cmd_audit.py``
tests ``audit_entry`` directly, since going through the CLI for every branch
of those helpers would mean re-mocking the whole pipeline for each case.
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

from click.testing import CliRunner

from kg_rag.cli.cmd_ingest import _add_to_corpus, _print_problems, _print_summary, _register
from kg_rag.cli.main import cli
from kg_rag.corpus_registry import CorpusRegistry
from kg_rag.primitives import CorpusEntry, KGEntry, KGKind
from kg_rag.registry import KGRegistry

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _reg_opt(tmp_path: Path) -> list[str]:
    return ["--registry", str(tmp_path / "registry.sqlite")]


def _record(status: str, name: str = "doc.pdf", reason: str = "") -> SimpleNamespace:
    return SimpleNamespace(source_path=f"/src/{name}", status=status, reason=reason)


def _stats(
    ingested: int = 1,
    skipped: int = 0,
    failed: int = 0,
    records: list | None = None,
) -> SimpleNamespace:
    stats = SimpleNamespace(
        ingested=ingested,
        skipped=skipped,
        failed=failed,
        records=records or [],
    )
    stats.considered = ingested + skipped + failed
    return stats


def _mock_pipeline(stats: SimpleNamespace) -> MagicMock:
    """Return a MagicMock standing in for ``IngestPipeline`` whose ``run()``
    returns *stats*."""
    instance = MagicMock()
    instance.run.return_value = stats
    cls = MagicMock(return_value=instance)
    return cls


# ---------------------------------------------------------------------------
# Import guard (kg_utils.ingest missing / too old)
# ---------------------------------------------------------------------------


class TestIngestUnavailable:
    def test_missing_kg_utils_ingest_exits_with_hint(self, tmp_path):
        """A predates-0.17.0 kgmodule-utils has no kg_utils.ingest module."""
        with patch.dict(sys.modules, {"kg_utils.ingest": None}):
            result = CliRunner().invoke(
                cli,
                ["ingest", str(tmp_path), "--into", str(tmp_path / "out")] + _reg_opt(tmp_path),
            )
        assert result.exit_code == 1
        assert "unavailable" in result.output.lower()
        assert "kgmodule-utils" in result.output


# ---------------------------------------------------------------------------
# Stage stage / early-exit
# ---------------------------------------------------------------------------


class TestIngestStage:
    def test_nothing_staged_and_empty_corpus_stops_before_build(self, tmp_path):
        source = tmp_path / "src"
        source.mkdir()
        (source / "f.txt").write_text("x")
        staging = tmp_path / "out"  # never created -> _staging_has_documents is False

        pipeline_cls = _mock_pipeline(_stats(ingested=0, skipped=1, records=[_record("skipped")]))
        with patch("kg_utils.ingest.IngestPipeline", pipeline_cls):
            result = CliRunner().invoke(
                cli,
                ["ingest", str(source), "--into", str(staging)] + _reg_opt(tmp_path),
            )
        assert result.exit_code == 1
        assert "Nothing staged" in result.output

    def test_rerun_with_only_duplicates_still_proceeds(self, tmp_path):
        """ingested==0 but the staging dir already has documents on disk (a
        re-run of all-duplicate sources) must not hit the empty-corpus exit."""
        source = tmp_path / "src"
        source.mkdir()
        (source / "f.txt").write_text("x")
        staging = tmp_path / "out"
        staging.mkdir()
        (staging / "already.md").write_text("# hi")

        pipeline_cls = _mock_pipeline(_stats(ingested=0, skipped=1))
        with (
            patch("kg_utils.ingest.IngestPipeline", pipeline_cls),
            patch("shutil.which", return_value=None),
        ):
            result = CliRunner().invoke(
                cli,
                ["ingest", str(source), "--into", str(staging), "--no-register"]
                + _reg_opt(tmp_path),
            )
        assert result.exit_code == 0, result.output
        assert "Nothing staged" not in result.output

    def test_update_flag_passed_through_to_pipeline_run(self, tmp_path):
        source = tmp_path / "src"
        source.mkdir()
        (source / "f.txt").write_text("x")
        staging = tmp_path / "out"

        instance = MagicMock()
        instance.run.return_value = _stats(ingested=1)
        pipeline_cls = MagicMock(return_value=instance)
        with patch("kg_utils.ingest.IngestPipeline", pipeline_cls):
            CliRunner().invoke(
                cli,
                ["ingest", str(source), "--into", str(staging), "--update", "--no-build"]
                + _reg_opt(tmp_path),
            )
        assert instance.run.call_args.kwargs["update"] is True

    def test_default_kg_name_derived_from_staging_dirname(self, tmp_path):
        source = tmp_path / "src"
        source.mkdir()
        (source / "f.txt").write_text("x")
        staging = tmp_path / "mycorpus"

        pipeline_cls = _mock_pipeline(_stats(ingested=1))
        with patch("kg_utils.ingest.IngestPipeline", pipeline_cls):
            result = CliRunner().invoke(
                cli,
                ["ingest", str(source), "--into", str(staging), "--no-build"] + _reg_opt(tmp_path),
            )
        assert "mycorpus-doc" in result.output

    def test_show_skipped_prints_problem_table(self, tmp_path):
        source = tmp_path / "src"
        source.mkdir()
        (source / "f.txt").write_text("x")
        staging = tmp_path / "out"

        records = [_record("failed", "bad.pdf", reason="scanned PDF needs OCR")]
        pipeline_cls = _mock_pipeline(_stats(ingested=0, failed=1, records=records))
        with patch("kg_utils.ingest.IngestPipeline", pipeline_cls):
            result = CliRunner().invoke(
                cli,
                ["ingest", str(source), "--into", str(staging)] + _reg_opt(tmp_path),
            )
        assert "bad.pdf" in result.output
        assert "scanned PDF needs OCR" in result.output

    def test_no_show_skipped_suppresses_problem_table(self, tmp_path):
        source = tmp_path / "src"
        source.mkdir()
        (source / "f.txt").write_text("x")
        staging = tmp_path / "out"

        records = [_record("failed", "bad.pdf", reason="scanned PDF needs OCR")]
        pipeline_cls = _mock_pipeline(_stats(ingested=0, failed=1, records=records))
        with patch("kg_utils.ingest.IngestPipeline", pipeline_cls):
            result = CliRunner().invoke(
                cli,
                ["ingest", str(source), "--into", str(staging), "--no-show-skipped"]
                + _reg_opt(tmp_path),
            )
        assert "bad.pdf" not in result.output


# ---------------------------------------------------------------------------
# Build stage
# ---------------------------------------------------------------------------


class TestIngestBuild:
    def test_no_build_skips_build_and_register(self, tmp_path):
        source = tmp_path / "src"
        source.mkdir()
        (source / "f.txt").write_text("x")
        staging = tmp_path / "out"

        pipeline_cls = _mock_pipeline(_stats(ingested=1))
        with patch("kg_utils.ingest.IngestPipeline", pipeline_cls):
            result = CliRunner().invoke(
                cli,
                ["ingest", str(source), "--into", str(staging), "--no-build"] + _reg_opt(tmp_path),
            )
        assert result.exit_code == 0, result.output
        assert "Skipping build (--no-build)" in result.output
        assert "not registered" in result.output

    def test_dockg_not_on_path_skips_build(self, tmp_path):
        source = tmp_path / "src"
        source.mkdir()
        (source / "f.txt").write_text("x")
        staging = tmp_path / "out"

        pipeline_cls = _mock_pipeline(_stats(ingested=1))
        with (
            patch("kg_utils.ingest.IngestPipeline", pipeline_cls),
            patch("shutil.which", return_value=None),
        ):
            result = CliRunner().invoke(
                cli,
                ["ingest", str(source), "--into", str(staging)] + _reg_opt(tmp_path),
            )
        assert result.exit_code == 0, result.output
        assert "dockg" in result.output.lower()
        assert "not found on PATH" in result.output
        assert "not registered" in result.output

    def test_build_failure_skips_registration(self, tmp_path):
        source = tmp_path / "src"
        source.mkdir()
        (source / "f.txt").write_text("x")
        staging = tmp_path / "out"

        pipeline_cls = _mock_pipeline(_stats(ingested=1))
        with (
            patch("kg_utils.ingest.IngestPipeline", pipeline_cls),
            patch("shutil.which", return_value="/usr/bin/dockg"),
            patch(
                "subprocess.run",
                side_effect=subprocess.CalledProcessError(1, ["dockg", "build"]),
            ),
        ):
            result = CliRunner().invoke(
                cli,
                ["ingest", str(source), "--into", str(staging)] + _reg_opt(tmp_path),
            )
        assert result.exit_code == 0, result.output
        assert "Build failed" in result.output
        assert "Not registering" in result.output

    def test_build_success_registers_kg(self, tmp_path):
        source = tmp_path / "src"
        source.mkdir()
        (source / "f.txt").write_text("x")
        staging = tmp_path / "out"

        pipeline_cls = _mock_pipeline(_stats(ingested=1))
        with (
            patch("kg_utils.ingest.IngestPipeline", pipeline_cls),
            patch("shutil.which", return_value="/usr/bin/dockg"),
            patch("subprocess.run") as mock_run,
        ):
            result = CliRunner().invoke(
                cli,
                ["ingest", str(source), "--into", str(staging), "--name", "mykg"]
                + _reg_opt(tmp_path),
            )
        assert result.exit_code == 0, result.output
        mock_run.assert_called_once()
        called_cmd = mock_run.call_args[0][0]
        assert called_cmd[:2] == ["dockg", "build"]
        assert "Registered" in result.output
        assert "mykg" in result.output

        with KGRegistry(db_path=tmp_path / "registry.sqlite") as reg:
            assert reg.get("mykg") is not None


# ---------------------------------------------------------------------------
# Corpus attachment (--corpus)
# ---------------------------------------------------------------------------


class TestIngestCorpusAttach:
    def test_registers_and_adds_to_existing_corpus(self, tmp_path):
        db = tmp_path / "registry.sqlite"
        with CorpusRegistry(db_path=db) as creg:
            creg.create(CorpusEntry(name="mycorpus", kg_ids=[]))

        source = tmp_path / "src"
        source.mkdir()
        (source / "f.txt").write_text("x")
        staging = tmp_path / "out"

        pipeline_cls = _mock_pipeline(_stats(ingested=1))
        with (
            patch("kg_utils.ingest.IngestPipeline", pipeline_cls),
            patch("shutil.which", return_value="/usr/bin/dockg"),
            patch("subprocess.run"),
        ):
            result = CliRunner().invoke(
                cli,
                [
                    "ingest",
                    str(source),
                    "--into",
                    str(staging),
                    "--name",
                    "mykg",
                    "--corpus",
                    "mycorpus",
                ]
                + _reg_opt(tmp_path),
            )
        assert result.exit_code == 0, result.output
        assert "Added" in result.output
        assert "mycorpus" in result.output

        with CorpusRegistry(db_path=db) as creg, KGRegistry(db_path=db) as kreg:
            entry = kreg.get("mykg")
            corpus = creg.get("mycorpus")
            assert entry.id in corpus.kg_ids

    def test_corpus_not_added_when_build_fails(self, tmp_path):
        """entry stays None on a failed build, so --corpus must be a no-op."""
        source = tmp_path / "src"
        source.mkdir()
        (source / "f.txt").write_text("x")
        staging = tmp_path / "out"

        pipeline_cls = _mock_pipeline(_stats(ingested=1))
        with (
            patch("kg_utils.ingest.IngestPipeline", pipeline_cls),
            patch("shutil.which", return_value="/usr/bin/dockg"),
            patch(
                "subprocess.run",
                side_effect=subprocess.CalledProcessError(1, ["dockg", "build"]),
            ),
        ):
            result = CliRunner().invoke(
                cli,
                ["ingest", str(source), "--into", str(staging), "--corpus", "nope"]
                + _reg_opt(tmp_path),
            )
        assert result.exit_code == 0, result.output
        assert "Added" not in result.output


# ---------------------------------------------------------------------------
# _register (unit)
# ---------------------------------------------------------------------------


class TestRegisterHelper:
    def test_registers_with_index_paths_present(self, tmp_path):
        staging = tmp_path / "corpus"
        kg_dir = staging / ".dockg"
        kg_dir.mkdir(parents=True)
        (kg_dir / "graph.sqlite").touch()
        (kg_dir / "vectors.sqlite").touch()

        entry = _register(staging, "mykg", str(tmp_path / "registry.sqlite"))

        assert entry.name == "mykg"
        assert entry.kind == KGKind.DOC
        assert entry.sqlite_path == kg_dir / "graph.sqlite"
        assert entry.vectors_path == kg_dir / "vectors.sqlite"
        assert entry.lancedb_path is None  # not created
        assert "ingested" in entry.tags

        with KGRegistry(db_path=tmp_path / "registry.sqlite") as reg:
            assert reg.get("mykg") is not None

    def test_missing_index_files_recorded_as_none(self, tmp_path):
        staging = tmp_path / "corpus"
        staging.mkdir()

        entry = _register(staging, "empty-kg", str(tmp_path / "registry.sqlite"))

        assert entry.sqlite_path is None
        assert entry.vectors_path is None
        assert entry.lancedb_path is None

    def test_default_registry_path_when_none(self, tmp_path):
        """registry=None must pass db_path=None so KGRegistry picks its own
        default location, rather than e.g. an empty string or cwd-relative
        path. The real KGRegistry class is never instantiated here, so this
        test cannot touch the real ~/.kgrag registry."""
        staging = tmp_path / "corpus"
        staging.mkdir()

        mock_instance = MagicMock()
        mock_cls = MagicMock()
        mock_cls.return_value.__enter__.return_value = mock_instance
        with patch("kg_rag.cli.cmd_ingest.KGRegistry", mock_cls):
            _register(staging, "kg1", None)

        assert mock_cls.call_args.kwargs["db_path"] is None
        mock_instance.register.assert_called_once()


# ---------------------------------------------------------------------------
# _add_to_corpus (unit)
# ---------------------------------------------------------------------------


class TestAddToCorpusHelper:
    def test_adds_registered_entry_to_corpus(self, tmp_path):
        db = tmp_path / "registry.sqlite"
        repo = tmp_path / "repo"
        repo.mkdir()
        entry = KGEntry(name="kg1", kind=KGKind.DOC, repo_path=repo, venv_path=repo / ".venv")
        with KGRegistry(db_path=db) as reg:
            reg.register(entry)
        with CorpusRegistry(db_path=db) as creg:
            creg.create(CorpusEntry(name="corpus1", kg_ids=[]))

        _add_to_corpus(entry, "corpus1", str(db))

        with CorpusRegistry(db_path=db) as creg, KGRegistry(db_path=db) as reg:
            registered = reg.get("kg1")
            corpus = creg.get("corpus1")
            assert registered.id in corpus.kg_ids

    def test_unresolvable_entry_prints_warning(self, tmp_path, capsys):
        db = tmp_path / "registry.sqlite"
        repo = tmp_path / "repo"
        repo.mkdir()
        # Entry was never registered, so kg_reg.get() will return None.
        entry = KGEntry(name="ghost", kind=KGKind.DOC, repo_path=repo, venv_path=repo / ".venv")
        with CorpusRegistry(db_path=db) as creg:
            creg.create(CorpusEntry(name="corpus1", kg_ids=[]))

        from kg_rag.cli.cmd_ingest import console

        with console.capture() as capture:
            _add_to_corpus(entry, "corpus1", str(db))
        assert "Could not resolve" in capture.get()

    def test_missing_corpus_prints_error(self, tmp_path):
        db = tmp_path / "registry.sqlite"
        repo = tmp_path / "repo"
        repo.mkdir()
        entry = KGEntry(name="kg1", kind=KGKind.DOC, repo_path=repo, venv_path=repo / ".venv")
        with KGRegistry(db_path=db) as reg:
            reg.register(entry)

        from kg_rag.cli.cmd_ingest import console

        with console.capture() as capture:
            _add_to_corpus(entry, "no-such-corpus", str(db))
        assert "Corpus not found" in capture.get()


# ---------------------------------------------------------------------------
# _print_problems (unit)
# ---------------------------------------------------------------------------


class TestPrintProblemsHelper:
    def test_no_problems_prints_nothing(self):
        from kg_rag.cli.cmd_ingest import console

        stats = _stats(ingested=1, records=[_record("ingested")])
        with console.capture() as capture:
            _print_problems(stats)
        assert capture.get() == ""

    def test_duplicates_are_filtered_out(self):
        from kg_rag.cli.cmd_ingest import console

        stats = _stats(
            ingested=1,
            skipped=1,
            records=[
                _record("ingested"),
                _record("skipped", "dup.txt", reason="already ingested (identical content)"),
            ],
        )
        with console.capture() as capture:
            _print_problems(stats)
        assert capture.get() == ""

    def test_failed_and_skipped_are_reported(self):
        from kg_rag.cli.cmd_ingest import console

        stats = _stats(
            failed=1,
            skipped=1,
            records=[
                _record("failed", "a.pdf", reason="unsupported encoding"),
                _record("skipped", "b.bin", reason="unknown format"),
            ],
        )
        with console.capture() as capture:
            _print_problems(stats)
        out = capture.get()
        assert "a.pdf" in out
        assert "unsupported encoding" in out
        assert "b.bin" in out
        assert "unknown format" in out


# ---------------------------------------------------------------------------
# _print_summary (unit)
# ---------------------------------------------------------------------------


class TestPrintSummaryHelper:
    def test_summary_shows_gaps_row_when_failures_present(self):
        from kg_rag.cli.cmd_ingest import console

        # A short path avoids Rich column-width truncation of the "gaps" cell
        # in the captured (fixed-width) console output.
        staging = Path("/corpus")
        stats = _stats(ingested=1, failed=1)
        with console.capture() as capture:
            _print_summary(stats, staging, "mykg", built_ok=True, entry=None)
        out = capture.get()
        assert "gaps" in out
        assert "manifest.json" in out

    def test_summary_omits_gaps_row_when_clean(self):
        from kg_rag.cli.cmd_ingest import console

        # A short, fixed path avoids both Rich column-width truncation and a
        # collision with pytest's tmp_path name (derived from this test's own
        # name, which happens to contain the literal substring "gaps").
        staging = Path("/corpus")
        stats = _stats(ingested=1)
        with console.capture() as capture:
            _print_summary(stats, staging, "mykg", built_ok=True, entry=None)
        out = capture.get()
        assert "gaps" not in out

    def test_summary_reflects_build_and_register_state(self, tmp_path):
        from kg_rag.cli.cmd_ingest import console

        staging = tmp_path / "corpus"
        entry = KGEntry(
            name="mykg", kind=KGKind.DOC, repo_path=staging, venv_path=staging / ".venv"
        )
        stats = _stats(ingested=2)
        with console.capture() as capture:
            _print_summary(stats, staging, "mykg", built_ok=False, entry=entry)
        out = capture.get()
        assert "not built" in out
        assert "mykg" in out
