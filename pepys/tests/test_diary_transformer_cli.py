"""
test_diary_transformer_cli.py

Tests for the diary_transformer Click CLI (diary_transformer.cli).

Uses Click's CliRunner.  The DiaryTransformer class is mocked so no real NLP
or file I/O is needed for the routing tests.  File-existence checks are tested
with real tmp_path fixtures.
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from click.testing import CliRunner

from diary_transformer.cli import cli


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _runner() -> CliRunner:
    return CliRunner(mix_stderr=False)


def _mock_dt(ingest_return: int = 5) -> MagicMock:
    dt = MagicMock()
    dt.transform_file.return_value = None
    dt.transform_file_incremental.return_value = None
    dt.ingest_to_corpus.return_value = ingest_return
    return dt


# ---------------------------------------------------------------------------
# --help  (no mocking needed)
# ---------------------------------------------------------------------------

class TestCliHelp:
    def test_root_help(self):
        result = _runner().invoke(cli, ["--help"])
        assert result.exit_code == 0
        assert "transform" in result.output
        assert "ingest" in result.output
        assert "build" in result.output

    def test_transform_help(self):
        result = _runner().invoke(cli, ["transform", "--help"])
        assert result.exit_code == 0
        assert "INPUT" in result.output
        assert "OUTPUT" in result.output

    def test_ingest_help(self):
        result = _runner().invoke(cli, ["ingest", "--help"])
        assert result.exit_code == 0
        assert "CORPUS_DIR" in result.output

    def test_build_help(self):
        result = _runner().invoke(cli, ["build", "--help"])
        assert result.exit_code == 0
        assert "CORPUS_DIR" in result.output


# ---------------------------------------------------------------------------
# transform command
# ---------------------------------------------------------------------------

class TestTransformCommand:
    def test_missing_input_exits_nonzero(self, tmp_path):
        out = str(tmp_path / "out.txt")
        result = _runner().invoke(cli, ["transform", "nonexistent.txt", out])
        assert result.exit_code != 0

    def test_calls_transform_file(self, tmp_path):
        inp = tmp_path / "diary.txt"
        inp.write_text("1660-01-01T00:00 | raw | DiaryEntry | Some text.\n", encoding="utf-8")
        out = str(tmp_path / "out.txt")
        mock_dt = _mock_dt()
        with patch("diary_transformer.cli._make_transformer", return_value=mock_dt):
            result = _runner().invoke(cli, ["transform", str(inp), out])
        assert result.exit_code == 0
        mock_dt.transform_file.assert_called_once()

    def test_resume_calls_incremental(self, tmp_path):
        inp = tmp_path / "diary.txt"
        inp.write_text("1660-01-01T00:00 | raw | DiaryEntry | Some text.\n", encoding="utf-8")
        out = str(tmp_path / "out.txt")
        mock_dt = _mock_dt()
        with patch("diary_transformer.cli._make_transformer", return_value=mock_dt):
            result = _runner().invoke(cli, ["transform", str(inp), out, "--resume"])
        assert result.exit_code == 0
        mock_dt.transform_file_incremental.assert_called_once()
        mock_dt.transform_file.assert_not_called()

    def test_batch_size_passed_through(self, tmp_path):
        inp = tmp_path / "diary.txt"
        inp.write_text("1660-01-01T00:00 | raw | DiaryEntry | text.\n", encoding="utf-8")
        out = str(tmp_path / "out.txt")
        mock_dt = _mock_dt()
        with patch("diary_transformer.cli._make_transformer", return_value=mock_dt):
            result = _runner().invoke(cli, [
                "transform", str(inp), out, "--batch-size", "50"
            ])
        assert result.exit_code == 0
        _, kwargs = mock_dt.transform_file.call_args
        assert kwargs.get("batch_size") == 50

    def test_seed_passed_through(self, tmp_path):
        inp = tmp_path / "diary.txt"
        inp.write_text("1660-01-01T00:00 | raw | DiaryEntry | text.\n", encoding="utf-8")
        out = str(tmp_path / "out.txt")
        mock_dt = _mock_dt()
        with patch("diary_transformer.cli._make_transformer", return_value=mock_dt):
            result = _runner().invoke(cli, [
                "transform", str(inp), out, "--seed", "42"
            ])
        assert result.exit_code == 0
        _, kwargs = mock_dt.transform_file.call_args
        assert kwargs.get("seed") == 42


# ---------------------------------------------------------------------------
# ingest command
# ---------------------------------------------------------------------------

class TestIngestCommand:
    def test_missing_input_exits_nonzero(self, tmp_path):
        corpus = str(tmp_path / "corpus")
        result = _runner().invoke(cli, ["ingest", "nonexistent.txt", corpus])
        assert result.exit_code != 0

    def test_calls_ingest_to_corpus(self, tmp_path):
        inp = tmp_path / "diary.txt"
        inp.write_text("1660-01-01T00:00 | raw | DiaryEntry | text.\n", encoding="utf-8")
        corpus = str(tmp_path / "corpus")
        mock_dt = _mock_dt(ingest_return=7)
        with patch("diary_transformer.cli._make_transformer", return_value=mock_dt):
            result = _runner().invoke(cli, ["ingest", str(inp), corpus])
        assert result.exit_code == 0
        mock_dt.ingest_to_corpus.assert_called_once()

    def test_wipe_flag_removes_md_files(self, tmp_path):
        inp = tmp_path / "diary.txt"
        inp.write_text("1660-01-01T00:00 | raw | DiaryEntry | text.\n", encoding="utf-8")
        corpus = tmp_path / "corpus"
        corpus.mkdir()
        # Create some stale .md files
        for i in range(3):
            (corpus / f"chunk_{i}.md").write_text("old", encoding="utf-8")
        mock_dt = _mock_dt()
        with patch("diary_transformer.cli._make_transformer", return_value=mock_dt):
            result = _runner().invoke(cli, ["ingest", str(inp), str(corpus), "--wipe"])
        assert result.exit_code == 0
        # Old .md files should have been removed
        old_files = list(corpus.glob("chunk_*.md"))
        assert old_files == []

    def test_source_file_passed_as_kwarg(self, tmp_path):
        inp = tmp_path / "diary.txt"
        inp.write_text("1660-01-01T00:00 | raw | DiaryEntry | text.\n", encoding="utf-8")
        corpus = str(tmp_path / "corpus")
        mock_dt = _mock_dt()
        with patch("diary_transformer.cli._make_transformer", return_value=mock_dt):
            result = _runner().invoke(cli, [
                "ingest", str(inp), corpus, "--source-file", "my_diary.txt"
            ])
        assert result.exit_code == 0
        _, kwargs = mock_dt.ingest_to_corpus.call_args
        assert kwargs.get("source_file") == "my_diary.txt"

    def test_output_mentions_chunk_count(self, tmp_path):
        inp = tmp_path / "diary.txt"
        inp.write_text("1660-01-01T00:00 | raw | DiaryEntry | text.\n", encoding="utf-8")
        corpus = str(tmp_path / "corpus")
        mock_dt = _mock_dt(ingest_return=13)
        with patch("diary_transformer.cli._make_transformer", return_value=mock_dt):
            result = _runner().invoke(cli, ["ingest", str(inp), corpus])
        assert result.exit_code == 0
        assert "13" in result.output


# ---------------------------------------------------------------------------
# build command
# ---------------------------------------------------------------------------

class TestBuildCommand:
    def test_missing_corpus_dir_exits_nonzero(self, tmp_path):
        result = _runner().invoke(cli, ["build", str(tmp_path / "nonexistent")])
        assert result.exit_code != 0

    def test_dockg_not_found_exits_nonzero(self, tmp_path):
        corpus = tmp_path / "corpus"
        corpus.mkdir()
        with patch("subprocess.run", side_effect=FileNotFoundError("dockg not found")):
            result = _runner().invoke(cli, ["build", str(corpus)])
        assert result.exit_code != 0
        assert "dockg" in result.output.lower() or result.exit_code != 0

    def test_dockg_build_called(self, tmp_path):
        corpus = tmp_path / "corpus"
        corpus.mkdir()
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0)
            result = _runner().invoke(cli, ["build", str(corpus)])
        mock_run.assert_called_once()
        cmd = mock_run.call_args[0][0]
        assert "dockg" in cmd
        assert "build" in cmd

    def test_wipe_flag_forwarded(self, tmp_path):
        corpus = tmp_path / "corpus"
        corpus.mkdir()
        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0)
            result = _runner().invoke(cli, ["build", str(corpus), "--wipe"])
        cmd = mock_run.call_args[0][0]
        assert "--wipe" in cmd
