"""
registry.py

KGRegistry — SQLite-backed system-wide registry for all KG instances.

Default location: ~/.kgrag/registry.sqlite
Override via KGRAG_REGISTRY env var or --registry CLI flag.
"""

from __future__ import annotations

import json
import os
import sqlite3
from collections.abc import Iterator
from datetime import UTC, datetime
from pathlib import Path

from kg_rag.primitives import KGEntry, KGKind, RegistryStats

_DEFAULT_REGISTRY_DIR = Path.home() / ".kgrag"
_DEFAULT_REGISTRY_DB = _DEFAULT_REGISTRY_DIR / "registry.sqlite"


def default_registry_path() -> Path:
    """Return the default registry path, respecting KGRAG_REGISTRY env var.

    :return: Absolute path to the registry SQLite file.
    """
    env = os.environ.get("KGRAG_REGISTRY")
    if env:
        return Path(env).resolve()
    return _DEFAULT_REGISTRY_DB


class KGRegistry:
    """System-wide registry of all KG instances (CodeKG, DocKG, MetaKG).

    Backed by a single SQLite file, typically at ``~/.kgrag/registry.sqlite``.
    Each sub-project can register its KG here so that KGRAG can orchestrate
    cross-KG queries and analysis.

    :param db_path: Path to the registry SQLite file.
    """

    _SCHEMA = """
    CREATE TABLE IF NOT EXISTS kg_entries (
        id          TEXT PRIMARY KEY,
        name        TEXT NOT NULL UNIQUE,
        kind        TEXT NOT NULL,
        repo_path   TEXT NOT NULL,
        venv_path   TEXT NOT NULL,
        sqlite_path TEXT,
        lancedb_path TEXT,
        version     TEXT NOT NULL DEFAULT 'unknown',
        tags        TEXT NOT NULL DEFAULT '[]',
        metadata    TEXT NOT NULL DEFAULT '{}',
        created_at  TEXT NOT NULL,
        updated_at  TEXT NOT NULL
    );
    CREATE INDEX IF NOT EXISTS idx_kind ON kg_entries(kind);
    CREATE INDEX IF NOT EXISTS idx_name ON kg_entries(name);
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

    def __enter__(self) -> KGRegistry:
        return self

    def __exit__(self, *_) -> None:
        self.close()

    # ------------------------------------------------------------------
    # Write operations
    # ------------------------------------------------------------------

    def register(self, entry: KGEntry) -> KGEntry:
        """Register a new KG entry, or replace if name already exists.

        :param entry: The KGEntry to register.
        :return: The registered entry (with resolved paths).
        :raises ValueError: If name conflicts with existing entry of different id.
        """
        existing = self.find_by_name(entry.name)
        if existing and existing.id != entry.id:
            # Replace by name - update the id to match existing
            entry = KGEntry(
                id=existing.id,
                name=entry.name,
                kind=entry.kind,
                repo_path=entry.repo_path,
                venv_path=entry.venv_path,
                sqlite_path=entry.sqlite_path,
                lancedb_path=entry.lancedb_path,
                version=entry.version,
                tags=entry.tags,
                created_at=existing.created_at,
                updated_at=datetime.now(UTC),
                metadata=entry.metadata,
            )
        self._conn.execute(
            """
            INSERT OR REPLACE INTO kg_entries
                (id, name, kind, repo_path, venv_path, sqlite_path, lancedb_path,
                 version, tags, metadata, created_at, updated_at)
            VALUES (?,?,?,?,?,?,?,?,?,?,?,?)
            """,
            (
                entry.id,
                entry.name,
                entry.kind.value,
                str(entry.repo_path),
                str(entry.venv_path),
                str(entry.sqlite_path) if entry.sqlite_path else None,
                str(entry.lancedb_path) if entry.lancedb_path else None,
                entry.version,
                json.dumps(entry.tags),
                json.dumps(entry.metadata),
                entry.created_at.isoformat(),
                entry.updated_at.isoformat(),
            ),
        )
        self._conn.commit()
        return entry

    def unregister(self, name_or_id: str) -> bool:
        """Remove a KG entry by name or id.

        :param name_or_id: The entry name or UUID.
        :return: True if an entry was deleted, False if not found.
        """
        cur = self._conn.execute(
            "DELETE FROM kg_entries WHERE id = ? OR name = ?",
            (name_or_id, name_or_id),
        )
        self._conn.commit()
        return cur.rowcount > 0

    def update(self, name_or_id: str, **kwargs) -> KGEntry | None:
        """Update fields of an existing entry.

        :param name_or_id: The entry name or UUID.
        :param kwargs: Fields to update (repo_path, venv_path, sqlite_path,
            lancedb_path, version, tags, metadata).
        :return: Updated entry, or None if not found.
        """
        entry = self.get(name_or_id)
        if entry is None:
            return None
        # Apply updates
        for k, v in kwargs.items():
            if hasattr(entry, k):
                setattr(entry, k, v)
        entry.updated_at = datetime.now(UTC)
        return self.register(entry)

    # ------------------------------------------------------------------
    # Read operations
    # ------------------------------------------------------------------

    def get(self, name_or_id: str) -> KGEntry | None:
        """Fetch a single entry by name or id.

        :param name_or_id: The entry name or UUID.
        :return: KGEntry if found, None otherwise.
        """
        row = self._conn.execute(
            "SELECT * FROM kg_entries WHERE id = ? OR name = ?",
            (name_or_id, name_or_id),
        ).fetchone()
        return self._row_to_entry(row) if row else None

    def find_by_name(self, name: str) -> KGEntry | None:
        """Fetch a single entry by exact name.

        :param name: Exact name of the KG entry.
        :return: KGEntry if found, None otherwise.
        """
        row = self._conn.execute("SELECT * FROM kg_entries WHERE name = ?", (name,)).fetchone()
        return self._row_to_entry(row) if row else None

    def find_by_repo(self, repo_path: Path | str) -> list[KGEntry]:
        """Find all entries whose repo_path matches.

        :param repo_path: Absolute path to the repository root.
        :return: List of matching KGEntry objects.
        """
        p = str(Path(repo_path).resolve())
        rows = self._conn.execute("SELECT * FROM kg_entries WHERE repo_path = ?", (p,)).fetchall()
        return [self._row_to_entry(r) for r in rows]

    def list(self, kind: KGKind | str | None = None) -> list[KGEntry]:
        """List all registered KG entries, optionally filtered by kind.

        :param kind: Optional KGKind filter (code, doc, meta).
        :return: List of KGEntry objects ordered by name.
        """
        if kind is not None:
            k = kind.value if isinstance(kind, KGKind) else str(kind)
            rows = self._conn.execute(
                "SELECT * FROM kg_entries WHERE kind = ? ORDER BY name", (k,)
            ).fetchall()
        else:
            rows = self._conn.execute("SELECT * FROM kg_entries ORDER BY name").fetchall()
        return [self._row_to_entry(r) for r in rows]

    def iter(self, kind: KGKind | None = None) -> Iterator[KGEntry]:
        """Iterate over all entries (memory-efficient for large registries).

        :param kind: Optional KGKind filter.
        """
        yield from self.list(kind=kind)

    def stats(self) -> RegistryStats:
        """Compute summary statistics for the registry.

        :return: RegistryStats with total counts, per-kind breakdown, and build status.
        """
        entries = self.list()
        by_kind: dict[str, int] = {}
        built = 0
        for e in entries:
            by_kind[e.kind.value] = by_kind.get(e.kind.value, 0) + 1
            if e.is_built:
                built += 1
        return RegistryStats(
            total=len(entries),
            by_kind=by_kind,
            built=built,
            registry_path=self._db_path,
        )

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _row_to_entry(row: sqlite3.Row) -> KGEntry:
        return KGEntry(
            id=row["id"],
            name=row["name"],
            kind=KGKind(row["kind"]),
            repo_path=Path(row["repo_path"]),
            venv_path=Path(row["venv_path"]),
            sqlite_path=Path(row["sqlite_path"]) if row["sqlite_path"] else None,
            lancedb_path=Path(row["lancedb_path"]) if row["lancedb_path"] else None,
            version=row["version"],
            tags=json.loads(row["tags"]),
            created_at=datetime.fromisoformat(row["created_at"]),
            updated_at=datetime.fromisoformat(row["updated_at"]),
            metadata=json.loads(row["metadata"]),
        )
