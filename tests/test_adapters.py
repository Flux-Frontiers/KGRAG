"""
test_adapters.py

Unit tests for kg_rag.adapters — make_adapter factory and
is_available / query / pack / stats on each adapter type.
External KG libraries (code_kg, doc_kg, metakg) are mocked so these
tests run without any heavyweight dependencies installed.
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

from kg_rag.adapters import make_adapter
from kg_rag.adapters.codekg_adapter import CodeKGAdapter
from kg_rag.adapters.dockg_adapter import DocKGAdapter
from kg_rag.adapters.metakg_adapter import MetaKGAdapter
from kg_rag.primitives import CrossHit, CrossSnippet, KGEntry, KGKind

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _entry(tmp_path, kind: KGKind, *, with_sqlite: bool = False) -> KGEntry:
    repo = tmp_path / "repo"
    repo.mkdir(exist_ok=True)
    venv = repo / ".venv"
    venv.mkdir(exist_ok=True)
    sqlite_path = None
    if with_sqlite:
        db = repo / "graph.sqlite"
        db.touch()
        sqlite_path = db
    return KGEntry(
        name="test-kg",
        kind=kind,
        repo_path=repo,
        venv_path=venv,
        sqlite_path=sqlite_path,
    )


# ---------------------------------------------------------------------------
# make_adapter factory
# ---------------------------------------------------------------------------


class TestMakeAdapter:
    def test_code_kind_returns_codekg_adapter(self, tmp_path):
        entry = _entry(tmp_path, KGKind.CODE)
        adapter = make_adapter(entry)
        assert isinstance(adapter, CodeKGAdapter)

    def test_doc_kind_returns_dockg_adapter(self, tmp_path):
        entry = _entry(tmp_path, KGKind.DOC)
        adapter = make_adapter(entry)
        assert isinstance(adapter, DocKGAdapter)

    def test_meta_kind_returns_metakg_adapter(self, tmp_path):
        entry = _entry(tmp_path, KGKind.META)
        adapter = make_adapter(entry)
        assert isinstance(adapter, MetaKGAdapter)

    def test_entry_is_stored(self, tmp_path):
        entry = _entry(tmp_path, KGKind.CODE)
        adapter = make_adapter(entry)
        assert adapter.entry is entry


# ---------------------------------------------------------------------------
# CodeKGAdapter
# ---------------------------------------------------------------------------


class TestCodeKGAdapterIsAvailable:
    def test_unavailable_when_import_fails(self, tmp_path):
        entry = _entry(tmp_path, KGKind.CODE)
        with patch.dict("sys.modules", {"code_kg": None}):
            adapter = CodeKGAdapter(entry)
            assert adapter.is_available() is False

    def test_unavailable_when_not_built(self, tmp_path):
        entry = _entry(tmp_path, KGKind.CODE)  # no sqlite
        mock_code_kg = MagicMock()
        with patch.dict("sys.modules", {"code_kg": mock_code_kg}):
            adapter = CodeKGAdapter(entry)
            assert adapter.is_available() is False

    def test_available_when_built(self, tmp_path):
        entry = _entry(tmp_path, KGKind.CODE, with_sqlite=True)
        mock_code_kg = MagicMock()
        with patch.dict("sys.modules", {"code_kg": mock_code_kg}):
            adapter = CodeKGAdapter(entry)
            assert adapter.is_available() is True


class TestCodeKGAdapterQuery:
    def _make_node(self, name="foo", score=0.9, docstring="doc", module="src/f.py"):
        return {
            "id": f"fn:{module}:{name}",
            "name": name,
            "kind": "function",
            "docstring": docstring,
            "module_path": module,
            "relevance": {"score": score},
        }

    def test_query_returns_cross_hits(self, tmp_path):
        entry = _entry(tmp_path, KGKind.CODE, with_sqlite=True)
        mock_result = MagicMock()
        mock_result.nodes = [self._make_node()]

        mock_kg = MagicMock()
        mock_kg.query.return_value = mock_result

        adapter = CodeKGAdapter(entry)
        adapter._kg = mock_kg

        hits = adapter.query("test query", k=5)
        assert len(hits) == 1
        assert isinstance(hits[0], CrossHit)
        assert hits[0].kg_kind == KGKind.CODE
        assert hits[0].score == 0.9
        mock_kg.query.assert_called_once_with("test query", k=5)

    def test_query_respects_k_limit(self, tmp_path):
        entry = _entry(tmp_path, KGKind.CODE, with_sqlite=True)
        mock_result = MagicMock()
        mock_result.nodes = [self._make_node(name=f"fn{i}", score=float(i)) for i in range(10)]

        mock_kg = MagicMock()
        mock_kg.query.return_value = mock_result

        adapter = CodeKGAdapter(entry)
        adapter._kg = mock_kg

        hits = adapter.query("q", k=3)
        assert len(hits) == 3


class TestCodeKGAdapterPack:
    def test_pack_returns_cross_snippets(self, tmp_path):
        entry = _entry(tmp_path, KGKind.CODE, with_sqlite=True)

        node = {
            "id": "fn:src/foo.py:bar",
            "relevance": {"score": 0.85},
            "snippet": {"path": "src/foo.py", "text": "def bar(): pass", "start": 10, "end": 12},
        }
        mock_pack = MagicMock()
        mock_pack.nodes = [node]
        mock_kg = MagicMock()
        mock_kg.pack.return_value = mock_pack

        adapter = CodeKGAdapter(entry)
        adapter._kg = mock_kg

        snippets = adapter.pack("query", k=4, context=3)
        assert len(snippets) == 1
        s = snippets[0]
        assert isinstance(s, CrossSnippet)
        assert s.kg_kind == KGKind.CODE
        assert s.content == "def bar(): pass"
        assert s.lineno == 10
        mock_kg.pack.assert_called_once_with("query", k=4, context=3)


class TestCodeKGAdapterStats:
    def test_stats_returns_dict(self, tmp_path):
        entry = _entry(tmp_path, KGKind.CODE, with_sqlite=True)
        mock_store = MagicMock()
        mock_store.stats.return_value = {"meaningful_nodes": 42, "total_edges": 99}
        mock_kg = MagicMock()
        mock_kg.store = mock_store

        adapter = CodeKGAdapter(entry)
        adapter._kg = mock_kg

        stats = adapter.stats()
        assert stats["node_count"] == 42
        assert stats["edge_count"] == 99
        assert stats["kind"] == "code"

    def test_stats_graceful_on_error(self, tmp_path):
        entry = _entry(tmp_path, KGKind.CODE, with_sqlite=True)
        mock_kg = MagicMock()
        mock_kg.store.stats.side_effect = RuntimeError("db error")

        adapter = CodeKGAdapter(entry)
        adapter._kg = mock_kg

        stats = adapter.stats()
        assert stats["kind"] == "code"
        assert "error" in stats


# ---------------------------------------------------------------------------
# DocKGAdapter
# ---------------------------------------------------------------------------


class TestDocKGAdapterIsAvailable:
    def test_unavailable_when_import_fails(self, tmp_path):
        entry = _entry(tmp_path, KGKind.DOC)
        with patch.dict("sys.modules", {"doc_kg": None}):
            adapter = DocKGAdapter(entry)
            assert adapter.is_available() is False

    def test_available_when_built(self, tmp_path):
        entry = _entry(tmp_path, KGKind.DOC, with_sqlite=True)
        mock_doc_kg = MagicMock()
        with patch.dict("sys.modules", {"doc_kg": mock_doc_kg}):
            adapter = DocKGAdapter(entry)
            assert adapter.is_available() is True


class TestDocKGAdapterQuery:
    def test_query_returns_cross_hits(self, tmp_path):
        entry = _entry(tmp_path, KGKind.DOC, with_sqlite=True)

        node = {
            "id": "chunk:docs/foo.md:intro",
            "name": "intro",
            "kind": "chunk",
            "title": "Overview section",
            "text": "Overview section text",
            "file_path": "docs/foo.md",
            "relevance": {"score": 0.75},
        }
        mock_result = MagicMock()
        mock_result.nodes = [node]
        mock_kg = MagicMock()
        mock_kg.query.return_value = mock_result

        adapter = DocKGAdapter(entry)
        adapter._kg = mock_kg

        hits = adapter.query("overview", k=5)
        assert len(hits) == 1
        assert hits[0].kg_kind == KGKind.DOC
        assert hits[0].score == 0.75


# ---------------------------------------------------------------------------
# MetaKGAdapter
# ---------------------------------------------------------------------------


class TestMetaKGAdapterIsAvailable:
    def test_unavailable_when_import_fails(self, tmp_path):
        entry = _entry(tmp_path, KGKind.META)
        with patch.dict("sys.modules", {"metakg": None}):
            adapter = MetaKGAdapter(entry)
            assert adapter.is_available() is False

    def test_available_when_built(self, tmp_path):
        entry = _entry(tmp_path, KGKind.META, with_sqlite=True)
        mock_metakg = MagicMock()
        with patch.dict("sys.modules", {"metakg": mock_metakg}):
            adapter = MetaKGAdapter(entry)
            assert adapter.is_available() is True


class TestMetaKGAdapterPackGraceful:
    def test_pack_returns_empty_on_exception(self, tmp_path):
        entry = _entry(tmp_path, KGKind.META, with_sqlite=True)
        mock_kg = MagicMock()
        mock_kg.pack.side_effect = RuntimeError("internal error")

        adapter = MetaKGAdapter(entry)
        adapter._kg = mock_kg

        snippets = adapter.pack("query")
        assert snippets == []
