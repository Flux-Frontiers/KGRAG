"""
test_person_registry.py

Unit tests for PersonCorpusRegistry and the PersonCorpusEntry primitives.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from kg_rag.person_registry import PersonCorpusRegistry
from kg_rag.primitives import KGEntry, KGKind, PersonCorpusEntry
from kg_rag.registry import KGRegistry

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def db_path(tmp_path: Path) -> Path:
    return tmp_path / "test_registry.sqlite"


@pytest.fixture
def person_reg(db_path: Path) -> PersonCorpusRegistry:
    reg = PersonCorpusRegistry(db_path=db_path)
    yield reg
    reg.close()


@pytest.fixture
def kg_reg(db_path: Path) -> KGRegistry:
    """Share the same SQLite file so both registries can coexist."""
    reg = KGRegistry(db_path=db_path)
    yield reg
    reg.close()


@pytest.fixture
def two_kg_entries(tmp_path: Path, kg_reg: KGRegistry) -> tuple[KGEntry, KGEntry]:
    """Register two KGEntries and return them."""
    repo_a = tmp_path / "repo_a"
    repo_a.mkdir()
    repo_b = tmp_path / "repo_b"
    repo_b.mkdir()

    entry_a = KGEntry(name="code-a", kind=KGKind.CODE, repo_path=repo_a, venv_path=repo_a / ".venv")
    entry_b = KGEntry(name="doc-b", kind=KGKind.DOC, repo_path=repo_b, venv_path=repo_b / ".venv")
    kg_reg.register(entry_a)
    kg_reg.register(entry_b)
    return entry_a, entry_b


# ---------------------------------------------------------------------------
# Construction
# ---------------------------------------------------------------------------


class TestPersonCorpusRegistryInit:
    def test_creates_db_file(self, tmp_path):
        db = tmp_path / "reg.sqlite"
        with PersonCorpusRegistry(db_path=db) as reg:
            assert db.exists()
            assert reg.db_path == db

    def test_creates_parent_dirs(self, tmp_path):
        db = tmp_path / "nested" / "deep" / "reg.sqlite"
        with PersonCorpusRegistry(db_path=db):
            assert db.exists()


# ---------------------------------------------------------------------------
# create
# ---------------------------------------------------------------------------


class TestPersonCorpusRegistryCreate:
    def test_create_minimal_person(self, person_reg: PersonCorpusRegistry):
        entry = PersonCorpusEntry(name="Jane Doe")
        saved = person_reg.create(entry)
        assert saved.name == "Jane Doe"
        assert saved.kg_ids == []

    def test_create_with_metadata(self, person_reg: PersonCorpusRegistry):
        entry = PersonCorpusEntry(
            name="John Smith",
            kg_ids=["id-1", "id-2"],
            birth_year=1980,
            birth_date="1980-05-14",
            address="123 Main St",
            email="john@example.com",
            phone="555-1234",
            notes="A test person",
            tags=["family", "friend"],
            metadata={"key": "val"},
        )
        saved = person_reg.create(entry)
        assert saved.kg_ids == ["id-1", "id-2"]
        assert saved.birth_year == 1980
        assert saved.birth_date == "1980-05-14"
        assert saved.address == "123 Main St"
        assert saved.email == "john@example.com"
        assert saved.phone == "555-1234"
        assert saved.notes == "A test person"
        assert saved.tags == ["family", "friend"]
        assert saved.metadata == {"key": "val"}

    def test_create_replaces_by_name(self, person_reg: PersonCorpusRegistry):
        e1 = PersonCorpusEntry(name="Jane Doe", kg_ids=["old-id"])
        saved1 = person_reg.create(e1)

        e2 = PersonCorpusEntry(name="Jane Doe", kg_ids=["new-id"])
        saved2 = person_reg.create(e2)

        # id and created_at are preserved from the original entry
        assert saved2.id == saved1.id
        assert saved2.created_at == saved1.created_at
        assert saved2.kg_ids == ["new-id"]
        assert len(person_reg.list()) == 1


# ---------------------------------------------------------------------------
# get / find_by_name
# ---------------------------------------------------------------------------


class TestPersonCorpusRegistryGet:
    def test_get_by_name(self, person_reg: PersonCorpusRegistry):
        person_reg.create(PersonCorpusEntry(name="alpha"))
        result = person_reg.get("alpha")
        assert result is not None
        assert result.name == "alpha"

    def test_get_by_id(self, person_reg: PersonCorpusRegistry):
        entry = PersonCorpusEntry(name="beta")
        saved = person_reg.create(entry)
        result = person_reg.get(saved.id)
        assert result is not None
        assert result.name == "beta"

    def test_get_missing_returns_none(self, person_reg: PersonCorpusRegistry):
        assert person_reg.get("no-such-person") is None

    def test_find_by_name(self, person_reg: PersonCorpusRegistry):
        person_reg.create(PersonCorpusEntry(name="gamma"))
        assert person_reg.find_by_name("gamma") is not None
        assert person_reg.find_by_name("delta") is None


# ---------------------------------------------------------------------------
# delete
# ---------------------------------------------------------------------------


class TestPersonCorpusRegistryDelete:
    def test_delete_by_name(self, person_reg: PersonCorpusRegistry):
        person_reg.create(PersonCorpusEntry(name="to-delete"))
        assert person_reg.delete("to-delete") is True
        assert person_reg.get("to-delete") is None

    def test_delete_by_id(self, person_reg: PersonCorpusRegistry):
        entry = PersonCorpusEntry(name="by-id")
        saved = person_reg.create(entry)
        assert person_reg.delete(saved.id) is True

    def test_delete_missing_returns_false(self, person_reg: PersonCorpusRegistry):
        assert person_reg.delete("phantom") is False


# ---------------------------------------------------------------------------
# add_kg / remove_kg
# ---------------------------------------------------------------------------


class TestPersonCorpusRegistryAddRemoveKG:
    def test_add_kg(self, person_reg: PersonCorpusRegistry):
        person_reg.create(PersonCorpusEntry(name="p"))
        updated = person_reg.add_kg("p", "kg-uuid-1")
        assert "kg-uuid-1" in updated.kg_ids

    def test_add_kg_idempotent(self, person_reg: PersonCorpusRegistry):
        person_reg.create(PersonCorpusEntry(name="p"))
        person_reg.add_kg("p", "kg-1")
        updated = person_reg.add_kg("p", "kg-1")  # add again
        assert updated.kg_ids.count("kg-1") == 1  # no duplicates

    def test_add_kg_missing_person(self, person_reg: PersonCorpusRegistry):
        result = person_reg.add_kg("no-such", "kg-1")
        assert result is None

    def test_remove_kg(self, person_reg: PersonCorpusRegistry):
        person_reg.create(PersonCorpusEntry(name="p", kg_ids=["kg-1", "kg-2"]))
        updated = person_reg.remove_kg("p", "kg-1")
        assert "kg-1" not in updated.kg_ids
        assert "kg-2" in updated.kg_ids

    def test_remove_kg_not_in_person(self, person_reg: PersonCorpusRegistry):
        person_reg.create(PersonCorpusEntry(name="p", kg_ids=["kg-1"]))
        updated = person_reg.remove_kg("p", "kg-999")
        assert updated.kg_ids == ["kg-1"]  # unchanged

    def test_remove_kg_missing_person(self, person_reg: PersonCorpusRegistry):
        result = person_reg.remove_kg("no-such", "kg-1")
        assert result is None


# ---------------------------------------------------------------------------
# update
# ---------------------------------------------------------------------------


class TestPersonCorpusRegistryUpdate:
    def test_update_notes(self, person_reg: PersonCorpusRegistry):
        person_reg.create(PersonCorpusEntry(name="p", notes="old"))
        updated = person_reg.update("p", notes="new")
        assert updated.notes == "new"

    def test_update_tags(self, person_reg: PersonCorpusRegistry):
        person_reg.create(PersonCorpusEntry(name="p", tags=["a"]))
        updated = person_reg.update("p", tags=["b", "c"])
        assert updated.tags == ["b", "c"]

    def test_update_multiple_fields(self, person_reg: PersonCorpusRegistry):
        person_reg.create(PersonCorpusEntry(name="p"))
        updated = person_reg.update("p", birth_year=1990, email="p@example.com")
        assert updated.birth_year == 1990
        assert updated.email == "p@example.com"

    def test_update_ignores_unknown_field(self, person_reg: PersonCorpusRegistry):
        person_reg.create(PersonCorpusEntry(name="p"))
        # hasattr() guard means unknown kwargs are silently ignored, not raised
        updated = person_reg.update("p", not_a_real_field="x")
        assert not hasattr(updated, "not_a_real_field")

    def test_update_missing_returns_none(self, person_reg: PersonCorpusRegistry):
        assert person_reg.update("ghost", notes="x") is None


# ---------------------------------------------------------------------------
# list / iter
# ---------------------------------------------------------------------------


class TestPersonCorpusRegistryList:
    def test_list_empty(self, person_reg: PersonCorpusRegistry):
        assert person_reg.list() == []

    def test_list_ordered_by_name(self, person_reg: PersonCorpusRegistry):
        person_reg.create(PersonCorpusEntry(name="zebra"))
        person_reg.create(PersonCorpusEntry(name="apple"))
        person_reg.create(PersonCorpusEntry(name="mango"))
        names = [e.name for e in person_reg.list()]
        assert names == ["apple", "mango", "zebra"]

    def test_iter(self, person_reg: PersonCorpusRegistry):
        person_reg.create(PersonCorpusEntry(name="p1"))
        person_reg.create(PersonCorpusEntry(name="p2"))
        names = [e.name for e in person_reg.iter()]
        assert "p1" in names
        assert "p2" in names


# ---------------------------------------------------------------------------
# stats
# ---------------------------------------------------------------------------


class TestPersonCorpusRegistryStats:
    def test_stats_empty(self, person_reg: PersonCorpusRegistry):
        stats = person_reg.stats()
        assert stats.total == 0
        assert stats.total_kg_refs == 0

    def test_stats_counts(self, person_reg: PersonCorpusRegistry):
        person_reg.create(PersonCorpusEntry(name="p1", kg_ids=["a", "b"]))
        person_reg.create(PersonCorpusEntry(name="p2", kg_ids=["c"]))
        stats = person_reg.stats()
        assert stats.total == 2
        assert stats.total_kg_refs == 3

    def test_stats_registry_path(self, person_reg: PersonCorpusRegistry):
        stats = person_reg.stats()
        assert stats.registry_path == person_reg.db_path


# ---------------------------------------------------------------------------
# Resolve KG entries
# ---------------------------------------------------------------------------


class TestResolveKGEntries:
    def test_resolve_returns_entries(
        self, person_reg: PersonCorpusRegistry, kg_reg: KGRegistry, two_kg_entries
    ):
        entry_a, entry_b = two_kg_entries
        person_reg.create(PersonCorpusEntry(name="p", kg_ids=[entry_a.id, entry_b.id]))
        resolved = person_reg.resolve_kg_entries("p", kg_reg)
        names = {e.name for e in resolved}
        assert names == {"code-a", "doc-b"}

    def test_resolve_skips_missing(
        self, person_reg: PersonCorpusRegistry, kg_reg: KGRegistry, two_kg_entries
    ):
        entry_a, _ = two_kg_entries
        person_reg.create(PersonCorpusEntry(name="p", kg_ids=[entry_a.id, "nonexistent-uuid"]))
        resolved = person_reg.resolve_kg_entries("p", kg_reg)
        assert len(resolved) == 1
        assert resolved[0].name == "code-a"

    def test_resolve_missing_person(self, person_reg: PersonCorpusRegistry, kg_reg: KGRegistry):
        resolved = person_reg.resolve_kg_entries("no-such-person", kg_reg)
        assert resolved == []


# ---------------------------------------------------------------------------
# Context manager usage
# ---------------------------------------------------------------------------


class TestContextManager:
    def test_context_manager(self, db_path: Path):
        with PersonCorpusRegistry(db_path=db_path) as reg:
            reg.create(PersonCorpusEntry(name="ctx-test"))
            assert reg.get("ctx-test") is not None

    def test_close_prevents_further_use(self, tmp_path):
        db = tmp_path / "reg.sqlite"
        reg = PersonCorpusRegistry(db_path=db)
        reg.close()
        with pytest.raises(Exception):
            reg.list()


# ---------------------------------------------------------------------------
# Persistence across connections
# ---------------------------------------------------------------------------


class TestPersistence:
    def test_data_survives_reconnect(self, db_path: Path):
        with PersonCorpusRegistry(db_path=db_path) as reg:
            reg.create(PersonCorpusEntry(name="persistent", kg_ids=["x", "y"]))

        with PersonCorpusRegistry(db_path=db_path) as reg2:
            entry = reg2.get("persistent")
            assert entry is not None
            assert entry.kg_ids == ["x", "y"]
