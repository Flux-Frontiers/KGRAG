"""
test_cmd_corpus.py

Tests for ``kgrag corpus ...`` and ``kgrag corpus person ...`` — corpus and
person-corpus management commands (create/delete/add/remove/list/info/query/pack).

The query/pack commands build a :class:`~kg_rag.orchestrator.KGRAG` instance via a
*local* import inside the command body (``from kg_rag.orchestrator import KGRAG``),
so there is no ``kg_rag.cli.cmd_corpus.KGRAG`` name to patch — the mock target is
``kg_rag.orchestrator.KGRAG`` itself (see tests/test_cmd_query.py for the same
pattern applied to the top-level ``kgrag query``/``kgrag pack`` commands).
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

from click.testing import CliRunner

from kg_rag.cli.main import cli
from kg_rag.corpus_registry import CorpusRegistry
from kg_rag.person_registry import PersonCorpusRegistry
from kg_rag.primitives import (
    CorpusEntry,
    CrossHit,
    CrossQueryResult,
    CrossSnippet,
    CrossSnippetPack,
    KGEntry,
    KGKind,
    PersonCorpusEntry,
)
from kg_rag.registry import KGRegistry

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _reg_opt(tmp_path: Path) -> list[str]:
    return ["--registry", str(tmp_path / "registry.sqlite")]


def _reg_db(tmp_path: Path) -> Path:
    return tmp_path / "registry.sqlite"


def _make_kg(tmp_path: Path, name: str, kind: KGKind = KGKind.CODE) -> KGEntry:
    repo = tmp_path / name
    repo.mkdir(exist_ok=True)
    return KGEntry(name=name, kind=kind, repo_path=repo, venv_path=repo / ".venv")


def _register_kg(tmp_path: Path, *entries: KGEntry) -> list[KGEntry]:
    """Register KGEntry fixtures; return the post-insert entries (with real ids)."""
    with KGRegistry(db_path=_reg_db(tmp_path)) as reg:
        return [reg.register(e) for e in entries]


def _make_corpus(tmp_path: Path, entry: CorpusEntry) -> CorpusEntry:
    with CorpusRegistry(db_path=_reg_db(tmp_path)) as reg:
        return reg.create(entry)


def _make_person(tmp_path: Path, entry: PersonCorpusEntry) -> PersonCorpusEntry:
    with PersonCorpusRegistry(db_path=_reg_db(tmp_path)) as reg:
        return reg.create(entry)


def _empty_query_result(kgs_queried: int = 1) -> CrossQueryResult:
    return CrossQueryResult(query="q", hits=[], by_kg={}, total_hits=0, kgs_queried=kgs_queried)


def _empty_pack_result(kgs_queried: int = 1) -> CrossSnippetPack:
    return CrossSnippetPack(query="q", snippets=[], total_tokens_approx=0, kgs_queried=kgs_queried)


def _mock_orch(
    corpus_hit: str | None = None,
    person_hit: str | None = None,
    query_result: CrossQueryResult | None = None,
    pack_result: CrossSnippetPack | None = None,
) -> MagicMock:
    """A mock KGRAG orchestrator wired for corpus/person query & pack routing.

    Names matching ``corpus_hit``/``person_hit`` succeed and return the supplied
    (or a default empty) result; every other name raises ``KeyError``, mirroring
    the orchestrator's real not-found behavior.
    """
    kg = MagicMock()
    kg.__enter__ = MagicMock(return_value=kg)
    kg.__exit__ = MagicMock(return_value=False)

    def _corpus_q(name, q, **kw):
        if corpus_hit and name == corpus_hit:
            return query_result or _empty_query_result()
        raise KeyError(f"Corpus {name!r} not found.")

    def _person_q(name, q, **kw):
        if person_hit and name == person_hit:
            return query_result or _empty_query_result()
        raise KeyError(f"Person corpus {name!r} not found.")

    def _corpus_p(name, q, **kw):
        if corpus_hit and name == corpus_hit:
            return pack_result or _empty_pack_result()
        raise KeyError(f"Corpus {name!r} not found.")

    def _person_p(name, q, **kw):
        if person_hit and name == person_hit:
            return pack_result or _empty_pack_result()
        raise KeyError(f"Person corpus {name!r} not found.")

    kg.query_corpus.side_effect = _corpus_q
    kg.query_person.side_effect = _person_q
    kg.pack_corpus.side_effect = _corpus_p
    kg.pack_person.side_effect = _person_p
    return kg


# ---------------------------------------------------------------------------
# corpus create
# ---------------------------------------------------------------------------


class TestCorpusCreate:
    def test_creates_empty_corpus(self, tmp_path):
        result = CliRunner().invoke(cli, ["corpus", "create", "my-project"] + _reg_opt(tmp_path))
        assert result.exit_code == 0, result.output
        assert "Created corpus" in result.output
        assert "my-project" in result.output

        with CorpusRegistry(db_path=_reg_db(tmp_path)) as reg:
            entry = reg.get("my-project")
        assert entry is not None
        assert entry.kg_ids == []

    def test_creates_with_kgs_desc_and_tags(self, tmp_path):
        kg1, kg2 = _register_kg(tmp_path, _make_kg(tmp_path, "kg1"), _make_kg(tmp_path, "kg2"))
        result = CliRunner().invoke(
            cli,
            [
                "corpus",
                "create",
                "research",
                "--kg",
                "kg1",
                "--kg",
                "kg2",
                "--desc",
                "Research project KGs",
                "--tag",
                "alpha",
            ]
            + _reg_opt(tmp_path),
        )
        assert result.exit_code == 0, result.output
        assert "Desc: Research project KGs" in result.output
        assert f"+ kg1 ({kg1.id})" in result.output
        assert f"+ kg2 ({kg2.id})" in result.output

        with CorpusRegistry(db_path=_reg_db(tmp_path)) as reg:
            entry = reg.get("research")
        assert set(entry.kg_ids) == {kg1.id, kg2.id}
        assert entry.tags == ["alpha"]

    def test_unknown_kg_ref_exits_nonzero(self, tmp_path):
        result = CliRunner().invoke(
            cli, ["corpus", "create", "bad", "--kg", "ghost"] + _reg_opt(tmp_path)
        )
        assert result.exit_code == 1
        assert "KG not found" in result.output
        assert "ghost" in result.output

        with CorpusRegistry(db_path=_reg_db(tmp_path)) as reg:
            assert reg.get("bad") is None


# ---------------------------------------------------------------------------
# corpus delete
# ---------------------------------------------------------------------------


class TestCorpusDelete:
    def test_delete_with_yes_flag(self, tmp_path):
        _make_corpus(tmp_path, CorpusEntry(name="gone"))
        result = CliRunner().invoke(cli, ["corpus", "delete", "gone", "--yes"] + _reg_opt(tmp_path))
        assert result.exit_code == 0, result.output
        assert "Deleted corpus" in result.output
        with CorpusRegistry(db_path=_reg_db(tmp_path)) as reg:
            assert reg.get("gone") is None

    def test_delete_confirm_accepted(self, tmp_path):
        _make_corpus(tmp_path, CorpusEntry(name="confirm-me"))
        result = CliRunner().invoke(
            cli, ["corpus", "delete", "confirm-me"] + _reg_opt(tmp_path), input="y\n"
        )
        assert result.exit_code == 0, result.output
        with CorpusRegistry(db_path=_reg_db(tmp_path)) as reg:
            assert reg.get("confirm-me") is None

    def test_delete_confirm_declined_aborts(self, tmp_path):
        _make_corpus(tmp_path, CorpusEntry(name="keep-me"))
        result = CliRunner().invoke(
            cli, ["corpus", "delete", "keep-me"] + _reg_opt(tmp_path), input="n\n"
        )
        assert result.exit_code != 0  # click.confirm(abort=True) raises Abort
        with CorpusRegistry(db_path=_reg_db(tmp_path)) as reg:
            assert reg.get("keep-me") is not None

    def test_delete_not_found(self, tmp_path):
        result = CliRunner().invoke(
            cli, ["corpus", "delete", "ghost", "--yes"] + _reg_opt(tmp_path)
        )
        assert result.exit_code == 1
        assert "Corpus not found" in result.output


# ---------------------------------------------------------------------------
# corpus add / remove
# ---------------------------------------------------------------------------


class TestCorpusAdd:
    def test_adds_kg(self, tmp_path):
        (kg,) = _register_kg(tmp_path, _make_kg(tmp_path, "kg1"))
        _make_corpus(tmp_path, CorpusEntry(name="proj"))
        result = CliRunner().invoke(cli, ["corpus", "add", "proj", "kg1"] + _reg_opt(tmp_path))
        assert result.exit_code == 0, result.output
        assert "Added" in result.output
        with CorpusRegistry(db_path=_reg_db(tmp_path)) as reg:
            assert kg.id in reg.get("proj").kg_ids

    def test_kg_not_found(self, tmp_path):
        _make_corpus(tmp_path, CorpusEntry(name="proj"))
        result = CliRunner().invoke(cli, ["corpus", "add", "proj", "ghost"] + _reg_opt(tmp_path))
        assert result.exit_code == 1
        assert "KG not found" in result.output

    def test_corpus_not_found(self, tmp_path):
        _register_kg(tmp_path, _make_kg(tmp_path, "kg1"))
        result = CliRunner().invoke(
            cli, ["corpus", "add", "ghost-corpus", "kg1"] + _reg_opt(tmp_path)
        )
        assert result.exit_code == 1
        assert "Corpus not found" in result.output


class TestCorpusRemove:
    def test_removes_kg(self, tmp_path):
        (kg,) = _register_kg(tmp_path, _make_kg(tmp_path, "kg1"))
        _make_corpus(tmp_path, CorpusEntry(name="proj", kg_ids=[kg.id]))
        result = CliRunner().invoke(cli, ["corpus", "remove", "proj", "kg1"] + _reg_opt(tmp_path))
        assert result.exit_code == 0, result.output
        assert "Removed" in result.output
        with CorpusRegistry(db_path=_reg_db(tmp_path)) as reg:
            assert kg.id not in reg.get("proj").kg_ids

    def test_kg_not_found(self, tmp_path):
        _make_corpus(tmp_path, CorpusEntry(name="proj"))
        result = CliRunner().invoke(cli, ["corpus", "remove", "proj", "ghost"] + _reg_opt(tmp_path))
        assert result.exit_code == 1
        assert "KG not found" in result.output

    def test_corpus_not_found(self, tmp_path):
        _register_kg(tmp_path, _make_kg(tmp_path, "kg1"))
        result = CliRunner().invoke(
            cli, ["corpus", "remove", "ghost-corpus", "kg1"] + _reg_opt(tmp_path)
        )
        assert result.exit_code == 1
        assert "Corpus not found" in result.output


# ---------------------------------------------------------------------------
# corpus list
# ---------------------------------------------------------------------------


class TestCorpusList:
    def test_empty_registry(self, tmp_path):
        result = CliRunner().invoke(cli, ["corpus", "list"] + _reg_opt(tmp_path))
        assert result.exit_code == 0, result.output
        assert "No corpora defined yet" in result.output

    def test_lists_entries(self, tmp_path):
        _make_corpus(
            tmp_path,
            CorpusEntry(name="proj-a", description="desc a", tags=["x", "y"]),
        )
        _make_corpus(tmp_path, CorpusEntry(name="proj-b"))
        result = CliRunner().invoke(
            cli, ["corpus", "list"] + _reg_opt(tmp_path), env={"COLUMNS": "200"}
        )
        assert result.exit_code == 0, result.output
        assert "proj-a" in result.output
        assert "proj-b" in result.output
        assert "desc a" in result.output
        assert "Total corpora: 2" in result.output


# ---------------------------------------------------------------------------
# corpus info
# ---------------------------------------------------------------------------


class TestCorpusInfo:
    def test_not_found(self, tmp_path):
        result = CliRunner().invoke(cli, ["corpus", "info", "ghost"] + _reg_opt(tmp_path))
        assert result.exit_code == 1
        assert "Corpus not found" in result.output

    def test_shows_resolved_kg_and_missing_kg(self, tmp_path):
        (kg,) = _register_kg(tmp_path, _make_kg(tmp_path, "real-kg"))
        missing_id = "00000000-0000-0000-0000-000000000000"
        _make_corpus(
            tmp_path,
            CorpusEntry(
                name="mixed",
                kg_ids=[kg.id, missing_id],
                description="a corpus",
                tags=["t1"],
                metadata={"note": "extra"},
            ),
        )
        result = CliRunner().invoke(
            cli, ["corpus", "info", "mixed"] + _reg_opt(tmp_path), env={"COLUMNS": "200"}
        )
        assert result.exit_code == 0, result.output
        assert "real-kg" in result.output
        assert "missing" in result.output
        assert missing_id in result.output
        assert "a corpus" in result.output
        assert "t1" in result.output
        assert "extra" in result.output


# ---------------------------------------------------------------------------
# corpus query
# ---------------------------------------------------------------------------


class TestCorpusQuery:
    def test_not_found_exits_nonzero(self, tmp_path):
        kg = _mock_orch(corpus_hit=None)
        with patch("kg_rag.orchestrator.KGRAG", return_value=kg):
            result = CliRunner().invoke(
                cli, ["corpus", "query", "ghost", "hello"] + _reg_opt(tmp_path)
            )
        assert result.exit_code == 1
        assert "not found" in result.output

    def test_json_output(self, tmp_path):
        hit = CrossHit(
            kg_name="kg1",
            kg_kind=KGKind.CODE,
            node_id="n1",
            name="foo",
            kind="function",
            score=0.87654,
            summary="a function",
            source_path="foo.py",
        )
        qr = CrossQueryResult(query="hello", hits=[hit], by_kg={}, total_hits=1, kgs_queried=1)
        kg = _mock_orch(corpus_hit="proj", query_result=qr)
        with patch("kg_rag.orchestrator.KGRAG", return_value=kg):
            result = CliRunner().invoke(
                cli, ["corpus", "query", "proj", "hello", "--json"] + _reg_opt(tmp_path)
            )
        assert result.exit_code == 0, result.output
        import json

        payload = json.loads(result.output)
        assert payload["corpus"] == "proj"
        assert payload["total_hits"] == 1
        assert payload["hits"][0]["name"] == "foo"
        assert payload["hits"][0]["score"] == 0.8765  # rounded to 4 places

    def test_no_hits_table_mode(self, tmp_path):
        kg = _mock_orch(corpus_hit="proj")
        with patch("kg_rag.orchestrator.KGRAG", return_value=kg):
            result = CliRunner().invoke(
                cli, ["corpus", "query", "proj", "hello"] + _reg_opt(tmp_path)
            )
        assert result.exit_code == 0, result.output
        assert "No results found" in result.output

    def test_hits_table_mode_truncates_long_summary(self, tmp_path):
        long_summary = "x" * 100
        hit = CrossHit(
            kg_name="kg1",
            kg_kind=KGKind.DOC,
            node_id="n1",
            name="bar",
            kind="chunk",
            score=0.5,
            summary=long_summary,
            source_path="bar.md",
        )
        qr = CrossQueryResult(query="hello", hits=[hit], by_kg={}, total_hits=1, kgs_queried=1)
        kg = _mock_orch(corpus_hit="proj", query_result=qr)
        with patch("kg_rag.orchestrator.KGRAG", return_value=kg):
            result = CliRunner().invoke(
                cli,
                ["corpus", "query", "proj", "hello"] + _reg_opt(tmp_path),
                env={"COLUMNS": "200"},
            )
        assert result.exit_code == 0, result.output
        assert "bar" in result.output
        assert "Total hits: 1" in result.output
        assert "…" in result.output  # truncation ellipsis
        assert long_summary not in result.output  # full 100-char text was cut


# ---------------------------------------------------------------------------
# corpus pack
# ---------------------------------------------------------------------------


class TestCorpusPack:
    def test_not_found_exits_nonzero(self, tmp_path):
        kg = _mock_orch(corpus_hit=None)
        with patch("kg_rag.orchestrator.KGRAG", return_value=kg):
            result = CliRunner().invoke(
                cli, ["corpus", "pack", "ghost", "hello"] + _reg_opt(tmp_path)
            )
        assert result.exit_code == 1
        assert "not found" in result.output

    def test_prints_rendered_output_without_out(self, tmp_path):
        snip = CrossSnippet(
            kg_name="kg1",
            kg_kind=KGKind.CODE,
            node_id="n1",
            source_path="foo.py",
            content="def foo():\n    return 42  # a real body, long enough",
            score=0.9,
            lineno=1,
            end_lineno=2,
        )
        pr = CrossSnippetPack(query="hello", snippets=[snip], total_tokens_approx=12, kgs_queried=1)
        kg = _mock_orch(corpus_hit="proj", pack_result=pr)
        with patch("kg_rag.orchestrator.KGRAG", return_value=kg):
            result = CliRunner().invoke(
                cli, ["corpus", "pack", "proj", "hello"] + _reg_opt(tmp_path)
            )
        assert result.exit_code == 0, result.output
        assert "Cross-KG Pack" in result.output
        assert "foo.py" in result.output

    def test_writes_to_out_file(self, tmp_path):
        snip = CrossSnippet(
            kg_name="kg1",
            kg_kind=KGKind.CODE,
            node_id="n1",
            source_path="foo.py",
            content="def foo():\n    return 42  # a real body, long enough",
            score=0.9,
        )
        pr = CrossSnippetPack(query="hello", snippets=[snip], total_tokens_approx=12, kgs_queried=1)
        kg = _mock_orch(corpus_hit="proj", pack_result=pr)
        out_file = tmp_path / "context.md"
        with patch("kg_rag.orchestrator.KGRAG", return_value=kg):
            result = CliRunner().invoke(
                cli,
                ["corpus", "pack", "proj", "hello", "--out", str(out_file)] + _reg_opt(tmp_path),
            )
        assert result.exit_code == 0, result.output
        assert "Written" in result.output
        assert out_file.exists()
        assert "foo.py" in out_file.read_text()


# ---------------------------------------------------------------------------
# corpus person create
# ---------------------------------------------------------------------------


class TestPersonCreate:
    def test_creates_minimal(self, tmp_path):
        result = CliRunner().invoke(
            cli, ["corpus", "person", "create", "Jane Doe"] + _reg_opt(tmp_path)
        )
        assert result.exit_code == 0, result.output
        assert "Created person corpus" in result.output
        with PersonCorpusRegistry(db_path=_reg_db(tmp_path)) as reg:
            assert reg.get("Jane Doe") is not None

    def test_creates_with_all_fields(self, tmp_path):
        (kg,) = _register_kg(tmp_path, _make_kg(tmp_path, "jane-diary"))
        result = CliRunner().invoke(
            cli,
            [
                "corpus",
                "person",
                "create",
                "Jane Doe",
                "--kg",
                "jane-diary",
                "--birth-year",
                "1985",
                "--birth-date",
                "1985-06-01",
                "--address",
                "123 Main St",
                "--email",
                "jane@example.com",
                "--phone",
                "555-1234",
                "--notes",
                "some notes",
                "--tag",
                "family",
            ]
            + _reg_opt(tmp_path),
        )
        assert result.exit_code == 0, result.output
        assert "Born : 1985-06-01" in result.output
        assert "Addr : 123 Main St" in result.output
        assert "Email: jane@example.com" in result.output

        with PersonCorpusRegistry(db_path=_reg_db(tmp_path)) as reg:
            entry = reg.get("Jane Doe")
        assert entry.kg_ids == [kg.id]
        assert entry.birth_year == 1985
        assert entry.tags == ["family"]

    def test_birth_year_only_uses_year_when_no_birth_date(self, tmp_path):
        result = CliRunner().invoke(
            cli,
            ["corpus", "person", "create", "No Date", "--birth-year", "2000"] + _reg_opt(tmp_path),
        )
        assert result.exit_code == 0, result.output
        assert "Born : 2000" in result.output

    def test_unknown_kg_ref_exits_nonzero(self, tmp_path):
        result = CliRunner().invoke(
            cli,
            ["corpus", "person", "create", "Bad Person", "--kg", "ghost"] + _reg_opt(tmp_path),
        )
        assert result.exit_code == 1
        assert "KG not found" in result.output
        with PersonCorpusRegistry(db_path=_reg_db(tmp_path)) as reg:
            assert reg.get("Bad Person") is None


# ---------------------------------------------------------------------------
# corpus person delete
# ---------------------------------------------------------------------------


class TestPersonDelete:
    def test_delete_with_yes_flag(self, tmp_path):
        _make_person(tmp_path, PersonCorpusEntry(name="Gone Person"))
        result = CliRunner().invoke(
            cli, ["corpus", "person", "delete", "Gone Person", "--yes"] + _reg_opt(tmp_path)
        )
        assert result.exit_code == 0, result.output
        assert "Deleted person corpus" in result.output
        with PersonCorpusRegistry(db_path=_reg_db(tmp_path)) as reg:
            assert reg.get("Gone Person") is None

    def test_delete_confirm_declined_aborts(self, tmp_path):
        _make_person(tmp_path, PersonCorpusEntry(name="Keep Person"))
        result = CliRunner().invoke(
            cli, ["corpus", "person", "delete", "Keep Person"] + _reg_opt(tmp_path), input="n\n"
        )
        assert result.exit_code != 0
        with PersonCorpusRegistry(db_path=_reg_db(tmp_path)) as reg:
            assert reg.get("Keep Person") is not None

    def test_delete_not_found(self, tmp_path):
        result = CliRunner().invoke(
            cli, ["corpus", "person", "delete", "ghost", "--yes"] + _reg_opt(tmp_path)
        )
        assert result.exit_code == 1
        assert "Person not found" in result.output


# ---------------------------------------------------------------------------
# corpus person add / remove
# ---------------------------------------------------------------------------


class TestPersonAdd:
    def test_adds_kg(self, tmp_path):
        (kg,) = _register_kg(tmp_path, _make_kg(tmp_path, "kg1"))
        _make_person(tmp_path, PersonCorpusEntry(name="Jane"))
        result = CliRunner().invoke(
            cli, ["corpus", "person", "add", "Jane", "kg1"] + _reg_opt(tmp_path)
        )
        assert result.exit_code == 0, result.output
        assert "Added" in result.output
        with PersonCorpusRegistry(db_path=_reg_db(tmp_path)) as reg:
            assert kg.id in reg.get("Jane").kg_ids

    def test_kg_not_found(self, tmp_path):
        _make_person(tmp_path, PersonCorpusEntry(name="Jane"))
        result = CliRunner().invoke(
            cli, ["corpus", "person", "add", "Jane", "ghost"] + _reg_opt(tmp_path)
        )
        assert result.exit_code == 1
        assert "KG not found" in result.output

    def test_person_not_found(self, tmp_path):
        _register_kg(tmp_path, _make_kg(tmp_path, "kg1"))
        result = CliRunner().invoke(
            cli, ["corpus", "person", "add", "ghost-person", "kg1"] + _reg_opt(tmp_path)
        )
        assert result.exit_code == 1
        assert "Person not found" in result.output


class TestPersonRemove:
    def test_removes_kg(self, tmp_path):
        (kg,) = _register_kg(tmp_path, _make_kg(tmp_path, "kg1"))
        _make_person(tmp_path, PersonCorpusEntry(name="Jane", kg_ids=[kg.id]))
        result = CliRunner().invoke(
            cli, ["corpus", "person", "remove", "Jane", "kg1"] + _reg_opt(tmp_path)
        )
        assert result.exit_code == 0, result.output
        assert "Removed" in result.output
        with PersonCorpusRegistry(db_path=_reg_db(tmp_path)) as reg:
            assert kg.id not in reg.get("Jane").kg_ids

    def test_kg_not_found(self, tmp_path):
        _make_person(tmp_path, PersonCorpusEntry(name="Jane"))
        result = CliRunner().invoke(
            cli, ["corpus", "person", "remove", "Jane", "ghost"] + _reg_opt(tmp_path)
        )
        assert result.exit_code == 1
        assert "KG not found" in result.output

    def test_person_not_found(self, tmp_path):
        _register_kg(tmp_path, _make_kg(tmp_path, "kg1"))
        result = CliRunner().invoke(
            cli, ["corpus", "person", "remove", "ghost-person", "kg1"] + _reg_opt(tmp_path)
        )
        assert result.exit_code == 1
        assert "Person not found" in result.output


# ---------------------------------------------------------------------------
# corpus person update
# ---------------------------------------------------------------------------


class TestPersonUpdate:
    def test_no_updates_specified(self, tmp_path):
        _make_person(tmp_path, PersonCorpusEntry(name="Jane"))
        result = CliRunner().invoke(
            cli, ["corpus", "person", "update", "Jane"] + _reg_opt(tmp_path)
        )
        assert result.exit_code == 0, result.output
        assert "No updates specified" in result.output

    def test_updates_fields(self, tmp_path):
        _make_person(tmp_path, PersonCorpusEntry(name="Jane"))
        result = CliRunner().invoke(
            cli,
            [
                "corpus",
                "person",
                "update",
                "Jane",
                "--email",
                "new@example.com",
                "--birth-year",
                "1990",
            ]
            + _reg_opt(tmp_path),
        )
        assert result.exit_code == 0, result.output
        assert "Updated" in result.output
        assert "email: new@example.com" in result.output
        assert "birth_year: 1990" in result.output

        with PersonCorpusRegistry(db_path=_reg_db(tmp_path)) as reg:
            entry = reg.get("Jane")
        assert entry.email == "new@example.com"
        assert entry.birth_year == 1990

    def test_not_found(self, tmp_path):
        result = CliRunner().invoke(
            cli,
            ["corpus", "person", "update", "ghost", "--email", "x@y.com"] + _reg_opt(tmp_path),
        )
        assert result.exit_code == 1
        assert "Person not found" in result.output


# ---------------------------------------------------------------------------
# corpus person list
# ---------------------------------------------------------------------------


class TestPersonList:
    def test_empty_registry(self, tmp_path):
        result = CliRunner().invoke(cli, ["corpus", "person", "list"] + _reg_opt(tmp_path))
        assert result.exit_code == 0, result.output
        assert "No person corpora defined yet" in result.output

    def test_lists_entries_with_and_without_birth_year(self, tmp_path):
        _make_person(
            tmp_path,
            PersonCorpusEntry(name="Jane Doe", birth_year=1985, email="jane@example.com"),
        )
        _make_person(tmp_path, PersonCorpusEntry(name="No Birth Year"))
        result = CliRunner().invoke(
            cli, ["corpus", "person", "list"] + _reg_opt(tmp_path), env={"COLUMNS": "200"}
        )
        assert result.exit_code == 0, result.output
        assert "Jane Doe" in result.output
        assert "1985" in result.output
        assert "No Birth Year" in result.output
        assert "Total persons: 2" in result.output


# ---------------------------------------------------------------------------
# corpus person info
# ---------------------------------------------------------------------------


class TestPersonInfo:
    def test_not_found(self, tmp_path):
        result = CliRunner().invoke(cli, ["corpus", "person", "info", "ghost"] + _reg_opt(tmp_path))
        assert result.exit_code == 1
        assert "Person not found" in result.output

    def test_shows_resolved_kg_and_missing_kg(self, tmp_path):
        (kg,) = _register_kg(tmp_path, _make_kg(tmp_path, "diary-kg"))
        missing_id = "00000000-0000-0000-0000-000000000000"
        _make_person(
            tmp_path,
            PersonCorpusEntry(
                name="Jane Doe",
                kg_ids=[kg.id, missing_id],
                birth_year=1985,
                birth_date="1985-06-01",
                address="123 Main St",
                email="jane@example.com",
                phone="555-1234",
                notes="likes hiking",
                tags=["family"],
                metadata={"note": "extra"},
            ),
        )
        result = CliRunner().invoke(
            cli,
            ["corpus", "person", "info", "Jane Doe"] + _reg_opt(tmp_path),
            env={"COLUMNS": "200"},
        )
        assert result.exit_code == 0, result.output
        assert "diary-kg" in result.output
        assert "missing" in result.output
        assert missing_id in result.output
        assert "1985-06-01" in result.output
        assert "123 Main St" in result.output
        assert "jane@example.com" in result.output
        assert "555-1234" in result.output
        assert "likes hiking" in result.output
        assert "extra" in result.output


# ---------------------------------------------------------------------------
# corpus person query
# ---------------------------------------------------------------------------


class TestPersonQuery:
    def test_not_found_exits_nonzero(self, tmp_path):
        kg = _mock_orch(person_hit=None)
        with patch("kg_rag.orchestrator.KGRAG", return_value=kg):
            result = CliRunner().invoke(
                cli, ["corpus", "person", "query", "ghost", "hello"] + _reg_opt(tmp_path)
            )
        assert result.exit_code == 1
        assert "not found" in result.output

    def test_json_output(self, tmp_path):
        hit = CrossHit(
            kg_name="kg1",
            kg_kind=KGKind.DIARY,
            node_id="n1",
            name="entry-1",
            kind="entry",
            score=0.5,
            summary="a diary entry",
            source_path="2020-01-01.md",
        )
        qr = CrossQueryResult(query="hello", hits=[hit], by_kg={}, total_hits=1, kgs_queried=1)
        kg = _mock_orch(person_hit="Jane", query_result=qr)
        with patch("kg_rag.orchestrator.KGRAG", return_value=kg):
            result = CliRunner().invoke(
                cli, ["corpus", "person", "query", "Jane", "hello", "--json"] + _reg_opt(tmp_path)
            )
        assert result.exit_code == 0, result.output
        import json

        payload = json.loads(result.output)
        assert payload["person"] == "Jane"
        assert payload["hits"][0]["name"] == "entry-1"

    def test_no_hits_table_mode(self, tmp_path):
        kg = _mock_orch(person_hit="Jane")
        with patch("kg_rag.orchestrator.KGRAG", return_value=kg):
            result = CliRunner().invoke(
                cli, ["corpus", "person", "query", "Jane", "hello"] + _reg_opt(tmp_path)
            )
        assert result.exit_code == 0, result.output
        assert "No results found" in result.output

    def test_hits_table_mode_truncates_long_summary(self, tmp_path):
        long_summary = "y" * 90
        hit = CrossHit(
            kg_name="kg1",
            kg_kind=KGKind.DIARY,
            node_id="n1",
            name="entry-1",
            kind="entry",
            score=0.5,
            summary=long_summary,
            source_path="2020-01-01.md",
        )
        qr = CrossQueryResult(query="hello", hits=[hit], by_kg={}, total_hits=1, kgs_queried=1)
        kg = _mock_orch(person_hit="Jane", query_result=qr)
        with patch("kg_rag.orchestrator.KGRAG", return_value=kg):
            result = CliRunner().invoke(
                cli,
                ["corpus", "person", "query", "Jane", "hello"] + _reg_opt(tmp_path),
                env={"COLUMNS": "200"},
            )
        assert result.exit_code == 0, result.output
        assert "entry-1" in result.output
        assert "Total hits: 1" in result.output
        assert "…" in result.output
        assert long_summary not in result.output


# ---------------------------------------------------------------------------
# corpus person pack
# ---------------------------------------------------------------------------


class TestPersonPack:
    def test_not_found_exits_nonzero(self, tmp_path):
        kg = _mock_orch(person_hit=None)
        with patch("kg_rag.orchestrator.KGRAG", return_value=kg):
            result = CliRunner().invoke(
                cli, ["corpus", "person", "pack", "ghost", "hello"] + _reg_opt(tmp_path)
            )
        assert result.exit_code == 1
        assert "not found" in result.output

    def test_prints_rendered_output_without_out(self, tmp_path):
        snip = CrossSnippet(
            kg_name="kg1",
            kg_kind=KGKind.DIARY,
            node_id="n1",
            source_path="2020-01-01.md",
            content="Today was a long walk in the woods, quite memorable.",
            score=0.7,
        )
        pr = CrossSnippetPack(query="hello", snippets=[snip], total_tokens_approx=20, kgs_queried=1)
        kg = _mock_orch(person_hit="Jane", pack_result=pr)
        with patch("kg_rag.orchestrator.KGRAG", return_value=kg):
            result = CliRunner().invoke(
                cli, ["corpus", "person", "pack", "Jane", "hello"] + _reg_opt(tmp_path)
            )
        assert result.exit_code == 0, result.output
        assert "Cross-KG Pack" in result.output
        assert "2020-01-01.md" in result.output

    def test_writes_to_out_file(self, tmp_path):
        snip = CrossSnippet(
            kg_name="kg1",
            kg_kind=KGKind.DIARY,
            node_id="n1",
            source_path="2020-01-01.md",
            content="Today was a long walk in the woods, quite memorable.",
            score=0.7,
        )
        pr = CrossSnippetPack(query="hello", snippets=[snip], total_tokens_approx=20, kgs_queried=1)
        kg = _mock_orch(person_hit="Jane", pack_result=pr)
        out_file = tmp_path / "jane_context.md"
        with patch("kg_rag.orchestrator.KGRAG", return_value=kg):
            result = CliRunner().invoke(
                cli,
                ["corpus", "person", "pack", "Jane", "hello", "--out", str(out_file)]
                + _reg_opt(tmp_path),
            )
        assert result.exit_code == 0, result.output
        assert "Written" in result.output
        assert out_file.exists()
        assert "2020-01-01.md" in out_file.read_text()
