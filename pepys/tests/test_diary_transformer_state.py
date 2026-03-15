"""
test_diary_transformer_state.py

Unit tests for diary_transformer.state — chunk cache I/O, filter_uninjected,
and StateManager.
"""

from __future__ import annotations

from datetime import datetime
from pathlib import Path

import pytest

from diary_transformer.models import DiaryEntry
from diary_transformer.state import (
    StateManager,
    filter_uninjected,
    load_chunks_from_cache,
    save_chunks_to_cache,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_entries(n: int = 3) -> list[DiaryEntry]:
    entries = []
    for i in range(n):
        e = DiaryEntry(
            timestamp=datetime(1660, 1, i + 1, 10, 0),
            original_type="raw",
            category="DiaryEntry",
            content=f"Entry number {i + 1}. Some meaningful text here.",
            source_file="pepys.txt",
        )
        e.index = i
        entries.append(e)
    return entries


def _segment_fn(content: str, timestamp=None) -> list[str]:
    """Trivial segmenter: split on period."""
    return [s.strip() for s in content.split(".") if s.strip()]


# ---------------------------------------------------------------------------
# Chunk cache round-trip
# ---------------------------------------------------------------------------

class TestChunkCache:
    def test_save_and_load_roundtrip(self, tmp_path):
        entries = _make_entries(3)
        cache = str(tmp_path / "chunks.json")
        save_chunks_to_cache(entries, cache, _segment_fn)
        loaded = load_chunks_from_cache(cache)
        assert len(loaded) == 3

    def test_loaded_entries_have_chunks(self, tmp_path):
        entries = _make_entries(2)
        cache = str(tmp_path / "chunks.json")
        save_chunks_to_cache(entries, cache, _segment_fn)
        loaded = load_chunks_from_cache(cache)
        for e in loaded:
            assert e.chunks is not None
            assert isinstance(e.chunks, list)

    def test_loaded_entries_preserve_content(self, tmp_path):
        entries = _make_entries(3)
        cache = str(tmp_path / "chunks.json")
        save_chunks_to_cache(entries, cache, _segment_fn)
        loaded = load_chunks_from_cache(cache)
        for orig, loaded_e in zip(entries, loaded):
            assert orig.content == loaded_e.content
            assert orig.timestamp == loaded_e.timestamp

    def test_loaded_entries_have_index(self, tmp_path):
        entries = _make_entries(3)
        cache = str(tmp_path / "chunks.json")
        save_chunks_to_cache(entries, cache, _segment_fn)
        loaded = load_chunks_from_cache(cache)
        for i, e in enumerate(loaded):
            assert e.index == i

    def test_missing_cache_raises(self, tmp_path):
        with pytest.raises(FileNotFoundError):
            load_chunks_from_cache(str(tmp_path / "nonexistent.json"))

    def test_saves_as_pkl(self, tmp_path):
        entries = _make_entries(2)
        cache = str(tmp_path / "chunks.json")
        save_chunks_to_cache(entries, cache, _segment_fn)
        # pkl should be written alongside the json path
        pkl = tmp_path / "chunks.pkl"
        assert pkl.exists()


# ---------------------------------------------------------------------------
# filter_uninjected
# ---------------------------------------------------------------------------

class TestFilterUninjected:
    def test_empty_injected_returns_all(self):
        entries = _make_entries(5)
        result = filter_uninjected(entries, set())
        assert result == entries

    def test_filters_known_indices(self):
        entries = _make_entries(5)
        result = filter_uninjected(entries, {0, 2, 4})
        indices = [e.index for e in result]
        assert indices == [1, 3]

    def test_all_injected_returns_empty(self):
        entries = _make_entries(3)
        result = filter_uninjected(entries, {0, 1, 2})
        assert result == []

    def test_entries_without_index_are_kept(self):
        entries = _make_entries(3)
        entries[1].index = None
        result = filter_uninjected(entries, {0, 2})
        # entry with index=None should not be filtered out
        assert entries[1] in result


# ---------------------------------------------------------------------------
# StateManager
# ---------------------------------------------------------------------------

class TestStateManager:
    def test_initial_state_is_empty(self, tmp_path):
        sm = StateManager(str(tmp_path / "state.json"))
        assert sm.injected_entry_indices == set()
        assert sm.processing_stats["total_runs"] == 0

    def test_load_missing_file_returns_false(self, tmp_path):
        sm = StateManager(str(tmp_path / "missing.json"))
        result = sm.load()
        assert result is False

    def test_save_and_load_roundtrip(self, tmp_path):
        sf = str(tmp_path / "state.json")
        sm = StateManager(sf)
        sm.injected_entry_indices = {0, 1, 2}
        sm.processing_stats["total_runs"] = 2
        sm.processing_stats["total_entries_injected"] = 3
        sm.save("output.txt", {"batch_size": 10})

        sm2 = StateManager(sf)
        sm2.load()
        assert sm2.injected_entry_indices == {0, 1, 2}
        assert sm2.processing_stats["total_runs"] == 2

    def test_mark_injected_adds_indices(self, tmp_path):
        sm = StateManager(str(tmp_path / "state.json"))
        entries = _make_entries(3)
        sm.mark_injected(entries)
        assert sm.injected_entry_indices == {0, 1, 2}

    def test_mark_injected_skips_none_index(self, tmp_path):
        sm = StateManager(str(tmp_path / "state.json"))
        e = DiaryEntry(
            timestamp=datetime(1660, 1, 1),
            original_type="raw",
            category="DiaryEntry",
            content="text",
        )
        e.index = None
        sm.mark_injected([e])
        assert sm.injected_entry_indices == set()

    def test_save_creates_parent_dirs(self, tmp_path):
        deep = tmp_path / "a" / "b" / "c" / "state.json"
        sm = StateManager(str(deep))
        sm.save("out.txt", {})
        assert deep.exists()

    def test_load_corrupted_file_returns_false(self, tmp_path):
        sf = tmp_path / "state.json"
        sf.write_text("not json", encoding="utf-8")
        sm = StateManager(str(sf))
        result = sm.load()
        assert result is False
