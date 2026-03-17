"""
tests/test_query.py

Tests for {{ClassName}} query and pack.
"""

from __future__ import annotations

import pytest
from pathlib import Path

from {{name}}.module import {{ClassName}}


@pytest.fixture
def kg(tmp_path: Path) -> {{ClassName}}:
    # TODO: populate tmp_path with representative sample source files
    instance = {{ClassName}}(
        repo_root=tmp_path,
        db_path=tmp_path / ".{{name}}" / "graph.sqlite",
        lancedb_path=tmp_path / ".{{name}}" / "lancedb",
    )
    instance.build(wipe=True)
    return instance


def test_build_produces_nodes(kg):
    s = kg.stats()
    assert s.node_count > 0, "build should produce at least one node"


def test_query_returns_results(kg):
    # Use a term likely to match something in the fixture corpus
    result = kg.query("TODO: replace with domain-relevant query term", k=5)
    assert result is not None
    assert isinstance(result.nodes, list)


def test_query_scores_in_range(kg):
    result = kg.query("TODO: replace with domain-relevant query term", k=5)
    for node in result.nodes:
        assert 0.0 <= node.get("score", 0.0) <= 1.0


def test_pack_returns_snippets(kg):
    pack = kg.pack("TODO: replace with domain-relevant query term", k=3)
    assert pack is not None
    assert isinstance(pack.snippets, list)


def test_pack_snippets_have_content(kg):
    pack = kg.pack("TODO: replace with domain-relevant query term", k=3)
    for snippet in pack.snippets:
        assert snippet.content, "each snippet should have non-empty content"
        assert snippet.node_id, "each snippet must have a node_id"


def test_analyze_returns_markdown(kg):
    report = kg.analyze()
    assert report.startswith("#"), "analyze() must return Markdown starting with a heading"
    assert "{{ClassName}}" in report or "Analysis" in report


def test_snapshot_round_trip(kg):
    snap = kg.snapshot_save(version="0.0.1")
    assert snap is not None
    listing = kg.snapshot_list(limit=5)
    assert len(listing) >= 1
    shown = kg.snapshot_show(key="latest")
    assert shown is not None
