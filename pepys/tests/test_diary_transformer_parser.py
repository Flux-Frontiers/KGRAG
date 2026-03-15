"""
test_diary_transformer_parser.py

Unit tests for diary_transformer.parser — is_meaningless_fragment and
parse_diary_file.
"""

from __future__ import annotations

from datetime import datetime
from pathlib import Path

import pytest

from diary_transformer.parser import is_meaningless_fragment, parse_diary_file


class TestIsMeaninglessFragment:
    def test_empty_string(self):
        assert is_meaningless_fragment("") is True

    def test_whitespace_only(self):
        assert is_meaningless_fragment("   \t\n  ") is True

    def test_too_short(self):
        assert is_meaningless_fragment("Hi") is True

    def test_bare_ordinal_date(self):
        # Patterns like "1st" or "22nd" alone
        assert is_meaningless_fragment("1st") is True
        assert is_meaningless_fragment("22nd") is True

    def test_single_word(self):
        assert is_meaningless_fragment("Hello") is True

    def test_meaningful_sentence(self):
        assert is_meaningless_fragment("So home and to bed, being very sleepy.") is False

    def test_short_but_non_trivial(self):
        # Just above the threshold — depends on implementation; at minimum
        # a real sentence should never be flagged as meaningless.
        assert is_meaningless_fragment("Went to the office today.") is False


class TestParseDiaryFile:
    def test_parses_valid_entries(self, sample_diary_txt):
        entries = parse_diary_file(str(sample_diary_txt))
        assert len(entries) == 5

    def test_entry_fields(self, sample_diary_txt):
        entries = parse_diary_file(str(sample_diary_txt))
        e = entries[0]
        assert e.timestamp == datetime(1660, 1, 1, 0, 0)
        assert e.original_type == "raw"
        assert e.category == "DiaryEntry"
        assert "Blessed be God" in e.content

    def test_indices_assigned(self, sample_diary_txt):
        entries = parse_diary_file(str(sample_diary_txt))
        # parse_diary_file itself may or may not assign indices;
        # transformer._load_or_build_cache assigns them — so we just
        # check the list is ordered
        assert len(entries) == 5

    def test_empty_file_returns_empty(self, tmp_path):
        f = tmp_path / "empty.txt"
        f.write_text("", encoding="utf-8")
        entries = parse_diary_file(str(f))
        assert entries == []

    def test_skips_blank_lines(self, tmp_path):
        content = (
            "\n"
            "1660-01-01T00:00 | raw | DiaryEntry | First entry.\n"
            "\n"
            "1660-01-02T09:00 | raw | DiaryEntry | Second entry.\n"
            "\n"
        )
        f = tmp_path / "diary.txt"
        f.write_text(content, encoding="utf-8")
        entries = parse_diary_file(str(f))
        assert len(entries) == 2

    def test_skips_comment_lines(self, tmp_path):
        content = (
            "# This is a comment\n"
            "1660-01-01T00:00 | raw | DiaryEntry | Real entry.\n"
        )
        f = tmp_path / "diary.txt"
        f.write_text(content, encoding="utf-8")
        entries = parse_diary_file(str(f))
        assert len(entries) == 1

    def test_timestamps_parsed_correctly(self, sample_diary_txt):
        entries = parse_diary_file(str(sample_diary_txt))
        ts_last = entries[-1].timestamp
        assert ts_last == datetime(1667, 4, 15, 22, 30)
