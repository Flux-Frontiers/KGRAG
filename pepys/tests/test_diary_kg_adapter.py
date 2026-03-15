"""
test_diary_kg_adapter.py

Unit tests for kg_rag.adapters.diary_adapter — DiaryKGAdapter.

All tests mock ``diary_kg.kg.DiaryKG`` so no real DocKG or LanceDB is needed.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any
from unittest.mock import MagicMock, patch

import pytest

from kg_rag.adapters.diary_adapter import DiaryKGAdapter
from kg_rag.primitives import CrossHit, CrossSnippet, KGEntry, KGKind


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _entry(is_built: bool = True, source_file: str = "pepys.txt") -> KGEntry:
    """Build a minimal KGEntry for a diary KG."""
    return KGEntry(
        name="pepys",
        kind=KGKind.DIARY,
        repo_path=Path("/fake/pepys"),
        metadata={"source_file": source_file},
        is_built=is_built,
    )


def _mock_kg(
    query_result: list[dict] | None = None,
    pack_result: list[dict] | None = None,
    stats_result: dict | None = None,
    info_result: dict | None = None,
    analyze_result: str = "# Report",
) -> MagicMock:
    kg = MagicMock()
    kg.query.return_value = query_result or []
    kg.pack.return_value = pack_result or []
    kg.stats.return_value = stats_result or {"node_count": 10, "edge_count": 5, "kind": "diary"}
    kg.info.return_value = info_result or {"chunk_count": 5, "entry_count": 3}
    kg.analyze.return_value = analyze_result
    return kg


# ---------------------------------------------------------------------------
# is_available
# ---------------------------------------------------------------------------

class TestIsAvailable:
    def test_returns_true_when_built(self):
        entry = _entry(is_built=True)
        adapter = DiaryKGAdapter(entry)
        with patch("diary_kg.__init__"):
            # diary_kg is importable (we patched it as a module)
            assert adapter.is_available() is True

    def test_returns_false_when_not_built(self):
        entry = _entry(is_built=False)
        adapter = DiaryKGAdapter(entry)
        with patch("diary_kg.__init__"):
            assert adapter.is_available() is False

    def test_returns_false_when_import_error(self):
        entry = _entry(is_built=True)
        adapter = DiaryKGAdapter(entry)
        with patch.dict("sys.modules", {"diary_kg": None}):
            assert adapter.is_available() is False


# ---------------------------------------------------------------------------
# _load
# ---------------------------------------------------------------------------

class TestLoad:
    def test_load_sets_kg(self):
        entry = _entry()
        adapter = DiaryKGAdapter(entry)
        mock_kg_cls = MagicMock(return_value=_mock_kg())
        with patch("diary_kg.kg.DiaryKG", mock_kg_cls):
            adapter._load()
        assert adapter._kg is not None

    def test_load_called_once(self):
        entry = _entry()
        adapter = DiaryKGAdapter(entry)
        mock_kg_cls = MagicMock(return_value=_mock_kg())
        with patch("diary_kg.kg.DiaryKG", mock_kg_cls):
            adapter._load()
            adapter._load()  # second call should not re-instantiate
        mock_kg_cls.assert_called_once()

    def test_load_passes_source_file(self):
        entry = _entry(source_file="my_diary.txt")
        adapter = DiaryKGAdapter(entry)
        mock_kg_cls = MagicMock(return_value=_mock_kg())
        with patch("diary_kg.kg.DiaryKG", mock_kg_cls):
            adapter._load()
        _, kwargs = mock_kg_cls.call_args
        assert kwargs.get("source_file") == "my_diary.txt"

    def test_load_raises_import_error(self):
        entry = _entry()
        adapter = DiaryKGAdapter(entry)
        with patch.dict("sys.modules", {"diary_kg": None, "diary_kg.kg": None}):
            with pytest.raises(ImportError, match="diary-kg is not installed"):
                adapter._load()


# ---------------------------------------------------------------------------
# query
# ---------------------------------------------------------------------------

class TestQuery:
    def test_returns_cross_hit_list(self):
        entry = _entry()
        adapter = DiaryKGAdapter(entry)
        mock_kg = _mock_kg(query_result=[
            {"node_id": "n1", "score": 0.9, "summary": "Went to the office.",
             "source_file": "pepys.txt", "timestamp": "1660-01-02T09:00",
             "category": "work", "context": "Office"},
        ])
        adapter._kg = mock_kg
        results = adapter.query("office work")
        assert len(results) == 1
        hit = results[0]
        assert isinstance(hit, CrossHit)
        assert hit.kg_name == "pepys"
        assert hit.kg_kind == KGKind.DIARY
        assert hit.score == 0.9
        assert hit.source_path == "pepys.txt"

    def test_empty_query_result(self):
        entry = _entry()
        adapter = DiaryKGAdapter(entry)
        adapter._kg = _mock_kg(query_result=[])
        assert adapter.query("nothing") == []

    def test_query_uses_timestamp_as_name(self):
        entry = _entry()
        adapter = DiaryKGAdapter(entry)
        adapter._kg = _mock_kg(query_result=[
            {"node_id": "n1", "score": 0.5, "summary": "text",
             "source_file": "pepys.txt", "timestamp": "1660-01-02T09:00"},
        ])
        results = adapter.query("q")
        assert results[0].name == "1660-01-02T09:00"

    def test_query_k_passed_through(self):
        entry = _entry()
        adapter = DiaryKGAdapter(entry)
        mock_kg = _mock_kg()
        adapter._kg = mock_kg
        adapter.query("q", k=12)
        mock_kg.query.assert_called_once_with("q", k=12)


# ---------------------------------------------------------------------------
# pack
# ---------------------------------------------------------------------------

class TestPack:
    def test_returns_cross_snippet_list(self):
        entry = _entry()
        adapter = DiaryKGAdapter(entry)
        adapter._kg = _mock_kg(pack_result=[
            {"node_id": "n1", "score": 0.8, "content": "So home and to bed.",
             "source_file": "pepys.txt", "timestamp": "1660-01-01T00:00"},
        ])
        snippets = adapter.pack("home bed")
        assert len(snippets) == 1
        s = snippets[0]
        assert isinstance(s, CrossSnippet)
        assert s.content == "So home and to bed."
        assert s.source_path == "pepys.txt"
        assert s.score == 0.8

    def test_empty_pack_result(self):
        entry = _entry()
        adapter = DiaryKGAdapter(entry)
        adapter._kg = _mock_kg(pack_result=[])
        assert adapter.pack("nothing") == []

    def test_pack_k_passed_through(self):
        entry = _entry()
        adapter = DiaryKGAdapter(entry)
        mock_kg = _mock_kg()
        adapter._kg = mock_kg
        adapter.pack("q", k=5)
        mock_kg.pack.assert_called_once_with("q", k=5)


# ---------------------------------------------------------------------------
# stats / info / analyze
# ---------------------------------------------------------------------------

class TestStatsInfoAnalyze:
    def test_stats_delegates_to_kg(self):
        entry = _entry()
        adapter = DiaryKGAdapter(entry)
        adapter._kg = _mock_kg(stats_result={"node_count": 42, "edge_count": 20, "kind": "diary"})
        result = adapter.stats()
        assert result["node_count"] == 42
        assert result["kind"] == "diary"

    def test_info_delegates_to_kg(self):
        entry = _entry()
        adapter = DiaryKGAdapter(entry)
        adapter._kg = _mock_kg(info_result={
            "chunk_count": 15,
            "entry_count": 8,
            "source_file": "pepys.txt",
        })
        result = adapter.info()
        assert result["chunk_count"] == 15
        assert result["entry_count"] == 8

    def test_analyze_returns_markdown(self):
        entry = _entry()
        adapter = DiaryKGAdapter(entry)
        adapter._kg = _mock_kg(analyze_result="# DiaryKG Analysis Report\n\nBody text.")
        report = adapter.analyze()
        assert "# DiaryKG Analysis Report" in report

    def test_stats_triggers_load(self):
        entry = _entry()
        adapter = DiaryKGAdapter(entry)
        mock_kg = _mock_kg()
        with patch("diary_kg.kg.DiaryKG", return_value=mock_kg):
            adapter.stats()
        mock_kg.stats.assert_called_once()
