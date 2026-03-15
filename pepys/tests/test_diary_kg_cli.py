"""
test_diary_kg_cli.py

Integration tests for the DiaryKG Click CLI (diary_kg.cli).

Uses Click's CliRunner so no real server or DB is needed.  DiaryKG is mocked
via patch so only CLI routing, argument handling, and output formatting are
tested.
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from click.testing import CliRunner

from diary_kg.cli import cli


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _runner() -> CliRunner:
    return CliRunner(mix_stderr=False)


def _mock_kg(
    is_built: bool = True,
    info_result: dict | None = None,
    stats_result: dict | None = None,
    snapshot_list_result: list | None = None,
) -> MagicMock:
    kg = MagicMock()
    kg.is_built.return_value = is_built
    kg._read_config.return_value = {"source_file": "pepys.txt", "built_at": "2024-01-01T00:00:00"}
    kg.info.return_value = info_result or {
        "chunk_count": 5,
        "entry_count": 3,
        "source_file": "pepys.txt",
        "built_at": "2024-01-01T00:00:00",
        "temporal_span": {"start": "1660-01-01", "end": "1667-04-15"},
        "topic_counts": {"work": 2, "domestic": 1},
        "context_counts": {"Home": 2},
    }
    kg.stats.return_value = stats_result or {"node_count": 10, "edge_count": 5, "kind": "diary"}
    kg.snapshot_list.return_value = snapshot_list_result or []
    return kg


# ---------------------------------------------------------------------------
# Root group --help
# ---------------------------------------------------------------------------

class TestCliHelp:
    def test_help_exits_zero(self):
        result = _runner().invoke(cli, ["--help"])
        assert result.exit_code == 0

    def test_build_help(self):
        result = _runner().invoke(cli, ["build", "--help"])
        assert result.exit_code == 0
        assert "--source" in result.output

    def test_query_help(self):
        result = _runner().invoke(cli, ["query", "--help"])
        assert result.exit_code == 0

    def test_pack_help(self):
        result = _runner().invoke(cli, ["pack", "--help"])
        assert result.exit_code == 0

    def test_analyze_help(self):
        result = _runner().invoke(cli, ["analyze", "--help"])
        assert result.exit_code == 0

    def test_status_help(self):
        result = _runner().invoke(cli, ["status", "--help"])
        assert result.exit_code == 0

    def test_snapshot_list_help(self):
        result = _runner().invoke(cli, ["snapshot", "list", "--help"])
        assert result.exit_code == 0

    def test_snapshot_save_help(self):
        result = _runner().invoke(cli, ["snapshot", "save", "--help"])
        assert result.exit_code == 0

    def test_snapshot_show_help(self):
        result = _runner().invoke(cli, ["snapshot", "show", "--help"])
        assert result.exit_code == 0

    def test_snapshot_diff_help(self):
        result = _runner().invoke(cli, ["snapshot", "diff", "--help"])
        assert result.exit_code == 0


# ---------------------------------------------------------------------------
# status
# ---------------------------------------------------------------------------

class TestStatusCommand:
    def test_status_shows_not_built(self, tmp_path):
        mock_kg = _mock_kg(is_built=False, snapshot_list_result=[])
        with patch("diary_kg.cli._kg", return_value=mock_kg):
            result = _runner().invoke(cli, ["status", str(tmp_path)])
        assert result.exit_code == 0

    def test_status_shows_built(self, built_kg_root):
        mock_kg = _mock_kg(is_built=True, snapshot_list_result=[])
        with patch("diary_kg.cli._kg", return_value=mock_kg):
            result = _runner().invoke(cli, ["status", str(built_kg_root)])
        assert result.exit_code == 0


# ---------------------------------------------------------------------------
# analyze
# ---------------------------------------------------------------------------

class TestAnalyzeCommand:
    def test_analyze_not_built_exits_nonzero(self, tmp_path):
        mock_kg = _mock_kg(is_built=False)
        with patch("diary_kg.cli._kg", return_value=mock_kg):
            result = _runner().invoke(cli, ["analyze", str(tmp_path)])
        assert result.exit_code != 0

    def test_analyze_outputs_report(self, tmp_path):
        mock_kg = _mock_kg(is_built=True)
        mock_kg.analyze.return_value = "# DiaryKG Analysis Report\n\nContent here."
        with patch("diary_kg.cli._kg", return_value=mock_kg):
            result = _runner().invoke(cli, ["analyze", str(tmp_path)])
        assert result.exit_code == 0

    def test_analyze_writes_output_file(self, tmp_path):
        mock_kg = _mock_kg(is_built=True)
        mock_kg.analyze.return_value = "# Report"
        out = tmp_path / "report.md"
        with patch("diary_kg.cli._kg", return_value=mock_kg):
            result = _runner().invoke(cli, ["analyze", str(tmp_path), "--output", str(out)])
        assert result.exit_code == 0
        assert out.exists()
        assert out.read_text(encoding="utf-8") == "# Report"


# ---------------------------------------------------------------------------
# query
# ---------------------------------------------------------------------------

class TestQueryCommand:
    def test_query_on_unbuilt_exits_nonzero(self, tmp_path):
        mock_kg = _mock_kg(is_built=False)
        mock_kg.query.side_effect = RuntimeError("DiaryKG is not built")
        with patch("diary_kg.cli._kg", return_value=mock_kg):
            result = _runner().invoke(cli, ["query", "office work", str(tmp_path)])
        assert result.exit_code != 0

    def test_query_json_output(self, tmp_path):
        mock_kg = _mock_kg()
        mock_kg.query.return_value = [
            {"node_id": "n1", "score": 0.9, "summary": "text",
             "source_file": "pepys.txt", "timestamp": "1660-01-01T00:00",
             "category": "work", "context": "Office"},
        ]
        with patch("diary_kg.cli._kg", return_value=mock_kg):
            result = _runner().invoke(cli, ["query", "office", str(tmp_path), "--json"])
        assert result.exit_code == 0
        import json
        data = json.loads(result.output)
        assert len(data) == 1
        assert data[0]["node_id"] == "n1"

    def test_query_no_results(self, tmp_path):
        mock_kg = _mock_kg()
        mock_kg.query.return_value = []
        with patch("diary_kg.cli._kg", return_value=mock_kg):
            result = _runner().invoke(cli, ["query", "zzz", str(tmp_path)])
        assert result.exit_code == 0


# ---------------------------------------------------------------------------
# pack
# ---------------------------------------------------------------------------

class TestPackCommand:
    def test_pack_on_unbuilt_exits_nonzero(self, tmp_path):
        mock_kg = _mock_kg(is_built=False)
        mock_kg.pack.side_effect = RuntimeError("DiaryKG is not built")
        with patch("diary_kg.cli._kg", return_value=mock_kg):
            result = _runner().invoke(cli, ["pack", "home", str(tmp_path)])
        assert result.exit_code != 0

    def test_pack_json_output(self, tmp_path):
        mock_kg = _mock_kg()
        mock_kg.pack.return_value = [
            {"node_id": "n1", "score": 0.8, "content": "So home.",
             "source_file": "pepys.txt", "timestamp": "1660-01-01T00:00"},
        ]
        with patch("diary_kg.cli._kg", return_value=mock_kg):
            result = _runner().invoke(cli, ["pack", "home", str(tmp_path), "--json"])
        assert result.exit_code == 0
        import json
        data = json.loads(result.output)
        assert data[0]["content"] == "So home."

    def test_pack_writes_file(self, tmp_path):
        mock_kg = _mock_kg()
        mock_kg.pack.return_value = [
            {"node_id": "n1", "score": 0.8, "content": "So home.",
             "source_file": "pepys.txt", "timestamp": None},
        ]
        out = tmp_path / "context.md"
        with patch("diary_kg.cli._kg", return_value=mock_kg):
            result = _runner().invoke(cli, [
                "pack", "home", str(tmp_path), "--output", str(out)
            ])
        assert result.exit_code == 0
        assert out.exists()


# ---------------------------------------------------------------------------
# snapshot list
# ---------------------------------------------------------------------------

class TestSnapshotListCommand:
    def test_empty_shows_no_snapshots_message(self, tmp_path):
        mock_kg = _mock_kg(snapshot_list_result=[])
        with patch("diary_kg.cli._kg", return_value=mock_kg):
            result = _runner().invoke(cli, ["snapshot", "list", str(tmp_path)])
        assert result.exit_code == 0
        assert "No snapshots" in result.output

    def test_json_output_empty(self, tmp_path):
        mock_kg = _mock_kg(snapshot_list_result=[])
        with patch("diary_kg.cli._kg", return_value=mock_kg):
            result = _runner().invoke(cli, ["snapshot", "list", str(tmp_path), "--json"])
        assert result.exit_code == 0
        import json
        assert json.loads(result.output) == []

    def test_json_output_with_snapshots(self, tmp_path):
        snaps = [
            {"key": "abc123", "branch": "main", "timestamp": "2024-01-01T00:00:00",
             "version": "0.1.0", "label": None,
             "metrics": {"chunk_count": 5, "entry_count": 3, "node_count": 10,
                         "edge_count": 5, "topic_counts": {}, "context_counts": {},
                         "temporal_span": {}, "chunking_strategy": "", "chunk_size": 512},
             "deltas": {"vs_previous": None, "vs_baseline": None}},
        ]
        mock_kg = _mock_kg(snapshot_list_result=snaps)
        with patch("diary_kg.cli._kg", return_value=mock_kg):
            result = _runner().invoke(cli, ["snapshot", "list", str(tmp_path), "--json"])
        assert result.exit_code == 0
        import json
        data = json.loads(result.output)
        assert data[0]["key"] == "abc123"


# ---------------------------------------------------------------------------
# snapshot show
# ---------------------------------------------------------------------------

class TestSnapshotShowCommand:
    def test_missing_key_exits_nonzero(self, tmp_path):
        mock_kg = _mock_kg()
        mock_kg.snapshot_show.side_effect = FileNotFoundError("not found")
        with patch("diary_kg.cli._kg", return_value=mock_kg):
            result = _runner().invoke(cli, ["snapshot", "show", "badkey", str(tmp_path)])
        assert result.exit_code != 0

    def test_json_output(self, tmp_path):
        snap = {
            "key": "abc123",
            "branch": "main",
            "timestamp": "2024-01-01T00:00:00+00:00",
            "version": "0.1.0",
            "label": None,
            "source_file": "pepys.txt",
            "metrics": {"chunk_count": 5, "entry_count": 3, "node_count": 10,
                        "edge_count": 5, "topic_counts": {}, "context_counts": {},
                        "temporal_span": {}, "chunking_strategy": "", "chunk_size": 512},
            "vs_previous": None,
            "vs_baseline": None,
        }
        mock_kg = _mock_kg()
        mock_kg.snapshot_show.return_value = snap
        with patch("diary_kg.cli._kg", return_value=mock_kg):
            result = _runner().invoke(
                cli, ["snapshot", "show", "abc123", str(tmp_path), "--json"]
            )
        assert result.exit_code == 0
        import json
        data = json.loads(result.output)
        assert data["key"] == "abc123"


# ---------------------------------------------------------------------------
# snapshot diff
# ---------------------------------------------------------------------------

class TestSnapshotDiffCommand:
    def test_missing_keys_outputs_diff_with_error(self, tmp_path):
        mock_kg = _mock_kg()
        mock_kg.snapshot_diff.return_value = {"error": "One or both snapshots not found"}
        with patch("diary_kg.cli._kg", return_value=mock_kg):
            result = _runner().invoke(cli, ["snapshot", "diff", "ka", "kb", str(tmp_path)])
        assert result.exit_code == 0  # diff command does not sys.exit on error dict

    def test_json_output(self, tmp_path):
        diff = {
            "a": {"key": "ka", "metrics": {}},
            "b": {"key": "kb", "metrics": {}},
            "delta": {"chunks": 5, "entries": 2, "nodes": 10, "edges": 8},
            "topic_counts_delta": {"work": 3},
        }
        mock_kg = _mock_kg()
        mock_kg.snapshot_diff.return_value = diff
        with patch("diary_kg.cli._kg", return_value=mock_kg):
            result = _runner().invoke(
                cli, ["snapshot", "diff", "ka", "kb", str(tmp_path), "--json"]
            )
        assert result.exit_code == 0
        import json
        data = json.loads(result.output)
        assert data["delta"]["chunks"] == 5


# ---------------------------------------------------------------------------
# snapshot save
# ---------------------------------------------------------------------------

class TestSnapshotSaveCommand:
    def test_not_built_exits_nonzero(self, tmp_path):
        mock_kg = _mock_kg()
        mock_kg.snapshot_save.side_effect = RuntimeError("not built")
        with patch("diary_kg.cli._kg", return_value=mock_kg):
            result = _runner().invoke(cli, ["snapshot", "save", str(tmp_path)])
        assert result.exit_code != 0

    def test_success_shows_key(self, tmp_path):
        snap = {
            "key": "deadbeef1234",
            "branch": "main",
            "version": "0.1.0",
            "label": None,
            "metrics": {"chunk_count": 5, "entry_count": 3},
            "vs_previous": None,
        }
        mock_kg = _mock_kg()
        mock_kg.snapshot_save.return_value = snap
        with patch("diary_kg.cli._kg", return_value=mock_kg):
            result = _runner().invoke(
                cli, ["snapshot", "save", str(tmp_path), "--label", "first"]
            )
        assert result.exit_code == 0
        assert "deadbeef1234" in result.output
