"""Which retrieved hits the image flow uses.

A live run on 2026-11-22 ranked three copies of one code node first, each with
no source text. The rewrite, given nothing, described neurons. These pin the
rule: hits with no text and repeats of one node are dropped before the cut.
"""

from __future__ import annotations

import pytest

from kg_rag.imagine import ImagineError, imagine, passages_text, rewrite_system, usable_passages
from kg_rag.primitives import CrossSnippet, KGKind


def _snip(kg: str, kind: KGKind, node: str, content: str, score: float) -> CrossSnippet:
    return CrossSnippet(
        kg_name=kg, kg_kind=kind, node_id=node, source_path="", content=content, score=score
    )


def _empty_first() -> list[CrossSnippet]:
    return [
        _snip("app-code", KGKind.CODE, "m:a.py:A.run", "", 0.9),
        _snip("app-code", KGKind.CODE, "m:a.py:A.run", "", 0.9),
        _snip("app-code", KGKind.CODE, "m:a.py:A.run", "   \n", 0.9),
        _snip("lib-code", KGKind.CODE, "fn:b.py:walk", "def walk(graph): ...", 0.8),
        _snip("lib-code", KGKind.CODE, "fn:b.py:walk", "def walk(graph): ...", 0.8),
        _snip("diary", KGKind.DIARY, "chunk:1", "He came home late.", 0.7),
        _snip("docs", KGKind.DOC, "chunk:2", "The walk visits each node once.", 0.6),
    ]


def test_usable_passages_drops_empty_text_and_repeated_nodes() -> None:
    kept = usable_passages(_empty_first())
    assert [s.node_id for s in kept] == ["fn:b.py:walk", "chunk:1", "chunk:2"]


def test_usable_passages_cuts_after_dropping() -> None:
    kept = usable_passages(_empty_first(), 2)
    assert [s.node_id for s in kept] == ["fn:b.py:walk", "chunk:1"]


def test_the_rewrite_prompt_follows_the_first_hit_with_text() -> None:
    from kg_utils.synthesis import IMAGE_REWRITE_TECHNICAL_SYSTEM

    kept = usable_passages(_empty_first())
    assert rewrite_system(kept) == IMAGE_REWRITE_TECHNICAL_SYSTEM
    assert passages_text(kept).startswith("def walk(graph): ...")


def test_imagine_uses_only_hits_with_text() -> None:
    result = imagine(
        query="walk a graph",
        retrieve=lambda _q: (_empty_first(), 3),
        max_passages=2,
        rewrite=False,
        render=False,
    )
    assert result.prompt == "def walk(graph): ...\n\nHe came home late."


def test_imagine_with_no_text_at_all_is_an_error() -> None:
    hits = _empty_first()[:3]
    with pytest.raises(ImagineError, match="No passages found"):
        imagine(query="walk a graph", retrieve=lambda _q: (hits, 1), rewrite=False, render=False)
