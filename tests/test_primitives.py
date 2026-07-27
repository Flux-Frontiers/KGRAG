"""
test_primitives.py

Unit tests for kg_rag.primitives — KGKind, KGEntry, RegistryStats,
CrossHit, CrossQueryResult, CrossSnippet, CrossSnippetPack.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from kg_rag.primitives import (
    CrossHit,
    CrossQueryResult,
    CrossSnippet,
    CrossSnippetPack,
    KGEntry,
    KGKind,
    QueryScope,
    RegistryStats,
)

# ---------------------------------------------------------------------------
# KGKind
# ---------------------------------------------------------------------------


class TestKGKind:
    def test_values(self):
        assert KGKind.CODE.value == "code"
        assert KGKind.DOC.value == "doc"
        assert KGKind.META.value == "meta"
        assert KGKind.MEMORY.value == "memory"
        assert KGKind.GUTENBERG.value == "gutenberg"
        assert KGKind.IA.value == "ia"

    def test_from_str_valid(self):
        assert KGKind.from_str("code") == KGKind.CODE
        assert KGKind.from_str("doc") == KGKind.DOC
        assert KGKind.from_str("meta") == KGKind.META
        assert KGKind.from_str("memory") == KGKind.MEMORY
        assert KGKind.from_str("gutenberg") == KGKind.GUTENBERG
        assert KGKind.from_str("ia") == KGKind.IA

    def test_from_str_case_insensitive(self):
        assert KGKind.from_str("CODE") == KGKind.CODE
        assert KGKind.from_str("Doc") == KGKind.DOC
        assert KGKind.from_str("META") == KGKind.META
        assert KGKind.from_str("GUTENBERG") == KGKind.GUTENBERG
        assert KGKind.from_str("IA") == KGKind.IA

    def test_from_str_invalid(self):
        with pytest.raises(ValueError, match="Unknown KG kind"):
            KGKind.from_str("unknown")

    def test_str_subclass(self):
        # KGKind inherits from str — compare directly with string
        assert KGKind.CODE == "code"


# ---------------------------------------------------------------------------
# KGEntry
# ---------------------------------------------------------------------------


class TestKGEntry:
    def test_basic_construction(self, tmp_path):
        repo = tmp_path / "repo"
        venv = tmp_path / "venv"
        entry = KGEntry(name="test", kind=KGKind.CODE, repo_path=repo, venv_path=venv)
        assert entry.name == "test"
        assert entry.kind == KGKind.CODE
        assert isinstance(entry.id, str) and len(entry.id) == 36  # UUID

    def test_path_normalization(self, tmp_path):
        """__post_init__ must resolve paths to absolute Paths."""
        entry = KGEntry(
            name="n",
            kind=KGKind.DOC,
            repo_path=str(tmp_path / "r"),
            venv_path=str(tmp_path / "v"),
        )
        assert isinstance(entry.repo_path, Path)
        assert entry.repo_path.is_absolute()

    def test_sqlite_path_normalization(self, tmp_path):
        entry = KGEntry(
            name="n",
            kind=KGKind.CODE,
            repo_path=tmp_path,
            venv_path=tmp_path,
            sqlite_path=str(tmp_path / "graph.sqlite"),
        )
        assert isinstance(entry.sqlite_path, Path)
        assert entry.sqlite_path.is_absolute()

    def test_lancedb_path_normalization(self, tmp_path):
        entry = KGEntry(
            name="n",
            kind=KGKind.CODE,
            repo_path=tmp_path,
            venv_path=tmp_path,
            lancedb_path=str(tmp_path / "lancedb"),
        )
        assert isinstance(entry.lancedb_path, Path)

    def test_vectors_path_normalization(self, tmp_path):
        entry = KGEntry(
            name="n",
            kind=KGKind.CODE,
            repo_path=tmp_path,
            venv_path=tmp_path,
            vectors_path=str(tmp_path / "vectors.sqlite"),
        )
        assert isinstance(entry.vectors_path, Path)
        assert entry.vectors_path.is_absolute()

    def test_vectors_path_defaults_to_none(self, tmp_path):
        entry = KGEntry(name="n", kind=KGKind.CODE, repo_path=tmp_path, venv_path=tmp_path)
        assert entry.vectors_path is None

    def test_kind_coercion_from_string(self, tmp_path):
        entry = KGEntry(name="n", kind="doc", repo_path=tmp_path, venv_path=tmp_path)
        assert entry.kind == KGKind.DOC

    def test_is_built_false_no_paths(self, tmp_path):
        entry = KGEntry(name="n", kind=KGKind.CODE, repo_path=tmp_path, venv_path=tmp_path)
        assert entry.is_built is False

    def test_is_built_false_path_missing(self, tmp_path):
        entry = KGEntry(
            name="n",
            kind=KGKind.CODE,
            repo_path=tmp_path,
            venv_path=tmp_path,
            sqlite_path=tmp_path / "nonexistent.sqlite",
        )
        assert entry.is_built is False

    def test_is_built_true_sqlite_exists(self, tmp_path):
        db = tmp_path / "graph.sqlite"
        db.touch()
        entry = KGEntry(
            name="n",
            kind=KGKind.CODE,
            repo_path=tmp_path,
            venv_path=tmp_path,
            sqlite_path=db,
        )
        assert entry.is_built is True

    def test_is_built_true_lancedb_exists(self, tmp_path):
        ldb = tmp_path / "lancedb"
        ldb.mkdir()
        entry = KGEntry(
            name="n",
            kind=KGKind.CODE,
            repo_path=tmp_path,
            venv_path=tmp_path,
            lancedb_path=ldb,
        )
        assert entry.is_built is True

    def test_is_built_true_vectors_exists(self, tmp_path):
        """A sqlite-vec store alone is evidence of a built KG."""
        vec = tmp_path / "vectors.sqlite"
        vec.touch()
        entry = KGEntry(
            name="n",
            kind=KGKind.CODE,
            repo_path=tmp_path,
            venv_path=tmp_path,
            vectors_path=vec,
        )
        assert entry.is_built is True

    def test_is_built_false_vectors_missing(self, tmp_path):
        entry = KGEntry(
            name="n",
            kind=KGKind.CODE,
            repo_path=tmp_path,
            venv_path=tmp_path,
            vectors_path=tmp_path / "nonexistent-vectors.sqlite",
        )
        assert entry.is_built is False

    def test_label(self, tmp_path):
        entry = KGEntry(name="mykg", kind=KGKind.META, repo_path=tmp_path, venv_path=tmp_path)
        assert entry.label == "mykg (meta)"

    def test_unique_ids(self, tmp_path):
        e1 = KGEntry(name="a", kind=KGKind.CODE, repo_path=tmp_path, venv_path=tmp_path)
        e2 = KGEntry(name="b", kind=KGKind.CODE, repo_path=tmp_path, venv_path=tmp_path)
        assert e1.id != e2.id

    def test_default_fields(self, tmp_path):
        entry = KGEntry(name="n", kind=KGKind.CODE, repo_path=tmp_path, venv_path=tmp_path)
        assert entry.version == "unknown"
        assert entry.tags == []
        assert entry.metadata == {}
        assert entry.sqlite_path is None
        assert entry.lancedb_path is None


# ---------------------------------------------------------------------------
# RegistryStats
# ---------------------------------------------------------------------------


class TestRegistryStats:
    def test_construction(self, tmp_path):
        stats = RegistryStats(
            total=5,
            by_kind={"code": 3, "doc": 2},
            built=2,
            registry_path=tmp_path / "registry.sqlite",
        )
        assert stats.total == 5
        assert stats.by_kind["code"] == 3
        assert stats.built == 2


# ---------------------------------------------------------------------------
# CrossHit
# ---------------------------------------------------------------------------


class TestCrossHit:
    def test_construction(self):
        hit = CrossHit(
            kg_name="mykg",
            kg_kind=KGKind.CODE,
            node_id="fn:src/foo.py:bar",
            name="bar",
            kind="function",
            score=0.92,
            summary="Does something",
            source_path="src/foo.py",
        )
        assert hit.score == 0.92
        assert hit.kg_kind == KGKind.CODE

    def test_defaults(self):
        hit = CrossHit(
            kg_name="kg",
            kg_kind=KGKind.DOC,
            node_id="x",
            name="x",
            kind="chunk",
            score=0.5,
        )
        assert hit.summary == ""
        assert hit.source_path == ""


# ---------------------------------------------------------------------------
# CrossQueryResult
# ---------------------------------------------------------------------------


class TestCrossQueryResult:
    def test_construction(self):
        hit = CrossHit(
            kg_name="a", kg_kind=KGKind.CODE, node_id="n", name="n", kind="fn", score=1.0
        )
        result = CrossQueryResult(
            query="foo",
            hits=[hit],
            by_kg={"a": [hit]},
            total_hits=1,
            kgs_queried=1,
        )
        assert result.total_hits == 1
        assert "a" in result.by_kg


# ---------------------------------------------------------------------------
# CrossSnippet
# ---------------------------------------------------------------------------


class TestCrossSnippet:
    def test_construction(self):
        s = CrossSnippet(
            kg_name="kg",
            kg_kind=KGKind.CODE,
            node_id="fn:src/foo.py:bar",
            source_path="src/foo.py",
            content="def bar(): pass",
            score=0.8,
            lineno=10,
            end_lineno=12,
        )
        assert s.lineno == 10
        assert s.content == "def bar(): pass"

    def test_defaults(self):
        s = CrossSnippet(kg_name="k", kg_kind=KGKind.DOC, node_id="x", source_path="p", content="c")
        assert s.score == 0.0
        assert s.lineno is None
        assert s.end_lineno is None


# ---------------------------------------------------------------------------
# CrossSnippetPack.render
# ---------------------------------------------------------------------------


class TestCrossSnippetPackRender:
    def _make_pack(self, snippets):
        return CrossSnippetPack(
            query="test query",
            snippets=snippets,
            total_tokens_approx=100,
            kgs_queried=1,
        )

    def test_render_empty(self):
        pack = self._make_pack([])
        rendered = pack.render()
        assert "test query" in rendered

    def test_render_with_snippet_no_lineno(self):
        s = CrossSnippet(
            kg_name="mykg",
            kg_kind=KGKind.CODE,
            node_id="fn:src/foo.py:bar",
            source_path="src/foo.py",
            content="def bar(x: int) -> int:\n    return x + 1",
            score=0.9,
        )
        rendered = self._make_pack([s]).render()
        assert "code:mykg" in rendered
        assert "src/foo.py" in rendered
        assert "def bar" in rendered
        # No lineno — should not have colon after path
        assert "src/foo.py:" not in rendered

    def test_render_with_lineno(self):
        s = CrossSnippet(
            kg_name="mykg",
            kg_kind=KGKind.CODE,
            node_id="fn:src/foo.py:bar",
            source_path="src/foo.py",
            content="def bar(x: int) -> int:\n    return x + 1",
            score=0.9,
            lineno=5,
            end_lineno=7,
        )
        rendered = self._make_pack([s]).render()
        assert "src/foo.py:5-7" in rendered

    def test_render_filters_short_snippets(self):
        snippets = [
            CrossSnippet(
                kg_name="mykg",
                kg_kind=KGKind.CODE,
                node_id="x",
                source_path="src/foo.py",
                content="see",  # <30 chars — should be filtered
                score=0.9,
            ),
            CrossSnippet(
                kg_name="mykg",
                kg_kind=KGKind.CODE,
                node_id="y",
                source_path="src/foo.py",
                content="def real_function():\n    pass  # substantial content",
                score=0.8,
            ),
        ]
        rendered = self._make_pack(snippets).render()
        assert "see" not in rendered
        assert "real_function" in rendered

    def test_render_multiple_snippets(self):
        snippets = [
            CrossSnippet(
                kg_name="a",
                kg_kind=KGKind.CODE,
                node_id="x",
                source_path="a.py",
                content="def alpha():\n    return 'this is enough content to pass the filter'",
                score=0.9,
            ),
            CrossSnippet(
                kg_name="b",
                kg_kind=KGKind.DOC,
                node_id="y",
                source_path="b.md",
                content="This section describes the beta feature in detail for users.",
                score=0.7,
            ),
        ]
        rendered = self._make_pack(snippets).render()
        assert "alpha" in rendered
        assert "beta feature" in rendered
        assert "code:a" in rendered
        assert "doc:b" in rendered


# ---------------------------------------------------------------------------
# QueryScope
# ---------------------------------------------------------------------------


class TestQueryScope:
    def test_empty_scope_is_falsy(self):
        scope = QueryScope()
        assert scope.is_empty is True
        assert bool(scope) is False

    def test_non_empty_scope_is_truthy(self):
        assert bool(QueryScope(source_path_prefixes=("sci-fi/",))) is True
        assert bool(QueryScope(node_kinds=("chunk",))) is True
        assert bool(QueryScope(metadata_eq={"book": "Moby Dick"})) is True

    def test_list_inputs_normalised_to_tuples(self):
        scope = QueryScope(source_path_prefixes=["a/", "b/"], node_kinds=["chunk"])
        assert scope.source_path_prefixes == ("a/", "b/")
        assert scope.node_kinds == ("chunk",)

    def test_is_hashable(self):
        # frozen + tuple-normalised → usable as dict key / in a set
        scope = QueryScope(source_path_prefixes=["a/"], node_kinds=["chunk"])
        assert len({scope, scope}) == 1

    def test_matches_prefix_in_scope(self):
        scope = QueryScope(source_path_prefixes=("science-fiction/",))
        assert scope.matches(source_path="science-fiction/Dune.md") is True

    def test_matches_prefix_out_of_scope(self):
        scope = QueryScope(source_path_prefixes=("science-fiction/",))
        assert scope.matches(source_path="philosophy/Ethics.md") is False

    def test_matches_any_of_multiple_prefixes(self):
        scope = QueryScope(source_path_prefixes=("a/", "b/"))
        assert scope.matches(source_path="b/x.md") is True

    def test_matches_kind_in_scope(self):
        scope = QueryScope(node_kinds=("chunk", "section"))
        assert scope.matches(source_path="x", kind="section") is True

    def test_matches_kind_out_of_scope(self):
        scope = QueryScope(node_kinds=("chunk",))
        assert scope.matches(source_path="x", kind="topic") is False

    def test_unknown_kind_not_rejected(self):
        # A None kind (e.g. a snippet with no kind field) must not be dropped
        # by a node_kinds constraint.
        scope = QueryScope(node_kinds=("chunk",))
        assert scope.matches(source_path="x", kind=None) is True

    def test_matches_requires_all_constraints(self):
        scope = QueryScope(source_path_prefixes=("a/",), node_kinds=("chunk",))
        assert scope.matches(source_path="a/x.md", kind="chunk") is True
        assert scope.matches(source_path="a/x.md", kind="topic") is False
        assert scope.matches(source_path="b/x.md", kind="chunk") is False

    def test_empty_scope_matches_everything(self):
        scope = QueryScope()
        assert scope.matches(source_path="anything", kind="whatever") is True
