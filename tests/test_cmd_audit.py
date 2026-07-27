"""
test_cmd_audit.py

Tests for ``kgrag audit-lancedb`` — the LanceDB retirement audit.

Fixtures build the four on-disk shapes the audit must tell apart
(unmigrated / residue / stale-row / clean) and assert both the
classification and the remediation command emitted for each.
"""

from __future__ import annotations

import json
from pathlib import Path

from click.testing import CliRunner

from kg_rag.cli.cmd_audit import audit_entry
from kg_rag.cli.main import cli
from kg_rag.corpus_registry import CorpusRegistry
from kg_rag.primitives import CorpusEntry, KGEntry, KGKind
from kg_rag.registry import KGRegistry

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _reg_opt(tmp_path: Path) -> list[str]:
    return ["--registry", str(tmp_path / "registry.sqlite")]


def _make_kg(
    tmp_path: Path,
    name: str,
    kind: KGKind = KGKind.CODE,
    *,
    marker: str = ".pycodekg",
    lancedb_on_disk: bool = False,
    vectors_on_disk: bool = False,
    record_lancedb: bool = False,
    lancedb_bytes: int = 0,
) -> KGEntry:
    """Build a repo layout and a matching KGEntry.

    ``record_lancedb`` controls the *registry* reference independently of
    whether the directory exists, so stale rows can be modelled.
    """
    repo = tmp_path / name
    kg_dir = repo / marker
    kg_dir.mkdir(parents=True, exist_ok=True)
    (repo / ".venv").mkdir(exist_ok=True)
    sqlite = kg_dir / "graph.sqlite"
    sqlite.touch()

    lancedb = kg_dir / "lancedb"
    if lancedb_on_disk:
        lancedb.mkdir(exist_ok=True)
        (lancedb / "data.lance").write_bytes(b"x" * lancedb_bytes)
    if vectors_on_disk:
        (kg_dir / "vectors.sqlite").touch()

    return KGEntry(
        name=name,
        kind=kind,
        repo_path=repo,
        venv_path=repo / ".venv",
        sqlite_path=sqlite,
        lancedb_path=lancedb if record_lancedb else None,
    )


def _register(tmp_path: Path, *entries: KGEntry) -> None:
    with KGRegistry(db_path=tmp_path / "registry.sqlite") as reg:
        for e in entries:
            reg.register(e)


# ---------------------------------------------------------------------------
# Classification
# ---------------------------------------------------------------------------


class TestAuditClassification:
    def test_unmigrated_when_lancedb_and_no_vectors(self, tmp_path):
        entry = _make_kg(tmp_path, "a", lancedb_on_disk=True, record_lancedb=True)
        f = audit_entry(entry)
        assert f.status == "unmigrated"
        assert f.has_vectors is False
        assert f.lancedb_dirs

    def test_residue_when_both_present(self, tmp_path):
        entry = _make_kg(tmp_path, "b", lancedb_on_disk=True, vectors_on_disk=True)
        f = audit_entry(entry)
        assert f.status == "residue"
        assert f.has_vectors is True

    def test_stale_row_when_registry_points_at_missing_dir(self, tmp_path):
        entry = _make_kg(tmp_path, "c", vectors_on_disk=True, record_lancedb=True)
        f = audit_entry(entry)
        assert f.status == "stale-row"
        assert f.registry_reference is True
        assert f.lancedb_dirs == []

    def test_clean_when_vectors_only(self, tmp_path):
        entry = _make_kg(tmp_path, "d", vectors_on_disk=True)
        f = audit_entry(entry)
        assert f.status == "clean"
        assert f.fix_cmd is None

    def test_no_index_when_nothing_present(self, tmp_path):
        entry = _make_kg(tmp_path, "e")
        f = audit_entry(entry)
        assert f.status == "no-index"
        assert f.fix_cmd is None

    def test_finds_unregistered_lancedb_dir(self, tmp_path):
        """A lancedb/ left on disk is reported even with no registry reference."""
        entry = _make_kg(tmp_path, "orphan", lancedb_on_disk=True, record_lancedb=False)
        f = audit_entry(entry)
        assert f.status == "unmigrated"
        assert f.registry_reference is False
        assert len(f.lancedb_dirs) == 1

    def test_reclaimable_bytes_measured(self, tmp_path):
        entry = _make_kg(tmp_path, "sized", lancedb_on_disk=True, lancedb_bytes=2048)
        assert audit_entry(entry).reclaimable_bytes == 2048

    def test_no_measure_skips_sizing(self, tmp_path):
        entry = _make_kg(tmp_path, "nosize", lancedb_on_disk=True, lancedb_bytes=2048)
        assert audit_entry(entry, measure=False).reclaimable_bytes == 0


# ---------------------------------------------------------------------------
# Remediation commands
# ---------------------------------------------------------------------------


class TestAuditFixCommands:
    def test_doc_kind_gets_convert_index(self, tmp_path):
        entry = _make_kg(tmp_path, "docs", KGKind.DOC, marker=".dockg", lancedb_on_disk=True)
        f = audit_entry(entry)
        assert f.action == "convert index"
        assert "dockg convert-index" in f.fix_cmd
        assert "--delete-lancedb" in f.fix_cmd

    def test_gutenberg_convert_uses_own_marker_dir(self, tmp_path):
        """gutenberg corpora live under .gutenbergkg — paths must be explicit,
        not convert-index's .dockg default."""
        entry = _make_kg(
            tmp_path,
            "book",
            KGKind.GUTENBERG,
            marker=".gutenbergkg",
            lancedb_on_disk=True,
        )
        f = audit_entry(entry)
        assert ".gutenbergkg/lancedb" in f.fix_cmd
        assert ".gutenbergkg/vectors.sqlite" in f.fix_cmd

    def test_code_kind_gets_rebuild_not_convert(self, tmp_path):
        """pycode-kg has no in-place converter — it must be rebuilt."""
        entry = _make_kg(tmp_path, "code", KGKind.CODE, lancedb_on_disk=True)
        f = audit_entry(entry)
        assert f.action == "rebuild"
        assert "pycodekg build" in f.fix_cmd
        assert "convert-index" not in f.fix_cmd

    def test_residue_gets_delete_command(self, tmp_path):
        entry = _make_kg(tmp_path, "res", lancedb_on_disk=True, vectors_on_disk=True)
        f = audit_entry(entry)
        assert f.fix_cmd.startswith("rm -rf ")
        assert "lancedb" in f.fix_cmd

    def test_stale_row_gets_reregister(self, tmp_path):
        entry = _make_kg(tmp_path, "stale", vectors_on_disk=True, record_lancedb=True)
        assert audit_entry(entry).fix_cmd.startswith("kgrag register stale code ")

    def test_paths_with_spaces_are_quoted(self, tmp_path):
        """Gutenberg corpus dirs contain spaces — commands must stay runnable."""
        entry = _make_kg(
            tmp_path, "My Book Title", KGKind.DOC, marker=".dockg", lancedb_on_disk=True
        )
        assert "'" in audit_entry(entry).fix_cmd


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


class TestAuditCLI:
    def test_reports_clean_fleet(self, tmp_path):
        _register(tmp_path, _make_kg(tmp_path, "ok", vectors_on_disk=True))
        result = CliRunner().invoke(cli, ["audit-lancedb"] + _reg_opt(tmp_path))
        assert result.exit_code == 0, result.output
        assert "No LanceDB residue found" in result.output

    def test_flags_outstanding_kg(self, tmp_path):
        _register(tmp_path, _make_kg(tmp_path, "bad", lancedb_on_disk=True))
        result = CliRunner().invoke(cli, ["audit-lancedb"] + _reg_opt(tmp_path))
        assert result.exit_code == 0, result.output
        assert "unmigrated" in result.output
        assert "bad" in result.output

    def test_commands_mode_emits_only_commands(self, tmp_path):
        _register(
            tmp_path,
            _make_kg(tmp_path, "c1", KGKind.DOC, marker=".dockg", lancedb_on_disk=True),
            _make_kg(tmp_path, "clean1", vectors_on_disk=True),
        )
        result = CliRunner().invoke(cli, ["audit-lancedb", "--commands"] + _reg_opt(tmp_path))
        assert result.exit_code == 0, result.output
        lines = [ln for ln in result.output.splitlines() if ln.strip()]
        assert len(lines) == 1  # only the one outstanding KG
        assert lines[0].startswith("dockg convert-index")

    def test_json_mode_shape(self, tmp_path):
        _register(tmp_path, _make_kg(tmp_path, "j1", lancedb_on_disk=True, lancedb_bytes=512))
        result = CliRunner().invoke(cli, ["audit-lancedb", "--json"] + _reg_opt(tmp_path))
        assert result.exit_code == 0, result.output
        payload = json.loads(result.output)
        assert payload["total_audited"] == 1
        assert payload["outstanding"] == 1
        assert payload["reclaimable_bytes"] == 512
        assert payload["findings"][0]["status"] == "unmigrated"

    def test_single_kg_scope(self, tmp_path):
        _register(
            tmp_path,
            _make_kg(tmp_path, "one", lancedb_on_disk=True),
            _make_kg(tmp_path, "two", lancedb_on_disk=True),
        )
        result = CliRunner().invoke(cli, ["audit-lancedb", "one", "--json"] + _reg_opt(tmp_path))
        assert result.exit_code == 0, result.output
        payload = json.loads(result.output)
        assert payload["total_audited"] == 1
        assert payload["findings"][0]["name"] == "one"

    def test_unknown_kg_exits_nonzero(self, tmp_path):
        _register(tmp_path, _make_kg(tmp_path, "present"))
        result = CliRunner().invoke(cli, ["audit-lancedb", "ghost"] + _reg_opt(tmp_path))
        assert result.exit_code == 1
        assert "Not found" in result.output

    def test_corpus_scope(self, tmp_path):
        member = _make_kg(tmp_path, "in-corpus", lancedb_on_disk=True)
        outsider = _make_kg(tmp_path, "outsider", lancedb_on_disk=True)
        _register(tmp_path, member, outsider)
        db = tmp_path / "registry.sqlite"
        with CorpusRegistry(db_path=db) as creg:
            creg.create(CorpusEntry(name="mycorpus", kg_ids=[member.id]))

        result = CliRunner().invoke(
            cli, ["audit-lancedb", "--corpus", "mycorpus", "--json"] + _reg_opt(tmp_path)
        )
        assert result.exit_code == 0, result.output
        payload = json.loads(result.output)
        assert payload["total_audited"] == 1
        assert payload["findings"][0]["name"] == "in-corpus"

    def test_unknown_corpus_exits_nonzero(self, tmp_path):
        _register(tmp_path, _make_kg(tmp_path, "k"))
        result = CliRunner().invoke(cli, ["audit-lancedb", "--corpus", "nope"] + _reg_opt(tmp_path))
        assert result.exit_code == 1
        assert "Corpus not found" in result.output

    def test_limit_truncation_is_disclosed(self, tmp_path):
        _register(tmp_path, *[_make_kg(tmp_path, f"kg{i}", lancedb_on_disk=True) for i in range(5)])
        result = CliRunner().invoke(cli, ["audit-lancedb", "--limit", "2"] + _reg_opt(tmp_path))
        assert result.exit_code == 0, result.output
        assert "and 3 more not shown" in result.output

    def test_all_flag_includes_clean_kgs(self, tmp_path):
        _register(tmp_path, _make_kg(tmp_path, "spotless", vectors_on_disk=True))
        result = CliRunner().invoke(
            cli,
            ["audit-lancedb", "--all"] + _reg_opt(tmp_path),
            env={"COLUMNS": "200"},
        )
        assert result.exit_code == 0, result.output
        # Without --all a fully clean fleet short-circuits to the green message.
        assert "No LanceDB residue found" not in result.output
        assert "spotless" in result.output
        assert "clean" in result.output
