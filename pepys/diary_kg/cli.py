"""cli.py — Click CLI for DiaryKG.

Commands::

    diarykg build    [ROOT] --source <file>   # ingest + index
    diarykg query    QUERY  [ROOT]            # semantic search
    diarykg pack     QUERY  [ROOT]            # LLM-ready snippets
    diarykg analyze  [ROOT]                   # Markdown analysis report
    diarykg status   [ROOT]                   # quick health check
    diarykg snapshot list   [ROOT]
    diarykg snapshot save   [ROOT] [--label]
    diarykg snapshot show   KEY [ROOT]
    diarykg snapshot diff   KEY_A KEY_B [ROOT]
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import click
from rich.console import Console
from rich.table import Table
from rich import box

console = Console()

_ROOT_ARG = click.argument(
    "root",
    metavar="ROOT",
    default=".",
    type=click.Path(file_okay=False, resolve_path=True),
)


def _kg(root: str, source_file: str | None = None):
    """Instantiate DiaryKG, importing lazily to keep CLI startup fast."""
    from diary_kg.kg import DiaryKG  # pylint: disable=import-outside-toplevel
    return DiaryKG(root, source_file=source_file)


# ---------------------------------------------------------------------------
# Root group
# ---------------------------------------------------------------------------

@click.group()
def cli():
    """DiaryKG — knowledge graph for diaries and journals."""


# ---------------------------------------------------------------------------
# build
# ---------------------------------------------------------------------------

@cli.command("build")
@_ROOT_ARG
@click.option("--source", "-s", "source_file", default=None,
              help="Diary .txt path relative to ROOT (required on first build).")
@click.option("--wipe", is_flag=True, help="Delete existing corpus + DBs before rebuilding.")
@click.option("--batch-size", "-b", default=0, show_default=True,
              help="Entries to sample (0 = all).")
@click.option("--seed", default=None, type=int, help="RNG seed.")
@click.option("--max-chunks", "-m", default=3, show_default=True,
              help="Max chunks per diary entry.")
@click.option("--chunking",
              type=click.Choice(["sentence_group", "semantic", "hybrid"]),
              default="sentence_group", show_default=True)
@click.option("--chunk-size", default=512, show_default=True,
              help="Max characters per chunk.")
@click.option("--workers", "-w", default=1, show_default=True,
              help="Parallel workers for feature extraction.")
@click.option("--topics-file", default=None, help="YAML topics override.")
@click.option("--snapshot", "save_snapshot", is_flag=True,
              help="Capture a snapshot after a successful build.")
def build(root, source_file, wipe, batch_size, seed, max_chunks,
          chunking, chunk_size, workers, topics_file, save_snapshot):
    """Build the DiaryKG: ingest diary → index into SQLite + LanceDB.

    \b
    ROOT  Project root directory (default: current directory).

    Examples:

    \b
        diarykg build . --source pepys_diary.txt
        diarykg build . --source pepys_diary.txt --wipe --batch-size 0
        diarykg build /projects/pepys --source pepys_diary.txt --snapshot
    """
    kg = _kg(root, source_file)
    try:
        n = kg.build(
            batch_size=batch_size,
            seed=seed,
            max_chunks_per_entry=max_chunks,
            chunking_strategy=chunking,
            chunk_size=chunk_size,
            workers=workers,
            topics_file=topics_file,
            wipe=wipe,
        )
    except (ValueError, FileNotFoundError) as exc:
        console.print(f"[red]Error:[/red] {exc}")
        sys.exit(1)
    except Exception as exc:  # pylint: disable=broad-exception-caught
        import traceback  # pylint: disable=import-outside-toplevel
        console.print(f"[red]Error:[/red] {exc}")
        traceback.print_exc()
        sys.exit(1)

    kg_dir = Path(root) / DiaryKGRef.KG_DIR
    console.print(f"\n[green]✓ DiaryKG built[/green]  {n} chunks indexed")
    console.print(f"  Corpus  : {kg_dir}/corpus/")
    console.print(f"  SQLite  : {kg_dir}/graph.sqlite")
    console.print(f"  LanceDB : {kg_dir}/lancedb/")

    if save_snapshot:
        try:
            snap = kg.snapshot_save()
            console.print(f"\n[green]✓ Snapshot saved[/green]  key: {snap['key'][:12]}...")
        except Exception as exc:  # pylint: disable=broad-exception-caught
            console.print(f"[yellow]Warning:[/yellow] snapshot failed: {exc}")


class DiaryKGRef:
    KG_DIR = ".diarykg"


# ---------------------------------------------------------------------------
# query
# ---------------------------------------------------------------------------

@cli.command("query")
@click.argument("query_str", metavar="QUERY")
@_ROOT_ARG
@click.option("-k", default=8, show_default=True, help="Number of results.")
@click.option("--json", "as_json", is_flag=True, help="Output raw JSON.")
def query(query_str, root, k, as_json):
    """Semantic search over the diary corpus.

    \b
    QUERY  Natural-language query string.
    ROOT   Project root directory (default: current directory).

    Examples:

    \b
        diarykg query "Pepys at the theatre"
        diarykg query "Navy affairs" . -k 12
    """
    kg = _kg(root)
    try:
        hits = kg.query(query_str, k=k)
    except RuntimeError as exc:
        console.print(f"[red]Error:[/red] {exc}")
        sys.exit(1)

    if as_json:
        click.echo(json.dumps(hits, indent=2, default=str))
        return

    if not hits:
        console.print("[yellow]No results.[/yellow]")
        return

    table = Table(title=f"DiaryKG Query: {query_str!r}", box=box.ROUNDED, show_lines=True)
    table.add_column("#", style="dim", width=3)
    table.add_column("Score", width=6)
    table.add_column("Date", width=16)
    table.add_column("Category", width=14)
    table.add_column("Context", width=10)
    table.add_column("Summary")
    table.add_column("Source", style="dim")

    for i, h in enumerate(hits, 1):
        ts = (h.get("timestamp") or "")[:10]
        summary = (h.get("summary") or "")[:120]
        table.add_row(
            str(i),
            f"{h.get('score', 0.0):.3f}",
            ts,
            h.get("category", ""),
            h.get("context", ""),
            summary,
            h.get("source_file", ""),
        )

    console.print(table)


# ---------------------------------------------------------------------------
# pack
# ---------------------------------------------------------------------------

@cli.command("pack")
@click.argument("query_str", metavar="QUERY")
@_ROOT_ARG
@click.option("-k", default=8, show_default=True, help="Number of snippets.")
@click.option("--output", "-o", default=None, type=click.Path(),
              help="Write output to file instead of stdout.")
@click.option("--json", "as_json", is_flag=True, help="Output raw JSON.")
def pack(query_str, root, k, output, as_json):
    """Extract LLM-ready diary snippets matching a query.

    \b
    QUERY  Natural-language query string.
    ROOT   Project root directory (default: current directory).

    Examples:

    \b
        diarykg pack "Pepys wife Elizabeth"
        diarykg pack "Navy corruption" . -k 12 --output context.md
    """
    kg = _kg(root)
    try:
        snippets = kg.pack(query_str, k=k)
    except RuntimeError as exc:
        console.print(f"[red]Error:[/red] {exc}")
        sys.exit(1)

    if as_json:
        text = json.dumps(snippets, indent=2, default=str)
    else:
        parts = [f"# DiaryKG Pack: {query_str!r}\n"]
        for s in snippets:
            ts = s.get("timestamp") or ""
            src = s.get("source_file") or ""
            header = f"## {src}"
            if ts:
                header += f" @ {ts[:10]}"
            parts.append(header)
            parts.append(f"```\n{s.get('content', '')}\n```")
        text = "\n\n".join(parts)

    if output:
        Path(output).write_text(text, encoding="utf-8")
        console.print(f"[green]✓[/green] Pack written to {output}  ({len(snippets)} snippets)")
    else:
        click.echo(text)


# ---------------------------------------------------------------------------
# analyze
# ---------------------------------------------------------------------------

@cli.command("analyze")
@_ROOT_ARG
@click.option("--output", "-o", default=None, type=click.Path(),
              help="Write Markdown report to file.")
def analyze(root, output):
    """Generate a Markdown analysis report for the diary corpus.

    \b
    ROOT  Project root directory (default: current directory).

    Examples:

    \b
        diarykg analyze
        diarykg analyze /projects/pepys --output analysis/report.md
    """
    kg = _kg(root)
    if not kg.is_built():
        console.print("[red]Error:[/red] DiaryKG is not built. Run [bold]diarykg build[/bold] first.")
        sys.exit(1)

    report = kg.analyze()

    if output:
        Path(output).write_text(report, encoding="utf-8")
        console.print(f"[green]✓[/green] Report written to {output}")
    else:
        console.print(report)


# ---------------------------------------------------------------------------
# status
# ---------------------------------------------------------------------------

@cli.command("status")
@_ROOT_ARG
def status(root):
    """Show DiaryKG health without loading the full database.

    \b
    ROOT  Project root directory (default: current directory).
    """
    kg = _kg(root)
    kg_dir = Path(root) / ".diarykg"

    def _size(p: Path) -> str:
        if not p.exists():
            return "missing"
        if p.is_dir():
            total = sum(f.stat().st_size for f in p.rglob("*") if f.is_file())
        else:
            total = p.stat().st_size
        for unit in ("B", "KB", "MB", "GB"):
            if total < 1024:
                return f"{total:.1f} {unit}"
            total /= 1024
        return f"{total:.1f} TB"

    config = kg._read_config()  # pylint: disable=protected-access
    corpus_dir = kg_dir / "corpus"
    md_count = len(list(corpus_dir.glob("*.md"))) if corpus_dir.exists() else 0
    snaps = len(kg.snapshot_list())

    built_str = "[green]yes[/green]" if kg.is_built() else "[red]no[/red]"

    console.print(f"\n[bold]DiaryKG status[/bold]  {root}")
    console.print(f"  Built       : {built_str}")
    console.print(f"  Source file : {config.get('source_file', '[dim]unknown[/dim]')}")
    console.print(f"  Built at    : {config.get('built_at', '[dim]n/a[/dim]')}")
    console.print(f"  Corpus      : {md_count} .md files  ({_size(corpus_dir)})")
    console.print(f"  SQLite      : {_size(kg_dir / 'graph.sqlite')}")
    console.print(f"  LanceDB     : {_size(kg_dir / 'lancedb')}")
    console.print(f"  Snapshots   : {snaps}")
    console.print()


# ---------------------------------------------------------------------------
# snapshot group
# ---------------------------------------------------------------------------

@cli.group("snapshot")
def snapshot():
    """Manage DiaryKG point-in-time snapshots."""


@snapshot.command("save")
@_ROOT_ARG
@click.option("--version", "-v", default="0.1.0", show_default=True, help="Version string for this snapshot.")
@click.option("--label", "-l", default=None, help="Human-readable label for this snapshot.")
def snapshot_save(root, version, label):
    """Capture a snapshot of current corpus metrics.

    \b
    ROOT  Project root directory (default: current directory).

    Examples:

    \b
        diarykg snapshot save
        diarykg snapshot save . --label "after adding 1667 entries"
    """
    kg = _kg(root)
    try:
        snap = kg.snapshot_save(version=version, label=label)
    except RuntimeError as exc:
        console.print(f"[red]Error:[/red] {exc}")
        sys.exit(1)

    m = snap.get("metrics", {})
    console.print(f"[green]✓ Snapshot saved[/green]")
    console.print(f"  Key     : {snap['key']}")
    console.print(f"  Branch  : {snap.get('branch')}")
    console.print(f"  Chunks  : {m.get('chunk_count')}")
    console.print(f"  Entries : {m.get('entry_count')}")
    if snap.get("vs_previous"):
        d = snap["vs_previous"]
        console.print(f"  Δ chunks  : {d.get('chunks'):+d}")
        console.print(f"  Δ entries : {d.get('entries'):+d}")


@snapshot.command("list")
@_ROOT_ARG
@click.option("--json", "as_json", is_flag=True, help="Output raw JSON.")
def snapshot_list(root, as_json):
    """List all snapshots for this DiaryKG.

    \b
    ROOT  Project root directory (default: current directory).
    """
    kg = _kg(root)
    snaps = kg.snapshot_list()

    if as_json:
        click.echo(json.dumps(snaps, indent=2, default=str))
        return

    if not snaps:
        console.print("[yellow]No snapshots yet.[/yellow]  Run [bold]diarykg snapshot save[/bold].")
        return

    table = Table(title="DiaryKG Snapshots", box=box.ROUNDED)
    table.add_column("#", style="dim", width=3)
    table.add_column("Key", width=14)
    table.add_column("Branch", width=14)
    table.add_column("Timestamp", width=22)
    table.add_column("Label")
    table.add_column("Chunks", justify="right")
    table.add_column("Entries", justify="right")

    for i, s in enumerate(snaps, 1):
        m = s.get("metrics", {})
        table.add_row(
            str(i),
            s["key"][:12] + "...",
            s.get("branch", ""),
            (s.get("timestamp") or "")[:19],
            s.get("label") or "",
            str(m.get("chunk_count", "")),
            str(m.get("entry_count", "")),
        )
    console.print(table)


@snapshot.command("show")
@click.argument("key")
@_ROOT_ARG
@click.option("--json", "as_json", is_flag=True, help="Output raw JSON.")
def snapshot_show(key, root, as_json):
    """Show full details for a snapshot.

    \b
    KEY   Snapshot key (commit hash or timestamp slug).
    ROOT  Project root directory (default: current directory).
    """
    kg = _kg(root)
    try:
        snap = kg.snapshot_show(key)
    except FileNotFoundError:
        console.print(f"[red]Error:[/red] Snapshot not found: {key!r}")
        sys.exit(1)

    if as_json:
        click.echo(json.dumps(snap, indent=2, default=str))
        return

    m = snap.get("metrics", {})
    span = m.get("temporal_span") or {}
    span_str = f"{span.get('start', '?')} → {span.get('end', '?')}" if span else "n/a"

    console.print(f"\n[bold]Snapshot[/bold]  {snap['key']}")
    console.print(f"  Branch      : {snap.get('branch')}")
    console.print(f"  Timestamp   : {snap.get('timestamp', '')[:19]}")
    console.print(f"  Label       : {snap.get('label') or '(none)'}")
    console.print(f"  Source file : {snap.get('source_file')}")
    console.print(f"  Chunks      : {m.get('chunk_count')}")
    console.print(f"  Entries     : {m.get('entry_count')}")
    console.print(f"  Nodes       : {m.get('node_count')}")
    console.print(f"  Edges       : {m.get('edge_count')}")
    console.print(f"  Time span   : {span_str}")
    console.print(f"  Strategy    : {m.get('chunking_strategy')}  chunk_size={m.get('chunk_size')}")

    if snap.get("vs_previous"):
        d = snap["vs_previous"]
        console.print(f"\n  vs previous → Δchunks={d.get('chunks'):+d}  Δentries={d.get('entries'):+d}")
    if snap.get("vs_baseline"):
        d = snap["vs_baseline"]
        console.print(f"  vs baseline → Δchunks={d.get('chunks'):+d}  Δentries={d.get('entries'):+d}")

    topics = m.get("topic_counts", {})
    if topics:
        console.print("\n  Top topics:")
        for cat, cnt in list(topics.items())[:5]:
            console.print(f"    {cat:<20} {cnt}")
    console.print()


@snapshot.command("diff")
@click.argument("key_a")
@click.argument("key_b")
@_ROOT_ARG
@click.option("--json", "as_json", is_flag=True, help="Output raw JSON.")
def snapshot_diff(key_a, key_b, root, as_json):
    """Compare two snapshots.

    \b
    KEY_A  Earlier snapshot key.
    KEY_B  Later snapshot key.
    ROOT   Project root directory (default: current directory).

    Examples:

    \b
        diarykg snapshot diff abc123 def456
        diarykg snapshot diff abc123 def456 --json
    """
    kg = _kg(root)
    try:
        diff = kg.snapshot_diff(key_a, key_b)
    except FileNotFoundError as exc:
        console.print(f"[red]Error:[/red] {exc}")
        sys.exit(1)

    if as_json:
        click.echo(json.dumps(diff, indent=2, default=str))
        return

    d = diff.get("delta", {})
    console.print(f"\n[bold]Snapshot diff[/bold]")
    console.print(f"  From : {diff['from']['key'][:12]}  {(diff['from'].get('timestamp') or '')[:19]}  {diff['from'].get('label') or ''}")
    console.print(f"  To   : {diff['to']['key'][:12]}  {(diff['to'].get('timestamp') or '')[:19]}  {diff['to'].get('label') or ''}")
    console.print()
    console.print(f"  Δ chunks  : {d.get('chunks', 'n/a'):+}" if isinstance(d.get('chunks'), int) else f"  Δ chunks  : n/a")
    console.print(f"  Δ entries : {d.get('entries', 'n/a'):+}" if isinstance(d.get('entries'), int) else f"  Δ entries : n/a")
    console.print(f"  Δ nodes   : {d.get('nodes', 'n/a'):+}" if isinstance(d.get('nodes'), int) else f"  Δ nodes   : n/a")
    console.print()


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main() -> None:
    """Console-script entry point."""
    cli()


if __name__ == "__main__":
    main()
