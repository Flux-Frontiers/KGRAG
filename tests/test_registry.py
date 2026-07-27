"""
test_registry.py

Unit tests for kg_rag.registry — KGRegistry and default_registry_path.
All tests use isolated temp SQLite files (no ~/.kgrag pollution).
"""

from __future__ import annotations

from pathlib import Path

import pytest

from kg_rag.primitives import KGEntry, KGKind, RegistryStats
from kg_rag.registry import KGRegistry, default_registry_path

# ---------------------------------------------------------------------------
# default_registry_path
# ---------------------------------------------------------------------------


class TestDefaultRegistryPath:
    def test_default_points_to_home(self, monkeypatch):
        monkeypatch.delenv("KGRAG_REGISTRY", raising=False)
        p = default_registry_path()
        assert p.name == "registry.sqlite"
        assert ".kgrag" in str(p)

    def test_env_override(self, monkeypatch, tmp_path):
        custom = str(tmp_path / "custom.sqlite")
        monkeypatch.setenv("KGRAG_REGISTRY", custom)
        assert default_registry_path() == Path(custom).resolve()


# ---------------------------------------------------------------------------
# KGRegistry — construction & schema
# ---------------------------------------------------------------------------


class TestKGRegistryInit:
    def test_creates_db_file(self, tmp_path):
        db = tmp_path / "reg.sqlite"
        with KGRegistry(db_path=db) as reg:
            assert db.exists()
            assert reg.db_path == db

    def test_creates_parent_dirs(self, tmp_path):
        db = tmp_path / "nested" / "deep" / "reg.sqlite"
        with KGRegistry(db_path=db):
            assert db.exists()

    def test_idempotent_schema(self, tmp_path):
        db = tmp_path / "reg.sqlite"
        # Opening twice should not raise
        with KGRegistry(db_path=db):
            pass
        with KGRegistry(db_path=db):
            pass


# ---------------------------------------------------------------------------
# register / get / find_by_name
# ---------------------------------------------------------------------------


class TestKGRegistryRegister:
    def test_register_and_get_by_name(self, tmp_registry, sample_entry):
        tmp_registry.register(sample_entry)
        fetched = tmp_registry.get(sample_entry.name)
        assert fetched is not None
        assert fetched.name == sample_entry.name
        assert fetched.kind == KGKind.CODE

    def test_register_and_get_by_id(self, tmp_registry, sample_entry):
        tmp_registry.register(sample_entry)
        fetched = tmp_registry.get(sample_entry.id)
        assert fetched is not None
        assert fetched.id == sample_entry.id

    def test_register_upsert_same_name(self, tmp_registry, tmp_path):
        """Re-registering by name should update in-place, preserving original id."""
        repo = tmp_path / "repo"
        repo.mkdir()
        venv = repo / ".venv"
        venv.mkdir()
        e1 = KGEntry(name="kg", kind=KGKind.CODE, repo_path=repo, venv_path=venv, version="1.0")
        tmp_registry.register(e1)

        e2 = KGEntry(name="kg", kind=KGKind.CODE, repo_path=repo, venv_path=venv, version="2.0")
        result = tmp_registry.register(e2)

        assert result.version == "2.0"
        assert result.id == e1.id  # id preserved from original
        assert len(tmp_registry.list()) == 1

    def test_get_missing_returns_none(self, tmp_registry):
        assert tmp_registry.get("nonexistent") is None

    def test_find_by_name(self, tmp_registry, sample_entry):
        tmp_registry.register(sample_entry)
        found = tmp_registry.find_by_name(sample_entry.name)
        assert found is not None
        assert found.name == sample_entry.name

    def test_find_by_name_missing(self, tmp_registry):
        assert tmp_registry.find_by_name("ghost") is None

    def test_register_with_optional_paths(self, tmp_path, tmp_registry):
        repo = tmp_path / "repo"
        repo.mkdir()
        venv = repo / ".venv"
        venv.mkdir()
        sqlite = tmp_path / "graph.sqlite"
        sqlite.touch()
        lancedb = tmp_path / "lancedb"
        lancedb.mkdir()

        entry = KGEntry(
            name="full-entry",
            kind=KGKind.DOC,
            repo_path=repo,
            venv_path=venv,
            sqlite_path=sqlite,
            lancedb_path=lancedb,
            version="1.2.3",
            tags=["a", "b"],
            metadata={"key": "val"},
        )
        tmp_registry.register(entry)
        fetched = tmp_registry.get("full-entry")
        assert fetched.sqlite_path is not None
        assert fetched.lancedb_path is not None
        assert fetched.tags == ["a", "b"]
        assert fetched.metadata == {"key": "val"}
        assert fetched.version == "1.2.3"

    def test_vectors_path_round_trips(self, tmp_path, tmp_registry):
        """A sqlite-vec store path must survive a register/get round trip."""
        repo = tmp_path / "repo"
        repo.mkdir()
        vectors = tmp_path / ".pycodekg" / "vectors.sqlite"
        vectors.parent.mkdir()
        vectors.touch()

        tmp_registry.register(
            KGEntry(
                name="vec-entry",
                kind=KGKind.CODE,
                repo_path=repo,
                venv_path=repo / ".venv",
                vectors_path=vectors,
            )
        )
        fetched = tmp_registry.get("vec-entry")
        assert fetched.vectors_path == vectors.resolve()
        assert fetched.lancedb_path is None
        assert fetched.is_built is True

    def test_vectors_path_survives_name_collision_replace(self, tmp_path, tmp_registry):
        """register() rebuilds the entry on a name collision — vectors_path must
        not be dropped by that rebuild."""
        repo = tmp_path / "repo"
        repo.mkdir()
        vectors = tmp_path / "vectors.sqlite"
        vectors.touch()

        tmp_registry.register(
            KGEntry(name="dup", kind=KGKind.CODE, repo_path=repo, venv_path=repo / ".venv")
        )
        tmp_registry.register(
            KGEntry(
                name="dup",
                kind=KGKind.CODE,
                repo_path=repo,
                venv_path=repo / ".venv",
                vectors_path=vectors,
            )
        )
        assert tmp_registry.get("dup").vectors_path == vectors.resolve()

    def test_update_vectors_path(self, tmp_path, tmp_registry):
        repo = tmp_path / "repo"
        repo.mkdir()
        vectors = tmp_path / "vectors.sqlite"
        vectors.touch()
        tmp_registry.register(
            KGEntry(name="upd", kind=KGKind.CODE, repo_path=repo, venv_path=repo / ".venv")
        )
        tmp_registry.update("upd", vectors_path=vectors)
        assert tmp_registry.get("upd").vectors_path == vectors.resolve()


# ---------------------------------------------------------------------------
# schema migration
# ---------------------------------------------------------------------------


class TestVectorsPathMigration:
    """A registry created before the vectors_path column must migrate in place."""

    _LEGACY_SCHEMA = """
    CREATE TABLE kg_entries (
        id          TEXT PRIMARY KEY,
        name        TEXT NOT NULL UNIQUE,
        kind        TEXT NOT NULL,
        repo_path   TEXT NOT NULL,
        venv_path   TEXT NOT NULL,
        sqlite_path TEXT,
        lancedb_path TEXT,
        version     TEXT NOT NULL DEFAULT 'unknown',
        builder_version TEXT NOT NULL DEFAULT 'unknown',
        tags        TEXT NOT NULL DEFAULT '[]',
        metadata    TEXT NOT NULL DEFAULT '{}',
        created_at  TEXT NOT NULL,
        updated_at  TEXT NOT NULL
    );
    """

    def _legacy_db(self, tmp_path: Path) -> Path:
        """Write a pre-migration registry holding one row."""
        import sqlite3
        from datetime import UTC, datetime

        db = tmp_path / "legacy.sqlite"
        conn = sqlite3.connect(str(db))
        conn.executescript(self._LEGACY_SCHEMA)
        now = datetime.now(UTC).isoformat()
        conn.execute(
            "INSERT INTO kg_entries (id, name, kind, repo_path, venv_path, sqlite_path,"
            " lancedb_path, version, builder_version, tags, metadata, created_at, updated_at)"
            " VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)",
            (
                "legacy-id",
                "legacy-kg",
                "code",
                str(tmp_path),
                str(tmp_path / ".venv"),
                str(tmp_path / "graph.sqlite"),
                str(tmp_path / "lancedb"),
                "1.0",
                "0.19.0",
                "[]",
                "{}",
                now,
                now,
            ),
        )
        conn.commit()
        conn.close()
        return db

    def test_column_added_to_legacy_db(self, tmp_path):
        db = self._legacy_db(tmp_path)
        with KGRegistry(db_path=db) as reg:
            cols = {
                r["name"] for r in reg._conn.execute("PRAGMA table_info(kg_entries)").fetchall()
            }
            assert "vectors_path" in cols

    def test_legacy_row_readable_with_null_vectors(self, tmp_path):
        db = self._legacy_db(tmp_path)
        with KGRegistry(db_path=db) as reg:
            entry = reg.get("legacy-kg")
            assert entry is not None
            assert entry.vectors_path is None
            assert entry.lancedb_path is not None

    def test_legacy_row_can_be_updated_with_vectors(self, tmp_path):
        db = self._legacy_db(tmp_path)
        vectors = tmp_path / "vectors.sqlite"
        vectors.touch()
        with KGRegistry(db_path=db) as reg:
            reg.update("legacy-kg", vectors_path=vectors)
            assert reg.get("legacy-kg").vectors_path == vectors.resolve()

    def test_migration_is_idempotent(self, tmp_path):
        db = self._legacy_db(tmp_path)
        with KGRegistry(db_path=db):
            pass
        with KGRegistry(db_path=db) as reg:  # second open must not re-ALTER
            assert reg.get("legacy-kg") is not None


# ---------------------------------------------------------------------------
# unregister
# ---------------------------------------------------------------------------


class TestKGRegistryUnregister:
    def test_unregister_by_name(self, tmp_registry, sample_entry):
        tmp_registry.register(sample_entry)
        removed = tmp_registry.unregister(sample_entry.name)
        assert removed is True
        assert tmp_registry.get(sample_entry.name) is None

    def test_unregister_by_id(self, tmp_registry, sample_entry):
        tmp_registry.register(sample_entry)
        removed = tmp_registry.unregister(sample_entry.id)
        assert removed is True
        assert tmp_registry.get(sample_entry.id) is None

    def test_unregister_not_found(self, tmp_registry):
        assert tmp_registry.unregister("no-such-entry") is False


# ---------------------------------------------------------------------------
# update
# ---------------------------------------------------------------------------


class TestKGRegistryUpdate:
    def test_update_version(self, tmp_registry, sample_entry):
        tmp_registry.register(sample_entry)
        updated = tmp_registry.update(sample_entry.name, version="9.9.9")
        assert updated is not None
        assert updated.version == "9.9.9"

    def test_update_tags(self, tmp_registry, sample_entry):
        tmp_registry.register(sample_entry)
        tmp_registry.update(sample_entry.name, tags=["x", "y"])
        fetched = tmp_registry.get(sample_entry.name)
        assert fetched.tags == ["x", "y"]

    def test_update_missing_returns_none(self, tmp_registry):
        assert tmp_registry.update("ghost", version="1.0") is None


# ---------------------------------------------------------------------------
# list / iter / find_by_repo
# ---------------------------------------------------------------------------


class TestKGRegistryList:
    def _add_entries(self, reg, tmp_path):
        repo = tmp_path / "repo"
        repo.mkdir(exist_ok=True)
        venv = repo / ".venv"
        venv.mkdir(exist_ok=True)
        for name, kind in [("c1", KGKind.CODE), ("c2", KGKind.CODE), ("d1", KGKind.DOC)]:
            reg.register(KGEntry(name=name, kind=kind, repo_path=repo, venv_path=venv))

    def test_list_all(self, tmp_registry, tmp_path):
        self._add_entries(tmp_registry, tmp_path)
        entries = tmp_registry.list()
        assert len(entries) == 3

    def test_list_filtered_by_kind(self, tmp_registry, tmp_path):
        self._add_entries(tmp_registry, tmp_path)
        code = tmp_registry.list(kind=KGKind.CODE)
        assert len(code) == 2
        assert all(e.kind == KGKind.CODE for e in code)

    def test_list_filtered_by_kind_string(self, tmp_registry, tmp_path):
        self._add_entries(tmp_registry, tmp_path)
        docs = tmp_registry.list(kind="doc")
        assert len(docs) == 1

    def test_list_empty(self, tmp_registry):
        assert tmp_registry.list() == []

    def test_iter(self, tmp_registry, tmp_path):
        self._add_entries(tmp_registry, tmp_path)
        results = list(tmp_registry.iter())
        assert len(results) == 3

    def test_iter_filtered(self, tmp_registry, tmp_path):
        self._add_entries(tmp_registry, tmp_path)
        docs = list(tmp_registry.iter(kind=KGKind.DOC))
        assert len(docs) == 1

    def test_find_by_repo(self, tmp_registry, tmp_path):
        repo = tmp_path / "shared_repo"
        repo.mkdir()
        venv = repo / ".venv"
        venv.mkdir()
        for name, kind in [("a", KGKind.CODE), ("b", KGKind.DOC)]:
            tmp_registry.register(KGEntry(name=name, kind=kind, repo_path=repo, venv_path=venv))
        results = tmp_registry.find_by_repo(repo)
        assert len(results) == 2

    def test_find_by_repo_no_match(self, tmp_registry, tmp_path):
        assert tmp_registry.find_by_repo(tmp_path / "nowhere") == []


# ---------------------------------------------------------------------------
# stats
# ---------------------------------------------------------------------------


class TestKGRegistryStats:
    def test_empty_registry(self, tmp_registry):
        s = tmp_registry.stats()
        assert isinstance(s, RegistryStats)
        assert s.total == 0
        assert s.built == 0
        assert s.by_kind == {}

    def test_stats_counts(self, tmp_path, tmp_registry):
        repo = tmp_path / "r"
        repo.mkdir()
        venv = repo / ".venv"
        venv.mkdir()
        for name, kind in [("a", KGKind.CODE), ("b", KGKind.CODE), ("c", KGKind.DOC)]:
            tmp_registry.register(KGEntry(name=name, kind=kind, repo_path=repo, venv_path=venv))
        s = tmp_registry.stats()
        assert s.total == 3
        assert s.by_kind["code"] == 2
        assert s.by_kind["doc"] == 1

    def test_stats_built_count(self, tmp_path, tmp_registry, built_entry):
        # built_entry has sqlite_path that exists → is_built = True
        tmp_registry.register(built_entry)

        unbuilt_repo = tmp_path / "unbuilt"
        unbuilt_repo.mkdir()
        venv = unbuilt_repo / ".venv"
        venv.mkdir()
        unbuilt = KGEntry(name="unbuilt", kind=KGKind.CODE, repo_path=unbuilt_repo, venv_path=venv)
        tmp_registry.register(unbuilt)

        s = tmp_registry.stats()
        assert s.built == 1
        assert s.total == 2

    def test_stats_registry_path(self, tmp_path, tmp_registry):
        s = tmp_registry.stats()
        assert s.registry_path == tmp_registry.db_path


# ---------------------------------------------------------------------------
# Context manager
# ---------------------------------------------------------------------------


class TestKGRegistryContextManager:
    def test_context_manager(self, tmp_path):
        db = tmp_path / "reg.sqlite"
        with KGRegistry(db_path=db) as reg:
            assert reg.db_path == db
        # Connection is closed — further operations should fail
        with pytest.raises(Exception):
            reg.list()
