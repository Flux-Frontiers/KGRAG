"""diary_kg — Knowledge graph module for diaries and journals.

``DiaryKG`` is the top-level class.  ``DiaryTransformer`` (in the sibling
``diary_transformer`` package) is the chunking engine; ``DiaryKG`` orchestrates
it and manages the DocKG-backed storage (SQLite + LanceDB).

Typical usage::

    from diary_kg import DiaryKG

    kg = DiaryKG("/path/to/project", source_file="pepys_diary.txt")
    kg.build()
    hits = kg.query("what did Pepys think of the theatre?")
"""

from __future__ import annotations

from .kg import DiaryKG

__all__ = ["DiaryKG"]
