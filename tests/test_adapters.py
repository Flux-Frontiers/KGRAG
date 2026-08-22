"""
test_adapters.py

Unit tests for kg_rag.adapters — make_adapter factory and
is_available / query / pack / stats on each adapter type.

Query, pack and stats are driven against a mocked ``_kg``: those tests are
about how the adapter reshapes results into CrossHit/CrossSnippet, and a real
KG would mean building a real graph to get results worth reshaping.

The ``_load`` tests are the exception and use the **real** doc-kg and pycode-kg
classes. A MagicMock accepts any call, so it validates the adapter's kwargs only
against the test's own expectations, never against the actual constructor
signature. Confirmed by mutation: adding a stale ``lancedb_uri=`` argument to
DocKGAdapter._load leaves the mocked version green while the real class raises
``TypeError: unexpected keyword argument``. Since upstream signature drift is
precisely what breaks these adapters in production, the real class is the only
thing worth asserting against.

Both packages are optional at runtime (the ``kg`` extra) but are dev
dependencies so the suite always has them. Constructing either is cheap — no
model load, no graph build.
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from kg_rag.adapters import make_adapter
from kg_rag.adapters.dockg_adapter import DocKGAdapter
from kg_rag.adapters.gutenberg_adapter import GutenbergKGAdapter
from kg_rag.adapters.ia_adapter import IABookKGAdapter
from kg_rag.adapters.memory_adapter import MemoryKGAdapter
from kg_rag.adapters.metakg_adapter import MetaKGAdapter
from kg_rag.adapters.pycodekg_adaptor import CodeKGAdapter
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
        with patch.dict("sys.modules", {"pycode_kg": None}):
            adapter = CodeKGAdapter(entry)
            assert adapter.is_available() is False

    def test_unavailable_when_not_built(self, tmp_path):
        entry = _entry(tmp_path, KGKind.CODE)  # no sqlite
        mock_pycode_kg = MagicMock()
        with patch.dict("sys.modules", {"pycode_kg": mock_pycode_kg}):
            adapter = CodeKGAdapter(entry)
            assert adapter.is_available() is False

    def test_available_when_built(self, tmp_path):
        entry = _entry(tmp_path, KGKind.CODE, with_sqlite=True)
        mock_pycode_kg = MagicMock()
        with patch.dict("sys.modules", {"pycode_kg": mock_pycode_kg}):
            adapter = CodeKGAdapter(entry)
            assert adapter.is_available() is True


class TestCodeKGAdapterLoad:
    """_load must hand PyCodeKG the recorded sqlite-vec store, not a guess.

    These build a **real** PyCodeKG rather than patching the constructor.
    Construction is cheap — no model load, no graph build — and the adapter's
    entire job is producing a correctly configured KG object, which is a claim
    only the real class can settle. Asserting on a mock's call kwargs proves
    just that we passed some strings to something.
    """

    def _loaded_kg(self, entry):
        """Run CodeKGAdapter._load and return the PyCodeKG it built.

        :param entry: Registry entry to load from.
        :return: The constructed PyCodeKG instance.
        """
        adapter = CodeKGAdapter(entry)
        adapter._load()
        return adapter._kg

    def test_uses_registered_vectors_path(self, tmp_path):
        entry = _entry(tmp_path, KGKind.CODE, with_sqlite=True)
        entry.vectors_path = tmp_path / "elsewhere" / "custom-vectors.sqlite"

        kg = self._loaded_kg(entry)
        assert Path(kg.vectors_path) == tmp_path / "elsewhere" / "custom-vectors.sqlite"

    def test_falls_back_to_default_layout(self, tmp_path):
        """With no vectors_path recorded, fall back to the default .pycodekg layout."""
        entry = _entry(tmp_path, KGKind.CODE, with_sqlite=True)
        assert entry.vectors_path is None

        kg = self._loaded_kg(entry)
        assert Path(kg.vectors_path) == entry.repo_path / ".pycodekg" / "vectors.sqlite"

    def test_lancedb_path_does_not_influence_vectors(self, tmp_path):
        """A legacy lancedb_path must no longer be used to derive the store."""
        entry = _entry(tmp_path, KGKind.CODE, with_sqlite=True)
        entry.lancedb_path = tmp_path / "stale" / "lancedb"

        kg = self._loaded_kg(entry)
        assert "stale" not in str(kg.vectors_path)
        assert Path(kg.vectors_path) == entry.repo_path / ".pycodekg" / "vectors.sqlite"


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
        mock_kg.query.assert_called_once_with("test query", k=5, min_score=0.0)

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

    def test_query_uses_semantic_over_score(self, tmp_path):
        # When PyCodeKG returns both "semantic" (raw cosine similarity) and
        # "score" (reranked, normalized per result set), the adapter must use
        # "semantic" so cross-KG comparisons aren't inflated by reranking.
        entry = _entry(tmp_path, KGKind.CODE, with_sqlite=True)
        node = {
            "id": "fn:src/f.py:bar",
            "name": "bar",
            "kind": "function",
            "docstring": "",
            "module_path": "src/f.py",
            "relevance": {"score": 1.0, "semantic": 0.52},
        }
        mock_result = MagicMock()
        mock_result.nodes = [node]
        mock_kg = MagicMock()
        mock_kg.query.return_value = mock_result

        adapter = CodeKGAdapter(entry)
        adapter._kg = mock_kg

        hits = adapter.query("q", k=5)
        assert len(hits) == 1
        assert hits[0].score == pytest.approx(0.52)

    def test_query_falls_back_to_score_when_semantic_absent(self, tmp_path):
        # Older PyCodeKG builds may not emit "semantic"; fall back to "score".
        entry = _entry(tmp_path, KGKind.CODE, with_sqlite=True)
        node = {
            "id": "fn:src/f.py:bar",
            "name": "bar",
            "kind": "function",
            "docstring": "",
            "module_path": "src/f.py",
            "relevance": {"score": 0.75},
        }
        mock_result = MagicMock()
        mock_result.nodes = [node]
        mock_kg = MagicMock()
        mock_kg.query.return_value = mock_result

        adapter = CodeKGAdapter(entry)
        adapter._kg = mock_kg

        hits = adapter.query("q", k=5)
        assert hits[0].score == pytest.approx(0.75)


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


class TestDocKGAdapterLoad:
    """The registry's vectors_path must reach DocKG (doc-kg >=0.18.2).

    As with the code adapter, these build a real DocKG rather than patching
    its constructor — see :class:`TestCodeKGAdapterLoad`.
    """

    def _loaded_kg(self, adapter):
        """Run an adapter's _load and return the DocKG it built.

        :param adapter: A DocKG-backed adapter.
        :return: The constructed DocKG instance.
        """
        adapter._load()
        return adapter._kg

    def test_forwards_registered_vectors_path(self, tmp_path):
        entry = _entry(tmp_path, KGKind.DOC, with_sqlite=True)
        entry.vectors_path = tmp_path / "offsite" / "vectors.sqlite"

        kg = self._loaded_kg(DocKGAdapter(entry))
        assert Path(kg.vectors_path) == tmp_path / "offsite" / "vectors.sqlite"

    def test_passes_none_when_unset(self, tmp_path):
        """None keeps doc-kg's derived-sidecar behaviour for default layouts."""
        entry = _entry(tmp_path, KGKind.DOC, with_sqlite=True)
        assert entry.vectors_path is None

        assert self._loaded_kg(DocKGAdapter(entry)).vectors_path is None

    def test_gutenberg_adapter_forwards_vectors_path(self, tmp_path):
        entry = _entry(tmp_path, KGKind.GUTENBERG, with_sqlite=True)
        entry.vectors_path = tmp_path / "books" / "vectors.sqlite"

        kg = self._loaded_kg(GutenbergKGAdapter(entry))
        assert Path(kg.vectors_path) == tmp_path / "books" / "vectors.sqlite"


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
        with patch.dict("sys.modules", {"metabokg": None}):
            adapter = MetaKGAdapter(entry)
            assert adapter.is_available() is False

    def test_available_when_built(self, tmp_path):
        entry = _entry(tmp_path, KGKind.META, with_sqlite=True)
        mock_metakg = MagicMock()
        with patch.dict("sys.modules", {"metabokg": mock_metakg}):
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


# ---------------------------------------------------------------------------
# analyze() — all adapters
# ---------------------------------------------------------------------------


class TestCodeKGAdapterAnalyze:
    def test_analyze_returns_string(self, tmp_path):
        entry = _entry(tmp_path, KGKind.CODE, with_sqlite=True)
        mock_kg = MagicMock()
        mock_kg.analyze.return_value = "# CodeKG Analysis\n\nSome report."

        adapter = CodeKGAdapter(entry)
        adapter._kg = mock_kg

        report = adapter.analyze()
        assert isinstance(report, str)
        assert len(report) > 0
        mock_kg.analyze.assert_called_once()

    def test_analyze_graceful_on_error(self, tmp_path):
        entry = _entry(tmp_path, KGKind.CODE, with_sqlite=True)
        mock_kg = MagicMock()
        mock_kg.analyze.side_effect = RuntimeError("analysis boom")

        adapter = CodeKGAdapter(entry)
        adapter._kg = mock_kg

        report = adapter.analyze()
        assert "Analysis failed" in report


class TestDocKGAdapterAnalyze:
    def test_analyze_returns_markdown(self, tmp_path):
        entry = _entry(tmp_path, KGKind.DOC, with_sqlite=True)

        mock_analyzer_result = {
            "timestamp": "2026-01-01T00:00:00+00:00",
            "elapsed_seconds": 0.5,
            "stats": {"total_nodes": 200, "total_edges": 1500},
            "semantic_coverage": {
                "topic_coverage": 0.95,
                "entity_coverage": 0.70,
                "keyword_coverage": 0.98,
            },
            "document_metrics": [
                {
                    "file_path": "docs/README.md",
                    "chunks": 10,
                    "sections": 5,
                    "refs_out": 3,
                    "semantic_links": 42,
                }
            ],
            "hot_chunks": [],
            "issues": ["Low entity coverage"],
            "strengths": ["Strong topic coverage"],
        }
        mock_analyzer = MagicMock()
        mock_analyzer.run_analysis.return_value = mock_analyzer_result

        mock_kg = MagicMock()
        adapter = DocKGAdapter(entry)
        adapter._kg = mock_kg

        mock_doc_kg_module = MagicMock()
        mock_analysis_module = MagicMock()
        mock_analysis_module.DocKGAnalyzer = MagicMock(return_value=mock_analyzer)
        with patch("kg_rag.adapters.dockg_adapter.DocKGAdapter._load"):
            with patch.dict(
                "sys.modules",
                {
                    "doc_kg": mock_doc_kg_module,
                    "doc_kg.dockg_thorough_analysis": mock_analysis_module,
                },
            ):
                report = adapter.analyze()

        assert "# DocKG Analysis Report" in report
        assert "200" in report  # total nodes
        assert "95.0%" in report  # topic coverage
        assert "Low entity coverage" in report
        assert "Strong topic coverage" in report

    def test_analyze_graceful_on_import_error(self, tmp_path):
        entry = _entry(tmp_path, KGKind.DOC, with_sqlite=True)
        mock_kg = MagicMock()
        adapter = DocKGAdapter(entry)
        adapter._kg = mock_kg

        with patch("kg_rag.adapters.dockg_adapter.DocKGAdapter._load"):
            with patch.dict("sys.modules", {"doc_kg.dockg_thorough_analysis": None}):
                report = adapter.analyze()

        assert "# DocKG Analysis" in report
        assert "failed" in report.lower() or "error" in report.lower()


class TestMetaKGAdapterAnalyze:
    def test_analyze_unavailable_returns_message(self, tmp_path):
        entry = _entry(tmp_path, KGKind.META)  # no sqlite -> not built
        with patch.dict("sys.modules", {"metabokg": None}):
            adapter = MetaKGAdapter(entry)
            report = adapter.analyze()
        assert "# MetaKG Analysis Report" in report
        assert "unavailable" in report

    def test_analyze_delegates_to_orchestrator_analyze(self, tmp_path):
        entry = _entry(tmp_path, KGKind.META, with_sqlite=True)
        mock_kg = MagicMock()
        mock_kg.analyze.return_value = "## Pathway Summary\n\nAll pathways healthy."

        mock_metakg = MagicMock()
        adapter = MetaKGAdapter(entry)
        adapter._kg = mock_kg

        with patch.dict("sys.modules", {"metabokg": mock_metakg}):
            report = adapter.analyze()

        assert "# MetaKG Analysis Report" in report
        assert "Pathway Summary" in report

    def test_analyze_fallback_stats_when_no_orchestrator_analyze(self, tmp_path):
        entry = _entry(tmp_path, KGKind.META, with_sqlite=True)
        mock_kg = MagicMock(spec=[])  # no analyze() method

        mock_metakg = MagicMock()
        adapter = MetaKGAdapter(entry)
        adapter._kg = mock_kg

        with patch.dict("sys.modules", {"metabokg": mock_metakg}):
            report = adapter.analyze()

        assert "# MetaKG Analysis Report" in report
        assert "Summary" in report


class TestMetaKGAdapterStats:
    def test_stats_unavailable_when_not_built(self, tmp_path):
        entry = _entry(tmp_path, KGKind.META)
        with patch.dict("sys.modules", {"metabokg": None}):
            adapter = MetaKGAdapter(entry)
            s = adapter.stats()
        assert s["kind"] == "meta"
        assert s["available"] is False

    def test_stats_includes_counts_when_orchestrator_provides_them(self, tmp_path):
        entry = _entry(tmp_path, KGKind.META, with_sqlite=True)
        mock_kg = MagicMock()
        mock_kg.stats.return_value = {"total_nodes": 55, "total_edges": 120}

        mock_metakg = MagicMock()
        adapter = MetaKGAdapter(entry)
        adapter._kg = mock_kg

        with patch.dict("sys.modules", {"metabokg": mock_metakg}):
            s = adapter.stats()

        assert s["node_count"] == 55
        assert s["edge_count"] == 120


# ---------------------------------------------------------------------------
# make_adapter — new kinds
# ---------------------------------------------------------------------------


class TestMakeAdapterNewKinds:
    def test_memory_kind_returns_memory_adapter(self, tmp_path):
        entry = _entry(tmp_path, KGKind.MEMORY)
        adapter = make_adapter(entry)
        assert isinstance(adapter, MemoryKGAdapter)

    def test_gutenberg_kind_returns_gutenberg_adapter(self, tmp_path):
        entry = _entry(tmp_path, KGKind.GUTENBERG)
        adapter = make_adapter(entry)
        assert isinstance(adapter, GutenbergKGAdapter)

    def test_ia_kind_returns_ia_adapter(self, tmp_path):
        entry = _entry(tmp_path, KGKind.IA)
        adapter = make_adapter(entry)
        assert isinstance(adapter, IABookKGAdapter)


# ---------------------------------------------------------------------------
# MemoryKGAdapter
# ---------------------------------------------------------------------------


class TestMemoryKGAdapterIsAvailable:
    def test_unavailable_when_import_fails(self, tmp_path):
        entry = _entry(tmp_path, KGKind.MEMORY)
        with patch.dict("sys.modules", {"memory_kg": None}):
            adapter = MemoryKGAdapter(entry)
            assert adapter.is_available() is False

    def test_unavailable_when_not_built(self, tmp_path):
        entry = _entry(tmp_path, KGKind.MEMORY)  # no sqlite
        mock_memory_kg = MagicMock()
        with patch.dict("sys.modules", {"memory_kg": mock_memory_kg}):
            adapter = MemoryKGAdapter(entry)
            assert adapter.is_available() is False

    def test_available_when_built(self, tmp_path):
        entry = _entry(tmp_path, KGKind.MEMORY, with_sqlite=True)
        mock_memory_kg = MagicMock()
        with patch.dict("sys.modules", {"memory_kg": mock_memory_kg}):
            adapter = MemoryKGAdapter(entry)
            assert adapter.is_available() is True


class TestMemoryKGAdapterQuery:
    def _make_node(
        self,
        id="chunk:docs/x.md:0",
        kind="chunk",
        title="Overview",
        file_path="docs/x.md",
        text="Some text",
    ):
        return {
            "id": id,
            "kind": kind,
            "title": title,
            "name": None,
            "file_path": file_path,
            "text": text,
        }

    def test_query_returns_cross_hits(self, tmp_path):
        entry = _entry(tmp_path, KGKind.MEMORY, with_sqlite=True)
        mock_result = MagicMock()
        mock_result.nodes = [self._make_node()]

        mock_kg = MagicMock()
        mock_kg.query.return_value = mock_result

        adapter = MemoryKGAdapter(entry)
        adapter._kg = mock_kg

        hits = adapter.query("test query", k=5)
        assert len(hits) == 1
        assert isinstance(hits[0], CrossHit)
        assert hits[0].kg_kind == KGKind.MEMORY
        assert hits[0].source_path == "docs/x.md"

    def test_query_positional_scores_descend(self, tmp_path):
        entry = _entry(tmp_path, KGKind.MEMORY, with_sqlite=True)
        nodes = [self._make_node(id=f"chunk:x.md:{i}") for i in range(5)]
        mock_result = MagicMock()
        mock_result.nodes = nodes

        mock_kg = MagicMock()
        mock_kg.query.return_value = mock_result

        adapter = MemoryKGAdapter(entry)
        adapter._kg = mock_kg

        hits = adapter.query("q", k=5)
        scores = [h.score for h in hits]
        assert scores == sorted(scores, reverse=True)
        assert scores[0] == 1.0
        assert scores[-1] > 0.0

    def test_query_respects_min_score(self, tmp_path):
        entry = _entry(tmp_path, KGKind.MEMORY, with_sqlite=True)
        nodes = [self._make_node(id=f"chunk:x.md:{i}") for i in range(10)]
        mock_result = MagicMock()
        mock_result.nodes = nodes

        mock_kg = MagicMock()
        mock_kg.query.return_value = mock_result

        adapter = MemoryKGAdapter(entry)
        adapter._kg = mock_kg

        hits = adapter.query("q", k=10, min_score=0.8)
        assert all(h.score >= 0.8 for h in hits)

    def test_query_semantic_floor_suppresses_all(self, tmp_path):
        entry = _entry(tmp_path, KGKind.MEMORY, with_sqlite=True)
        mock_result = MagicMock()
        mock_result.nodes = [self._make_node()]

        mock_kg = MagicMock()
        mock_kg.query.return_value = mock_result

        adapter = MemoryKGAdapter(entry)
        adapter._kg = mock_kg

        # With 1 node, score is 1.0; floor of 1.1 should suppress
        hits = adapter.query("q", k=5, semantic_floor=1.1)
        assert hits == []

    def test_query_uses_title_as_name(self, tmp_path):
        entry = _entry(tmp_path, KGKind.MEMORY, with_sqlite=True)
        node = self._make_node(title="My Chapter", file_path="book/ch1.md")
        mock_result = MagicMock()
        mock_result.nodes = [node]

        mock_kg = MagicMock()
        mock_kg.query.return_value = mock_result

        adapter = MemoryKGAdapter(entry)
        adapter._kg = mock_kg

        hits = adapter.query("q")
        assert hits[0].name == "My Chapter"


class TestMemoryKGAdapterPack:
    def _make_node(
        self,
        id="chunk:docs/y.md:0",
        file_path="docs/y.md",
        excerpt="Excerpt text",
        text="Full text",
    ):
        return {"id": id, "kind": "chunk", "file_path": file_path, "excerpt": excerpt, "text": text}

    def test_pack_returns_cross_snippets(self, tmp_path):
        entry = _entry(tmp_path, KGKind.MEMORY, with_sqlite=True)
        mock_pack = MagicMock()
        mock_pack.nodes = [self._make_node()]

        mock_kg = MagicMock()
        mock_kg.pack.return_value = mock_pack

        adapter = MemoryKGAdapter(entry)
        adapter._kg = mock_kg

        snippets = adapter.pack("test query", k=5)
        assert len(snippets) == 1
        s = snippets[0]
        assert isinstance(s, CrossSnippet)
        assert s.kg_kind == KGKind.MEMORY
        assert s.content == "Excerpt text"
        assert s.source_path == "docs/y.md"

    def test_pack_falls_back_to_text_when_no_excerpt(self, tmp_path):
        entry = _entry(tmp_path, KGKind.MEMORY, with_sqlite=True)
        node = {"id": "x", "kind": "chunk", "file_path": "f.md", "text": "Fallback text"}
        mock_pack = MagicMock()
        mock_pack.nodes = [node]

        mock_kg = MagicMock()
        mock_kg.pack.return_value = mock_pack

        adapter = MemoryKGAdapter(entry)
        adapter._kg = mock_kg

        snippets = adapter.pack("q")
        assert snippets[0].content == "Fallback text"

    def test_pack_semantic_floor_suppresses_all(self, tmp_path):
        entry = _entry(tmp_path, KGKind.MEMORY, with_sqlite=True)
        mock_pack = MagicMock()
        mock_pack.nodes = [self._make_node()]

        mock_kg = MagicMock()
        mock_kg.pack.return_value = mock_pack

        adapter = MemoryKGAdapter(entry)
        adapter._kg = mock_kg

        snippets = adapter.pack("q", semantic_floor=1.1)
        assert snippets == []


class TestMemoryKGAdapterStats:
    def test_stats_maps_total_nodes_and_edges(self, tmp_path):
        entry = _entry(tmp_path, KGKind.MEMORY, with_sqlite=True)
        mock_kg = MagicMock()
        mock_kg.stats.return_value = {
            "total_nodes": 120,
            "total_edges": 300,
            "node_counts": {"chunk": 100, "section": 20},
            "edge_counts": {"CONTAINS": 300},
        }

        adapter = MemoryKGAdapter(entry)
        adapter._kg = mock_kg

        s = adapter.stats()
        assert s["kind"] == "memory"
        assert s["node_count"] == 120
        assert s["edge_count"] == 300
        assert s["node_counts"]["chunk"] == 100

    def test_stats_graceful_on_error(self, tmp_path):
        entry = _entry(tmp_path, KGKind.MEMORY, with_sqlite=True)
        mock_kg = MagicMock()
        mock_kg.stats.side_effect = RuntimeError("db gone")

        adapter = MemoryKGAdapter(entry)
        adapter._kg = mock_kg

        s = adapter.stats()
        assert s["kind"] == "memory"
        assert "error" in s


class TestMemoryKGAdapterAnalyze:
    def test_analyze_returns_markdown(self, tmp_path):
        entry = _entry(tmp_path, KGKind.MEMORY, with_sqlite=True)
        mock_analyzer = MagicMock()
        mock_analyzer.run_analysis.return_value = {"stats": {"total_nodes": 80, "total_edges": 200}}
        mock_analyzer_cls = MagicMock(return_value=mock_analyzer)

        mock_kg = MagicMock()
        adapter = MemoryKGAdapter(entry)
        adapter._kg = mock_kg

        mock_analysis_module = MagicMock()
        mock_analysis_module.MemoryKGAnalyzer = mock_analyzer_cls
        with patch("kg_rag.adapters.memory_adapter.MemoryKGAdapter._load"):
            with patch.dict(
                "sys.modules",
                {"memory_kg.memorykg_thorough_analysis": mock_analysis_module},
            ):
                report = adapter.analyze()

        assert "# MemoryKG Analysis Report" in report
        assert "80" in report

    def test_analyze_graceful_on_error(self, tmp_path):
        entry = _entry(tmp_path, KGKind.MEMORY, with_sqlite=True)
        mock_kg = MagicMock()
        mock_kg.analyze.side_effect = RuntimeError("analysis boom")

        adapter = MemoryKGAdapter(entry)
        adapter._kg = mock_kg

        with patch("kg_rag.adapters.memory_adapter.MemoryKGAdapter._load"):
            with patch.dict("sys.modules", {"memory_kg.memorykg_thorough_analysis": None}):
                report = adapter.analyze()

        assert "MemoryKG Analysis" in report
        assert "failed" in report.lower() or "error" in report.lower()


# ---------------------------------------------------------------------------
# GutenbergKGAdapter (stub)
# ---------------------------------------------------------------------------


class TestGutenbergKGAdapterStub:
    def test_unavailable_when_not_installed(self, tmp_path):
        entry = _entry(tmp_path, KGKind.GUTENBERG)
        with patch.dict("sys.modules", {"gutenberg_kg": None}):
            adapter = GutenbergKGAdapter(entry)
            assert adapter.is_available() is False

    def test_unavailable_when_not_built(self, tmp_path):
        entry = _entry(tmp_path, KGKind.GUTENBERG)  # no sqlite
        mock_pkg = MagicMock()
        with patch.dict("sys.modules", {"gutenberg_kg": mock_pkg}):
            adapter = GutenbergKGAdapter(entry)
            assert adapter.is_available() is False

    def test_query_returns_empty(self, tmp_path):
        entry = _entry(tmp_path, KGKind.GUTENBERG)
        adapter = GutenbergKGAdapter(entry)
        assert adapter.query("any") == []

    def test_pack_returns_empty(self, tmp_path):
        entry = _entry(tmp_path, KGKind.GUTENBERG)
        adapter = GutenbergKGAdapter(entry)
        assert adapter.pack("any") == []

    def test_stats_reports_unavailable(self, tmp_path):
        entry = _entry(tmp_path, KGKind.GUTENBERG)
        adapter = GutenbergKGAdapter(entry)
        s = adapter.stats()
        assert s.get("available") is False or s.get("status") == "unavailable"

    def test_analyze_reports_unavailable(self, tmp_path):
        entry = _entry(tmp_path, KGKind.GUTENBERG)
        adapter = GutenbergKGAdapter(entry)
        report = adapter.analyze()
        assert "unavailable" in report.lower()


# ---------------------------------------------------------------------------
# IABookKGAdapter (stub)
# ---------------------------------------------------------------------------


class TestIABookKGAdapterStub:
    def test_unavailable_when_not_installed(self, tmp_path):
        entry = _entry(tmp_path, KGKind.IA)
        with patch.dict("sys.modules", {"ia_kg": None}):
            adapter = IABookKGAdapter(entry)
            assert adapter.is_available() is False

    def test_unavailable_when_not_built(self, tmp_path):
        entry = _entry(tmp_path, KGKind.IA)  # no sqlite
        mock_pkg = MagicMock()
        with patch.dict("sys.modules", {"ia_kg": mock_pkg}):
            adapter = IABookKGAdapter(entry)
            assert adapter.is_available() is False

    def test_query_returns_empty(self, tmp_path):
        entry = _entry(tmp_path, KGKind.IA)
        adapter = IABookKGAdapter(entry)
        assert adapter.query("any") == []

    def test_pack_returns_empty(self, tmp_path):
        entry = _entry(tmp_path, KGKind.IA)
        adapter = IABookKGAdapter(entry)
        assert adapter.pack("any") == []

    def test_stats_reports_unavailable(self, tmp_path):
        entry = _entry(tmp_path, KGKind.IA)
        adapter = IABookKGAdapter(entry)
        s = adapter.stats()
        assert s.get("available") is False or s.get("status") == "unavailable"

    def test_analyze_reports_unavailable(self, tmp_path):
        entry = _entry(tmp_path, KGKind.IA)
        adapter = IABookKGAdapter(entry)
        report = adapter.analyze()
        assert "unavailable" in report.lower()


# ---------------------------------------------------------------------------
# node_metadata — the bridge that makes time scoping reach real hits
# ---------------------------------------------------------------------------


class TestNodeMetadataHelper:
    """Adapters must carry node metadata into hits or time scoping cannot work.

    QueryScope.time_range reads CrossHit.metadata; if an adapter leaves it
    empty, every hit from that KG counts as undated and is filtered out. This
    helper is what each adapter calls to populate it.
    """

    def test_reads_nested_metadata(self):
        from kg_rag.adapters.base import node_metadata

        node = {"id": "n", "metadata": {"occurred_start": "2026-04-15"}}
        assert node_metadata(node) == {"occurred_start": "2026-04-15"}

    def test_reads_flattened_contract_keys(self):
        """Some modules put the contract keys straight on the node."""
        from kg_rag.adapters.base import node_metadata

        node = {"id": "n", "occurred_start": "2026-04-15", "recorded_at": "2026-08-17"}
        assert node_metadata(node) == {
            "occurred_start": "2026-04-15",
            "recorded_at": "2026-08-17",
        }

    def test_nested_wins_over_flattened(self):
        from kg_rag.adapters.base import node_metadata

        node = {"metadata": {"occurred_start": "2026-04-15"}, "occurred_start": "1999-01-01"}
        assert node_metadata(node)["occurred_start"] == "2026-04-15"

    def test_undated_node_yields_empty(self):
        from kg_rag.adapters.base import node_metadata

        assert node_metadata({"id": "n", "kind": "function"}) == {}

    def test_ignores_non_dict_metadata(self):
        from kg_rag.adapters.base import node_metadata

        assert node_metadata({"metadata": "not-a-dict"}) == {}

    def test_returns_a_copy(self):
        """Mutating a hit's metadata must not reach back into the backend's node."""
        from kg_rag.adapters.base import node_metadata

        original = {"occurred_start": "2026-04-15"}
        out = node_metadata({"metadata": original})
        out["occurred_start"] = "changed"
        assert original["occurred_start"] == "2026-04-15"
