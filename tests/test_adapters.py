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
from kg_rag.adapters._stub_adapter import StubKGAdapter
from kg_rag.adapters.agent_adapter import AgentKGAdapter
from kg_rag.adapters.diary_adapter import DiaryKGAdapter
from kg_rag.adapters.dockg_adapter import DocKGAdapter
from kg_rag.adapters.ftree_adapter import FTreeKGAdapter
from kg_rag.adapters.genealogy_adapter import GenealogyKGAdapter
from kg_rag.adapters.gutenberg_adapter import GutenbergKGAdapter
from kg_rag.adapters.ia_adapter import IABookKGAdapter
from kg_rag.adapters.memory_adapter import MemoryKGAdapter
from kg_rag.adapters.metakg_adapter import MetaKGAdapter
from kg_rag.adapters.person_adapter import PersonKGAdapter
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

    def test_genealogy_kind_returns_genealogykg_adapter(self, tmp_path):
        entry = _entry(tmp_path, KGKind.GENEALOGY)
        adapter = make_adapter(entry)
        assert isinstance(adapter, GenealogyKGAdapter)

    def test_filetree_kind_returns_ftreekg_adapter(self, tmp_path):
        entry = _entry(tmp_path, KGKind.FILETREE)
        adapter = make_adapter(entry)
        assert isinstance(adapter, FTreeKGAdapter)

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


# ---------------------------------------------------------------------------
# GenealogyKGAdapter
# ---------------------------------------------------------------------------


class TestGenealogyKGAdapterIsAvailable:
    def test_unavailable_when_import_fails(self, tmp_path):
        entry = _entry(tmp_path, KGKind.GENEALOGY)
        with patch.dict("sys.modules", {"genealogy_kg": None}):
            adapter = GenealogyKGAdapter(entry)
            assert adapter.is_available() is False

    def test_available_when_built(self, tmp_path):
        entry = _entry(tmp_path, KGKind.GENEALOGY, with_sqlite=True)
        mock_genealogy_kg = MagicMock()
        with patch.dict("sys.modules", {"genealogy_kg": mock_genealogy_kg}):
            adapter = GenealogyKGAdapter(entry)
            assert adapter.is_available() is True

    def test_unavailable_when_not_built(self, tmp_path):
        entry = _entry(tmp_path, KGKind.GENEALOGY)  # no sqlite
        mock_genealogy_kg = MagicMock()
        with patch.dict("sys.modules", {"genealogy_kg": mock_genealogy_kg}):
            adapter = GenealogyKGAdapter(entry)
            assert adapter.is_available() is False


class TestGenealogyKGAdapterQuery:
    """The score kg_utils.pipeline actually returns lives at
    node["relevance"]["score"], not a top-level "score" key -- and the node
    id is under "id", not "node_id". These tests pin that shape so a future
    kg_utils.pipeline refactor is caught here rather than silently degrading
    every hit to score 0.0 and node_id "", the way ftree_adapter.py currently
    does (verified against a live GenealogyKG.query() call, not assumed).
    """

    def test_query_returns_cross_hits(self, tmp_path):
        entry = _entry(tmp_path, KGKind.GENEALOGY, with_sqlite=True)
        mock_kg = MagicMock()
        mock_kg.query.return_value.nodes = [
            {
                "id": "person:I1",
                "name": "John Hartwell",
                "kind": "person",
                "docstring": "John Hartwell (male).",
                "module_path": "family.ged",
                "metadata": {"occurred_start": "1820", "occurred_end": "1891-11-07"},
                "relevance": {"score": 0.93},
            }
        ]

        adapter = GenealogyKGAdapter(entry)
        adapter._kg = mock_kg

        hits = adapter.query("Hartwell")
        assert len(hits) == 1
        hit = hits[0]
        assert isinstance(hit, CrossHit)
        assert hit.node_id == "person:I1"
        assert hit.name == "John Hartwell"
        assert hit.score == 0.93
        assert hit.source_path == "family.ged"
        assert hit.metadata == {"occurred_start": "1820", "occurred_end": "1891-11-07"}
        assert hit.kg_kind == KGKind.GENEALOGY

    def test_query_drops_hits_below_min_score(self, tmp_path):
        entry = _entry(tmp_path, KGKind.GENEALOGY, with_sqlite=True)
        mock_kg = MagicMock()
        mock_kg.query.return_value.nodes = [
            {"id": "a", "name": "A", "kind": "person", "relevance": {"score": 0.9}},
            {"id": "b", "name": "B", "kind": "person", "relevance": {"score": 0.1}},
        ]

        adapter = GenealogyKGAdapter(entry)
        adapter._kg = mock_kg

        hits = adapter.query("x", min_score=0.5)
        assert [h.node_id for h in hits] == ["a"]

    def test_query_semantic_floor_discards_whole_result_set(self, tmp_path):
        entry = _entry(tmp_path, KGKind.GENEALOGY, with_sqlite=True)
        mock_kg = MagicMock()
        mock_kg.query.return_value.nodes = [
            {"id": "a", "name": "A", "kind": "person", "relevance": {"score": 0.2}},
        ]

        adapter = GenealogyKGAdapter(entry)
        adapter._kg = mock_kg

        assert adapter.query("x", semantic_floor=0.5) == []


class TestGenealogyKGAdapterPack:
    def test_pack_returns_cross_snippets_from_node_snippet(self, tmp_path):
        entry = _entry(tmp_path, KGKind.GENEALOGY, with_sqlite=True)
        mock_kg = MagicMock()
        mock_kg.pack.return_value.nodes = [
            {
                "id": "person:I1",
                "module_path": "family.ged",
                "relevance": {"score": 0.8},
                "metadata": {"occurred_start": "1820"},
                "snippet": {
                    "path": "family.ged",
                    "start": 13,
                    "end": 30,
                    "text": "0 @I1@ INDI\n...",
                },
            }
        ]

        adapter = GenealogyKGAdapter(entry)
        adapter._kg = mock_kg

        snippets = adapter.pack("Hartwell")
        assert len(snippets) == 1
        s = snippets[0]
        assert isinstance(s, CrossSnippet)
        assert s.node_id == "person:I1"
        assert s.lineno == 13
        assert s.end_lineno == 30
        assert "0 @I1@ INDI" in s.content
        assert s.score == 0.8
        assert s.kg_kind == KGKind.GENEALOGY

    def test_pack_skips_nodes_without_a_snippet(self, tmp_path):
        entry = _entry(tmp_path, KGKind.GENEALOGY, with_sqlite=True)
        mock_kg = MagicMock()
        mock_kg.pack.return_value.nodes = [
            {"id": "person:I1", "relevance": {"score": 0.8}},  # no snippet: span omitted
        ]

        adapter = GenealogyKGAdapter(entry)
        adapter._kg = mock_kg

        assert adapter.pack("x") == []

    def test_pack_returns_empty_on_exception(self, tmp_path):
        entry = _entry(tmp_path, KGKind.GENEALOGY, with_sqlite=True)
        mock_kg = MagicMock()
        mock_kg.pack.side_effect = RuntimeError("internal error")

        adapter = GenealogyKGAdapter(entry)
        adapter._kg = mock_kg

        # pack() does not itself catch exceptions -- the orchestrator does,
        # per KGAdapter's documented contract (query/pack "or [] on error"
        # is enforced one layer up, not in every adapter). Assert the
        # exception propagates rather than assuming it is swallowed here.
        with pytest.raises(RuntimeError):
            adapter.pack("x")


class TestGenealogyKGAdapterStats:
    def test_stats_returns_dict_with_person_and_family_counts(self, tmp_path):
        entry = _entry(tmp_path, KGKind.GENEALOGY, with_sqlite=True)
        mock_kg = MagicMock()
        mock_kg.stats.return_value = {
            "total_nodes": 42,
            "total_edges": 55,
            "node_counts": {"person": 12, "family": 4, "event": 20, "place": 5, "source": 1},
        }

        adapter = GenealogyKGAdapter(entry)
        adapter._kg = mock_kg

        stats = adapter.stats()
        assert stats["kind"] == "genealogy"
        assert stats["node_count"] == 42
        assert stats["edge_count"] == 55
        assert stats["person_count"] == 12
        assert stats["family_count"] == 4

    def test_stats_graceful_on_error(self, tmp_path):
        entry = _entry(tmp_path, KGKind.GENEALOGY, with_sqlite=True)
        mock_kg = MagicMock()
        mock_kg.stats.side_effect = RuntimeError("boom")

        adapter = GenealogyKGAdapter(entry)
        adapter._kg = mock_kg

        stats = adapter.stats()
        assert stats["kind"] == "genealogy"
        assert "error" in stats


class TestGenealogyKGAdapterAnalyze:
    def test_analyze_returns_string(self, tmp_path):
        entry = _entry(tmp_path, KGKind.GENEALOGY, with_sqlite=True)
        mock_kg = MagicMock()
        mock_kg.analyze.return_value = "# GenealogyKG Analysis\n\nSome report."

        adapter = GenealogyKGAdapter(entry)
        adapter._kg = mock_kg

        report = adapter.analyze()
        assert isinstance(report, str)
        assert "GenealogyKG Analysis" in report

    def test_analyze_graceful_on_error(self, tmp_path):
        entry = _entry(tmp_path, KGKind.GENEALOGY, with_sqlite=True)
        mock_kg = MagicMock()
        mock_kg.analyze.side_effect = RuntimeError("analysis boom")

        adapter = GenealogyKGAdapter(entry)
        adapter._kg = mock_kg

        report = adapter.analyze()
        assert "Analysis failed" in report


class TestGenealogyKGAdapterSnapshotMetrics:
    def test_collect_snapshot_metrics(self, tmp_path):
        entry = _entry(tmp_path, KGKind.GENEALOGY, with_sqlite=True)
        mock_kg = MagicMock()
        mock_kg.stats.return_value = {
            "total_nodes": 42,
            "total_edges": 55,
            "node_counts": {"person": 12, "family": 4},
        }

        adapter = GenealogyKGAdapter(entry)
        adapter._kg = mock_kg

        metrics = adapter._collect_snapshot_metrics()
        assert metrics == {
            "total_nodes": 42,
            "total_edges": 55,
            "person_count": 12,
            "family_count": 4,
        }


# ---------------------------------------------------------------------------
# FTreeKGAdapter
# ---------------------------------------------------------------------------


class TestFTreeKGAdapterFieldMapping:
    """FileTreeKG.query()/pack() do NOT return the generic
    kg_utils.pipeline.KGModule shape -- FileTreeKG overrides both methods
    itself and deliberately keeps the older "node_id" / top-level "score" /
    populated SnippetPack.snippets shape for backward compatibility (see
    ftree_kg/module.py's own docstrings). Verified live against a real
    FileTreeKG build, not assumed: node_id and score were already correct
    here. What pack() was NOT doing was forwarding the metadata dict that
    FileTreeKG.pack() puts on every snippet (query()'s CrossHit already got
    it via node_metadata()) -- a time_range-scoped pack() call therefore saw
    every FTreeKG snippet as undated. These tests pin the fix.
    """

    def test_query_passes_through_node_id_score_and_metadata(self, tmp_path):
        entry = _entry(tmp_path, KGKind.FILETREE, with_sqlite=True)
        mock_kg = MagicMock()
        mock_kg.query.return_value.nodes = [
            {
                "id": "file:readme.txt:readme.txt",
                "node_id": "file:readme.txt:readme.txt",
                "name": "readme.txt",
                "kind": "file",
                "docstring": "a readme",
                "source_path": "readme.txt",
                "score": 0.87,
                "metadata": {"occurred_start": "2026-01-01T00:00:00+00:00"},
            }
        ]

        adapter = FTreeKGAdapter(entry)
        adapter._kg = mock_kg

        hits = adapter.query("readme")
        assert len(hits) == 1
        assert hits[0].node_id == "file:readme.txt:readme.txt"
        assert hits[0].score == 0.87
        assert hits[0].metadata == {"occurred_start": "2026-01-01T00:00:00+00:00"}

    def test_pack_carries_metadata_from_the_snippet_dict(self, tmp_path):
        entry = _entry(tmp_path, KGKind.FILETREE, with_sqlite=True)
        mock_kg = MagicMock()
        mock_kg.pack.return_value.snippets = [
            {
                "node_id": "file:readme.txt:readme.txt",
                "source_path": "readme.txt",
                "content": "file: readme.txt\na readme",
                "score": 0.87,
                "kind": "file",
                "name": "readme.txt",
                "metadata": {"occurred_start": "2026-01-01T00:00:00+00:00"},
            }
        ]

        adapter = FTreeKGAdapter(entry)
        adapter._kg = mock_kg

        snippets = adapter.pack("readme")
        assert len(snippets) == 1
        assert snippets[0].node_id == "file:readme.txt:readme.txt"
        # This is the regression the fix pins: before it, metadata was
        # dropped here even though FileTreeKG.pack() populates it.
        assert snippets[0].metadata == {"occurred_start": "2026-01-01T00:00:00+00:00"}

    def test_pack_omits_metadata_key_gracefully(self, tmp_path):
        entry = _entry(tmp_path, KGKind.FILETREE, with_sqlite=True)
        mock_kg = MagicMock()
        mock_kg.pack.return_value.snippets = [
            {"node_id": "n", "source_path": "p", "content": "c", "score": 0.5}
        ]

        adapter = FTreeKGAdapter(entry)
        adapter._kg = mock_kg

        snippets = adapter.pack("x")
        assert snippets[0].metadata == {}


# ---------------------------------------------------------------------------
# AgentKGAdapter
# ---------------------------------------------------------------------------


class TestAgentKGAdapterConstruction:
    def test_kg_starts_none(self, tmp_path):
        entry = _entry(tmp_path, KGKind.AGENT)
        adapter = AgentKGAdapter(entry)
        assert adapter._kg is None


class TestAgentKGAdapterLoad:
    def test_load_raises_import_error_when_agent_kg_missing(self, tmp_path):
        entry = _entry(tmp_path, KGKind.AGENT)
        adapter = AgentKGAdapter(entry)
        with patch.dict("sys.modules", {"agent_kg": None, "agent_kg.graph": None}):
            with pytest.raises(ImportError, match="agent-kg is not installed"):
                adapter._load()

    def test_load_constructs_agentkg_with_person_and_session(self, tmp_path):
        entry = _entry(tmp_path, KGKind.AGENT)
        entry.metadata["person_id"] = "eric"
        entry.metadata["session_id"] = "sess-1"

        mock_agentkg_cls = MagicMock()
        mock_graph_module = MagicMock(AgentKG=mock_agentkg_cls)

        adapter = AgentKGAdapter(entry)
        with patch.dict(
            "sys.modules", {"agent_kg": MagicMock(), "agent_kg.graph": mock_graph_module}
        ):
            adapter._load()

        mock_agentkg_cls.assert_called_once_with(
            repo_path=entry.repo_path, person_id="eric", session_id="sess-1"
        )
        assert adapter._kg is mock_agentkg_cls.return_value

    def test_load_defaults_person_id_and_session(self, tmp_path):
        entry = _entry(tmp_path, KGKind.AGENT)
        mock_agentkg_cls = MagicMock()
        mock_graph_module = MagicMock(AgentKG=mock_agentkg_cls)

        adapter = AgentKGAdapter(entry)
        with patch.dict(
            "sys.modules", {"agent_kg": MagicMock(), "agent_kg.graph": mock_graph_module}
        ):
            adapter._load()

        mock_agentkg_cls.assert_called_once_with(
            repo_path=entry.repo_path, person_id="default", session_id=None
        )


class TestAgentKGAdapterIsAvailable:
    def test_unavailable_when_import_fails(self, tmp_path):
        entry = _entry(tmp_path, KGKind.AGENT)
        with patch.dict("sys.modules", {"agent_kg": None}):
            adapter = AgentKGAdapter(entry)
            assert adapter.is_available() is False

    def test_available_when_entry_is_built(self, tmp_path):
        entry = _entry(tmp_path, KGKind.AGENT, with_sqlite=True)
        with patch.dict("sys.modules", {"agent_kg": MagicMock()}):
            adapter = AgentKGAdapter(entry)
            assert adapter.is_available() is True

    def test_unavailable_when_not_built_and_no_default_db(self, tmp_path):
        entry = _entry(tmp_path, KGKind.AGENT)  # no sqlite_path recorded
        with patch.dict("sys.modules", {"agent_kg": MagicMock()}):
            adapter = AgentKGAdapter(entry)
            assert adapter.is_available() is False

    def test_available_when_default_agentkg_db_exists(self, tmp_path):
        entry = _entry(tmp_path, KGKind.AGENT)  # no sqlite_path recorded
        default_dir = entry.repo_path / ".agentkg"
        default_dir.mkdir(parents=True)
        (default_dir / "graph.sqlite").touch()
        with patch.dict("sys.modules", {"agent_kg": MagicMock()}):
            adapter = AgentKGAdapter(entry)
            assert adapter.is_available() is True


class TestAgentKGAdapterQuery:
    def test_query_returns_cross_hits(self, tmp_path):
        entry = _entry(tmp_path, KGKind.AGENT)
        mock_kg = MagicMock()
        mock_kg.index.search.return_value = [
            {
                "node_id": "turn:1",
                "label": "hello",
                "kind": "turn",
                "score": 0.8,
                "text": "hello world",
            },
        ]

        adapter = AgentKGAdapter(entry)
        adapter._kg = mock_kg

        hits = adapter.query("hi", k=5)
        assert len(hits) == 1
        hit = hits[0]
        assert isinstance(hit, CrossHit)
        assert hit.kg_kind == KGKind.AGENT
        assert hit.node_id == "turn:1"
        assert hit.name == "hello"
        assert hit.score == 0.8
        mock_kg.index.search.assert_called_once_with("hi", k=5)

    def test_query_respects_min_score(self, tmp_path):
        entry = _entry(tmp_path, KGKind.AGENT)
        mock_kg = MagicMock()
        mock_kg.index.search.return_value = [
            {"node_id": "a", "label": "A", "score": 0.9, "text": "a"},
            {"node_id": "b", "label": "B", "score": 0.1, "text": "b"},
        ]
        adapter = AgentKGAdapter(entry)
        adapter._kg = mock_kg

        hits = adapter.query("q", min_score=0.5)
        assert [h.node_id for h in hits] == ["a"]

    def test_query_semantic_floor_discards_all(self, tmp_path):
        entry = _entry(tmp_path, KGKind.AGENT)
        mock_kg = MagicMock()
        mock_kg.index.search.return_value = [
            {"node_id": "a", "label": "A", "score": 0.2, "text": "a"},
        ]
        adapter = AgentKGAdapter(entry)
        adapter._kg = mock_kg

        assert adapter.query("q", semantic_floor=0.5) == []

    def test_query_uses_text_when_label_missing(self, tmp_path):
        entry = _entry(tmp_path, KGKind.AGENT)
        mock_kg = MagicMock()
        mock_kg.index.search.return_value = [
            {"node_id": "a", "score": 0.5, "text": "fallback text"},
        ]
        adapter = AgentKGAdapter(entry)
        adapter._kg = mock_kg

        hits = adapter.query("q")
        assert hits[0].name == "fallback text"


class TestAgentKGAdapterPack:
    def test_pack_returns_cross_snippets(self, tmp_path):
        entry = _entry(tmp_path, KGKind.AGENT)
        mock_kg = MagicMock()
        mock_kg.pack.return_value = [
            {"node_id": "turn:1", "content": "hello there", "score": 0.6},
        ]
        adapter = AgentKGAdapter(entry)
        adapter._kg = mock_kg

        snippets = adapter.pack("hi", k=4)
        assert len(snippets) == 1
        s = snippets[0]
        assert isinstance(s, CrossSnippet)
        assert s.kg_kind == KGKind.AGENT
        assert s.content == "hello there"
        mock_kg.pack.assert_called_once_with("hi", k=4)

    def test_pack_semantic_floor_discards_all(self, tmp_path):
        entry = _entry(tmp_path, KGKind.AGENT)
        mock_kg = MagicMock()
        mock_kg.pack.return_value = [{"node_id": "a", "content": "x", "score": 0.2}]
        adapter = AgentKGAdapter(entry)
        adapter._kg = mock_kg

        assert adapter.pack("q", semantic_floor=0.5) == []


class TestAgentKGAdapterStats:
    def test_stats_returns_dict(self, tmp_path):
        entry = _entry(tmp_path, KGKind.AGENT)
        mock_kg = MagicMock()
        mock_kg.stats.return_value = {
            "node_count": 10,
            "edge_count": 20,
            "session_id": "s1",
            "turn_count": 5,
        }
        adapter = AgentKGAdapter(entry)
        adapter._kg = mock_kg

        stats = adapter.stats()
        assert stats["kind"] == "agent"
        assert stats["node_count"] == 10
        assert stats["turn_count"] == 5

    def test_stats_graceful_on_error(self, tmp_path):
        entry = _entry(tmp_path, KGKind.AGENT)
        mock_kg = MagicMock()
        mock_kg.stats.side_effect = RuntimeError("boom")
        adapter = AgentKGAdapter(entry)
        adapter._kg = mock_kg

        stats = adapter.stats()
        assert stats == {"node_count": 0, "edge_count": 0, "kind": "agent"}


class TestAgentKGAdapterAnalyze:
    def test_analyze_returns_string(self, tmp_path):
        entry = _entry(tmp_path, KGKind.AGENT)
        mock_kg = MagicMock()
        mock_kg.analyze.return_value = "# AgentKG Analysis\n\nAll good."
        adapter = AgentKGAdapter(entry)
        adapter._kg = mock_kg

        report = adapter.analyze()
        assert "AgentKG Analysis" in report

    def test_analyze_graceful_on_error(self, tmp_path):
        entry = _entry(tmp_path, KGKind.AGENT)
        mock_kg = MagicMock()
        mock_kg.analyze.side_effect = RuntimeError("boom")
        adapter = AgentKGAdapter(entry)
        adapter._kg = mock_kg

        report = adapter.analyze()
        assert "Analysis failed" in report


class TestAgentKGAdapterWriteInterface:
    """AgentKG-specific write/assembly methods -- ingest/prune/assemble_context/
    should_prune/close_session -- unique to AgentKGAdapter among the KGAdapter
    family since AgentKG is mutated during a session rather than just queried.
    """

    def test_ingest_delegates_to_kg(self, tmp_path):
        entry = _entry(tmp_path, KGKind.AGENT)
        mock_kg = MagicMock()
        mock_kg.ingest.return_value = "result"
        adapter = AgentKGAdapter(entry)
        adapter._kg = mock_kg

        result = adapter.ingest("hello", role="user")
        assert result == "result"
        mock_kg.ingest.assert_called_once_with(text="hello", role="user")

    def test_prune_delegates_to_kg(self, tmp_path):
        entry = _entry(tmp_path, KGKind.AGENT)
        mock_kg = MagicMock()
        mock_kg.prune.return_value = "report"
        adapter = AgentKGAdapter(entry)
        adapter._kg = mock_kg

        result = adapter.prune(token_budget=1000, window=10)
        assert result == "report"
        mock_kg.prune.assert_called_once_with(token_budget=1000, window=10)

    def test_assemble_context_delegates_to_kg(self, tmp_path):
        entry = _entry(tmp_path, KGKind.AGENT)
        mock_kg = MagicMock()
        mock_kg.assemble_context.return_value = "context block"
        adapter = AgentKGAdapter(entry)
        adapter._kg = mock_kg

        result = adapter.assemble_context("query", budget=2000)
        assert result == "context block"
        mock_kg.assemble_context.assert_called_once_with("query", budget=2000)

    def test_should_prune_delegates_to_kg(self, tmp_path):
        entry = _entry(tmp_path, KGKind.AGENT)
        mock_kg = MagicMock()
        mock_kg.should_prune.return_value = True
        adapter = AgentKGAdapter(entry)
        adapter._kg = mock_kg

        assert adapter.should_prune(token_budget=500) is True
        mock_kg.should_prune.assert_called_once_with(token_budget=500)

    def test_close_session_delegates_when_loaded(self, tmp_path):
        entry = _entry(tmp_path, KGKind.AGENT)
        mock_kg = MagicMock()
        adapter = AgentKGAdapter(entry)
        adapter._kg = mock_kg

        adapter.close_session()
        mock_kg.close_session.assert_called_once()

    def test_close_session_noop_when_not_loaded(self, tmp_path):
        entry = _entry(tmp_path, KGKind.AGENT)
        adapter = AgentKGAdapter(entry)
        adapter.close_session()  # must not raise, self._kg is still None


class TestAgentKGAdapterSnapshotMetrics:
    def test_collect_snapshot_metrics(self, tmp_path):
        entry = _entry(tmp_path, KGKind.AGENT)
        mock_kg = MagicMock()
        mock_kg.stats.return_value = {
            "node_count": 10,
            "edge_count": 20,
            "turn_count": 5,
            "session_id": "s1",
        }
        adapter = AgentKGAdapter(entry)
        adapter._kg = mock_kg

        metrics = adapter._collect_snapshot_metrics()
        assert metrics == {
            "total_nodes": 10,
            "total_edges": 20,
            "turn_count": 5,
            "session_id": "s1",
        }

    def test_collect_snapshot_metrics_graceful_on_error(self, tmp_path):
        entry = _entry(tmp_path, KGKind.AGENT)
        with patch.dict("sys.modules", {"agent_kg": None}):
            adapter = AgentKGAdapter(entry)
            metrics = adapter._collect_snapshot_metrics()
        assert metrics == {}


# ---------------------------------------------------------------------------
# DiaryKGAdapter
# ---------------------------------------------------------------------------


class TestDiaryKGAdapterConstruction:
    def test_kg_starts_none(self, tmp_path):
        entry = _entry(tmp_path, KGKind.DIARY)
        adapter = DiaryKGAdapter(entry)
        assert adapter._kg is None


class TestDiaryKGAdapterLoad:
    def test_load_raises_import_error_when_diary_kg_missing(self, tmp_path):
        entry = _entry(tmp_path, KGKind.DIARY)
        adapter = DiaryKGAdapter(entry)
        with patch.dict("sys.modules", {"diary_kg": None, "diary_kg.kg": None}):
            with pytest.raises(ImportError, match="diary-kg is not installed"):
                adapter._load()

    def test_load_constructs_diarykg_with_source_file(self, tmp_path):
        entry = _entry(tmp_path, KGKind.DIARY)
        entry.metadata["source_file"] = "1893-04-12.txt"

        mock_diarykg_cls = MagicMock()
        mock_kg_module = MagicMock(DiaryKG=mock_diarykg_cls)

        adapter = DiaryKGAdapter(entry)
        with patch.dict("sys.modules", {"diary_kg": MagicMock(), "diary_kg.kg": mock_kg_module}):
            adapter._load()

        mock_diarykg_cls.assert_called_once_with(entry.repo_path, source_file="1893-04-12.txt")
        assert adapter._kg is mock_diarykg_cls.return_value

    def test_load_defaults_source_file_to_none(self, tmp_path):
        entry = _entry(tmp_path, KGKind.DIARY)
        mock_diarykg_cls = MagicMock()
        mock_kg_module = MagicMock(DiaryKG=mock_diarykg_cls)

        adapter = DiaryKGAdapter(entry)
        with patch.dict("sys.modules", {"diary_kg": MagicMock(), "diary_kg.kg": mock_kg_module}):
            adapter._load()

        mock_diarykg_cls.assert_called_once_with(entry.repo_path, source_file=None)


class TestDiaryKGAdapterIsAvailable:
    def test_unavailable_when_import_fails(self, tmp_path):
        entry = _entry(tmp_path, KGKind.DIARY, with_sqlite=True)
        with patch.dict("sys.modules", {"diary_kg": None}):
            adapter = DiaryKGAdapter(entry)
            assert adapter.is_available() is False

    def test_available_when_built(self, tmp_path):
        entry = _entry(tmp_path, KGKind.DIARY, with_sqlite=True)
        with patch.dict("sys.modules", {"diary_kg": MagicMock()}):
            adapter = DiaryKGAdapter(entry)
            assert adapter.is_available() is True

    def test_unavailable_when_not_built(self, tmp_path):
        entry = _entry(tmp_path, KGKind.DIARY)  # no sqlite
        with patch.dict("sys.modules", {"diary_kg": MagicMock()}):
            adapter = DiaryKGAdapter(entry)
            assert adapter.is_available() is False


class TestDiaryKGAdapterQuery:
    def test_query_returns_cross_hits(self, tmp_path):
        entry = _entry(tmp_path, KGKind.DIARY)
        mock_kg = MagicMock()
        mock_kg.query.return_value = [
            {
                "node_id": "chunk:1893-04-12:0",
                "timestamp": "1893-04-12",
                "source_file": "1893-04-12.txt",
                "score": 0.7,
                "summary": "Went to the market.",
                "metadata": {"occurred_start": "1893-04-12"},
            }
        ]
        adapter = DiaryKGAdapter(entry)
        adapter._kg = mock_kg

        hits = adapter.query("market", k=5)
        assert len(hits) == 1
        hit = hits[0]
        assert isinstance(hit, CrossHit)
        assert hit.kg_kind == KGKind.DIARY
        assert hit.name == "1893-04-12"
        assert hit.kind == "chunk"
        assert hit.source_path == "1893-04-12.txt"
        assert hit.metadata == {"occurred_start": "1893-04-12"}
        mock_kg.query.assert_called_once_with("market", k=5)

    def test_query_uses_source_file_when_no_timestamp(self, tmp_path):
        entry = _entry(tmp_path, KGKind.DIARY)
        mock_kg = MagicMock()
        mock_kg.query.return_value = [
            {"node_id": "a", "source_file": "diary.txt", "score": 0.5},
        ]
        adapter = DiaryKGAdapter(entry)
        adapter._kg = mock_kg

        hits = adapter.query("q")
        assert hits[0].name == "diary.txt"

    def test_query_respects_min_score(self, tmp_path):
        entry = _entry(tmp_path, KGKind.DIARY)
        mock_kg = MagicMock()
        mock_kg.query.return_value = [
            {"node_id": "a", "score": 0.9},
            {"node_id": "b", "score": 0.1},
        ]
        adapter = DiaryKGAdapter(entry)
        adapter._kg = mock_kg

        hits = adapter.query("q", min_score=0.5)
        assert [h.node_id for h in hits] == ["a"]

    def test_query_semantic_floor_discards_all(self, tmp_path):
        entry = _entry(tmp_path, KGKind.DIARY)
        mock_kg = MagicMock()
        mock_kg.query.return_value = [{"node_id": "a", "score": 0.2}]
        adapter = DiaryKGAdapter(entry)
        adapter._kg = mock_kg

        assert adapter.query("q", semantic_floor=0.5) == []


class TestDiaryKGAdapterPack:
    def test_pack_returns_cross_snippets(self, tmp_path):
        entry = _entry(tmp_path, KGKind.DIARY)
        mock_kg = MagicMock()
        mock_kg.pack.return_value = [
            {
                "node_id": "a",
                "source_file": "diary.txt",
                "content": "Went to market.",
                "score": 0.6,
            },
        ]
        adapter = DiaryKGAdapter(entry)
        adapter._kg = mock_kg

        snippets = adapter.pack("market", k=4)
        assert len(snippets) == 1
        s = snippets[0]
        assert isinstance(s, CrossSnippet)
        assert s.kg_kind == KGKind.DIARY
        assert s.source_path == "diary.txt"
        assert s.content == "Went to market."
        mock_kg.pack.assert_called_once_with("market", k=4)

    def test_pack_semantic_floor_discards_all(self, tmp_path):
        entry = _entry(tmp_path, KGKind.DIARY)
        mock_kg = MagicMock()
        mock_kg.pack.return_value = [{"node_id": "a", "content": "x", "score": 0.2}]
        adapter = DiaryKGAdapter(entry)
        adapter._kg = mock_kg

        assert adapter.pack("q", semantic_floor=0.5) == []


class TestDiaryKGAdapterStatsInfoAnalyze:
    def test_stats_delegates_to_kg(self, tmp_path):
        entry = _entry(tmp_path, KGKind.DIARY)
        mock_kg = MagicMock()
        mock_kg.stats.return_value = {"node_count": 5, "edge_count": 9}
        adapter = DiaryKGAdapter(entry)
        adapter._kg = mock_kg

        assert adapter.stats() == {"node_count": 5, "edge_count": 9}

    def test_info_delegates_to_kg(self, tmp_path):
        entry = _entry(tmp_path, KGKind.DIARY)
        mock_kg = MagicMock()
        mock_kg.info.return_value = {"entry_count": 42, "temporal_span": ["1893", "1894"]}
        adapter = DiaryKGAdapter(entry)
        adapter._kg = mock_kg

        assert adapter.info() == {"entry_count": 42, "temporal_span": ["1893", "1894"]}

    def test_analyze_delegates_to_kg(self, tmp_path):
        entry = _entry(tmp_path, KGKind.DIARY)
        mock_kg = MagicMock()
        mock_kg.analyze.return_value = "# DiaryKG Analysis\n\nAll good."
        adapter = DiaryKGAdapter(entry)
        adapter._kg = mock_kg

        assert adapter.analyze() == "# DiaryKG Analysis\n\nAll good."


class TestDiaryKGAdapterSnapshotMetrics:
    def test_collect_snapshot_metrics(self, tmp_path):
        entry = _entry(tmp_path, KGKind.DIARY)
        mock_kg = MagicMock()
        mock_kg.stats.return_value = {"node_count": 5, "edge_count": 9}
        adapter = DiaryKGAdapter(entry)
        adapter._kg = mock_kg

        assert adapter._collect_snapshot_metrics() == {"total_nodes": 5, "total_edges": 9}

    def test_collect_snapshot_metrics_graceful_on_error(self, tmp_path):
        entry = _entry(tmp_path, KGKind.DIARY)
        with patch.dict("sys.modules", {"diary_kg": None}):
            adapter = DiaryKGAdapter(entry)
            metrics = adapter._collect_snapshot_metrics()
        assert metrics == {}


# ---------------------------------------------------------------------------
# GutenbergKGAdapter -- full adapter behaviour (real DocKG-backed)
#
# GutenbergKGAdapter's is_available()/query()/pack() unavailable-and-empty
# branches are already pinned by TestGutenbergKGAdapterStub above. These
# classes cover the available/success branches plus the corpus-level status
# and snapshot methods that delegate to gutenberg_kg.corpus.
# ---------------------------------------------------------------------------


class TestGutenbergKGAdapterLoad:
    def test_load_raises_import_error_when_doc_kg_missing(self, tmp_path):
        entry = _entry(tmp_path, KGKind.GUTENBERG)
        adapter = GutenbergKGAdapter(entry)
        # "doc_kg.kg" is already cached in sys.modules by earlier tests in this
        # file that build a real DocKG -- __import__ resolves the dotted
        # "doc_kg.kg" target from sys.modules directly, so shadowing only the
        # top-level "doc_kg" entry is not enough to force the ImportError path.
        with patch.dict("sys.modules", {"doc_kg": None, "doc_kg.kg": None}):
            with pytest.raises(ImportError, match="doc-kg is not installed"):
                adapter._load()

    def test_load_is_idempotent(self, tmp_path):
        """Uses the real doc-kg, like TestDocKGAdapterLoad -- construction is cheap."""
        entry = _entry(tmp_path, KGKind.GUTENBERG, with_sqlite=True)
        adapter = GutenbergKGAdapter(entry)
        adapter._load()
        first = adapter._kg
        adapter._load()
        assert adapter._kg is first


class TestGutenbergKGAdapterIsAvailableImportError:
    def test_unavailable_when_doc_kg_import_fails(self, tmp_path):
        """The existing stub test patches the wrong module name (gutenberg_kg,
        not doc_kg) -- is_available() actually gates on doc_kg. Pin the real
        ImportError branch here.
        """
        entry = _entry(tmp_path, KGKind.GUTENBERG, with_sqlite=True)
        with patch.dict("sys.modules", {"doc_kg": None}):
            adapter = GutenbergKGAdapter(entry)
            assert adapter.is_available() is False


class TestGutenbergKGAdapterQuery:
    def _make_node(self, id="chunk:x:0", name="ch1", score=0.8, kind="chunk", file_path="foo.md"):
        return {
            "id": id,
            "name": name,
            "kind": kind,
            "text": "Some passage text",
            "file_path": file_path,
            "relevance": {"score": score},
        }

    def test_query_returns_cross_hits(self, tmp_path):
        entry = _entry(tmp_path, KGKind.GUTENBERG, with_sqlite=True)
        mock_result = MagicMock()
        mock_result.nodes = [self._make_node()]
        mock_kg = MagicMock()
        mock_kg.query.return_value = mock_result

        adapter = GutenbergKGAdapter(entry)
        adapter._kg = mock_kg

        hits = adapter.query("passage", k=5)
        assert len(hits) == 1
        hit = hits[0]
        assert isinstance(hit, CrossHit)
        assert hit.kg_kind == KGKind.GUTENBERG
        assert hit.score == 0.8
        assert hit.source_path == "foo.md"
        mock_kg.query.assert_called_once_with("passage", k=5)

    def test_query_respects_min_score(self, tmp_path):
        entry = _entry(tmp_path, KGKind.GUTENBERG, with_sqlite=True)
        mock_result = MagicMock()
        mock_result.nodes = [
            self._make_node(id="a", score=0.9),
            self._make_node(id="b", score=0.1),
        ]
        mock_kg = MagicMock()
        mock_kg.query.return_value = mock_result

        adapter = GutenbergKGAdapter(entry)
        adapter._kg = mock_kg

        hits = adapter.query("q", k=10, min_score=0.5)
        assert [h.node_id for h in hits] == ["a"]

    def test_query_semantic_floor_discards_all(self, tmp_path):
        entry = _entry(tmp_path, KGKind.GUTENBERG, with_sqlite=True)
        mock_result = MagicMock()
        mock_result.nodes = [self._make_node(score=0.2)]
        mock_kg = MagicMock()
        mock_kg.query.return_value = mock_result

        adapter = GutenbergKGAdapter(entry)
        adapter._kg = mock_kg

        assert adapter.query("q", semantic_floor=0.5) == []


class TestGutenbergKGAdapterPack:
    def test_pack_returns_cross_snippets(self, tmp_path):
        entry = _entry(tmp_path, KGKind.GUTENBERG, with_sqlite=True)
        node = {
            "id": "chunk:x:0",
            "file_path": "foo.md",
            "excerpt": "Some excerpt",
            "relevance": {"score": 0.7},
        }
        mock_pack = MagicMock()
        mock_pack.nodes = [node]
        mock_kg = MagicMock()
        mock_kg.pack.return_value = mock_pack

        adapter = GutenbergKGAdapter(entry)
        adapter._kg = mock_kg

        snippets = adapter.pack("q", k=4)
        assert len(snippets) == 1
        s = snippets[0]
        assert isinstance(s, CrossSnippet)
        assert s.kg_kind == KGKind.GUTENBERG
        assert s.content == "Some excerpt"
        assert s.score == 0.7
        mock_kg.pack.assert_called_once_with("q", k=4)

    def test_pack_skips_nodes_with_no_text(self, tmp_path):
        entry = _entry(tmp_path, KGKind.GUTENBERG, with_sqlite=True)
        mock_pack = MagicMock()
        mock_pack.nodes = [{"id": "a", "file_path": "f.md", "relevance": {"score": 0.5}}]
        mock_kg = MagicMock()
        mock_kg.pack.return_value = mock_pack

        adapter = GutenbergKGAdapter(entry)
        adapter._kg = mock_kg

        assert adapter.pack("q") == []

    def test_pack_semantic_floor_discards_all(self, tmp_path):
        entry = _entry(tmp_path, KGKind.GUTENBERG, with_sqlite=True)
        node = {"id": "a", "file_path": "f.md", "excerpt": "x", "relevance": {"score": 0.2}}
        mock_pack = MagicMock()
        mock_pack.nodes = [node]
        mock_kg = MagicMock()
        mock_kg.pack.return_value = mock_pack

        adapter = GutenbergKGAdapter(entry)
        adapter._kg = mock_kg

        assert adapter.pack("q", semantic_floor=0.5) == []


class TestGutenbergKGAdapterStats:
    def test_stats_returns_full_dict_on_success(self, tmp_path):
        entry = _entry(tmp_path, KGKind.GUTENBERG, with_sqlite=True)
        mock_kg = MagicMock()
        mock_kg.stats.return_value = {
            "node_count": 100,
            "edge_count": 400,
            "document_count": 3,
            "chunk_count": 80,
            "section_count": 10,
            "topic_count": 5,
            "entity_count": 20,
            "keyword_count": 30,
        }
        adapter = GutenbergKGAdapter(entry)
        adapter._kg = mock_kg

        stats = adapter.stats()
        assert stats["kind"] == "gutenberg"
        assert stats["available"] is True
        assert stats["node_count"] == 100
        assert stats["document_count"] == 3

    def test_stats_graceful_on_error(self, tmp_path):
        entry = _entry(tmp_path, KGKind.GUTENBERG, with_sqlite=True)
        mock_kg = MagicMock()
        mock_kg.stats.side_effect = RuntimeError("db gone")
        adapter = GutenbergKGAdapter(entry)
        adapter._kg = mock_kg

        stats = adapter.stats()
        assert stats["kind"] == "gutenberg"
        assert stats["available"] is True
        assert "error" in stats


class TestGutenbergKGAdapterAnalyze:
    def test_analyze_returns_markdown(self, tmp_path):
        entry = _entry(tmp_path, KGKind.GUTENBERG, with_sqlite=True)

        mock_analyzer_result = {
            "stats": {"total_nodes": 200, "total_edges": 1500},
            "semantic_coverage": {
                "topic_coverage": 0.95,
                "entity_coverage": 0.70,
                "keyword_coverage": 0.98,
            },
            "document_metrics": [
                {
                    "file_path": "books/foo.md",
                    "chunks": 10,
                    "sections": 5,
                    "refs_out": 3,
                    "semantic_links": 42,
                }
            ],
            "hot_chunks": [
                {"id": "chunk:1", "file_path": "books/foo.md", "semantic_links": 9, "references": 2}
            ],
            "issues": ["Low entity coverage"],
            "strengths": ["Strong topic coverage"],
        }
        mock_analyzer = MagicMock()
        mock_analyzer.run_analysis.return_value = mock_analyzer_result

        mock_kg = MagicMock()
        adapter = GutenbergKGAdapter(entry)
        adapter._kg = mock_kg

        mock_analysis_module = MagicMock()
        mock_analysis_module.DocKGAnalyzer = MagicMock(return_value=mock_analyzer)
        with patch("kg_rag.adapters.gutenberg_adapter.GutenbergKGAdapter._load"):
            with patch.dict(
                "sys.modules", {"doc_kg.dockg_thorough_analysis": mock_analysis_module}
            ):
                report = adapter.analyze()

        assert "# GutenbergKG Analysis Report" in report
        assert "200" in report
        assert "95.0%" in report
        assert "Low entity coverage" in report
        assert "Strong topic coverage" in report
        assert "chunk:1" in report

    def test_analyze_graceful_on_error(self, tmp_path):
        entry = _entry(tmp_path, KGKind.GUTENBERG, with_sqlite=True)
        mock_kg = MagicMock()
        adapter = GutenbergKGAdapter(entry)
        adapter._kg = mock_kg

        with patch("kg_rag.adapters.gutenberg_adapter.GutenbergKGAdapter._load"):
            with patch.dict("sys.modules", {"doc_kg.dockg_thorough_analysis": None}):
                report = adapter.analyze()

        assert "# GutenbergKG Analysis" in report
        assert "failed" in report.lower() or "error" in report.lower()


class TestGutenbergKGAdapterSnapshotMetrics:
    def test_collect_snapshot_metrics(self, tmp_path):
        entry = _entry(tmp_path, KGKind.GUTENBERG, with_sqlite=True)
        mock_store = MagicMock()
        mock_store.stats.return_value = {
            "total_nodes": 200,
            "total_edges": 1500,
            "node_counts": {"chunk": 100},
            "edge_counts": {"CONTAINS": 1500},
        }
        mock_kg = MagicMock()
        mock_kg.store = mock_store
        adapter = GutenbergKGAdapter(entry)
        adapter._kg = mock_kg

        metrics = adapter._collect_snapshot_metrics()
        assert metrics["total_nodes"] == 200
        assert metrics["node_counts"] == {"chunk": 100}

    def test_collect_snapshot_metrics_graceful_on_error(self, tmp_path):
        entry = _entry(tmp_path, KGKind.GUTENBERG, with_sqlite=True)
        mock_kg = MagicMock()
        mock_kg.store.stats.side_effect = RuntimeError("boom")
        adapter = GutenbergKGAdapter(entry)
        adapter._kg = mock_kg

        assert adapter._collect_snapshot_metrics() == {}


def _gutenberg_kg_sys_modules(corpus_module):
    """Build a sys.modules patch dict wiring gutenberg_kg.corpus correctly.

    ``import gutenberg_kg.corpus as _c`` resolves via attribute access on the
    already-imported ``gutenberg_kg`` package object (not a second sys.modules
    lookup), so the mock package must expose ``.corpus`` itself -- a bare
    ``{"gutenberg_kg.corpus": mock}`` patch is silently ignored by that import
    form. Confirmed empirically: a MagicMock package's auto-generated
    ``.corpus`` attribute is a *different* object than a separately
    constructed corpus mock.
    """
    pkg = MagicMock()
    pkg.corpus = corpus_module
    return {"gutenberg_kg": pkg, "gutenberg_kg.corpus": corpus_module}


class TestGutenbergKGAdapterCorpusHelpers:
    def test_corpus_lib_raises_when_not_installed(self, tmp_path):
        entry = _entry(tmp_path, KGKind.GUTENBERG)
        adapter = GutenbergKGAdapter(entry)
        with patch.dict("sys.modules", {"gutenberg_kg": None}):
            with pytest.raises(ImportError, match="gutenberg-kg is not installed"):
                adapter._corpus_lib()

    def test_corpus_lib_returns_module_when_installed(self, tmp_path):
        entry = _entry(tmp_path, KGKind.GUTENBERG)
        adapter = GutenbergKGAdapter(entry)
        mock_corpus_module = MagicMock()
        with patch.dict("sys.modules", _gutenberg_kg_sys_modules(mock_corpus_module)):
            assert adapter._corpus_lib() is mock_corpus_module

    def test_registry_defaults_to_home_kgrag(self, tmp_path):
        entry = _entry(tmp_path, KGKind.GUTENBERG)
        adapter = GutenbergKGAdapter(entry)
        assert adapter._registry(None) == Path.home() / ".kgrag" / "registry.sqlite"

    def test_registry_uses_override(self, tmp_path):
        entry = _entry(tmp_path, KGKind.GUTENBERG)
        adapter = GutenbergKGAdapter(entry)
        assert adapter._registry(str(tmp_path / "custom.sqlite")) == tmp_path / "custom.sqlite"

    def test_snapshots_dir(self, tmp_path):
        entry = _entry(tmp_path, KGKind.GUTENBERG)
        adapter = GutenbergKGAdapter(entry)
        assert adapter._snapshots_dir() == entry.repo_path / "corpus" / ".snapshots"


class TestGutenbergKGAdapterCorpusStatus:
    def test_returns_error_when_gutenberg_kg_not_installed(self, tmp_path):
        entry = _entry(tmp_path, KGKind.GUTENBERG)
        adapter = GutenbergKGAdapter(entry)
        with patch.dict("sys.modules", {"gutenberg_kg": None}):
            status = adapter.corpus_status()
        assert status["available"] is False
        assert "not installed" in status["error"]

    def test_returns_error_when_registry_missing(self, tmp_path):
        entry = _entry(tmp_path, KGKind.GUTENBERG)
        adapter = GutenbergKGAdapter(entry)
        mock_corpus_module = MagicMock()
        with patch.dict("sys.modules", _gutenberg_kg_sys_modules(mock_corpus_module)):
            status = adapter.corpus_status(registry_path=str(tmp_path / "missing.sqlite"))
        assert status["available"] is False
        assert "Registry not found" in status["error"]

    def test_returns_status_dict_on_success(self, tmp_path):
        entry = _entry(tmp_path, KGKind.GUTENBERG)
        registry = tmp_path / "registry.sqlite"
        registry.touch()
        mock_corpus_module = MagicMock()
        mock_corpus_module.corpus_status.return_value = {"kind": "corpus_status", "available": True}
        adapter = GutenbergKGAdapter(entry)
        with patch.dict("sys.modules", _gutenberg_kg_sys_modules(mock_corpus_module)):
            status = adapter.corpus_status(registry_path=str(registry))
        assert status == {"kind": "corpus_status", "available": True}
        mock_corpus_module.corpus_status.assert_called_once_with(
            registry, entry.repo_path, entry.repo_path / "corpus"
        )

    def test_returns_error_dict_on_exception(self, tmp_path):
        entry = _entry(tmp_path, KGKind.GUTENBERG)
        registry = tmp_path / "registry.sqlite"
        registry.touch()
        mock_corpus_module = MagicMock()
        mock_corpus_module.corpus_status.side_effect = RuntimeError("boom")
        adapter = GutenbergKGAdapter(entry)
        with patch.dict("sys.modules", _gutenberg_kg_sys_modules(mock_corpus_module)):
            status = adapter.corpus_status(registry_path=str(registry))
        assert status["available"] is False
        assert "boom" in status["error"]


class TestGutenbergKGAdapterSnapshots:
    def test_snapshot_save_raises_import_error(self, tmp_path):
        entry = _entry(tmp_path, KGKind.GUTENBERG)
        adapter = GutenbergKGAdapter(entry)
        with patch.dict("sys.modules", {"gutenberg_kg": None}):
            with pytest.raises(ImportError):
                adapter.snapshot_save()

    def test_snapshot_save_raises_file_not_found_when_registry_missing(self, tmp_path):
        entry = _entry(tmp_path, KGKind.GUTENBERG)
        adapter = GutenbergKGAdapter(entry)
        mock_corpus_module = MagicMock()
        with patch.dict("sys.modules", _gutenberg_kg_sys_modules(mock_corpus_module)):
            with pytest.raises(FileNotFoundError):
                adapter.snapshot_save(registry_path=str(tmp_path / "missing.sqlite"))

    def test_snapshot_save_returns_saved_snapshot(self, tmp_path):
        entry = _entry(tmp_path, KGKind.GUTENBERG)
        registry = tmp_path / "registry.sqlite"
        registry.touch()
        mock_corpus_module = MagicMock()
        mock_corpus_module.snapshot_save.return_value = (None, {"timestamp": "now"})
        adapter = GutenbergKGAdapter(entry)
        with patch.dict("sys.modules", _gutenberg_kg_sys_modules(mock_corpus_module)):
            snap = adapter.snapshot_save(registry_path=str(registry))
        assert snap == {"timestamp": "now"}

    def test_snapshot_list_returns_empty_when_not_installed(self, tmp_path):
        entry = _entry(tmp_path, KGKind.GUTENBERG)
        adapter = GutenbergKGAdapter(entry)
        with patch.dict("sys.modules", {"gutenberg_kg": None}):
            assert adapter.snapshot_list() == []

    def test_snapshot_list_delegates_to_corpus_lib(self, tmp_path):
        entry = _entry(tmp_path, KGKind.GUTENBERG)
        mock_corpus_module = MagicMock()
        mock_corpus_module.snapshot_list.return_value = [{"timestamp": "t1"}]
        adapter = GutenbergKGAdapter(entry)
        with patch.dict("sys.modules", _gutenberg_kg_sys_modules(mock_corpus_module)):
            result = adapter.snapshot_list()
        assert result == [{"timestamp": "t1"}]

    def test_snapshot_show_returns_empty_when_not_installed(self, tmp_path):
        entry = _entry(tmp_path, KGKind.GUTENBERG)
        adapter = GutenbergKGAdapter(entry)
        with patch.dict("sys.modules", {"gutenberg_kg": None}):
            assert adapter.snapshot_show() == {}

    def test_snapshot_show_delegates_to_corpus_lib(self, tmp_path):
        entry = _entry(tmp_path, KGKind.GUTENBERG)
        mock_corpus_module = MagicMock()
        mock_corpus_module.snapshot_show.return_value = {"timestamp": "t1"}
        adapter = GutenbergKGAdapter(entry)
        with patch.dict("sys.modules", _gutenberg_kg_sys_modules(mock_corpus_module)):
            result = adapter.snapshot_show("t1")
        assert result == {"timestamp": "t1"}

    def test_snapshot_diff_returns_error_when_not_installed(self, tmp_path):
        entry = _entry(tmp_path, KGKind.GUTENBERG)
        adapter = GutenbergKGAdapter(entry)
        with patch.dict("sys.modules", {"gutenberg_kg": None}):
            result = adapter.snapshot_diff()
        assert "error" in result

    def test_snapshot_diff_delegates_to_corpus_lib(self, tmp_path):
        entry = _entry(tmp_path, KGKind.GUTENBERG)
        mock_corpus_module = MagicMock()
        mock_corpus_module.snapshot_diff.return_value = {"a": "s1", "b": "s2", "totals": {}}
        adapter = GutenbergKGAdapter(entry)
        with patch.dict("sys.modules", _gutenberg_kg_sys_modules(mock_corpus_module)):
            result = adapter.snapshot_diff("s1", "s2")
        assert result == {"a": "s1", "b": "s2", "totals": {}}


# ---------------------------------------------------------------------------
# StubKGAdapter -- shared base for domain adapters whose backing library is
# not yet installed/released (PersonKG, VerseKG, LegalKG, DisulfideKG,
# PDBFileKG, IABookKG). PersonKGAdapter is used below as a concrete stand-in
# since it adds nothing over the base beyond _pkg_name/_kind, exactly like
# its siblings -- see the module docstring.
# ---------------------------------------------------------------------------


class TestStubKGAdapterIsAvailable:
    def test_unavailable_when_pkg_name_unset(self, tmp_path):
        """The base class itself ships with no _pkg_name configured."""
        entry = _entry(tmp_path, KGKind.CODE, with_sqlite=True)
        adapter = StubKGAdapter(entry)
        assert adapter.is_available() is False


class TestStubKGAdapterDefaultTryLoad:
    def test_load_raises_import_error_by_default(self, tmp_path):
        """A subclass that has not overridden _try_load() (not yet wired to a
        real backend) must fail loudly rather than silently no-op.
        """
        entry = _entry(tmp_path, KGKind.PERSON, with_sqlite=True)
        adapter = PersonKGAdapter(entry)
        with pytest.raises(ImportError, match="No backing library configured"):
            adapter._load()

    def test_load_is_idempotent_once_kg_is_set(self, tmp_path):
        entry = _entry(tmp_path, KGKind.PERSON, with_sqlite=True)
        adapter = PersonKGAdapter(entry)
        sentinel = object()
        adapter._kg = sentinel
        adapter._load()  # must not call _try_load() (which would raise)
        assert adapter._kg is sentinel


def _available_person_adapter(tmp_path, mock_kg):
    """Build a PersonKGAdapter whose _try_load() populates `mock_kg` as
    `self._kg`, standing in for a real backend library becoming available.
    """
    entry = _entry(tmp_path, KGKind.PERSON, with_sqlite=True)
    adapter = PersonKGAdapter(entry)
    adapter._try_load = lambda: setattr(adapter, "_kg", mock_kg)
    return adapter


class TestStubKGAdapterQuery:
    def test_query_returns_cross_hits_from_node(self, tmp_path):
        # NOTE: MagicMock(name=...) is a reserved kwarg that sets the mock's
        # own repr, not a settable ".name" attribute -- must assign it after
        # construction.
        node = MagicMock(id="p1", kind="person", description="bio", source="file.ged")
        node.name = "Alice"
        hit_obj = MagicMock(score=0.8, node=node)
        mock_kg = MagicMock()
        mock_kg.query.return_value = MagicMock(ranked_hits=[hit_obj])
        adapter = _available_person_adapter(tmp_path, mock_kg)

        with patch.dict("sys.modules", {"person_kg": MagicMock()}):
            hits = adapter.query("alice", k=5)

        assert len(hits) == 1
        hit = hits[0]
        assert isinstance(hit, CrossHit)
        assert hit.kg_kind == KGKind.PERSON
        assert hit.node_id == "p1"
        assert hit.name == "Alice"
        assert hit.score == 0.8
        assert hit.source_path == "file.ged"

    def test_query_respects_min_score(self, tmp_path):
        hit_a = MagicMock(
            score=0.9, node=MagicMock(id="a", kind="person", description="", source="")
        )
        hit_b = MagicMock(
            score=0.1, node=MagicMock(id="b", kind="person", description="", source="")
        )
        mock_kg = MagicMock()
        mock_kg.query.return_value = MagicMock(ranked_hits=[hit_a, hit_b])
        adapter = _available_person_adapter(tmp_path, mock_kg)

        with patch.dict("sys.modules", {"person_kg": MagicMock()}):
            hits = adapter.query("q", min_score=0.5)

        assert [h.node_id for h in hits] == ["a"]

    def test_query_semantic_floor_discards_all(self, tmp_path):
        hit_a = MagicMock(
            score=0.2, node=MagicMock(id="a", kind="person", description="", source="")
        )
        mock_kg = MagicMock()
        mock_kg.query.return_value = MagicMock(ranked_hits=[hit_a])
        adapter = _available_person_adapter(tmp_path, mock_kg)

        with patch.dict("sys.modules", {"person_kg": MagicMock()}):
            hits = adapter.query("q", semantic_floor=0.5)

        assert hits == []

    def test_query_returns_empty_on_backend_exception(self, tmp_path):
        mock_kg = MagicMock()
        mock_kg.query.side_effect = RuntimeError("boom")
        adapter = _available_person_adapter(tmp_path, mock_kg)

        with patch.dict("sys.modules", {"person_kg": MagicMock()}):
            hits = adapter.query("q")

        assert hits == []


class TestStubKGAdapterPack:
    def test_pack_returns_cross_snippets(self, tmp_path):
        snippet = MagicMock(node_id="p1", path="file.ged", text="0 @I1@ INDI", score=0.8)
        mock_kg = MagicMock()
        mock_kg.pack.return_value = MagicMock(snippets=[snippet])
        adapter = _available_person_adapter(tmp_path, mock_kg)

        with patch.dict("sys.modules", {"person_kg": MagicMock()}):
            snippets = adapter.pack("alice", k=4)

        assert len(snippets) == 1
        s = snippets[0]
        assert isinstance(s, CrossSnippet)
        assert s.kg_kind == KGKind.PERSON
        assert s.node_id == "p1"
        assert s.source_path == "file.ged"
        assert s.content == "0 @I1@ INDI"
        assert s.score == 0.8

    def test_pack_semantic_floor_discards_all(self, tmp_path):
        snippet = MagicMock(score=0.2)
        mock_kg = MagicMock()
        mock_kg.pack.return_value = MagicMock(snippets=[snippet])
        adapter = _available_person_adapter(tmp_path, mock_kg)

        with patch.dict("sys.modules", {"person_kg": MagicMock()}):
            snippets = adapter.pack("q", semantic_floor=0.5)

        assert snippets == []

    def test_pack_returns_empty_on_backend_exception(self, tmp_path):
        mock_kg = MagicMock()
        mock_kg.pack.side_effect = RuntimeError("boom")
        adapter = _available_person_adapter(tmp_path, mock_kg)

        with patch.dict("sys.modules", {"person_kg": MagicMock()}):
            snippets = adapter.pack("q")

        assert snippets == []


class TestStubKGAdapterStats:
    def test_stats_maps_node_and_edge_counts(self, tmp_path):
        mock_kg = MagicMock()
        mock_kg.stats.return_value = {"node_count": 12, "edge_count": 30}
        adapter = _available_person_adapter(tmp_path, mock_kg)

        with patch.dict("sys.modules", {"person_kg": MagicMock()}):
            stats = adapter.stats()

        assert stats == {
            "kind": "person",
            "status": "available",
            "node_count": 12,
            "edge_count": 30,
        }

    def test_stats_falls_back_to_total_nodes_and_edges(self, tmp_path):
        mock_kg = MagicMock()
        mock_kg.stats.return_value = {"total_nodes": 5, "total_edges": 9}
        adapter = _available_person_adapter(tmp_path, mock_kg)

        with patch.dict("sys.modules", {"person_kg": MagicMock()}):
            stats = adapter.stats()

        assert stats["node_count"] == 5
        assert stats["edge_count"] == 9

    def test_stats_graceful_on_backend_exception(self, tmp_path):
        mock_kg = MagicMock()
        mock_kg.stats.side_effect = RuntimeError("boom")
        adapter = _available_person_adapter(tmp_path, mock_kg)

        with patch.dict("sys.modules", {"person_kg": MagicMock()}):
            stats = adapter.stats()

        assert stats == {"kind": "person", "status": "available"}


class TestStubKGAdapterAnalyze:
    def test_analyze_returns_string_result_verbatim(self, tmp_path):
        mock_kg = MagicMock()
        mock_kg.analyze.return_value = "All biographical data indexed."
        adapter = _available_person_adapter(tmp_path, mock_kg)

        with patch.dict("sys.modules", {"person_kg": MagicMock()}):
            report = adapter.analyze()

        assert "# PersonKG Analysis Report" in report
        assert "All biographical data indexed." in report

    def test_analyze_renders_dict_result_as_json(self, tmp_path):
        mock_kg = MagicMock()
        mock_kg.analyze.return_value = {"people": 12}
        adapter = _available_person_adapter(tmp_path, mock_kg)

        with patch.dict("sys.modules", {"person_kg": MagicMock()}):
            report = adapter.analyze()

        assert "```json" in report
        assert '"people": 12' in report

    def test_analyze_falls_back_to_stats_summary_when_no_analyze_method(self, tmp_path):
        mock_kg = MagicMock(spec=["stats"])  # no analyze() method
        mock_kg.stats.return_value = {"node_count": 4, "edge_count": 6}
        adapter = _available_person_adapter(tmp_path, mock_kg)

        with patch.dict("sys.modules", {"person_kg": MagicMock()}):
            report = adapter.analyze()

        assert "## Summary" in report
        assert "**Node count:** 4" in report
        assert "**Edge count:** 6" in report

    def test_analyze_graceful_on_exception(self, tmp_path):
        mock_kg = MagicMock()
        mock_kg.analyze.side_effect = RuntimeError("boom")
        adapter = _available_person_adapter(tmp_path, mock_kg)

        with patch.dict("sys.modules", {"person_kg": MagicMock()}):
            report = adapter.analyze()

        assert "Analysis failed" in report


class TestStubKGAdapterSnapshotMetrics:
    def test_returns_unavailable_status_when_not_available(self, tmp_path):
        entry = _entry(tmp_path, KGKind.PERSON)  # no sqlite -> not built
        adapter = PersonKGAdapter(entry)
        with patch.dict("sys.modules", {"person_kg": MagicMock()}):
            metrics = adapter._collect_snapshot_metrics()
        assert metrics == {"status": "unavailable"}

    def test_returns_node_and_edge_totals_on_success(self, tmp_path):
        mock_kg = MagicMock()
        mock_kg.stats.return_value = {"total_nodes": 12, "total_edges": 30}
        adapter = _available_person_adapter(tmp_path, mock_kg)

        with patch.dict("sys.modules", {"person_kg": MagicMock()}):
            metrics = adapter._collect_snapshot_metrics()

        assert metrics == {"status": "available", "total_nodes": 12, "total_edges": 30}

    def test_falls_back_to_bare_status_on_exception(self, tmp_path):
        mock_kg = MagicMock()
        mock_kg.stats.side_effect = RuntimeError("boom")
        adapter = _available_person_adapter(tmp_path, mock_kg)

        with patch.dict("sys.modules", {"person_kg": MagicMock()}):
            metrics = adapter._collect_snapshot_metrics()

        assert metrics == {"status": "available"}
