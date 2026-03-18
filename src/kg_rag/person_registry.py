"""
person_registry.py

PersonCorpusRegistry — SQLite-backed registry for person-centric KG corpora.

A PersonCorpusEntry groups all knowledge graphs relevant to a specific individual
(documents, memories, diary entries, verse, code, etc.) under a single entity,
enriched with personal metadata such as birth year, address, and contact info.

Stored in the same SQLite file as KGRegistry and CorpusRegistry
(default: ~/.kgrag/registry.sqlite).
"""

from __future__ import annotations

import json
import sqlite3
from collections.abc import Iterator
from datetime import UTC, datetime
from pathlib import Path

from kg_rag.primitives import KGEntry, PersonCorpusEntry, PersonCorpusStats
from kg_rag.registry import KGRegistry, default_registry_path


class PersonCorpusRegistry:
    """Registry of person-centric KG corpora.

    Each entry represents a person and aggregates the KG instances associated
    with them — documents, memories, diary entries, verses, and more.
    Personal metadata (birth year, address, email, phone, notes) is stored
    alongside the KG references.

    :param db_path: Path to the registry SQLite file. Defaults to
        ``~/.kgrag/registry.sqlite`` (or KGRAG_REGISTRY env var).
    """

    _SCHEMA = """
    CREATE TABLE IF NOT EXISTS person_corpora (
        id          TEXT PRIMARY KEY,
        name        TEXT NOT NULL UNIQUE,
        kg_ids      TEXT NOT NULL DEFAULT '[]',
        birth_year  INTEGER,
        birth_date  TEXT,
        address     TEXT NOT NULL DEFAULT '',
        email       TEXT NOT NULL DEFAULT '',
        phone       TEXT NOT NULL DEFAULT '',
        notes       TEXT NOT NULL DEFAULT '',
        tags        TEXT NOT NULL DEFAULT '[]',
        metadata    TEXT NOT NULL DEFAULT '{}',
        created_at  TEXT NOT NULL,
        updated_at  TEXT NOT NULL
    );
    CREATE INDEX IF NOT EXISTS idx_person_name ON person_corpora(name);
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

    def __enter__(self) -> PersonCorpusRegistry:
        return self

    def __exit__(self, *_) -> None:
        self.close()

    # ------------------------------------------------------------------
    # Write operations
    # ------------------------------------------------------------------

    def create(self, entry: PersonCorpusEntry) -> PersonCorpusEntry:
        """Create a new person corpus entry, or replace if name already exists.

        :param entry: The PersonCorpusEntry to store.
        :return: The stored entry.
        """
        existing = self.find_by_name(entry.name)
        if existing and existing.id != entry.id:
            entry = PersonCorpusEntry(
                id=existing.id,
                name=entry.name,
                kg_ids=entry.kg_ids,
                birth_year=entry.birth_year,
                birth_date=entry.birth_date,
                address=entry.address,
                email=entry.email,
                phone=entry.phone,
                notes=entry.notes,
                tags=entry.tags,
                created_at=existing.created_at,
                updated_at=datetime.now(UTC),
                metadata=entry.metadata,
            )
        self._conn.execute(
            """
            INSERT OR REPLACE INTO person_corpora
                (id, name, kg_ids, birth_year, birth_date, address, email, phone,
                 notes, tags, metadata, created_at, updated_at)
            VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)
            """,
            (
                entry.id,
                entry.name,
                json.dumps(entry.kg_ids),
                entry.birth_year,
                entry.birth_date,
                entry.address,
                entry.email,
                entry.phone,
                entry.notes,
                json.dumps(entry.tags),
                json.dumps(entry.metadata),
                entry.created_at.isoformat(),
                entry.updated_at.isoformat(),
            ),
        )
        self._conn.commit()
        return entry

    def delete(self, name_or_id: str) -> bool:
        """Remove a person corpus entry by name or id.

        :param name_or_id: The entry name or UUID.
        :return: True if deleted, False if not found.
        """
        cur = self._conn.execute(
            "DELETE FROM person_corpora WHERE id = ? OR name = ?",
            (name_or_id, name_or_id),
        )
        self._conn.commit()
        return cur.rowcount > 0

    def add_kg(self, name_or_id: str, kg_id: str) -> PersonCorpusEntry | None:
        """Add a KG (by its UUID) to a person corpus.

        :param name_or_id: The person entry name or UUID.
        :param kg_id: The KGEntry UUID to add.
        :return: Updated PersonCorpusEntry, or None if not found.
        """
        entry = self.get(name_or_id)
        if entry is None:
            return None
        if kg_id not in entry.kg_ids:
            entry.kg_ids.append(kg_id)
            entry.updated_at = datetime.now(UTC)
            self.create(entry)
        return entry

    def remove_kg(self, name_or_id: str, kg_id: str) -> PersonCorpusEntry | None:
        """Remove a KG (by its UUID) from a person corpus.

        :param name_or_id: The person entry name or UUID.
        :param kg_id: The KGEntry UUID to remove.
        :return: Updated PersonCorpusEntry, or None if not found.
        """
        entry = self.get(name_or_id)
        if entry is None:
            return None
        if kg_id in entry.kg_ids:
            entry.kg_ids.remove(kg_id)
            entry.updated_at = datetime.now(UTC)
            self.create(entry)
        return entry

    def update(self, name_or_id: str, **kwargs) -> PersonCorpusEntry | None:
        """Update fields of an existing person corpus entry.

        :param name_or_id: The entry name or UUID.
        :param kwargs: Fields to update (birth_year, birth_date, address, email,
            phone, notes, tags, metadata, kg_ids).
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

    def get(self, name_or_id: str) -> PersonCorpusEntry | None:
        """Fetch a person corpus entry by name or id.

        :param name_or_id: The entry name or UUID.
        :return: PersonCorpusEntry if found, None otherwise.
        """
        row = self._conn.execute(
            "SELECT * FROM person_corpora WHERE id = ? OR name = ?",
            (name_or_id, name_or_id),
        ).fetchone()
        return self._row_to_entry(row) if row else None

    def find_by_name(self, name: str) -> PersonCorpusEntry | None:
        """Fetch a person corpus entry by exact name.

        :param name: Exact name of the person.
        :return: PersonCorpusEntry if found, None otherwise.
        """
        row = self._conn.execute("SELECT * FROM person_corpora WHERE name = ?", (name,)).fetchone()
        return self._row_to_entry(row) if row else None

    def list(self) -> list[PersonCorpusEntry]:
        """List all person corpus entries ordered by name.

        :return: List of PersonCorpusEntry objects.
        """
        rows = self._conn.execute("SELECT * FROM person_corpora ORDER BY name").fetchall()
        return [self._row_to_entry(r) for r in rows]

    def iter(self) -> Iterator[PersonCorpusEntry]:
        """Iterate over all person corpus entries (memory-efficient).

        :return: Iterator of PersonCorpusEntry objects.
        """
        yield from self.list()

    def stats(self) -> PersonCorpusStats:
        """Compute summary statistics for the person corpus registry.

        :return: PersonCorpusStats with total counts and KG reference totals.
        """
        entries = self.list()
        total_kg_refs = sum(e.size for e in entries)
        return PersonCorpusStats(
            total=len(entries),
            total_kg_refs=total_kg_refs,
            registry_path=self._db_path,
        )

    def resolve_kg_entries(self, name_or_id: str, kg_registry: KGRegistry) -> list[KGEntry]:  # type: ignore[valid-type]
        """Resolve a person's KG IDs to actual KGEntry objects.

        :param name_or_id: The person entry name or UUID.
        :param kg_registry: The KGRegistry to look up entries from.
        :return: List of KGEntry objects (missing ones skipped).
        """
        entry = self.get(name_or_id)
        if entry is None:
            return []
        entries = []
        for kg_id in entry.kg_ids:
            kg_entry = kg_registry.get(kg_id)
            if kg_entry is not None:
                entries.append(kg_entry)
        return entries

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _row_to_entry(row: sqlite3.Row) -> PersonCorpusEntry:
        return PersonCorpusEntry(
            id=row["id"],
            name=row["name"],
            kg_ids=json.loads(row["kg_ids"]),
            birth_year=row["birth_year"],
            birth_date=row["birth_date"],
            address=row["address"],
            email=row["email"],
            phone=row["phone"],
            notes=row["notes"],
            tags=json.loads(row["tags"]),
            metadata=json.loads(row["metadata"]),
            created_at=datetime.fromisoformat(row["created_at"]),
            updated_at=datetime.fromisoformat(row["updated_at"]),
        )
