"""
test_cmd_query.py

Tests for --scope routing in the kgrag query and pack commands.

Covers:
  - _known_scopes: builds correct human-readable scope list
  - _resolve_scoped_query: corpus-first fallback chain, error message
  - _resolve_scoped_pack: mirrors query routing for pack
  - CLI kgrag query --scope: routing, mutual exclusion with --kind, min-score pass-through
  - CLI kgrag pack  --scope: routing, mutual exclusion with --kind
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import click
import pytest
from click.testing import CliRunner

from kg_rag.cli.cmd_query import _known_scopes, _resolve_scoped_pack, _resolve_scoped_query
from kg_rag.cli.main import cli
from kg_rag.primitives import (
    CorpusEntry,
    CrossQueryResult,
    CrossSnippetPack,
    KGKind,
    PersonCorpusEntry,
)

# ---------------------------------------------------------------------------
# Shared factories
# ---------------------------------------------------------------------------


def _query_result(kgs_queried: int = 1) -> CrossQueryResult:
    return CrossQueryResult(
        query="test",
        hits=[],
        by_kg={},
        total_hits=0,
        kgs_queried=kgs_queried,
    )


def _pack_result(kgs_queried: int = 1) -> CrossSnippetPack:
    return CrossSnippetPack(
        query="test",
        snippets=[],
        total_tokens_approx=0,
        kgs_queried=kgs_queried,
    )


def _mock_kg(
    corpus_hit: str | None = None,
    person_hit: str | None = None,
    corpora: list[str] | None = None,
    persons: list[str] | None = None,
) -> MagicMock:
    """Build a mock KGRAG instance pre-wired for scope routing tests.

    :param corpus_hit: Name of the corpus that query_corpus/pack_corpus accepts.
        All other names raise KeyError.
    :param person_hit: Name of the person corpus that query_person/pack_person
        accepts. All other names raise KeyError.
    :param corpora: Names returned by corpus_registry.list().
    :param persons: Names returned by person_registry.list().
    """
    kg = MagicMock()
    kg.__enter__ = MagicMock(return_value=kg)
    kg.__exit__ = MagicMock(return_value=False)

    def _corpus_q(name, q, **kw):
        if corpus_hit and name == corpus_hit:
            return _query_result()
        raise KeyError(name)

    def _person_q(name, q, **kw):
        if person_hit and name == person_hit:
            return _query_result()
        raise KeyError(name)

    def _corpus_p(name, q, **kw):
        if corpus_hit and name == corpus_hit:
            return _pack_result()
        raise KeyError(name)

    def _person_p(name, q, **kw):
        if person_hit and name == person_hit:
            return _pack_result()
        raise KeyError(name)

    kg.query_corpus.side_effect = _corpus_q
    kg.query_person.side_effect = _person_q
    kg.pack_corpus.side_effect = _corpus_p
    kg.pack_person.side_effect = _person_p
    kg.query.return_value = _query_result()
    kg.pack.return_value = _pack_result()

    kg.corpus_registry.list.return_value = [CorpusEntry(name=n) for n in (corpora or [])]
    kg.person_registry.list.return_value = [PersonCorpusEntry(name=n) for n in (persons or [])]

    return kg


def _invoke_query(args: list[str], kg: MagicMock) -> object:
    """Invoke 'kgrag query' with a patched KGRAG class."""
    with patch("kg_rag.cli.cmd_query.KGRAG", return_value=kg):
        return CliRunner().invoke(cli, ["query"] + args, catch_exceptions=False)


def _invoke_pack(args: list[str], kg: MagicMock) -> object:
    """Invoke 'kgrag pack' with a patched KGRAG class."""
    with patch("kg_rag.cli.cmd_query.KGRAG", return_value=kg):
        return CliRunner().invoke(cli, ["pack"] + args, catch_exceptions=False)


# ---------------------------------------------------------------------------
# _known_scopes
# ---------------------------------------------------------------------------


class TestKnownScopes:
    def test_empty_registries_returns_sentinel(self):
        kg = _mock_kg(corpora=[], persons=[])
        assert _known_scopes(kg) == "(none registered)"

    def test_corpus_names_quoted(self):
        kg = _mock_kg(corpora=["alpha", "beta"], persons=[])
        out = _known_scopes(kg)
        assert "'alpha'" in out
        assert "'beta'" in out

    def test_person_names_quoted(self):
        kg = _mock_kg(corpora=[], persons=["alice", "bob"])
        out = _known_scopes(kg)
        assert "'alice'" in out
        assert "'bob'" in out

    def test_mixed_names_sorted(self):
        kg = _mock_kg(corpora=["zz-corpus"], persons=["aa-person"])
        out = _known_scopes(kg)
        assert out.index("aa-person") < out.index("zz-corpus")

    def test_no_duplicate_separators(self):
        kg = _mock_kg(corpora=["c1"], persons=["p1"])
        out = _known_scopes(kg)
        assert out.count("(none") == 0


# ---------------------------------------------------------------------------
# _resolve_scoped_query
# ---------------------------------------------------------------------------


class TestResolveScopedQuery:
    def test_corpus_match_skips_person(self):
        kg = _mock_kg(corpus_hit="my-corpus", person_hit="alice")
        _resolve_scoped_query(kg, "my-corpus", "q", k=5, min_score=0.0, semantic_floor=0.0)
        kg.query_corpus.assert_called_once_with(
            "my-corpus", "q", k=5, min_score=0.0, semantic_floor=0.0
        )
        kg.query_person.assert_not_called()

    def test_falls_back_to_person_when_corpus_absent(self):
        kg = _mock_kg(corpus_hit=None, person_hit="alice")
        _resolve_scoped_query(kg, "alice", "q", k=5, min_score=0.0, semantic_floor=0.0)
        kg.query_corpus.assert_called_once()
        kg.query_person.assert_called_once_with(
            "alice", "q", k=5, min_score=0.0, semantic_floor=0.0
        )

    def test_raises_usage_error_when_both_absent(self):
        kg = _mock_kg(
            corpus_hit=None,
            person_hit=None,
            corpora=["known-c"],
            persons=["known-p"],
        )
        with pytest.raises(click.UsageError) as exc:
            _resolve_scoped_query(kg, "ghost", "q", k=5, min_score=0.0, semantic_floor=0.0)
        msg = str(exc.value)
        assert "'ghost'" in msg
        assert "'known-c'" in msg
        assert "'known-p'" in msg

    def test_min_score_forwarded_to_corpus(self):
        kg = _mock_kg(corpus_hit="c")
        _resolve_scoped_query(kg, "c", "q", k=8, min_score=0.45, semantic_floor=0.0)
        assert kg.query_corpus.call_args.kwargs["min_score"] == pytest.approx(0.45)

    def test_min_score_forwarded_to_person(self):
        kg = _mock_kg(corpus_hit=None, person_hit="alice")
        _resolve_scoped_query(kg, "alice", "q", k=8, min_score=0.3, semantic_floor=0.0)
        assert kg.query_person.call_args.kwargs["min_score"] == pytest.approx(0.3)

    def test_k_forwarded_to_corpus(self):
        kg = _mock_kg(corpus_hit="c")
        _resolve_scoped_query(kg, "c", "q", k=12, min_score=0.0, semantic_floor=0.0)
        assert kg.query_corpus.call_args.kwargs["k"] == 12

    def test_semantic_floor_forwarded_to_corpus(self):
        kg = _mock_kg(corpus_hit="c")
        _resolve_scoped_query(kg, "c", "q", k=8, min_score=0.0, semantic_floor=0.55)
        assert kg.query_corpus.call_args.kwargs["semantic_floor"] == pytest.approx(0.55)

    def test_semantic_floor_forwarded_to_person(self):
        kg = _mock_kg(corpus_hit=None, person_hit="alice")
        _resolve_scoped_query(kg, "alice", "q", k=8, min_score=0.0, semantic_floor=0.6)
        assert kg.query_person.call_args.kwargs["semantic_floor"] == pytest.approx(0.6)

    def test_returns_query_result(self):
        kg = _mock_kg(corpus_hit="c")
        result = _resolve_scoped_query(kg, "c", "q", k=8, min_score=0.0, semantic_floor=0.0)
        assert isinstance(result, CrossQueryResult)


# ---------------------------------------------------------------------------
# _resolve_scoped_pack
# ---------------------------------------------------------------------------


class TestResolveScopedPack:
    def test_corpus_match_skips_person(self):
        kg = _mock_kg(corpus_hit="my-corpus", person_hit="alice")
        _resolve_scoped_pack(kg, "my-corpus", "q", k=5, context=3, semantic_floor=0.0)
        kg.pack_corpus.assert_called_once_with("my-corpus", "q", k=5, context=3, semantic_floor=0.0)
        kg.pack_person.assert_not_called()

    def test_falls_back_to_person_when_corpus_absent(self):
        kg = _mock_kg(corpus_hit=None, person_hit="alice")
        _resolve_scoped_pack(kg, "alice", "q", k=5, context=3, semantic_floor=0.0)
        kg.pack_corpus.assert_called_once()
        kg.pack_person.assert_called_once_with("alice", "q", k=5, context=3, semantic_floor=0.0)

    def test_raises_usage_error_when_both_absent(self):
        kg = _mock_kg(
            corpus_hit=None,
            person_hit=None,
            corpora=["c1"],
            persons=["p1"],
        )
        with pytest.raises(click.UsageError) as exc:
            _resolve_scoped_pack(kg, "ghost", "q", k=8, context=5, semantic_floor=0.0)
        msg = str(exc.value)
        assert "'ghost'" in msg
        assert "'c1'" in msg
        assert "'p1'" in msg

    def test_context_forwarded_to_corpus(self):
        kg = _mock_kg(corpus_hit="c")
        _resolve_scoped_pack(kg, "c", "q", k=8, context=7, semantic_floor=0.0)
        assert kg.pack_corpus.call_args.kwargs["context"] == 7

    def test_semantic_floor_forwarded_to_corpus(self):
        kg = _mock_kg(corpus_hit="c")
        _resolve_scoped_pack(kg, "c", "q", k=8, context=5, semantic_floor=0.55)
        assert kg.pack_corpus.call_args.kwargs["semantic_floor"] == pytest.approx(0.55)

    def test_semantic_floor_forwarded_to_person(self):
        kg = _mock_kg(corpus_hit=None, person_hit="alice")
        _resolve_scoped_pack(kg, "alice", "q", k=8, context=5, semantic_floor=0.6)
        assert kg.pack_person.call_args.kwargs["semantic_floor"] == pytest.approx(0.6)

    def test_returns_pack_result(self):
        kg = _mock_kg(corpus_hit="c")
        result = _resolve_scoped_pack(kg, "c", "q", k=8, context=5, semantic_floor=0.0)
        assert isinstance(result, CrossSnippetPack)


# ---------------------------------------------------------------------------
# CLI: kgrag query --scope
# ---------------------------------------------------------------------------


class TestCLIQueryScope:
    def test_scope_routes_to_corpus(self):
        kg = _mock_kg(corpus_hit="my-corpus")
        result = _invoke_query(["hello", "--scope", "my-corpus"], kg)
        assert result.exit_code == 0
        kg.query_corpus.assert_called_once()
        kg.query_person.assert_not_called()
        kg.query.assert_not_called()

    def test_scope_falls_back_to_person(self):
        kg = _mock_kg(corpus_hit=None, person_hit="alice")
        result = _invoke_query(["hello", "--scope", "alice"], kg)
        assert result.exit_code == 0
        kg.query_person.assert_called_once()
        kg.query.assert_not_called()

    def test_scope_unknown_exits_nonzero(self):
        kg = _mock_kg(
            corpus_hit=None,
            person_hit=None,
            corpora=["valid-c"],
            persons=[],
        )
        # catch_exceptions=False would raise; allow click to handle UsageError
        with patch("kg_rag.cli.cmd_query.KGRAG", return_value=kg):
            result = CliRunner().invoke(cli, ["query", "hello", "--scope", "ghost"])
        assert result.exit_code != 0
        assert "ghost" in result.output

    def test_scope_and_kind_mutually_exclusive(self):
        kg = _mock_kg(corpus_hit="c")
        with patch("kg_rag.cli.cmd_query.KGRAG", return_value=kg):
            result = CliRunner().invoke(cli, ["query", "hello", "--scope", "c", "--kind", "code"])
        assert result.exit_code != 0
        assert "mutually exclusive" in result.output

    def test_scope_passes_min_score_to_corpus(self):
        kg = _mock_kg(corpus_hit="my-corpus")
        _invoke_query(["hello", "--scope", "my-corpus", "--min-score", "0.4"], kg)
        assert kg.query_corpus.call_args.kwargs["min_score"] == pytest.approx(0.4)

    def test_no_scope_uses_flat_registry(self):
        kg = _mock_kg()
        result = _invoke_query(["hello"], kg)
        assert result.exit_code == 0
        kg.query.assert_called_once()
        kg.query_corpus.assert_not_called()
        kg.query_person.assert_not_called()

    def test_no_scope_with_kind_filters_flat_registry(self):
        kg = _mock_kg()
        result = _invoke_query(["hello", "--kind", "code"], kg)
        assert result.exit_code == 0
        kg.query.assert_called_once()
        _, kwargs = kg.query.call_args
        assert kwargs["kinds"] == [KGKind.CODE]

    def test_help_shows_scope_option(self):
        result = CliRunner().invoke(cli, ["query", "--help"])
        assert "--scope" in result.output

    def test_help_shows_routing_explanation(self):
        result = CliRunner().invoke(cli, ["query", "--help"])
        assert "Scope routing" in result.output


# ---------------------------------------------------------------------------
# CLI: kgrag pack --scope
# ---------------------------------------------------------------------------


class TestCLIPackScope:
    def test_scope_routes_to_corpus(self):
        kg = _mock_kg(corpus_hit="my-corpus")
        result = _invoke_pack(["hello", "--scope", "my-corpus"], kg)
        assert result.exit_code == 0
        kg.pack_corpus.assert_called_once()
        kg.pack_person.assert_not_called()
        kg.pack.assert_not_called()

    def test_scope_falls_back_to_person(self):
        kg = _mock_kg(corpus_hit=None, person_hit="alice")
        result = _invoke_pack(["hello", "--scope", "alice"], kg)
        assert result.exit_code == 0
        kg.pack_person.assert_called_once()
        kg.pack.assert_not_called()

    def test_scope_unknown_exits_nonzero(self):
        kg = _mock_kg(corpus_hit=None, person_hit=None, corpora=["c1"])
        with patch("kg_rag.cli.cmd_query.KGRAG", return_value=kg):
            result = CliRunner().invoke(cli, ["pack", "hello", "--scope", "ghost"])
        assert result.exit_code != 0
        assert "ghost" in result.output

    def test_scope_and_kind_mutually_exclusive(self):
        kg = _mock_kg(corpus_hit="c")
        with patch("kg_rag.cli.cmd_query.KGRAG", return_value=kg):
            result = CliRunner().invoke(cli, ["pack", "hello", "--scope", "c", "--kind", "doc"])
        assert result.exit_code != 0
        assert "mutually exclusive" in result.output

    def test_no_scope_uses_flat_registry(self):
        kg = _mock_kg()
        result = _invoke_pack(["hello"], kg)
        assert result.exit_code == 0
        kg.pack.assert_called_once()
        kg.pack_corpus.assert_not_called()
        kg.pack_person.assert_not_called()

    def test_help_shows_scope_option(self):
        result = CliRunner().invoke(cli, ["pack", "--help"])
        assert "--scope" in result.output

    def test_help_shows_routing_explanation(self):
        result = CliRunner().invoke(cli, ["pack", "--help"])
        assert "Scope routing" in result.output
