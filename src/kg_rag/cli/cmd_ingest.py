"""
cmd_ingest.py

kgrag ingest — turn loose documents into a registered, queryable KG.

Until now KGRAG could only *read* corpora that already existed as Markdown or
plain text on disk.  This command supplies the missing front end: point it at
PDFs, Word documents, EPUBs, spreadsheets, slide decks or a directory of mixed
formats, and it normalizes them to Markdown, builds a DocKG over the result,
and registers that KG — one command from raw files to federated query.

The pipeline runs in three stages, each independently skippable:

    stage    — convert sources to Markdown in a staging corpus (kg_utils.ingest)
    build    — run ``dockg build`` over the staged corpus
    register — record the built KG in the KGRAG registry

Conversion is provided by ``anydoc`` via the ``kgmodule-utils[ingest]`` extra.
Documents it cannot convert — most often scanned PDFs, which need OCR — are
recorded in the staging manifest with a reason rather than silently dropped,
so a corpus always accounts for every file it was shown.
"""

from __future__ import annotations

import shutil
import subprocess
from datetime import date
from pathlib import Path

import click
from rich import box
from rich.console import Console
from rich.table import Table

from kg_rag.cli.group import cli
from kg_rag.cli.options import registry_option
from kg_rag.config import read_pyproject_version
from kg_rag.corpus_registry import CorpusRegistry
from kg_rag.primitives import KGEntry, KGKind
from kg_rag.registry import KGRegistry

console = Console()

#: Marker directory DocKG writes its databases into.
_DOCKG_DIR = ".dockg"


@cli.command("ingest")
@click.argument(
    "sources",
    nargs=-1,
    required=True,
    type=click.Path(exists=True, resolve_path=True),
)
@click.option(
    "--into",
    "staging_root",
    required=True,
    metavar="PATH",
    type=click.Path(file_okay=False, resolve_path=True),
    help="Directory to stage the normalized Markdown corpus into.",
)
@click.option(
    "--name",
    "kg_name",
    default=None,
    metavar="NAME",
    help="Name to register the KG under (default: <staging-dir>-doc).",
)
@click.option(
    "--recreate",
    is_flag=True,
    help="Wipe the staging corpus before ingesting.",
)
@click.option(
    "--reingest",
    is_flag=True,
    help="Re-convert sources already staged (use after a converter upgrade).",
)
@click.option("--build/--no-build", default=True, show_default=True, help="Run dockg build.")
@click.option(
    "--register/--no-register",
    "do_register",
    default=True,
    show_default=True,
    help="Register the built KG in the KGRAG registry.",
)
@click.option(
    "--corpus",
    "corpus_name",
    default=None,
    metavar="NAME",
    help="Add the registered KG to this existing corpus.",
)
@click.option(
    "--show-skipped/--no-show-skipped",
    default=True,
    show_default=True,
    help="List documents that could not be ingested, with reasons.",
)
@registry_option
def ingest(  # noqa: PLR0913 — one option per pipeline stage; a config object would hide the CLI surface
    sources,
    staging_root,
    kg_name,
    recreate,
    reingest,
    build,
    do_register,
    corpus_name,
    show_skipped,
    registry,
):
    """Ingest documents into a staged corpus, build a KG, and register it.

    Accepts Markdown, plain text and reStructuredText directly, and converts
    Word, PowerPoint, Excel, OpenDocument, RTF, EPUB, CSV and text-based PDF
    via anydoc.  Directories are walked recursively.

    Re-running is idempotent: sources already staged are skipped by content
    digest, so pointing this at a growing folder only ingests what is new.

    \b
    SOURCES  One or more files and/or directories to ingest.

    Examples:

    \b
        kgrag ingest ~/Documents/specs --into ~/corpora/specs
        kgrag ingest report.pdf notes.docx --into ~/corpora/mixed --name mixed-docs
        kgrag ingest ~/Downloads --into ~/corpora/inbox --no-build
        kgrag ingest ~/papers --into ~/corpora/papers --corpus research
        kgrag ingest ~/papers --into ~/corpora/papers --reingest
    """
    try:
        from kg_utils.ingest import IngestPipeline
    except ImportError:
        console.print(
            "[red]Document ingestion is unavailable.[/red] "
            "Install the ingest extra:\n\n"
            "    pip install 'kgmodule-utils[ingest]'\n"
        )
        raise SystemExit(1) from None

    staging = Path(staging_root)
    name = kg_name or f"{staging.name}-doc"

    # ---------------------------------------------------------------- stage
    console.rule("[bold]stage[/bold] — converting sources to Markdown")
    for source in sources:
        console.print(f"  source: {source}")
    console.print(f"  staging: [bold]{staging}[/bold]")

    pipeline = IngestPipeline(staging_root=staging)
    stats = pipeline.run(
        list(sources),
        recreate=recreate,
        skip_existing=not reingest,
    )

    console.print(
        f"\n  [green]{stats.ingested} staged[/green] · "
        f"[yellow]{stats.skipped} skipped[/yellow] · "
        f"[red]{stats.failed} failed[/red] "
        f"(of {stats.considered} examined)"
    )

    if show_skipped:
        _print_problems(stats)

    if stats.ingested == 0 and not _staging_has_documents(staging):
        console.print(
            "\n[yellow]Nothing staged and the corpus is empty — stopping before build.[/yellow]"
        )
        raise SystemExit(1)

    # ---------------------------------------------------------------- build
    built_ok = False
    if build:
        console.rule("[bold]build[/bold] — dockg")
        if shutil.which("dockg") is None:
            console.print(
                "[yellow]Skipping build[/yellow]: [bold]dockg[/bold] not found on PATH.\n"
                "Install it with: pip install doc-kg"
            )
        else:
            cmd = ["dockg", "build", "--repo", str(staging)]
            console.print(f"Running: {' '.join(cmd)}")
            try:
                subprocess.run(cmd, check=True, cwd=staging)
                built_ok = True
            except subprocess.CalledProcessError:
                console.print("[red]Build failed.[/red]")
    else:
        console.print("\n[dim]Skipping build (--no-build).[/dim]")

    # ------------------------------------------------------------- register
    entry: KGEntry | None = None
    if do_register and built_ok:
        console.rule("[bold]register[/bold]")
        entry = _register(staging, name, registry)
        console.print(f"[green]Registered[/green] [bold]{name}[/bold]")
    elif do_register and not built_ok:
        console.print("\n[dim]Not registering: no successful build to register.[/dim]")

    if corpus_name and entry is not None:
        _add_to_corpus(entry, corpus_name, registry)

    _print_summary(stats, staging, name, built_ok, entry)


def _staging_has_documents(staging: Path) -> bool:
    """Return ``True`` if *staging* already holds staged documents.

    Lets a re-run whose sources were all duplicates still proceed to build,
    rather than treating "nothing new" as "nothing there".

    :param staging: Staging corpus root.
    :return: Whether any staged document file is present.
    """
    if not staging.exists():
        return False
    return any(
        p.is_file() and p.suffix.lower() in {".md", ".txt", ".rst"} for p in staging.rglob("*")
    )


def _print_problems(stats) -> None:
    """Print the documents that were not staged, with their reasons.

    The point of the ingest manifest: a corpus that explains its own gaps.

    :param stats: Stats returned by the ingest run.
    """
    problems = [r for r in stats.records if r.status != "ingested"]
    # A duplicate is expected on a re-run and is not a gap worth reporting.
    problems = [r for r in problems if "already ingested" not in r.reason]
    if not problems:
        return

    table = Table(title="Not ingested", box=box.ROUNDED, show_lines=False)
    table.add_column("Document", style="bold")
    table.add_column("Status", justify="center")
    table.add_column("Reason", style="dim", overflow="fold")

    _STATUS_FMT = {
        "skipped": "[yellow]skipped[/yellow]",
        "failed": "[red]failed[/red]",
    }
    for record in problems:
        table.add_row(
            Path(record.source_path).name,
            _STATUS_FMT.get(record.status, record.status),
            record.reason,
        )
    console.print()
    console.print(table)


def _register(staging: Path, name: str, registry: str | None) -> KGEntry:
    """Register the DocKG built over *staging* in the KGRAG registry.

    :param staging: Staging corpus root, which is also the DocKG repo root.
    :param name: Name to register the KG under.
    :param registry: Registry path override, or ``None`` for the default.
    :return: The registered entry.
    """
    kg_dir = staging / _DOCKG_DIR
    sqlite_path = kg_dir / "graph.sqlite"
    vectors_path = kg_dir / "vectors.sqlite"
    lancedb_path = kg_dir / "lancedb"

    entry = KGEntry(
        name=name,
        kind=KGKind.from_str("doc"),
        repo_path=staging,
        venv_path=staging / ".venv",
        sqlite_path=sqlite_path if sqlite_path.exists() else None,
        vectors_path=vectors_path if vectors_path.exists() else None,
        lancedb_path=lancedb_path if lancedb_path.exists() else None,
        version=read_pyproject_version(staging),
        tags=["ingested", date.today().isoformat()],
    )

    with KGRegistry(db_path=Path(registry) if registry else None) as reg:
        reg.register(entry)
    return entry


def _add_to_corpus(entry: KGEntry, corpus_name: str, registry: str | None) -> None:
    """Add *entry* to an existing corpus.

    :param entry: The registered KG entry.
    :param corpus_name: Name of the corpus to add it to.
    :param registry: Registry path override, or ``None`` for the default.
    """
    db_path = Path(registry).resolve() if registry else None
    with KGRegistry(db_path=db_path) as kg_reg, CorpusRegistry(db_path=db_path) as corp_reg:
        registered = kg_reg.get(entry.name)
        if registered is None:
            console.print(f"[yellow]Could not resolve {entry.name!r} for corpus add.[/yellow]")
            return
        if corp_reg.add_kg(corpus_name, registered.id) is None:
            console.print(f"[red]Corpus not found[/red]: {corpus_name!r}")
            return
    console.print(
        f"[green]Added[/green] [bold]{entry.name}[/bold] to corpus [bold]{corpus_name}[/bold]"
    )


def _print_summary(
    stats,
    staging: Path,
    name: str,
    built_ok: bool,
    entry: KGEntry | None,
) -> None:
    """Print the end-of-run summary table.

    :param stats: Stats returned by the ingest run.
    :param staging: Staging corpus root.
    :param name: KG name.
    :param built_ok: Whether the build succeeded.
    :param entry: The registered entry, or ``None`` if not registered.
    """
    console.rule("Summary")
    table = Table(title=f"KG Ingest — {name}", box=box.ROUNDED)
    table.add_column("Stage", style="magenta")
    table.add_column("Result", justify="left")

    table.add_row("stage", f"{stats.ingested} staged of {stats.considered} examined")
    table.add_row("corpus", str(staging))
    table.add_row("build", "[green]ok[/green]" if built_ok else "[yellow]not built[/yellow]")
    table.add_row(
        "register",
        f"[green]{name}[/green]" if entry is not None else "[yellow]not registered[/yellow]",
    )
    if stats.failed or stats.skipped:
        table.add_row(
            "gaps",
            f"see {staging / '.ingest' / 'manifest.json'}",
        )
    console.print(table)
