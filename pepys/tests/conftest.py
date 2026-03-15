"""
conftest.py — shared fixtures for the pepys test suite.
"""

from __future__ import annotations

from datetime import datetime
from pathlib import Path

import pytest

from diary_transformer.models import DiaryEntry, EntryChunk


# ---------------------------------------------------------------------------
# Diary entry / chunk fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def diary_entry() -> DiaryEntry:
    return DiaryEntry(
        timestamp=datetime(1667, 4, 15, 22, 30),
        original_type="raw",
        category="DiaryEntry",
        content="So home and to bed, being very sleepy after a great deal of mirth.",
        source_file="pepys_diary.txt",
        index=0,
    )


@pytest.fixture
def diary_entry_no_source() -> DiaryEntry:
    return DiaryEntry(
        timestamp=datetime(1660, 1, 1, 0, 0),
        original_type="raw",
        category="DiaryEntry",
        content="Blessed be God, at the end of the last year I was in very good health.",
    )


@pytest.fixture
def entry_chunk(diary_entry) -> EntryChunk:
    return EntryChunk(
        timestamp=diary_entry.timestamp,
        semantic_category="social",
        context_classification="Home",
        content="So home and to bed, being very sleepy.",
        confidence=0.9,
        phase="immediate",
        source_entry_index=0,
        source_entry=diary_entry,
    )


@pytest.fixture
def sample_diary_txt(tmp_path) -> Path:
    """A minimal pipe-delimited diary file with 5 entries."""
    lines = [
        "1660-01-01T00:00 | raw | DiaryEntry | Blessed be God, at the end of the last year I was in very good health.",
        "1660-01-02T09:00 | raw | DiaryEntry | This morning I went to the office and there did some business.",
        "1660-01-03T20:00 | raw | DiaryEntry | Home and to supper, and so to bed.",
        "1661-04-23T00:00 | raw | DiaryEntry | Up early and to the office, where much business.",
        "1667-04-15T22:30 | raw | DiaryEntry | So home and to bed, being very sleepy after great mirth.",
    ]
    p = tmp_path / "pepys_diary.txt"
    p.write_text("\n".join(lines), encoding="utf-8")
    return p


@pytest.fixture
def tmp_kg_root(tmp_path) -> Path:
    """A temporary project root suitable for DiaryKG."""
    root = tmp_path / "pepys_project"
    root.mkdir()
    return root


@pytest.fixture
def built_kg_root(tmp_kg_root, sample_diary_txt) -> Path:
    """A DiaryKG root with a minimal pre-built corpus (no real DocKG needed)."""
    import json
    from datetime import UTC

    kg_dir = tmp_kg_root / ".diarykg"
    corpus_dir = kg_dir / "corpus"
    corpus_dir.mkdir(parents=True)

    # Write a handful of fake chunk .md files
    chunks = [
        ("1660-01-01T00:00", "domestic", "Home", "pepys_diary.txt", 0, 0,
         "Blessed be God, at the end of the last year I was in very good health."),
        ("1660-01-02T09:00", "work", "Work", "pepys_diary.txt", 1, 0,
         "This morning I went to the office and there did some business."),
        ("1660-01-03T20:00", "domestic", "Home", "pepys_diary.txt", 2, 0,
         "Home and to supper, and so to bed."),
        ("1661-04-23T00:00", "work", "Office", "pepys_diary.txt", 3, 0,
         "Up early and to the office, where much business."),
        ("1667-04-15T22:30", "social", "General", "pepys_diary.txt", 4, 0,
         "So home and to bed, being very sleepy after great mirth."),
    ]
    for ts, cat, ctx, sf, eidx, cidx, body in chunks:
        fname = f"entry_{eidx:04d}_chunk_{cidx}.md"
        (corpus_dir / fname).write_text(
            f"---\nsource_file: {sf}\nentry_index: {eidx}\n"
            f"chunk_index: {cidx}\ntimestamp: {ts}\n"
            f"category: {cat}\ncontext: {ctx}\n---\n\n{body}\n",
            encoding="utf-8",
        )

    # Fake sqlite to satisfy is_built()
    db = kg_dir / "graph.sqlite"
    db.touch()

    # config.json
    (kg_dir / "config.json").write_text(
        json.dumps({
            "source_file": "pepys_diary.txt",
            "built_at": datetime.now(UTC).isoformat(),
            "chunk_count": len(chunks),
            "chunking_strategy": "sentence_group",
            "chunk_size": 512,
        }),
        encoding="utf-8",
    )

    return tmp_kg_root
