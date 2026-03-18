"""
test_corpus_registry.py

Unit tests for CorpusRegistry and the CorpusEntry primitives.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from kg_rag.corpus_registry import CorpusRegistry
from kg_rag.primitives import CorpusEntry, KGEntry, KGKind
from kg_rag.registry import KGRegistry

# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def db_path(tmp_path: Path) -> Path:
    return tmp_path / "test_registry.sqlite"


@pytest.fixture
def corp_reg(db_path: Path) -> CorpusRegistry:
    reg = CorpusRegistry(db_path=db_path)
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
# CorpusEntry primitive tests
# ---------------------------------------------------------------------------


class TestCorpusEntryPrimitive:
    def test_default_fields(self):
        e = CorpusEntry(name="my-corpus")
        assert e.name == "my-corpus"
        assert e.kg_ids == []
        assert e.description == ""
        assert e.tags == []
        assert e.metadata == {}
        assert len(e.id) == 36  # UUID format

    def test_size_property(self):
        e = CorpusEntry(name="c", kg_ids=["a", "b", "c"])
        assert e.size == 3

    def test_size_empty(self):
        e = CorpusEntry(name="empty")
        assert e.size == 0


# ---------------------------------------------------------------------------
# CorpusRegistry CRUD
# ---------------------------------------------------------------------------


class TestCorpusRegistryCreate:
    def test_create_empty_corpus(self, corp_reg: CorpusRegistry):
        entry = CorpusEntry(name="empty-corpus")
        saved = corp_reg.create(entry)
        assert saved.name == "empty-corpus"
        assert saved.kg_ids == []

    def test_create_with_kg_ids(self, corp_reg: CorpusRegistry):
        entry = CorpusEntry(name="rich-corpus", kg_ids=["id-1", "id-2"], description="A test")
        saved = corp_reg.create(entry)
        assert saved.kg_ids == ["id-1", "id-2"]
        assert saved.description == "A test"

    def test_create_replaces_by_name(self, corp_reg: CorpusRegistry):
        e1 = CorpusEntry(name="my-corpus", kg_ids=["old-id"])
        saved1 = corp_reg.create(e1)

        e2 = CorpusEntry(name="my-corpus", kg_ids=["new-id"])
        saved2 = corp_reg.create(e2)

        # ID is preserved from original
        assert saved2.id == saved1.id
        assert saved2.kg_ids == ["new-id"]

    def test_create_with_tags(self, corp_reg: CorpusRegistry):
        entry = CorpusEntry(name="tagged", tags=["research", "2025"])
        corp_reg.create(entry)
        fetched = corp_reg.get("tagged")
        assert fetched.tags == ["research", "2025"]


class TestCorpusRegistryGet:
    def test_get_by_name(self, corp_reg: CorpusRegistry):
        corp_reg.create(CorpusEntry(name="alpha"))
        result = corp_reg.get("alpha")
        assert result is not None
        assert result.name == "alpha"

    def test_get_by_id(self, corp_reg: CorpusRegistry):
        entry = CorpusEntry(name="beta")
        saved = corp_reg.create(entry)
        result = corp_reg.get(saved.id)
        assert result is not None
        assert result.name == "beta"

    def test_get_missing_returns_none(self, corp_reg: CorpusRegistry):
        assert corp_reg.get("no-such-corpus") is None

    def test_find_by_name(self, corp_reg: CorpusRegistry):
        corp_reg.create(CorpusEntry(name="gamma"))
        assert corp_reg.find_by_name("gamma") is not None
        assert corp_reg.find_by_name("delta") is None


class TestCorpusRegistryDelete:
    def test_delete_by_name(self, corp_reg: CorpusRegistry):
        corp_reg.create(CorpusEntry(name="to-delete"))
        assert corp_reg.delete("to-delete") is True
        assert corp_reg.get("to-delete") is None

    def test_delete_by_id(self, corp_reg: CorpusRegistry):
        entry = CorpusEntry(name="by-id")
        saved = corp_reg.create(entry)
        assert corp_reg.delete(saved.id) is True

    def test_delete_missing_returns_false(self, corp_reg: CorpusRegistry):
        assert corp_reg.delete("phantom") is False


class TestCorpusRegistryAddRemoveKG:
    def test_add_kg(self, corp_reg: CorpusRegistry):
        corp_reg.create(CorpusEntry(name="c"))
        updated = corp_reg.add_kg("c", "kg-uuid-1")
        assert "kg-uuid-1" in updated.kg_ids

    def test_add_kg_idempotent(self, corp_reg: CorpusRegistry):
        corp_reg.create(CorpusEntry(name="c"))
        corp_reg.add_kg("c", "kg-1")
        updated = corp_reg.add_kg("c", "kg-1")  # add again
        assert updated.kg_ids.count("kg-1") == 1  # no duplicates

    def test_add_kg_missing_corpus(self, corp_reg: CorpusRegistry):
        result = corp_reg.add_kg("no-such", "kg-1")
        assert result is None

    def test_remove_kg(self, corp_reg: CorpusRegistry):
        corp_reg.create(CorpusEntry(name="c", kg_ids=["kg-1", "kg-2"]))
        updated = corp_reg.remove_kg("c", "kg-1")
        assert "kg-1" not in updated.kg_ids
        assert "kg-2" in updated.kg_ids

    def test_remove_kg_not_in_corpus(self, corp_reg: CorpusRegistry):
        corp_reg.create(CorpusEntry(name="c", kg_ids=["kg-1"]))
        updated = corp_reg.remove_kg("c", "kg-999")
        assert updated.kg_ids == ["kg-1"]  # unchanged

    def test_remove_kg_missing_corpus(self, corp_reg: CorpusRegistry):
        result = corp_reg.remove_kg("no-such", "kg-1")
        assert result is None


class TestCorpusRegistryUpdate:
    def test_update_description(self, corp_reg: CorpusRegistry):
        corp_reg.create(CorpusEntry(name="c", description="old"))
        updated = corp_reg.update("c", description="new")
        assert updated.description == "new"

    def test_update_tags(self, corp_reg: CorpusRegistry):
        corp_reg.create(CorpusEntry(name="c", tags=["a"]))
        updated = corp_reg.update("c", tags=["b", "c"])
        assert updated.tags == ["b", "c"]

    def test_update_missing_returns_none(self, corp_reg: CorpusRegistry):
        result = corp_reg.update("ghost", description="x")
        assert result is None


class TestCorpusRegistryList:
    def test_list_empty(self, corp_reg: CorpusRegistry):
        assert corp_reg.list() == []

    def test_list_ordered_by_name(self, corp_reg: CorpusRegistry):
        corp_reg.create(CorpusEntry(name="zebra"))
        corp_reg.create(CorpusEntry(name="apple"))
        corp_reg.create(CorpusEntry(name="mango"))
        names = [e.name for e in corp_reg.list()]
        assert names == ["apple", "mango", "zebra"]

    def test_iter(self, corp_reg: CorpusRegistry):
        corp_reg.create(CorpusEntry(name="c1"))
        corp_reg.create(CorpusEntry(name="c2"))
        names = [e.name for e in corp_reg.iter()]
        assert "c1" in names
        assert "c2" in names


class TestCorpusRegistryStats:
    def test_stats_empty(self, corp_reg: CorpusRegistry):
        stats = corp_reg.stats()
        assert stats.total == 0
        assert stats.total_kg_refs == 0

    def test_stats_counts(self, corp_reg: CorpusRegistry):
        corp_reg.create(CorpusEntry(name="c1", kg_ids=["a", "b"]))
        corp_reg.create(CorpusEntry(name="c2", kg_ids=["c"]))
        stats = corp_reg.stats()
        assert stats.total == 2
        assert stats.total_kg_refs == 3


# ---------------------------------------------------------------------------
# Resolve KG entries
# ---------------------------------------------------------------------------


class TestResolveKGEntries:
    def test_resolve_returns_entries(
        self, corp_reg: CorpusRegistry, kg_reg: KGRegistry, two_kg_entries
    ):
        entry_a, entry_b = two_kg_entries
        corp_reg.create(CorpusEntry(name="c", kg_ids=[entry_a.id, entry_b.id]))
        resolved = corp_reg.resolve_kg_entries("c", kg_reg)
        names = {e.name for e in resolved}
        assert names == {"code-a", "doc-b"}

    def test_resolve_skips_missing(
        self, corp_reg: CorpusRegistry, kg_reg: KGRegistry, two_kg_entries
    ):
        entry_a, _ = two_kg_entries
        corp_reg.create(CorpusEntry(name="c", kg_ids=[entry_a.id, "nonexistent-uuid"]))
        resolved = corp_reg.resolve_kg_entries("c", kg_reg)
        assert len(resolved) == 1
        assert resolved[0].name == "code-a"

    def test_resolve_missing_corpus(self, corp_reg: CorpusRegistry, kg_reg: KGRegistry):
        resolved = corp_reg.resolve_kg_entries("no-such-corpus", kg_reg)
        assert resolved == []


# ---------------------------------------------------------------------------
# Context manager usage
# ---------------------------------------------------------------------------


class TestContextManager:
    def test_context_manager(self, db_path: Path):
        with CorpusRegistry(db_path=db_path) as reg:
            reg.create(CorpusEntry(name="ctx-test"))
            assert reg.get("ctx-test") is not None


# ---------------------------------------------------------------------------
# Persistence across connections
# ---------------------------------------------------------------------------


class TestPersistence:
    def test_data_survives_reconnect(self, db_path: Path):
        with CorpusRegistry(db_path=db_path) as reg:
            reg.create(CorpusEntry(name="persistent", kg_ids=["x", "y"]))

        with CorpusRegistry(db_path=db_path) as reg2:
            entry = reg2.get("persistent")
            assert entry is not None
            assert entry.kg_ids == ["x", "y"]
