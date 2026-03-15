"""
test_diary_transformer_models.py

Unit tests for diary_transformer.models — DiaryEntry and EntryChunk.
"""

from __future__ import annotations

from datetime import datetime

import pytest

from diary_transformer.models import DiaryEntry, EntryChunk


class TestDiaryEntry:
    def test_required_fields(self):
        e = DiaryEntry(
            timestamp=datetime(1660, 1, 1),
            original_type="raw",
            category="DiaryEntry",
            content="Some text.",
        )
        assert e.timestamp == datetime(1660, 1, 1)
        assert e.original_type == "raw"
        assert e.category == "DiaryEntry"
        assert e.content == "Some text."

    def test_source_file_defaults_to_empty_string(self):
        e = DiaryEntry(
            timestamp=datetime(1660, 1, 1),
            original_type="raw",
            category="DiaryEntry",
            content="text",
        )
        assert e.source_file == ""

    def test_source_file_can_be_set(self):
        e = DiaryEntry(
            timestamp=datetime(1660, 1, 1),
            original_type="raw",
            category="DiaryEntry",
            content="text",
            source_file="pepys_diary.txt",
        )
        assert e.source_file == "pepys_diary.txt"

    def test_index_defaults_to_none(self):
        e = DiaryEntry(
            timestamp=datetime(1660, 1, 1),
            original_type="raw",
            category="DiaryEntry",
            content="text",
        )
        assert e.index is None

    def test_chunks_defaults_to_none(self):
        e = DiaryEntry(
            timestamp=datetime(1660, 1, 1),
            original_type="raw",
            category="DiaryEntry",
            content="text",
        )
        assert e.chunks is None

    def test_chunks_can_be_set(self):
        e = DiaryEntry(
            timestamp=datetime(1660, 1, 1),
            original_type="raw",
            category="DiaryEntry",
            content="text",
            chunks=["chunk one", "chunk two"],
        )
        assert e.chunks == ["chunk one", "chunk two"]


class TestEntryChunk:
    def test_required_fields(self, diary_entry):
        chunk = EntryChunk(
            timestamp=diary_entry.timestamp,
            semantic_category="domestic",
            context_classification="Home",
            content="So home and to bed.",
        )
        assert chunk.semantic_category == "domestic"
        assert chunk.context_classification == "Home"
        assert chunk.content == "So home and to bed."

    def test_confidence_defaults_to_1(self, diary_entry):
        chunk = EntryChunk(
            timestamp=diary_entry.timestamp,
            semantic_category="work",
            context_classification="Work",
            content="Office work.",
        )
        assert chunk.confidence == 1.0

    def test_phase_defaults_to_immediate(self, diary_entry):
        chunk = EntryChunk(
            timestamp=diary_entry.timestamp,
            semantic_category="work",
            context_classification="Work",
            content="Office work.",
        )
        assert chunk.phase == "immediate"

    def test_source_entry_index_defaults_to_minus_one(self, diary_entry):
        chunk = EntryChunk(
            timestamp=diary_entry.timestamp,
            semantic_category="work",
            context_classification="Work",
            content="Office work.",
        )
        assert chunk.source_entry_index == -1

    def test_source_entry_can_be_set(self, diary_entry):
        chunk = EntryChunk(
            timestamp=diary_entry.timestamp,
            semantic_category="social",
            context_classification="Social",
            content="Dinner with friends.",
            source_entry=diary_entry,
        )
        assert chunk.source_entry is diary_entry
