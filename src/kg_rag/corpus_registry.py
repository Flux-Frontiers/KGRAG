"""
corpus_registry.py

CorpusRegistry — SQLite-backed registry for named KG corpora.

A corpus is a named collection of KG instances (referenced by their IDs)
that can be queried and managed as a unified group.

Stored in the same SQLite file as KGRegistry (default: ~/.kgrag/registry.sqlite).
"""

from __future__ import annotations

import json
import sqlite3
from collections.abc import Iterator
from datetime import UTC, datetime
from pathlib import Path

from kg_rag.primitives import CorpusEntry, CorpusStats, KGEntry
from kg_rag.registry import KGRegistry, default_registry_path


class CorpusRegistry:
    """Registry of named KG corpora, stored alongside the KGRegistry.

    A corpus groups multiple KGEntry IDs under a single logical name,
    enabling scoped queries and batch operations across a defined subset
    of registered KGs.

    :param db_path: Path to the registry SQLite file. Defaults to
        ``~/.kgrag/registry.sqlite`` (or KGRAG_REGISTRY env var).
    """

    _SCHEMA = """
    CREATE TABLE IF NOT EXISTS corpora (
        id          TEXT PRIMARY KEY,
        name        TEXT NOT NULL UNIQUE,
        description TEXT NOT NULL DEFAULT '',
        kg_ids      TEXT NOT NULL DEFAULT '[]',
        tags        TEXT NOT NULL DEFAULT '[]',
        metadata    TEXT NOT NULL DEFAULT '{}',
        created_at  TEXT NOT NULL,
        updated_at  TEXT NOT NULL
    );
    CREATE INDEX IF NOT EXISTS idx_corpus_name ON corpora(name);
    """

    def __init__(self, db_path: Path | None = None) -> None:
        self._db_path = Path(db_path).resolve() if db_path else default_registry_path()
        self._db_path.parent.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(str(self._db_path), check_same_thread=False)
        self._conn.row_factory = sqlite3.Row
        self._conn.executescript(self._SCHEMA)
        self._conn.commit()

    @property
    def db_path(self) -> Path:
        """Path to the registry database file."""
        return self._db_path

    def close(self) -> None:
        """Close the database connection."""
        self._conn.close()

    def __enter__(self) -> CorpusRegistry:
        return self

    def __exit__(self, *_) -> None:
        self.close()

    # ------------------------------------------------------------------
    # Write operations
    # ------------------------------------------------------------------

    def create(self, entry: CorpusEntry) -> CorpusEntry:
        """Create a new corpus, or replace if name already exists.

        :param entry: The CorpusEntry to store.
        :return: The stored entry.
        :raises ValueError: If name conflicts with existing entry of different id.
        """
        existing = self.find_by_name(entry.name)
        if existing and existing.id != entry.id:
            entry = CorpusEntry(
                id=existing.id,
                name=entry.name,
                description=entry.description,
                kg_ids=entry.kg_ids,
                tags=entry.tags,
                created_at=existing.created_at,
                updated_at=datetime.now(UTC),
                metadata=entry.metadata,
            )
        self._conn.execute(
            """
            INSERT OR REPLACE INTO corpora
                (id, name, description, kg_ids, tags, metadata, created_at, updated_at)
            VALUES (?,?,?,?,?,?,?,?)
            """,
            (
                entry.id,
                entry.name,
                entry.description,
                json.dumps(entry.kg_ids),
                json.dumps(entry.tags),
                json.dumps(entry.metadata),
                entry.created_at.isoformat(),
                entry.updated_at.isoformat(),
            ),
        )
        self._conn.commit()
        return entry

    def delete(self, name_or_id: str) -> bool:
        """Remove a corpus by name or id.

        :param name_or_id: The corpus name or UUID.
        :return: True if deleted, False if not found.
        """
        cur = self._conn.execute(
            "DELETE FROM corpora WHERE id = ? OR name = ?",
            (name_or_id, name_or_id),
        )
        self._conn.commit()
        return cur.rowcount > 0

    def add_kg(self, name_or_id: str, kg_id: str) -> CorpusEntry | None:
        """Add a KG (by its ID) to an existing corpus.

        :param name_or_id: The corpus name or UUID.
        :param kg_id: The KGEntry UUID to add.
        :return: Updated CorpusEntry, or None if corpus not found.
        """
        entry = self.get(name_or_id)
        if entry is None:
            return None
        if kg_id not in entry.kg_ids:
            entry.kg_ids.append(kg_id)
            entry.updated_at = datetime.now(UTC)
            self.create(entry)
        return entry

    def remove_kg(self, name_or_id: str, kg_id: str) -> CorpusEntry | None:
        """Remove a KG (by its ID) from an existing corpus.

        :param name_or_id: The corpus name or UUID.
        :param kg_id: The KGEntry UUID to remove.
        :return: Updated CorpusEntry, or None if corpus not found.
        """
        entry = self.get(name_or_id)
        if entry is None:
            return None
        if kg_id in entry.kg_ids:
            entry.kg_ids.remove(kg_id)
            entry.updated_at = datetime.now(UTC)
            self.create(entry)
        return entry

    def update(self, name_or_id: str, **kwargs) -> CorpusEntry | None:
        """Update fields of an existing corpus.

        :param name_or_id: The corpus name or UUID.
        :param kwargs: Fields to update (description, tags, metadata, kg_ids).
        :return: Updated entry, or None if not found.
        """
        entry = self.get(name_or_id)
        if entry is None:
            return None
        for k, v in kwargs.items():
            if hasattr(entry, k):
                setattr(entry, k, v)
        entry.updated_at = datetime.now(UTC)
        return self.create(entry)

    # ------------------------------------------------------------------
    # Read operations
    # ------------------------------------------------------------------

    def get(self, name_or_id: str) -> CorpusEntry | None:
        """Fetch a corpus by name or id.

        :param name_or_id: The corpus name or UUID.
        :return: CorpusEntry if found, None otherwise.
        """
        row = self._conn.execute(
            "SELECT * FROM corpora WHERE id = ? OR name = ?",
            (name_or_id, name_or_id),
        ).fetchone()
        return self._row_to_entry(row) if row else None

    def find_by_name(self, name: str) -> CorpusEntry | None:
        """Fetch a corpus by exact name.

        :param name: Exact name of the corpus.
        :return: CorpusEntry if found, None otherwise.
        """
        row = self._conn.execute("SELECT * FROM corpora WHERE name = ?", (name,)).fetchone()
        return self._row_to_entry(row) if row else None

    def list(self) -> list[CorpusEntry]:  # ty: ignore[invalid-type-form]
        """List all corpora ordered by name.

        :return: List of CorpusEntry objects.
        """
        rows = self._conn.execute("SELECT * FROM corpora ORDER BY name").fetchall()
        return [self._row_to_entry(r) for r in rows]

    def iter(self) -> Iterator[CorpusEntry]:
        """Iterate over all corpora (memory-efficient).

        :return: Iterator of CorpusEntry objects.
        """
        yield from self.list()

    def stats(self) -> CorpusStats:
        """Compute summary statistics for the corpus registry.

        :return: CorpusStats with total counts and KG reference totals.
        """
        entries = self.list()
        total_kg_refs = sum(e.size for e in entries)
        return CorpusStats(
            total=len(entries),
            total_kg_refs=total_kg_refs,
            registry_path=self._db_path,
        )

    def resolve_kg_entries(
        self, name_or_id: str, kg_registry: KGRegistry
    ) -> list[KGEntry]:  # ty: ignore[invalid-type-form]
        """Resolve corpus KG IDs to actual KGEntry objects.

        :param name_or_id: The corpus name or UUID.
        :param kg_registry: The KGRegistry to look up entries from.
        :return: List of KGEntry objects for the corpus members (missing ones skipped).
        """
        corpus = self.get(name_or_id)
        if corpus is None:
            return []
        entries = []
        for kg_id in corpus.kg_ids:
            entry = kg_registry.get(kg_id)
            if entry is not None:
                entries.append(entry)
        return entries

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _row_to_entry(row: sqlite3.Row) -> CorpusEntry:
        return CorpusEntry(
            id=row["id"],
            name=row["name"],
            description=row["description"],
            kg_ids=json.loads(row["kg_ids"]),
            tags=json.loads(row["tags"]),
            metadata=json.loads(row["metadata"]),
            created_at=datetime.fromisoformat(row["created_at"]),
            updated_at=datetime.fromisoformat(row["updated_at"]),
        )
