"""
test_cli_retrieval.py

Tests for kg_rag.cli.retrieval.retrieve_snippets, the federated retrieval
shared by ``kgrag synthesize`` and later commands.

Registries, corpora and the KGRAG orchestrator are real; only the KG
adapters are faked, since a real adapter needs a built KG in its own venv.
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

import click
import pytest

from kg_rag.cli.retrieval import retrieve_snippets
from kg_rag.corpus_registry import CorpusRegistry
from kg_rag.orchestrator import KGRAG
from kg_rag.primitives import CorpusEntry, CrossSnippet, KGEntry, KGKind
from kg_rag.registry import KGRegistry

_SCORES = {"code-a": 0.5, "doc-b": 0.9, "diary-c": 0.7}


class _FakeAdapter:
    """Stands in for a built KG: two snippets per pack, scored by KG."""

    def __init__(self, entry: KGEntry, embedder: object = None) -> None:
        self.entry = entry

    def is_available(self) -> bool:
        return True

    def pack(self, q: str, k: int = 8, context: int = 5, **_: object) -> list[CrossSnippet]:
        top = _SCORES[self.entry.name]
        return [
            CrossSnippet(
                kg_name=self.entry.name,
                kg_kind=self.entry.kind,
                node_id=f"{self.entry.name}-{i}",
                source_path=f"{self.entry.name}/{i}.txt",
                content=f"{q} from {self.entry.name} #{i}",
                score=round(top - i * 0.01, 4),
            )
            for i in range(2)
        ]


@pytest.fixture
def reg_path(tmp_path: Path) -> Path:
    """A registry with code, doc and diary KGs and a corpus holding all three."""
    db = tmp_path / "registry.sqlite"
    kinds = {"code-a": KGKind.CODE, "doc-b": KGKind.DOC, "diary-c": KGKind.DIARY}
    with KGRegistry(db_path=db) as reg:
        ids = []
        for name, kind in kinds.items():
            repo = tmp_path / name
            (repo / ".venv").mkdir(parents=True)
            sqlite = repo / "graph.sqlite"
            sqlite.touch()
            entry = reg.register(
                KGEntry(
                    name=name,
                    kind=kind,
                    repo_path=repo,
                    venv_path=repo / ".venv",
                    sqlite_path=sqlite,
                )
            )
            ids.append(entry.id)
    with CorpusRegistry(db_path=db) as creg:
        creg.create(CorpusEntry(name="mixed", kg_ids=ids))
        creg.create(CorpusEntry(name="empty"))
    return db


def _retrieve(reg_path: Path, **kwargs):
    opts = {
        "k": 8,
        "kinds": None,
        "corpus": None,
        "reg_path": reg_path,
        "context_lines": 5,
        "max_context": 20,
    }
    opts.update(kwargs)
    with (
        patch("kg_rag.adapters.make_adapter", _FakeAdapter),
        patch("kg_rag.orchestrator.make_adapter", _FakeAdapter),
        KGRAG(registry_path=reg_path) as kg,
    ):
        return retrieve_snippets(kg, "whale", **opts)


@pytest.mark.parametrize("corpus", [None, "mixed"])
class TestRetrieveSnippets:
    def test_ranked_by_score_with_kg_kind(self, reg_path, corpus):
        snippets, kgs_queried = _retrieve(reg_path, corpus=corpus)
        assert kgs_queried == 3
        assert [s.score for s in snippets] == sorted((s.score for s in snippets), reverse=True)
        assert {(s.kg_name, s.kg_kind) for s in snippets} == {
            ("code-a", KGKind.CODE),
            ("doc-b", KGKind.DOC),
            ("diary-c", KGKind.DIARY),
        }

    def test_max_context_keeps_top_n(self, reg_path, corpus):
        snippets, _ = _retrieve(reg_path, corpus=corpus, max_context=2)
        assert [s.node_id for s in snippets] == ["doc-b-0", "doc-b-1"]

    def test_kind_filter(self, reg_path, corpus):
        snippets, _ = _retrieve(reg_path, corpus=corpus, kinds=[KGKind.CODE])
        assert {s.kg_kind for s in snippets} == {KGKind.CODE}


def test_corpus_kgs_queried_counts_members_before_kind_filter(reg_path):
    _, kgs_queried = _retrieve(reg_path, corpus="mixed", kinds=[KGKind.CODE])
    assert kgs_queried == 3


def test_unknown_corpus_raises(reg_path):
    with pytest.raises(click.ClickException, match="Corpus not found: 'nope'"):
        _retrieve(reg_path, corpus="nope")


def test_empty_corpus_exits_zero(reg_path, capsys):
    with pytest.raises(SystemExit) as exc:
        _retrieve(reg_path, corpus="empty")
    assert exc.value.code == 0
    assert "has no registered KGs" in capsys.readouterr().out
