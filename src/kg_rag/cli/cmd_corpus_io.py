"""
cmd_corpus_io.py

Corpus export / import — make a registered KG portable as a single archive.

A KGRAG corpus is the pair (SQLite graph, LanceDB index). These commands
bundle that pair plus a manifest into a ``.kgrag.tar.gz`` archive that can
be copied to another machine, mirrored, or shipped to long-term storage,
and re-registered with a single command.

Archive layout::

    <archive>.kgrag.tar.gz
        manifest.json          # KG metadata (name, kind, versions, tags)
        graph.sqlite           # structural KG (if present)
        lancedb/               # semantic vector index (if present)
"""

from __future__ import annotations

import json
import shutil
import tarfile
import tempfile
from datetime import UTC, datetime
from pathlib import Path

import click
from rich.console import Console

from kg_rag.cli.group import cli
from kg_rag.cli.options import registry_option
from kg_rag.primitives import KGEntry, KGKind
from kg_rag.registry import KGRegistry

console = Console()

MANIFEST_NAME = "manifest.json"
ARCHIVE_SUFFIX = ".kgrag.tar.gz"
MANIFEST_VERSION = 1


def _build_manifest(entry: KGEntry) -> dict:
    """Serialize a KGEntry into a portable, path-free manifest dict.

    :param entry: The registry entry being exported.
    :return: A JSON-serializable manifest dictionary.
    """
    return {
        "manifest_version": MANIFEST_VERSION,
        "exported_at": datetime.now(UTC).isoformat(),
        "name": entry.name,
        "kind": entry.kind.value,
        "version": entry.version,
        "builder_version": entry.builder_version,
        "tags": list(entry.tags),
        "metadata": dict(entry.metadata),
        "has_sqlite": entry.sqlite_path is not None and entry.sqlite_path.exists(),
        "has_lancedb": entry.lancedb_path is not None and entry.lancedb_path.exists(),
    }


@cli.command("export")
@click.argument("name_or_id")
@click.option(
    "--output",
    "-o",
    "output_path",
    type=click.Path(dir_okay=False, resolve_path=True),
    default=None,
    help="Output archive path. Defaults to ./<name>.kgrag.tar.gz",
)
@click.option(
    "--force",
    is_flag=True,
    help="Overwrite the output archive if it already exists.",
)
@registry_option
def export_corpus(name_or_id: str, output_path: str | None, force: bool, registry: str | None):
    """Export a registered KG as a portable .kgrag.tar.gz archive.

    \b
    NAME_OR_ID  Name or UUID of the KG to export.

    Example:

    \b
        kgrag export gutenberg-all
        kgrag export my-codekg -o /backups/codekg-2026-05.kgrag.tar.gz
    """
    with KGRegistry(db_path=Path(registry) if registry else None) as reg:
        entry = reg.get(name_or_id)

    if entry is None:
        console.print(f"[red]Not found[/red]: {name_or_id!r}")
        raise SystemExit(1)

    if not entry.is_built:
        console.print(
            f"[red]Cannot export[/red] [bold]{entry.name}[/bold]: no SQLite or LanceDB on disk."
        )
        raise SystemExit(1)

    # Resolve output path
    out = (
        Path(output_path).resolve() if output_path else Path.cwd() / f"{entry.name}{ARCHIVE_SUFFIX}"
    )
    if out.exists() and not force:
        console.print(
            f"[red]Refusing to overwrite[/red] {out}\nPass [bold]--force[/bold] to overwrite."
        )
        raise SystemExit(1)
    out.parent.mkdir(parents=True, exist_ok=True)

    manifest = _build_manifest(entry)

    console.print(f"Exporting [bold]{entry.label}[/bold]...")
    with tarfile.open(out, "w:gz") as tar:
        # Manifest first so a partial read can identify the archive
        with tempfile.NamedTemporaryFile("w", suffix=".json", delete=False) as mf:
            json.dump(manifest, mf, indent=2)
            mf_path = Path(mf.name)
        try:
            tar.add(mf_path, arcname=MANIFEST_NAME)
        finally:
            mf_path.unlink(missing_ok=True)

        sqlite_path = entry.sqlite_path
        if manifest["has_sqlite"] and sqlite_path is not None:
            console.print(f"  + graph.sqlite   ({sqlite_path})")
            tar.add(sqlite_path, arcname="graph.sqlite")

        lancedb_path = entry.lancedb_path
        if manifest["has_lancedb"] and lancedb_path is not None:
            console.print(f"  + lancedb/       ({lancedb_path})")
            tar.add(lancedb_path, arcname="lancedb")

    size_mb = out.stat().st_size / (1024 * 1024)
    console.print(f"[green]Wrote[/green] {out}  [dim]({size_mb:.1f} MB)[/dim]")


@cli.command("import")
@click.argument(
    "archive_path",
    type=click.Path(exists=True, dir_okay=False, resolve_path=True),
)
@click.option(
    "--name",
    "new_name",
    default=None,
    help="Override the corpus name (useful on collision).",
)
@click.option(
    "--dest",
    "dest_dir",
    type=click.Path(file_okay=False, resolve_path=True),
    default=None,
    help="Destination directory for the unpacked KG. Defaults to ~/.kgrag/corpora/<name>/",
)
@click.option(
    "--no-register",
    is_flag=True,
    help="Unpack only — do not add to the registry.",
)
@click.option(
    "--force",
    is_flag=True,
    help="Overwrite an existing destination directory.",
)
@registry_option
def import_corpus(
    archive_path: str,
    new_name: str | None,
    dest_dir: str | None,
    no_register: bool,
    force: bool,
    registry: str | None,
):
    """Import a .kgrag.tar.gz archive and register it.

    \b
    ARCHIVE_PATH  Path to a .kgrag.tar.gz archive produced by `kgrag export`.

    Example:

    \b
        kgrag import gutenberg-all.kgrag.tar.gz
        kgrag import codekg-2026-05.kgrag.tar.gz --name codekg-restored
    """
    archive = Path(archive_path).resolve()

    # Peek at the manifest before extracting anywhere
    with tarfile.open(archive, "r:gz") as tar:
        try:
            mf_member = tar.getmember(MANIFEST_NAME)
        except KeyError as exc:
            console.print(f"[red]Bad archive[/red]: no {MANIFEST_NAME} found.")
            raise SystemExit(1) from exc
        mf_file = tar.extractfile(mf_member)
        if mf_file is None:
            console.print(f"[red]Bad archive[/red]: could not read {MANIFEST_NAME}.")
            raise SystemExit(1)
        manifest = json.load(mf_file)

    if manifest.get("manifest_version") != MANIFEST_VERSION:
        console.print(
            f"[yellow]Warning[/yellow]: manifest version "
            f"{manifest.get('manifest_version')!r} != expected {MANIFEST_VERSION}. "
            "Attempting import anyway."
        )

    corpus_name = new_name or manifest["name"]
    kind = manifest["kind"]

    # Resolve destination
    if dest_dir:
        dest = Path(dest_dir).resolve()
    else:
        dest = Path.home() / ".kgrag" / "corpora" / corpus_name

    if dest.exists():
        if not force:
            console.print(
                f"[red]Destination exists[/red]: {dest}\n"
                "Pass [bold]--force[/bold] to overwrite, or use [bold]--dest[/bold]."
            )
            raise SystemExit(1)
        shutil.rmtree(dest)
    dest.mkdir(parents=True, exist_ok=False)

    console.print(f"Importing [bold]{manifest['name']}[/bold] ({kind}) → [dim]{dest}[/dim]")

    # Extract everything except the manifest (already parsed)
    with tarfile.open(archive, "r:gz") as tar:
        for member in tar.getmembers():
            if member.name == MANIFEST_NAME:
                continue
            tar.extract(member, dest, filter="data")

    # Resolve unpacked artifact paths
    sqlite_path = (dest / "graph.sqlite") if manifest.get("has_sqlite") else None
    lancedb_path = (dest / "lancedb") if manifest.get("has_lancedb") else None

    if sqlite_path and not sqlite_path.exists():
        console.print("[yellow]Warning[/yellow]: manifest claimed SQLite but file is missing.")
        sqlite_path = None
    if lancedb_path and not lancedb_path.exists():
        console.print("[yellow]Warning[/yellow]: manifest claimed LanceDB but dir is missing.")
        lancedb_path = None

    console.print(f"  ✓ unpacked to {dest}")
    if sqlite_path:
        console.print(f"  ✓ graph.sqlite   ({sqlite_path.stat().st_size / 1024 / 1024:.1f} MB)")
    if lancedb_path:
        console.print("  ✓ lancedb/")

    if no_register:
        console.print("[dim]Skipping registration (--no-register).[/dim]")
        return

    # Re-register. repo_path = dest (the corpus is self-describing now).
    entry = KGEntry(
        name=corpus_name,
        kind=KGKind.from_str(kind),
        repo_path=dest,
        venv_path=dest / ".venv",  # may not exist; that's fine
        sqlite_path=sqlite_path,
        lancedb_path=lancedb_path,
        version=manifest.get("version", "unknown"),
        builder_version=manifest.get("builder_version", "unknown"),
        tags=list(manifest.get("tags", [])) + ["imported"],
        metadata={
            **manifest.get("metadata", {}),
            "imported_from": str(archive),
            "imported_at": datetime.now(UTC).isoformat(),
            "original_export_at": manifest.get("exported_at"),
        },
    )

    with KGRegistry(db_path=Path(registry) if registry else None) as reg:
        reg.register(entry)

    console.print(
        f"[green]Registered[/green] [bold]{corpus_name}[/bold] ({kind}) — "
        f"use [bold]kgrag info {corpus_name}[/bold] to inspect."
    )
