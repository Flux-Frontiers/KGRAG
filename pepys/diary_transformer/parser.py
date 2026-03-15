"""parser.py — Pipe-delimited diary file parser."""

from __future__ import annotations

import re
from datetime import datetime
from typing import List

from .models import DiaryEntry


def is_meaningless_fragment(text: str) -> bool:
    """Return True if text is too trivial to store as a memory chunk.

    Filters out very short strings, bare ordinal dates (``1st``, ``23rd``),
    and single-character tokens.

    :param text: Text to evaluate.
    :return: True if the text should be discarded.
    """
    cleaned = text.strip()
    if len(cleaned) < 10:
        return True
    if re.match(r"^\d+(st|nd|rd|th)\.?$", cleaned):
        return True
    if re.match(r"^[A-Za-z0-9]\.?$", cleaned):
        return True
    return False


def parse_diary_file(file_path: str) -> List[DiaryEntry]:
    """Parse a pipe-delimited diary file into DiaryEntry objects.

    Expected line format::

        TIMESTAMP | TYPE | CATEGORY | CONTENT

    Lines that fail to parse or contain only meaningless content are skipped
    with a warning.

    :param file_path: Path to the diary text file.
    :return: Ordered list of DiaryEntry objects.
    """
    print(f"Parsing diary file: {file_path}")
    entries: List[DiaryEntry] = []

    with open(file_path, "r", encoding="utf-8") as f:
        raw = f.read()

    lines = [ln.strip() for ln in raw.split("\n") if ln.strip()]
    total = len(lines)
    print(f"Processing {total} lines...")

    for i, line in enumerate(lines):
        if i > 0 and i % 500 == 0:
            print(f"  Parsed {i}/{total} lines ({i * 100 // total}%)")

        parts = line.split(" | ", 3)
        if len(parts) < 4:
            continue

        try:
            timestamp = datetime.fromisoformat(parts[0].replace("T", " "))
            content = parts[3].strip()
            if is_meaningless_fragment(content):
                continue
            entries.append(
                DiaryEntry(
                    timestamp=timestamp,
                    original_type=parts[1],
                    category=parts[2],
                    content=content,
                )
            )
        except ValueError as exc:
            print(f"Warning: Failed to parse line: {line[:100]}... Error: {exc}")

    print(f"Parsed {len(entries)} diary entries")
    return entries
