"""
test_cmd_health.py

Tests for `kgrag health` — the full-stack registry health command.

All tests use an isolated temp registry via --registry so they never
touch ~/.kgrag.
"""

from __future__ import annotations

import json
from pathlib import Path

from click.testing import CliRunner

from kg_rag.cli.main import cli
from kg_rag.corpus_registry import CorpusRegistry
from kg_rag.primitives import CorpusEntry, KGEntry, KGKind
from kg_rag.registry import KGRegistry

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _runner() -> CliRunner:
    return CliRunner()


def _reg_args(db: Path) -> list[str]:
    return ["--registry", str(db)]


def _reg_db(tmp_path: Path) -> Path:
    return tmp_path / "registry.sqlite"


def _make_built_entry(tmp_path: Path, name: str, kind: KGKind = KGKind.CODE) -> KGEntry:
    """Create a KGEntry whose SQLite file actually exists on disk."""
    repo = tmp_path / name
    repo.mkdir(exist_ok=True)
    marker = repo / f".{kind.value}kg"
    marker.mkdir(exist_ok=True)
    sqlite = marker / "graph.sqlite"
    sqlite.touch()
    return KGEntry(
        name=name,
        kind=kind,
        repo_path=repo,
        venv_path=repo / ".venv",
        sqlite_path=sqlite,
    )


def _make_unbuilt_entry(tmp_path: Path, name: str, kind: KGKind = KGKind.CODE) -> KGEntry:
    """Create a KGEntry with no SQLite file (is_built=False)."""
    repo = tmp_path / name
    repo.mkdir(exist_ok=True)
    return KGEntry(
        name=name,
        kind=kind,
        repo_path=repo,
        venv_path=repo / ".venv",
        sqlite_path=None,
    )


# ---------------------------------------------------------------------------
# Basic invocation
# ---------------------------------------------------------------------------


class TestHealthBasic:
    def test_help(self):
        result = _runner().invoke(cli, ["health", "--help"])
        assert result.exit_code == 0
        assert "health" in result.output.lower()

    def test_empty_registry_is_healthy(self, tmp_path):
        db = _reg_db(tmp_path)
        result = _runner().invoke(cli, ["health"] + _reg_args(db))
        assert result.exit_code == 0
        assert "passed" in result.output.lower() or "healthy" in result.output.lower()

    def test_all_built_is_healthy(self, tmp_path):
        db = _reg_db(tmp_path)
        entry = _make_built_entry(tmp_path, "my-code")
        with KGRegistry(db_path=db) as reg:
            reg.register(entry)

        result = _runner().invoke(cli, ["health"] + _reg_args(db))
        assert result.exit_code == 0
        assert "passed" in result.output.lower() or "healthy" in result.output.lower()


# ---------------------------------------------------------------------------
# Unbuilt KG detection
# ---------------------------------------------------------------------------


class TestHealthUnbuilt:
    def test_detects_unbuilt_kg(self, tmp_path):
        db = _reg_db(tmp_path)
        entry = _make_unbuilt_entry(tmp_path, "stale-code")
        with KGRegistry(db_path=db) as reg:
            reg.register(entry)

        result = _runner().invoke(cli, ["health"] + _reg_args(db))
        assert result.exit_code == 0
        assert "unbuilt" in result.output
        assert "stale-code" in result.output

    def test_suggests_build_command(self, tmp_path):
        db = _reg_db(tmp_path)
        entry = _make_unbuilt_entry(tmp_path, "stale-code", kind=KGKind.CODE)
        with KGRegistry(db_path=db) as reg:
            reg.register(entry)

        result = _runner().invoke(cli, ["health"] + _reg_args(db))
        assert "codekg build" in result.output

    def test_doc_kg_suggests_dockg_build(self, tmp_path):
        db = _reg_db(tmp_path)
        entry = _make_unbuilt_entry(tmp_path, "stale-doc", kind=KGKind.DOC)
        with KGRegistry(db_path=db) as reg:
            reg.register(entry)

        result = _runner().invoke(cli, ["health"] + _reg_args(db))
        assert "dockg build" in result.output


# ---------------------------------------------------------------------------
# Missing repo path (critical)
# ---------------------------------------------------------------------------


class TestHealthMissingRepo:
    def test_detects_missing_repo(self, tmp_path):
        db = _reg_db(tmp_path)
        # Register with a path that doesn't exist
        ghost_repo = tmp_path / "ghost"
        entry = KGEntry(
            name="ghost-kg",
            kind=KGKind.CODE,
            repo_path=ghost_repo,
            venv_path=ghost_repo / ".venv",
        )
        with KGRegistry(db_path=db) as reg:
            reg.register(entry)

        result = _runner().invoke(cli, ["health"] + _reg_args(db))
        assert result.exit_code == 0
        assert "missing_repo" in result.output
        assert "ghost-kg" in result.output
        assert "critical" in result.output.lower() or "✖" in result.output

    def test_nudges_toward_fix(self, tmp_path):
        """Auto-fixable issues should display the --fix nudge, not a manual cmd."""
        db = _reg_db(tmp_path)
        ghost_repo = tmp_path / "ghost"
        entry = KGEntry(
            name="ghost-kg",
            kind=KGKind.CODE,
            repo_path=ghost_repo,
            venv_path=ghost_repo / ".venv",
        )
        with KGRegistry(db_path=db) as reg:
            reg.register(entry)

        result = _runner().invoke(cli, ["health"] + _reg_args(db))
        # auto-fixable: nudge shown, not a manual command block
        assert "auto-repair" in result.output or "--fix" in result.output

    def test_fix_unregisters_with_confirmation(self, tmp_path):
        db = _reg_db(tmp_path)
        ghost_repo = tmp_path / "ghost"
        entry = KGEntry(
            name="ghost-kg",
            kind=KGKind.CODE,
            repo_path=ghost_repo,
            venv_path=ghost_repo / ".venv",
        )
        with KGRegistry(db_path=db) as reg:
            reg.register(entry)

        # Provide 'y' to the confirmation prompt
        result = _runner().invoke(cli, ["health", "--fix"] + _reg_args(db), input="y\n")
        assert result.exit_code == 0
        assert "Unregistered" in result.output or "fixed" in result.output

        # Confirm it's actually gone
        with KGRegistry(db_path=db) as reg:
            assert reg.get("ghost-kg") is None

    def test_fix_skips_if_declined(self, tmp_path):
        db = _reg_db(tmp_path)
        ghost_repo = tmp_path / "ghost"
        entry = KGEntry(
            name="ghost-kg",
            kind=KGKind.CODE,
            repo_path=ghost_repo,
            venv_path=ghost_repo / ".venv",
        )
        with KGRegistry(db_path=db) as reg:
            reg.register(entry)

        result = _runner().invoke(cli, ["health", "--fix"] + _reg_args(db), input="n\n")
        assert result.exit_code == 0
        # Still present
        with KGRegistry(db_path=db) as reg:
            assert reg.get("ghost-kg") is not None


# ---------------------------------------------------------------------------
# Stale index paths
# ---------------------------------------------------------------------------


class TestHealthStalePaths:
    def test_detects_stale_sqlite(self, tmp_path):
        db = _reg_db(tmp_path)
        repo = tmp_path / "myrepo"
        repo.mkdir()
        entry = KGEntry(
            name="stale-sqlite",
            kind=KGKind.CODE,
            repo_path=repo,
            venv_path=repo / ".venv",
            sqlite_path=repo / ".codekg" / "graph.sqlite",  # path set but file absent
        )
        with KGRegistry(db_path=db) as reg:
            reg.register(entry)

        result = _runner().invoke(cli, ["health"] + _reg_args(db))
        assert result.exit_code == 0
        assert "stale_sqlite" in result.output
        assert "stale-sqlite" in result.output

    def test_detects_stale_lancedb(self, tmp_path):
        db = _reg_db(tmp_path)
        repo = tmp_path / "myrepo"
        repo.mkdir()
        # SQLite exists so is_built=True; LanceDB dir is absent
        db_dir = repo / ".codekg"
        db_dir.mkdir()
        sqlite = db_dir / "graph.sqlite"
        sqlite.touch()
        entry = KGEntry(
            name="stale-lance",
            kind=KGKind.CODE,
            repo_path=repo,
            venv_path=repo / ".venv",
            sqlite_path=sqlite,
            lancedb_path=db_dir / "lancedb",  # doesn't exist
        )
        with KGRegistry(db_path=db) as reg:
            reg.register(entry)

        result = _runner().invoke(cli, ["health"] + _reg_args(db))
        assert result.exit_code == 0
        assert "stale_lancedb" in result.output


# ---------------------------------------------------------------------------
# Corpus checks
# ---------------------------------------------------------------------------


class TestHealthCorpus:
    def test_detects_broken_corpus_ref(self, tmp_path):
        db = _reg_db(tmp_path)
        # Create a corpus that references a KG UUID that doesn't exist
        fake_id = "00000000-0000-0000-0000-000000000000"
        corpus = CorpusEntry(name="my-corpus", kg_ids=[fake_id])
        with CorpusRegistry(db_path=db) as corp_reg:
            corp_reg.create(corpus)

        result = _runner().invoke(cli, ["health"] + _reg_args(db))
        assert result.exit_code == 0
        assert "corpus_broken_ref" in result.output
        assert "my-corpus" in result.output

    def test_fix_removes_broken_corpus_ref(self, tmp_path):
        db = _reg_db(tmp_path)
        fake_id = "00000000-0000-0000-0000-000000000000"
        corpus = CorpusEntry(name="my-corpus", kg_ids=[fake_id])
        with CorpusRegistry(db_path=db) as corp_reg:
            corp_reg.create(corpus)

        result = _runner().invoke(cli, ["health", "--fix"] + _reg_args(db))
        assert result.exit_code == 0
        assert "fixed" in result.output or "Removed" in result.output

        with CorpusRegistry(db_path=db) as corp_reg:
            updated = corp_reg.get("my-corpus")
            assert updated is not None
            assert fake_id not in updated.kg_ids

    def test_detects_corpus_unbuilt_member(self, tmp_path):
        db = _reg_db(tmp_path)
        entry = _make_unbuilt_entry(tmp_path, "unbuilt-member")
        with KGRegistry(db_path=db) as kg_reg:
            kg_reg.register(entry)
            registered = kg_reg.get("unbuilt-member")

        corpus = CorpusEntry(name="my-corpus", kg_ids=[registered.id])
        with CorpusRegistry(db_path=db) as corp_reg:
            corp_reg.create(corpus)

        result = _runner().invoke(cli, ["health"] + _reg_args(db))
        assert result.exit_code == 0
        assert "corpus_unbuilt_member" in result.output
        assert "my-corpus" in result.output

    def test_healthy_corpus_no_issues(self, tmp_path):
        db = _reg_db(tmp_path)
        entry = _make_built_entry(tmp_path, "good-member")
        with KGRegistry(db_path=db) as kg_reg:
            kg_reg.register(entry)
            registered = kg_reg.get("good-member")

        corpus = CorpusEntry(name="good-corpus", kg_ids=[registered.id])
        with CorpusRegistry(db_path=db) as corp_reg:
            corp_reg.create(corpus)

        result = _runner().invoke(cli, ["health"] + _reg_args(db))
        assert result.exit_code == 0
        assert "passed" in result.output.lower() or "healthy" in result.output.lower()


# ---------------------------------------------------------------------------
# JSON output
# ---------------------------------------------------------------------------


class TestHealthJSON:
    def test_json_empty_registry(self, tmp_path):
        db = _reg_db(tmp_path)
        result = _runner().invoke(cli, ["health", "--json"] + _reg_args(db))
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert data["issues"] == []
        assert data["total_kgs"] == 0

    def test_json_reports_issues(self, tmp_path):
        db = _reg_db(tmp_path)
        entry = _make_unbuilt_entry(tmp_path, "unbuilt")
        with KGRegistry(db_path=db) as reg:
            reg.register(entry)

        result = _runner().invoke(cli, ["health", "--json"] + _reg_args(db))
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert len(data["issues"]) == 1
        assert data["issues"][0]["check"] == "unbuilt"
        assert data["issues"][0]["target"] == "unbuilt"
        assert data["issues"][0]["severity"] == "warning"

    def test_json_fix_log_populated(self, tmp_path):
        db = _reg_db(tmp_path)
        fake_id = "00000000-0000-0000-0000-000000000000"
        corpus = CorpusEntry(name="corp", kg_ids=[fake_id])
        with CorpusRegistry(db_path=db) as corp_reg:
            corp_reg.create(corpus)

        result = _runner().invoke(cli, ["health", "--fix", "--json"] + _reg_args(db))
        assert result.exit_code == 0
        data = json.loads(result.output)
        assert len(data["fixed"]) == 1
        assert len(data["issues"]) == 0
