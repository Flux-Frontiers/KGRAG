"""
test_orchestrator.py

Unit tests for kg_rag.orchestrator.KGRAG.
Adapters are mocked — no real KG libraries needed.
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from kg_rag.orchestrator import KGRAG
from kg_rag.primitives import (
    CrossHit,
    CrossQueryResult,
    CrossSnippet,
    CrossSnippetPack,
    KGEntry,
    KGKind,
)
from kg_rag.registry import KGRegistry

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_entry(tmp_path, name: str, kind: KGKind = KGKind.CODE) -> KGEntry:
    repo = tmp_path / name
    repo.mkdir(exist_ok=True)
    venv = repo / ".venv"
    venv.mkdir(exist_ok=True)
    return KGEntry(name=name, kind=kind, repo_path=repo, venv_path=venv)


def _mock_adapter(hits=None, snippets=None, available=True):
    adapter = MagicMock()
    adapter.is_available.return_value = available
    adapter.query.return_value = hits or []
    adapter.pack.return_value = snippets or []
    adapter.stats.return_value = {"node_count": 10, "kind": "code"}
    return adapter


def _make_hit(kg_name: str, score: float = 0.9) -> CrossHit:
    return CrossHit(
        kg_name=kg_name,
        kg_kind=KGKind.CODE,
        node_id="fn:src/foo.py:bar",
        name="bar",
        kind="function",
        score=score,
    )


def _make_snippet(kg_name: str, score: float = 0.9) -> CrossSnippet:
    return CrossSnippet(
        kg_name=kg_name,
        kg_kind=KGKind.CODE,
        node_id="fn:src/foo.py:bar",
        source_path="src/foo.py",
        content="def bar(): pass",
        score=score,
    )


# ---------------------------------------------------------------------------
# Construction & context manager
# ---------------------------------------------------------------------------


class TestKGRAGInit:
    def test_creates_registry(self, tmp_path):
        kgrag = KGRAG(registry_path=tmp_path / "reg.sqlite")
        assert isinstance(kgrag.registry, KGRegistry)
        kgrag.close()

    def test_context_manager(self, tmp_path):
        with KGRAG(registry_path=tmp_path / "reg.sqlite") as kgrag:
            assert isinstance(kgrag.registry, KGRegistry)


# ---------------------------------------------------------------------------
# _resolve_entries
# ---------------------------------------------------------------------------


class TestResolveEntries:
    def test_returns_all_entries(self, tmp_path):
        with KGRAG(registry_path=tmp_path / "reg.sqlite") as kgrag:
            e1 = _make_entry(tmp_path, "a", KGKind.CODE)
            e2 = _make_entry(tmp_path, "b", KGKind.DOC)
            kgrag.registry.register(e1)
            kgrag.registry.register(e2)
            entries = kgrag._resolve_entries()
            assert len(entries) == 2

    def test_filters_by_kind(self, tmp_path):
        with KGRAG(registry_path=tmp_path / "reg.sqlite") as kgrag:
            kgrag.registry.register(_make_entry(tmp_path, "a", KGKind.CODE))
            kgrag.registry.register(_make_entry(tmp_path, "b", KGKind.DOC))
            entries = kgrag._resolve_entries(kinds=[KGKind.CODE])
            assert len(entries) == 1
            assert entries[0].kind == KGKind.CODE


# ---------------------------------------------------------------------------
# _get_adapter
# ---------------------------------------------------------------------------


class TestGetAdapter:
    def test_skips_unavailable_adapter_permissive(self, tmp_path):
        with KGRAG(registry_path=tmp_path / "reg.sqlite", strict=False) as kgrag:
            entry = _make_entry(tmp_path, "a")
            unavailable = _mock_adapter(available=False)
            with patch("kg_rag.orchestrator.make_adapter", return_value=unavailable):
                result = kgrag._get_adapter(entry)
            assert result is None

    def test_raises_for_unavailable_adapter_strict(self, tmp_path):
        with KGRAG(registry_path=tmp_path / "reg.sqlite", strict=True) as kgrag:
            entry = _make_entry(tmp_path, "a")
            unavailable = _mock_adapter(available=False)
            with patch("kg_rag.orchestrator.make_adapter", return_value=unavailable):
                with pytest.raises(ImportError, match="not available"):
                    kgrag._get_adapter(entry)

    def test_caches_adapter(self, tmp_path):
        with KGRAG(registry_path=tmp_path / "reg.sqlite") as kgrag:
            entry = _make_entry(tmp_path, "a")
            mock = _mock_adapter(available=True)
            with patch("kg_rag.orchestrator.make_adapter", return_value=mock) as factory:
                kgrag._get_adapter(entry)
                kgrag._get_adapter(entry)
            # make_adapter called only once — second call uses cache
            factory.assert_called_once()


# ---------------------------------------------------------------------------
# query
# ---------------------------------------------------------------------------


class TestKGRAGQuery:
    def test_empty_registry_returns_empty_result(self, tmp_path):
        with KGRAG(registry_path=tmp_path / "reg.sqlite") as kgrag:
            result = kgrag.query("anything")
        assert isinstance(result, CrossQueryResult)
        assert result.total_hits == 0
        assert result.kgs_queried == 0

    def test_query_aggregates_hits(self, tmp_path):
        with KGRAG(registry_path=tmp_path / "reg.sqlite") as kgrag:
            e1 = _make_entry(tmp_path, "kg1")
            e2 = _make_entry(tmp_path, "kg2")
            kgrag.registry.register(e1)
            kgrag.registry.register(e2)

            hits1 = [_make_hit("kg1", score=0.9)]
            hits2 = [_make_hit("kg2", score=0.7)]
            adapters = {e1.name: _mock_adapter(hits=hits1), e2.name: _mock_adapter(hits=hits2)}

            def _fake_adapter(entry):
                return adapters[entry.name]

            with patch("kg_rag.orchestrator.make_adapter", side_effect=_fake_adapter):
                result = kgrag.query("test query", k=5)

        assert result.total_hits == 2
        assert result.kgs_queried == 2
        # Globally ranked: highest score first
        assert result.hits[0].score >= result.hits[1].score

    def test_query_skips_unavailable(self, tmp_path):
        with KGRAG(registry_path=tmp_path / "reg.sqlite") as kgrag:
            e = _make_entry(tmp_path, "a")
            kgrag.registry.register(e)
            unavailable = _mock_adapter(available=False)
            with patch("kg_rag.orchestrator.make_adapter", return_value=unavailable):
                result = kgrag.query("test")
        assert result.kgs_queried == 0

    def test_query_filters_by_kinds(self, tmp_path):
        with KGRAG(registry_path=tmp_path / "reg.sqlite") as kgrag:
            code_entry = _make_entry(tmp_path, "code-kg", KGKind.CODE)
            doc_entry = _make_entry(tmp_path, "doc-kg", KGKind.DOC)
            kgrag.registry.register(code_entry)
            kgrag.registry.register(doc_entry)

            adapters = {
                code_entry.name: _mock_adapter(hits=[_make_hit("code-kg")]),
                doc_entry.name: _mock_adapter(hits=[_make_hit("doc-kg")]),
            }
            with patch("kg_rag.orchestrator.make_adapter", side_effect=lambda e: adapters[e.name]):
                result = kgrag.query("test", kinds=[KGKind.CODE])

        assert result.kgs_queried == 1

    def test_query_permissive_skips_failing_kg(self, tmp_path):
        with KGRAG(registry_path=tmp_path / "reg.sqlite", strict=False) as kgrag:
            e = _make_entry(tmp_path, "a")
            kgrag.registry.register(e)
            failing = _mock_adapter(available=True)
            failing.query.side_effect = RuntimeError("boom")
            with patch("kg_rag.orchestrator.make_adapter", return_value=failing):
                result = kgrag.query("test")
        assert result.total_hits == 0

    def test_query_strict_raises_on_failing_kg(self, tmp_path):
        with KGRAG(registry_path=tmp_path / "reg.sqlite", strict=True) as kgrag:
            e = _make_entry(tmp_path, "a")
            kgrag.registry.register(e)
            failing = _mock_adapter(available=True)
            failing.query.side_effect = RuntimeError("boom")
            with patch("kg_rag.orchestrator.make_adapter", return_value=failing):
                with pytest.raises(RuntimeError, match="boom"):
                    kgrag.query("test")


# ---------------------------------------------------------------------------
# pack
# ---------------------------------------------------------------------------


class TestKGRAGPack:
    def test_pack_returns_snippet_pack(self, tmp_path):
        with KGRAG(registry_path=tmp_path / "reg.sqlite") as kgrag:
            e = _make_entry(tmp_path, "a")
            kgrag.registry.register(e)
            snippets = [_make_snippet("a", 0.8)]
            mock = _mock_adapter(snippets=snippets)
            with patch("kg_rag.orchestrator.make_adapter", return_value=mock):
                pack = kgrag.pack("query", k=5, context=3)

        assert isinstance(pack, CrossSnippetPack)
        assert len(pack.snippets) == 1
        assert pack.kgs_queried == 1
        mock.pack.assert_called_once_with("query", k=5, context=3)

    def test_pack_empty_registry(self, tmp_path):
        with KGRAG(registry_path=tmp_path / "reg.sqlite") as kgrag:
            pack = kgrag.pack("q")
        assert pack.kgs_queried == 0
        assert pack.snippets == []

    def test_pack_ranked_by_score(self, tmp_path):
        with KGRAG(registry_path=tmp_path / "reg.sqlite") as kgrag:
            e1 = _make_entry(tmp_path, "a")
            e2 = _make_entry(tmp_path, "b")
            kgrag.registry.register(e1)
            kgrag.registry.register(e2)
            adapters = {
                e1.name: _mock_adapter(snippets=[_make_snippet("a", 0.5)]),
                e2.name: _mock_adapter(snippets=[_make_snippet("b", 0.9)]),
            }
            with patch("kg_rag.orchestrator.make_adapter", side_effect=lambda e: adapters[e.name]):
                pack = kgrag.pack("q")

        assert pack.snippets[0].score >= pack.snippets[1].score

    def test_pack_approx_tokens_nonzero(self, tmp_path):
        with KGRAG(registry_path=tmp_path / "reg.sqlite") as kgrag:
            e = _make_entry(tmp_path, "a")
            kgrag.registry.register(e)
            s = CrossSnippet(
                kg_name="a",
                kg_kind=KGKind.CODE,
                node_id="x",
                source_path="f.py",
                content="def foo(): pass # this has several words",
                score=0.5,
            )
            mock = _mock_adapter(snippets=[s])
            with patch("kg_rag.orchestrator.make_adapter", return_value=mock):
                pack = kgrag.pack("q")

        assert pack.total_tokens_approx > 0


# ---------------------------------------------------------------------------
# stats
# ---------------------------------------------------------------------------


class TestKGRAGStats:
    def test_stats_available(self, tmp_path):
        with KGRAG(registry_path=tmp_path / "reg.sqlite") as kgrag:
            e = _make_entry(tmp_path, "a")
            kgrag.registry.register(e)
            mock = _mock_adapter(available=True)
            with patch("kg_rag.orchestrator.make_adapter", return_value=mock):
                stats = kgrag.stats()
        assert "a" in stats
        assert stats["a"]["available"] is True

    def test_stats_unavailable(self, tmp_path):
        with KGRAG(registry_path=tmp_path / "reg.sqlite") as kgrag:
            e = _make_entry(tmp_path, "a")
            kgrag.registry.register(e)
            mock = _mock_adapter(available=False)
            with patch("kg_rag.orchestrator.make_adapter", return_value=mock):
                stats = kgrag.stats()
        assert stats["a"]["available"] is False

    def test_stats_graceful_on_exception(self, tmp_path):
        with KGRAG(registry_path=tmp_path / "reg.sqlite") as kgrag:
            e = _make_entry(tmp_path, "a")
            kgrag.registry.register(e)
            mock = _mock_adapter(available=True)
            mock.stats.side_effect = RuntimeError("db error")
            with patch("kg_rag.orchestrator.make_adapter", return_value=mock):
                stats = kgrag.stats()
        assert stats["a"]["available"] is False
        assert "error" in stats["a"]
