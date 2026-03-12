"""
cmd_registry.py

Registry management commands: register, unregister, list, info, status, scan.
"""
from __future__ import annotations

from pathlib import Path

import click
from rich.console import Console
from rich.table import Table
from rich import box

from kg_rag.cli.group import cli
from kg_rag.cli.options import kind_option, registry_option
from kg_rag.primitives import KGEntry, KGKind
from kg_rag.registry import KGRegistry, default_registry_path

console = Console()


@cli.command("register")
@click.argument("name")
@click.argument("kind", type=click.Choice(["code", "doc", "meta"], case_sensitive=False))
@click.argument("repo_path", type=click.Path(exists=True, file_okay=False, resolve_path=True))
@click.option("--venv", "venv_path", default=None, help="Path to .venv (default: REPO/.venv)")
@click.option("--sqlite", "sqlite_path", default=None, help="Path to SQLite DB file.")
@click.option("--lancedb", "lancedb_path", default=None, help="Path to LanceDB directory.")
@click.option("--version", "version", default="unknown", help="Version string.")
@click.option("--tag", "tags", multiple=True, help="Tags (repeatable: --tag foo --tag bar).")
@registry_option
def register(name, kind, repo_path, venv_path, sqlite_path, lancedb_path, version, tags, registry):
    """Register a KG instance in the KGRAG registry.

    \b
    NAME      Human-readable name for this KG (e.g. my-codekg)
    KIND      KG type: code, doc, or meta
    REPO_PATH Absolute path to the repository root

    Examples:

    \b
        kgrag register my-code code ~/repos/myproject
        kgrag register my-docs doc ~/repos/myproject --sqlite ~/repos/myproject/.dockg/graph.sqlite
    """
    repo = Path(repo_path).resolve()
    venv = Path(venv_path).resolve() if venv_path else (repo / ".venv")

    # Auto-detect db paths if not provided
    if sqlite_path is None:
        db_dir = ".codekg" if kind == "code" else (".dockg" if kind == "doc" else ".metakg")
        candidate = repo / db_dir / "graph.sqlite"
        sqlite_path = str(candidate) if candidate.exists() else None

    if lancedb_path is None:
        db_dir = ".codekg" if kind == "code" else (".dockg" if kind == "doc" else ".metakg")
        candidate = repo / db_dir / "lancedb"
        lancedb_path = str(candidate) if candidate.exists() else None

    entry = KGEntry(
        name=name,
        kind=KGKind.from_str(kind),
        repo_path=repo,
        venv_path=venv,
        sqlite_path=Path(sqlite_path) if sqlite_path else None,
        lancedb_path=Path(lancedb_path) if lancedb_path else None,
        version=version,
        tags=list(tags),
    )

    with KGRegistry(db_path=Path(registry) if registry else None) as reg:
        reg.register(entry)

    console.print(f"[green]Registered[/green] [bold]{name}[/bold] ({kind}) -> {repo}")
    if entry.sqlite_path:
        console.print(f"  SQLite  : {entry.sqlite_path}")
    if entry.lancedb_path:
        console.print(f"  LanceDB : {entry.lancedb_path}")
    console.print(f"  venv    : {entry.venv_path}")


@cli.command("unregister")
@click.argument("name_or_id")
@click.option("--yes", is_flag=True, help="Skip confirmation prompt.")
@registry_option
def unregister(name_or_id, yes, registry):
    """Remove a KG entry from the registry.

    \b
    NAME_OR_ID  Name or UUID of the KG entry to remove
    """
    with KGRegistry(db_path=Path(registry) if registry else None) as reg:
        entry = reg.get(name_or_id)
        if entry is None:
            console.print(f"[red]Not found[/red]: {name_or_id!r}")
            raise SystemExit(1)
        if not yes:
            click.confirm(f"Remove '{entry.name}' ({entry.kind.value}) from registry?", abort=True)
        reg.unregister(name_or_id)
    console.print(f"[green]Unregistered[/green] [bold]{entry.name}[/bold]")


@cli.command("list")
@kind_option
@registry_option
def list_kgs(kind, registry):
    """List all registered KG instances."""
    with KGRegistry(db_path=Path(registry) if registry else None) as reg:
        entries = reg.list(kind=KGKind.from_str(kind) if kind else None)
        stats = reg.stats()

    if not entries:
        console.print("[yellow]No KG instances registered yet.[/yellow]")
        console.print("Use [bold]kgrag register[/bold] to add one.")
        return

    table = Table(title="KGRAG Registry", box=box.ROUNDED, show_lines=False)
    table.add_column("Name", style="bold cyan")
    table.add_column("Kind", style="magenta")
    table.add_column("Built", justify="center")
    table.add_column("Version")
    table.add_column("Repo Path")
    table.add_column("Tags")

    for e in entries:
        built = "[green]yes[/green]" if e.is_built else "[dim]-[/dim]"
        table.add_row(
            e.name,
            e.kind.value,
            built,
            e.version,
            str(e.repo_path),
            ", ".join(e.tags) if e.tags else "",
        )

    console.print(table)
    console.print(
        f"\n[dim]Total: {stats.total}  |  "
        + "  ".join(f"{k}: {v}" for k, v in stats.by_kind.items())
        + f"  |  Built: {stats.built}"
        + f"  |  Registry: {stats.registry_path}[/dim]"
    )


@cli.command("info")
@click.argument("name_or_id")
@registry_option
def info(name_or_id, registry):
    """Show detailed information about a registered KG.

    \b
    NAME_OR_ID  Name or UUID of the KG entry
    """
    with KGRegistry(db_path=Path(registry) if registry else None) as reg:
        entry = reg.get(name_or_id)

    if entry is None:
        console.print(f"[red]Not found[/red]: {name_or_id!r}")
        raise SystemExit(1)

    from rich.panel import Panel
    lines = [
        f"[bold]ID[/bold]       : {entry.id}",
        f"[bold]Name[/bold]     : {entry.name}",
        f"[bold]Kind[/bold]     : {entry.kind.value}",
        f"[bold]Version[/bold]  : {entry.version}",
        f"[bold]Built[/bold]    : {'yes' if entry.is_built else 'no'}",
        f"[bold]Repo[/bold]     : {entry.repo_path}",
        f"[bold]Venv[/bold]     : {entry.venv_path}",
        f"[bold]SQLite[/bold]   : {entry.sqlite_path or '(not set)'}",
        f"[bold]LanceDB[/bold]  : {entry.lancedb_path or '(not set)'}",
        f"[bold]Tags[/bold]     : {', '.join(entry.tags) or '(none)'}",
        f"[bold]Created[/bold]  : {entry.created_at.strftime('%Y-%m-%d %H:%M UTC')}",
        f"[bold]Updated[/bold]  : {entry.updated_at.strftime('%Y-%m-%d %H:%M UTC')}",
    ]
    if entry.metadata:
        lines.append(f"[bold]Metadata[/bold] : {entry.metadata}")

    console.print(Panel("\n".join(lines), title=f"[bold]{entry.label}[/bold]", expand=False))


@cli.command("status")
@registry_option
def status(registry):
    """Show registry health: counts, built/unbuilt, missing paths."""
    reg_path = Path(registry).resolve() if registry else default_registry_path()
    with KGRegistry(db_path=reg_path) as reg:
        stats = reg.stats()
        entries = reg.list()

    console.print(f"[bold]Registry[/bold] : {reg_path}")
    console.print(f"[bold]Total KGs[/bold] : {stats.total}")
    for k, v in stats.by_kind.items():
        console.print(f"  {k:8s} : {v}")
    console.print(f"[bold]Built[/bold]    : {stats.built} / {stats.total}")

    issues = []
    for e in entries:
        if not e.repo_path.exists():
            issues.append(f"  [red]missing[/red] {e.name}: repo_path missing ({e.repo_path})")
        if not e.venv_path.exists():
            issues.append(f"  [yellow]warning[/yellow] {e.name}: venv missing ({e.venv_path})")
        if not e.is_built:
            issues.append(f"  [dim]-[/dim] {e.name}: no databases found (run build first)")

    if issues:
        console.print("\n[bold]Issues:[/bold]")
        for i in issues:
            console.print(i)
    else:
        console.print("\n[green]All registered KGs look healthy.[/green]")


@cli.command("scan")
@click.argument(
    "root_path",
    type=click.Path(exists=True, file_okay=False, resolve_path=True),
    default=".",
)
@click.option("--auto-register", is_flag=True, help="Automatically register all discovered KGs.")
@registry_option
def scan(root_path, auto_register, registry):
    """Scan a directory tree for existing KG databases and (optionally) register them.

    Looks for .codekg/, .dockg/, .metakg/ directories with built databases.

    \b
    ROOT_PATH  Directory to scan (default: current directory)
    """
    root = Path(root_path).resolve()
    console.print(f"Scanning [bold]{root}[/bold] for KG databases...")

    found = []
    markers = {
        ".codekg": "code",
        ".dockg": "doc",
        ".metakg": "meta",
    }

    for marker, kind in markers.items():
        for db_dir in root.rglob(marker):
            if db_dir.is_dir():
                repo = db_dir.parent
                sqlite = db_dir / "graph.sqlite"
                lancedb = db_dir / "lancedb"
                found.append({
                    "kind": kind,
                    "repo": repo,
                    "sqlite": sqlite if sqlite.exists() else None,
                    "lancedb": lancedb if lancedb.exists() else None,
                })

    if not found:
        console.print("[yellow]No KG databases found.[/yellow]")
        return

    table = Table(title=f"Discovered KGs under {root}", box=box.SIMPLE)
    table.add_column("#", style="dim")
    table.add_column("Kind", style="magenta")
    table.add_column("Repo")
    table.add_column("SQLite", justify="center")
    table.add_column("LanceDB", justify="center")

    for i, f in enumerate(found, 1):
        table.add_row(
            str(i),
            f["kind"],
            str(f["repo"]),
            "[green]yes[/green]" if f["sqlite"] else "-",
            "[green]yes[/green]" if f["lancedb"] else "-",
        )
    console.print(table)

    if auto_register:
        with KGRegistry(db_path=Path(registry) if registry else None) as reg:
            for f in found:
                name = f["repo"].name + "-" + f["kind"]
                entry = KGEntry(
                    name=name,
                    kind=KGKind.from_str(f["kind"]),
                    repo_path=f["repo"],
                    venv_path=f["repo"] / ".venv",
                    sqlite_path=f["sqlite"],
                    lancedb_path=f["lancedb"],
                )
                reg.register(entry)
                console.print(f"[green]Registered[/green] [bold]{name}[/bold]")
    else:
        console.print(f"\nRun with [bold]--auto-register[/bold] to register all discovered KGs.")
