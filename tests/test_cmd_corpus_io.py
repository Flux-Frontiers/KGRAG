"""
test_cmd_corpus_io.py

Tests for the ``kgrag export`` / ``kgrag import`` commands and their helpers.

These tests build small on-disk fixtures (a fake SQLite file and a fake
LanceDB directory), exercise the CLI with an isolated --registry, and
verify both the archive contents and the post-import registry state.
"""

from __future__ import annotations

import json
import tarfile
from pathlib import Path

from click.testing import CliRunner

from kg_rag.cli.cmd_corpus_io import (
    ARCHIVE_SUFFIX,
    MANIFEST_NAME,
    MANIFEST_VERSION,
    _build_manifest,
)
from kg_rag.cli.main import cli
from kg_rag.primitives import KGEntry, KGKind
from kg_rag.registry import KGRegistry

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _reg_opt(tmp_path: Path) -> list[str]:
    return ["--registry", str(tmp_path / "registry.sqlite")]


def _make_built_kg(
    tmp_path: Path,
    name: str = "mykg",
    *,
    with_sqlite: bool = True,
    with_lancedb: bool = False,
    sqlite_bytes: bytes = b"FAKE-SQLITE-CONTENT\n",
    lancedb_files: dict[str, bytes] | None = None,
) -> KGEntry:
    """Create a repo layout with optional sqlite/lancedb artifacts and
    return a corresponding KGEntry."""
    repo = tmp_path / name
    repo.mkdir(parents=True, exist_ok=True)
    venv = repo / ".venv"
    venv.mkdir(exist_ok=True)

    sqlite_path = None
    if with_sqlite:
        kg_dir = repo / ".pycodekg"
        kg_dir.mkdir(exist_ok=True)
        sqlite_path = kg_dir / "graph.sqlite"
        sqlite_path.write_bytes(sqlite_bytes)

    lancedb_path = None
    if with_lancedb:
        kg_dir = repo / ".pycodekg"
        kg_dir.mkdir(exist_ok=True)
        lancedb_path = kg_dir / "lancedb"
        lancedb_path.mkdir(exist_ok=True)
        files = lancedb_files or {"chunks.lance": b"LANCE-DATA\n"}
        for fname, content in files.items():
            (lancedb_path / fname).write_bytes(content)

    return KGEntry(
        name=name,
        kind=KGKind.CODE,
        repo_path=repo,
        venv_path=venv,
        sqlite_path=sqlite_path,
        lancedb_path=lancedb_path,
        version="1.2.3",
        builder_version="9.9.9",
        tags=["alpha", "beta"],
        metadata={"description": "fixture KG"},
    )


def _register(tmp_path: Path, entry: KGEntry) -> None:
    """Register an entry into the test-isolated registry."""
    with KGRegistry(db_path=tmp_path / "registry.sqlite") as reg:
        reg.register(entry)


# ---------------------------------------------------------------------------
# _build_manifest
# ---------------------------------------------------------------------------


class TestBuildManifest:
    def test_built_with_sqlite_only(self, tmp_path):
        entry = _make_built_kg(tmp_path, "code-only", with_sqlite=True, with_lancedb=False)
        m = _build_manifest(entry)

        assert m["manifest_version"] == MANIFEST_VERSION
        assert m["name"] == "code-only"
        assert m["kind"] == "code"
        assert m["version"] == "1.2.3"
        assert m["builder_version"] == "9.9.9"
        assert m["tags"] == ["alpha", "beta"]
        assert m["metadata"] == {"description": "fixture KG"}
        assert m["has_sqlite"] is True
        assert m["has_lancedb"] is False
        # exported_at must round-trip as ISO 8601
        assert "T" in m["exported_at"]

    def test_built_with_both(self, tmp_path):
        entry = _make_built_kg(tmp_path, "both", with_sqlite=True, with_lancedb=True)
        m = _build_manifest(entry)
        assert m["has_sqlite"] is True
        assert m["has_lancedb"] is True

    def test_unbuilt_marks_both_false(self, tmp_path):
        # Construct an entry whose paths point nowhere.
        repo = tmp_path / "ghost"
        repo.mkdir()
        (repo / ".venv").mkdir()
        entry = KGEntry(
            name="ghost",
            kind=KGKind.CODE,
            repo_path=repo,
            venv_path=repo / ".venv",
            sqlite_path=repo / "does_not_exist.sqlite",
            lancedb_path=repo / "missing_lancedb",
        )
        m = _build_manifest(entry)
        assert m["has_sqlite"] is False
        assert m["has_lancedb"] is False

    def test_manifest_is_json_serializable(self, tmp_path):
        entry = _make_built_kg(tmp_path)
        # Round-trip through JSON to catch any non-serializable values.
        s = json.dumps(_build_manifest(entry))
        assert "mykg" in s


# ---------------------------------------------------------------------------
# kgrag export
# ---------------------------------------------------------------------------


class TestCLIExport:
    def test_export_sqlite_only_creates_archive(self, tmp_path):
        entry = _make_built_kg(tmp_path, "exp-sqlite", with_sqlite=True)
        _register(tmp_path, entry)

        out = tmp_path / "exp-sqlite.kgrag.tar.gz"
        result = CliRunner().invoke(
            cli,
            ["export", "exp-sqlite", "-o", str(out)] + _reg_opt(tmp_path),
        )

        assert result.exit_code == 0, result.output
        assert out.exists()
        with tarfile.open(out, "r:gz") as tar:
            names = set(tar.getnames())
        assert MANIFEST_NAME in names
        assert "graph.sqlite" in names
        # No lancedb member when source didn't have one.
        assert not any(n.startswith("lancedb") for n in names)

    def test_export_includes_lancedb(self, tmp_path):
        entry = _make_built_kg(
            tmp_path,
            "exp-both",
            with_sqlite=True,
            with_lancedb=True,
            lancedb_files={
                "a.lance": b"a",
                "b.lance": b"b",
            },
        )
        _register(tmp_path, entry)

        out = tmp_path / "exp-both.kgrag.tar.gz"
        result = CliRunner().invoke(
            cli, ["export", "exp-both", "-o", str(out)] + _reg_opt(tmp_path)
        )
        assert result.exit_code == 0, result.output

        with tarfile.open(out, "r:gz") as tar:
            names = set(tar.getnames())
        assert "graph.sqlite" in names
        # lancedb is added as a directory; its files appear as lancedb/<name>
        assert any(n == "lancedb" or n.startswith("lancedb/") for n in names)
        assert "lancedb/a.lance" in names
        assert "lancedb/b.lance" in names

    def test_export_manifest_content(self, tmp_path):
        entry = _make_built_kg(tmp_path, "manifest-kg", with_sqlite=True, with_lancedb=True)
        _register(tmp_path, entry)

        out = tmp_path / "manifest-kg.kgrag.tar.gz"
        result = CliRunner().invoke(
            cli, ["export", "manifest-kg", "-o", str(out)] + _reg_opt(tmp_path)
        )
        assert result.exit_code == 0, result.output

        with tarfile.open(out, "r:gz") as tar:
            mf_file = tar.extractfile(MANIFEST_NAME)
            assert mf_file is not None
            manifest = json.load(mf_file)

        assert manifest["name"] == "manifest-kg"
        assert manifest["kind"] == "code"
        assert manifest["version"] == "1.2.3"
        assert manifest["builder_version"] == "9.9.9"
        assert manifest["tags"] == ["alpha", "beta"]
        assert manifest["has_sqlite"] is True
        assert manifest["has_lancedb"] is True

    def test_export_default_output_path(self, tmp_path, monkeypatch):
        entry = _make_built_kg(tmp_path, "default-out", with_sqlite=True)
        _register(tmp_path, entry)

        # Default path is ./<name>.kgrag.tar.gz — run CWD inside tmp_path.
        monkeypatch.chdir(tmp_path)
        result = CliRunner().invoke(cli, ["export", "default-out"] + _reg_opt(tmp_path))
        assert result.exit_code == 0, result.output

        expected = tmp_path / f"default-out{ARCHIVE_SUFFIX}"
        assert expected.exists()

    def test_export_not_found(self, tmp_path):
        result = CliRunner().invoke(
            cli,
            ["export", "ghost", "-o", str(tmp_path / "ghost.kgrag.tar.gz")] + _reg_opt(tmp_path),
        )
        assert result.exit_code != 0
        assert "Not found" in result.output

    def test_export_unbuilt_fails(self, tmp_path):
        entry = _make_built_kg(tmp_path, "unbuilt", with_sqlite=False, with_lancedb=False)
        _register(tmp_path, entry)

        result = CliRunner().invoke(
            cli,
            ["export", "unbuilt", "-o", str(tmp_path / "unbuilt.kgrag.tar.gz")]
            + _reg_opt(tmp_path),
        )
        assert result.exit_code != 0
        assert "Cannot export" in result.output

    def test_export_refuses_overwrite_without_force(self, tmp_path):
        entry = _make_built_kg(tmp_path, "noforce", with_sqlite=True)
        _register(tmp_path, entry)

        out = tmp_path / "noforce.kgrag.tar.gz"
        out.write_bytes(b"existing")

        result = CliRunner().invoke(cli, ["export", "noforce", "-o", str(out)] + _reg_opt(tmp_path))
        assert result.exit_code != 0
        assert "Refusing to overwrite" in result.output
        # Original content must be untouched
        assert out.read_bytes() == b"existing"

    def test_export_force_overwrites(self, tmp_path):
        entry = _make_built_kg(tmp_path, "force", with_sqlite=True)
        _register(tmp_path, entry)

        out = tmp_path / "force.kgrag.tar.gz"
        out.write_bytes(b"existing")

        result = CliRunner().invoke(
            cli, ["export", "force", "-o", str(out), "--force"] + _reg_opt(tmp_path)
        )
        assert result.exit_code == 0, result.output
        # Should be a valid tarball now (not the placeholder bytes).
        with tarfile.open(out, "r:gz") as tar:
            assert MANIFEST_NAME in tar.getnames()


# ---------------------------------------------------------------------------
# kgrag import
# ---------------------------------------------------------------------------


def _export_to(tmp_path: Path, name: str, **kg_kwargs) -> Path:
    """Build, register, export a KG; return the archive path."""
    entry = _make_built_kg(tmp_path, name, **kg_kwargs)
    _register(tmp_path, entry)
    out = tmp_path / f"{name}{ARCHIVE_SUFFIX}"
    result = CliRunner().invoke(cli, ["export", name, "-o", str(out)] + _reg_opt(tmp_path))
    assert result.exit_code == 0, result.output
    return out


class TestCLIImport:
    def test_import_unpacks_and_registers(self, tmp_path):
        archive = _export_to(tmp_path, "src-kg", with_sqlite=True, with_lancedb=True)

        # Fresh registry in a separate path so we exercise true registration.
        dest_root = tmp_path / "imported"
        reg2 = tmp_path / "registry2.sqlite"
        result = CliRunner().invoke(
            cli,
            [
                "import",
                str(archive),
                "--dest",
                str(dest_root),
                "--registry",
                str(reg2),
            ],
        )
        assert result.exit_code == 0, result.output
        assert (dest_root / "graph.sqlite").exists()
        assert (dest_root / "lancedb").is_dir()

        with KGRegistry(db_path=reg2) as reg:
            entry = reg.get("src-kg")
        assert entry is not None
        assert entry.kind == KGKind.CODE
        assert entry.sqlite_path == (dest_root / "graph.sqlite").resolve()
        assert entry.lancedb_path == (dest_root / "lancedb").resolve()
        assert "imported" in entry.tags
        assert "imported_from" in entry.metadata
        assert "imported_at" in entry.metadata

    def test_import_with_rename(self, tmp_path):
        archive = _export_to(tmp_path, "orig", with_sqlite=True)

        dest_root = tmp_path / "renamed"
        reg2 = tmp_path / "registry2.sqlite"
        result = CliRunner().invoke(
            cli,
            [
                "import",
                str(archive),
                "--name",
                "newname",
                "--dest",
                str(dest_root),
                "--registry",
                str(reg2),
            ],
        )
        assert result.exit_code == 0, result.output

        with KGRegistry(db_path=reg2) as reg:
            assert reg.get("newname") is not None
            assert reg.get("orig") is None

    def test_import_no_register(self, tmp_path):
        archive = _export_to(tmp_path, "no-reg", with_sqlite=True)

        dest_root = tmp_path / "no-reg-out"
        reg2 = tmp_path / "registry2.sqlite"
        result = CliRunner().invoke(
            cli,
            [
                "import",
                str(archive),
                "--dest",
                str(dest_root),
                "--no-register",
                "--registry",
                str(reg2),
            ],
        )
        assert result.exit_code == 0, result.output
        assert (dest_root / "graph.sqlite").exists()

        with KGRegistry(db_path=reg2) as reg:
            assert reg.get("no-reg") is None

    def test_import_refuses_existing_dest(self, tmp_path):
        archive = _export_to(tmp_path, "collide", with_sqlite=True)

        dest_root = tmp_path / "collide-out"
        dest_root.mkdir()
        (dest_root / "leave_me_alone").write_text("untouched")

        result = CliRunner().invoke(
            cli,
            [
                "import",
                str(archive),
                "--dest",
                str(dest_root),
                "--registry",
                str(tmp_path / "registry2.sqlite"),
            ],
        )
        assert result.exit_code != 0
        assert "Destination exists" in result.output
        # Pre-existing file must still be there.
        assert (dest_root / "leave_me_alone").read_text() == "untouched"

    def test_import_force_overwrites_dest(self, tmp_path):
        archive = _export_to(tmp_path, "force-dest", with_sqlite=True)

        dest_root = tmp_path / "force-dest-out"
        dest_root.mkdir()
        (dest_root / "stale.txt").write_text("stale")

        result = CliRunner().invoke(
            cli,
            [
                "import",
                str(archive),
                "--dest",
                str(dest_root),
                "--force",
                "--registry",
                str(tmp_path / "registry2.sqlite"),
            ],
        )
        assert result.exit_code == 0, result.output
        # Old file is gone after force-overwrite, archive contents are in place.
        assert not (dest_root / "stale.txt").exists()
        assert (dest_root / "graph.sqlite").exists()

    def test_import_bad_archive_no_manifest(self, tmp_path):
        bad = tmp_path / "bogus.kgrag.tar.gz"
        # Build a tarball that contains *no* manifest.
        payload = tmp_path / "junk.txt"
        payload.write_text("not a manifest")
        with tarfile.open(bad, "w:gz") as tar:
            tar.add(payload, arcname="junk.txt")

        result = CliRunner().invoke(
            cli,
            [
                "import",
                str(bad),
                "--dest",
                str(tmp_path / "should-not-be-created"),
                "--registry",
                str(tmp_path / "registry2.sqlite"),
            ],
        )
        assert result.exit_code != 0
        assert "Bad archive" in result.output

    def test_import_warns_on_manifest_version_mismatch(self, tmp_path):
        # Hand-roll an archive with a future manifest version.
        archive = tmp_path / "future.kgrag.tar.gz"
        sqlite_src = tmp_path / "graph.sqlite"
        sqlite_src.write_bytes(b"FAKE")
        manifest = {
            "manifest_version": MANIFEST_VERSION + 99,
            "exported_at": "2099-01-01T00:00:00+00:00",
            "name": "future-kg",
            "kind": "code",
            "version": "x",
            "builder_version": "y",
            "tags": [],
            "metadata": {},
            "has_sqlite": True,
            "has_lancedb": False,
        }
        mf_path = tmp_path / "manifest.json"
        mf_path.write_text(json.dumps(manifest))
        with tarfile.open(archive, "w:gz") as tar:
            tar.add(mf_path, arcname=MANIFEST_NAME)
            tar.add(sqlite_src, arcname="graph.sqlite")

        dest_root = tmp_path / "future-out"
        result = CliRunner().invoke(
            cli,
            [
                "import",
                str(archive),
                "--dest",
                str(dest_root),
                "--registry",
                str(tmp_path / "registry2.sqlite"),
            ],
        )
        # Import proceeds, but warns.
        assert result.exit_code == 0, result.output
        assert "Warning" in result.output
        assert (dest_root / "graph.sqlite").exists()


# ---------------------------------------------------------------------------
# Round-trip
# ---------------------------------------------------------------------------


class TestRoundTrip:
    def test_export_then_import_preserves_data(self, tmp_path):
        # Source: build, register, export
        sqlite_payload = b"the original bits\n"
        lance_payload = b"vectors here\n"
        entry = _make_built_kg(
            tmp_path,
            "round",
            with_sqlite=True,
            with_lancedb=True,
            sqlite_bytes=sqlite_payload,
            lancedb_files={"chunks.lance": lance_payload},
        )
        _register(tmp_path, entry)

        archive = tmp_path / f"round{ARCHIVE_SUFFIX}"
        r = CliRunner().invoke(cli, ["export", "round", "-o", str(archive)] + _reg_opt(tmp_path))
        assert r.exit_code == 0, r.output

        # Destination: import into a fresh registry/dest, verify bytes match.
        dest_root = tmp_path / "round-out"
        reg_dest = tmp_path / "registry-dest.sqlite"
        r2 = CliRunner().invoke(
            cli,
            [
                "import",
                str(archive),
                "--dest",
                str(dest_root),
                "--registry",
                str(reg_dest),
            ],
        )
        assert r2.exit_code == 0, r2.output

        assert (dest_root / "graph.sqlite").read_bytes() == sqlite_payload
        assert (dest_root / "lancedb" / "chunks.lance").read_bytes() == lance_payload

        with KGRegistry(db_path=reg_dest) as reg:
            imported = reg.get("round")
        assert imported is not None
        assert imported.version == "1.2.3"
        assert imported.builder_version == "9.9.9"
        # Original tags preserved; "imported" appended.
        assert set(["alpha", "beta", "imported"]).issubset(set(imported.tags))
        # Original metadata preserved alongside imported_* keys.
        assert imported.metadata.get("description") == "fixture KG"
