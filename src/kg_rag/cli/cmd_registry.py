"""
cmd_registry.py

Registry management commands: register, unregister, list, info, status, scan.
"""

from __future__ import annotations

import os
from datetime import date
from pathlib import Path

import click
from rich import box
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from kg_rag.cli.group import cli
from kg_rag.cli.options import _KIND_CHOICES, kind_option, registry_option
from kg_rag.config import read_builder_version, read_pyproject_version
from kg_rag.primitives import KGEntry, KGKind
from kg_rag.registry import KGRegistry, default_registry_path

console = Console()

# Map KG marker directory name → kind string
_KG_MARKERS: dict[str, str] = {
    ".pycodekg": "code",
    ".dockg": "doc",
    ".metakg": "meta",
    ".diarykg": "diary",
    ".versekg": "verse",
    ".memorykg": "memory",
    ".disulfidekg": "disulfide",
    ".pdbfilekg": "pdbfile",
    ".legalkg": "legal",
    ".personkg": "person",
}

# Map kind string → default database subdirectory name
_KIND_DB_DIR: dict[str, str] = {v: k for k, v in _KG_MARKERS.items()}


def _find_kg_dirs(root: Path) -> list[dict]:
    """Walk *root* for KG database directories, skipping hidden subdirectories.

    For each non-hidden directory encountered, checks for the presence of
    ``.pycodekg``, ``.dockg``, and ``.metakg`` child directories.  Hidden dirs
    (names starting with ``"."``) are pruned from traversal so we never
    descend into ``.git``, ``.venv``, or a neighbour repo's own KG dirs.

    :param root: Directory to walk.
    :return: List of dicts with keys ``kind``, ``repo``, ``sqlite``, ``lancedb``.
    """
    found: list[dict] = []
    for dirpath, dirnames, _ in os.walk(root):
        current = Path(dirpath)
        for marker, kind in _KG_MARKERS.items():
            kg_dir = current / marker
            if kg_dir.is_dir():
                sqlite = kg_dir / "graph.sqlite"
                lancedb_dir = kg_dir / "lancedb"
                found.append(
                    {
                        "kind": kind,
                        "repo": current,
                        "sqlite": sqlite if sqlite.exists() else None,
                        "lancedb": lancedb_dir if lancedb_dir.exists() else None,
                    }
                )
        # Prune hidden directories so we never recurse into them
        dirnames[:] = [d for d in dirnames if not d.startswith(".")]
    return found


@cli.command("register")
@click.argument("name")
@click.argument("kind", type=click.Choice(_KIND_CHOICES, case_sensitive=False))
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
    KIND      KG type: code, doc, meta, diary, verse, memory, disulfide, pdbfile
    REPO_PATH Absolute path to the repository root

    Examples:

    \b
        kgrag register my-code code ~/repos/myproject
        kgrag register my-docs doc ~/repos/myproject --sqlite ~/repos/myproject/.dockg/graph.sqlite
    """
    repo = Path(repo_path).resolve()
    venv = Path(venv_path).resolve() if venv_path else (repo / ".venv")

    # Auto-detect db paths if not provided
    db_dir = _KIND_DB_DIR.get(kind, f".{kind}kg")
    if sqlite_path is None:
        candidate = repo / db_dir / "graph.sqlite"
        sqlite_path = str(candidate) if candidate.exists() else None

    if lancedb_path is None:
        candidate = repo / db_dir / "lancedb"
        lancedb_path = str(candidate) if candidate.exists() else None

    # Auto-read version from pyproject.toml when not explicitly supplied
    if version == "unknown":
        version = read_pyproject_version(repo)

    # Default to a datestamp tag when none are specified
    resolved_tags = list(tags) if tags else [date.today().isoformat()]

    entry = KGEntry(
        name=name,
        kind=KGKind.from_str(kind),
        repo_path=repo,
        venv_path=venv,
        sqlite_path=Path(sqlite_path) if sqlite_path else None,
        lancedb_path=Path(lancedb_path) if lancedb_path else None,
        version=version,
        builder_version=read_builder_version(sqlite_path),
        tags=resolved_tags,
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

    lines = [
        f"[bold]ID[/bold]       : {entry.id}",
        f"[bold]Name[/bold]     : {entry.name}",
        f"[bold]Kind[/bold]     : {entry.kind.value}",
        f"[bold]Version[/bold]  : {entry.version}",
        f"[bold]Builder[/bold]  : {entry.builder_version}",
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


def _fmt_domain(s: dict) -> str:
    """Format domain-specific stats into a compact display string."""
    kind = s.get("kind", "")
    if kind == "doc":
        parts = []
        if s.get("document_count"):
            parts.append(f"docs:{s['document_count']}")
        if s.get("chunk_count"):
            parts.append(f"chunks:{s['chunk_count']}")
        if s.get("topic_count"):
            parts.append(f"topics:{s['topic_count']}")
        if s.get("entity_count"):
            parts.append(f"entities:{s['entity_count']}")
        return "  ".join(parts) or "—"
    if kind == "code":
        cov = s.get("docstring_coverage", 0)
        parts = [
            f"mod:{s.get('module_count', 0)}",
            f"cls:{s.get('class_count', 0)}",
            f"fn:{s.get('function_count', 0)}",
            f"meth:{s.get('method_count', 0)}",
            f"cov:{int(cov * 100)}%",
        ]
        return "  ".join(parts)
    if kind == "meta":
        parts = []
        if s.get("pathway_count"):
            parts.append(f"paths:{s['pathway_count']}")
        if s.get("compound_count"):
            parts.append(f"cpds:{s['compound_count']}")
        if s.get("reaction_count"):
            parts.append(f"rxns:{s['reaction_count']}")
        return "  ".join(parts) or "—"
    if kind in ("diary", "memory", "verse"):
        ec = s.get("entry_count", 0)
        return f"entries:{ec}"
    if kind == "agent":
        return f"turns:{s.get('turn_count', 0)}"
    return "—"


@cli.command("status")
@click.argument("name_or_id", required=False, default=None)
@click.option(
    "--stats",
    "show_stats",
    is_flag=True,
    default=False,
    help="Load each KG and show live domain counts (slower).",
)
@click.option(
    "--kind",
    "kind_filter",
    default=None,
    type=click.Choice(
        list(_KIND_CHOICES) + ["agent", "memory", "diary", "verse"], case_sensitive=False
    ),
    help="Filter --stats output to a specific KG kind.",
)
@registry_option
def status(name_or_id, show_stats, kind_filter, registry):
    """Show registry health: counts, built/unbuilt, missing paths.

    With --stats, open each built KG and display live domain counts
    (chunks, nodes, coverage, etc.).  Pass a NAME_OR_ID to limit to one KG.

    \b
    Examples:
        kgrag status
        kgrag status --stats
        kgrag status --stats --kind doc
        kgrag status my-dockg --stats
    """
    reg_path = Path(registry).resolve() if registry else default_registry_path()
    with KGRegistry(db_path=reg_path) as reg:
        reg_stats = reg.stats()
        if name_or_id:
            entry = reg.get(name_or_id)
            entries = [entry] if entry else []
        else:
            entries = reg.list()

    if not show_stats:
        # ── fast registry-only view ──────────────────────────────────────
        console.print(f"[bold]Registry[/bold] : {reg_path}")
        console.print(f"[bold]Total KGs[/bold] : {reg_stats.total}")
        for k, v in reg_stats.by_kind.items():
            console.print(f"  {k:8s} : {v}")
        console.print(f"[bold]Built[/bold]    : {reg_stats.built} / {reg_stats.total}")

        issues = []
        for e in entries:
            if not e.repo_path.exists():
                issues.append(f"  [red]missing[/red] {e.name}: repo_path missing ({e.repo_path})")
            if not e.is_built:
                issues.append(f"  [dim]-[/dim] {e.name}: no databases found (run build first)")

        if issues:
            console.print("\n[bold]Issues:[/bold]")
            for i in issues:
                console.print(i)
        else:
            console.print("\n[green]All registered KGs look healthy.[/green]")
        return

    # ── live stats view ──────────────────────────────────────────────────
    from kg_rag.orchestrator import KGRAG  # pylint: disable=import-outside-toplevel

    if kind_filter:
        entries = [e for e in entries if e.kind.value == kind_filter]

    if not entries:
        console.print("[yellow]No matching KGs found.[/yellow]")
        return

    if len(entries) > 20 and not name_or_id:
        console.print(
            f"[yellow]Loading stats for {len(entries)} KGs — this may take a moment…[/yellow]"
        )

    table = Table(title="KG Live Stats", box=box.ROUNDED, show_lines=False)
    table.add_column("Name", style="bold cyan", no_wrap=False, max_width=38)
    table.add_column("Kind", style="magenta", width=6)
    table.add_column("Builder", width=9)
    table.add_column("Nodes", justify="right", width=7)
    table.add_column("Edges", justify="right", width=7)
    table.add_column("MB", justify="right", width=5)
    table.add_column("Domain Counts")

    with KGRAG(registry_path=reg_path) as kg:
        for entry in entries:
            if not entry.is_built:
                table.add_row(
                    entry.name,
                    entry.kind.value,
                    entry.builder_version,
                    "—",
                    "—",
                    "—",
                    "[dim]not built[/dim]",
                )
                continue
            adapter = kg._get_adapter(entry)
            if adapter is None:
                table.add_row(
                    entry.name,
                    entry.kind.value,
                    entry.builder_version,
                    "—",
                    "—",
                    "—",
                    "[dim]no adapter[/dim]",
                )
                continue
            try:
                s = adapter.stats()
            except Exception as exc:  # pylint: disable=broad-exception-caught
                table.add_row(
                    entry.name,
                    entry.kind.value,
                    entry.builder_version,
                    "—",
                    "—",
                    "—",
                    f"[red]error: {exc}[/red]",
                )
                continue

            bver = s.get("builder_version", "?")
            nodes = str(s.get("node_count", "—"))
            edges = str(s.get("edge_count", "—"))
            mb = str(s.get("db_size_mb", "—"))
            err = s.get("error")
            if err:
                domain = f"[red]{err}[/red]"
            else:
                domain = _fmt_domain(s)

            table.add_row(entry.name, entry.kind.value, bver, nodes, edges, mb, domain)

    console.print(table)


@cli.command("refresh-versions")
@registry_option
def refresh_versions(registry):
    """Re-read ``builder_version`` from each registered KG's SQLite stamp.

    Walks the registry, opens each KG's ``sqlite_path``, reads the
    ``_kgrag_meta`` builder-version stamp (see
    ``docs/KG_BUILDER_VERSION_SPEC.md``), and updates the registry row.
    Use this after rebuilding KGs with a newer builder.
    """
    reg_path = Path(registry).resolve() if registry else None
    updated = 0
    unchanged = 0
    unstamped = 0
    with KGRegistry(db_path=reg_path) as reg:
        for entry in reg.list():
            new_ver = read_builder_version(entry.sqlite_path)
            if new_ver == "unknown":
                unstamped += 1
                console.print(f"  [dim]{entry.name}[/dim]: no stamp")
                continue
            if new_ver == entry.builder_version:
                unchanged += 1
                continue
            reg.update(entry.id, builder_version=new_ver)
            updated += 1
            console.print(f"  [green]{entry.name}[/green]: {entry.builder_version} → {new_ver}")
    console.print(
        f"\n[bold]Updated[/bold] {updated}  "
        f"[bold]Unchanged[/bold] {unchanged}  "
        f"[bold]Unstamped[/bold] {unstamped}"
    )


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

    Looks for .pycodekg/, .dockg/, .metakg/ directories with built databases.

    \b
    ROOT_PATH  Directory to scan (default: current directory)
    """
    root = Path(root_path).resolve()
    console.print(f"Scanning [bold]{root}[/bold] for KG databases...")

    found = _find_kg_dirs(root)

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
                repo_dir: Path = f["repo"]
                name = repo_dir.name + "-" + f["kind"]
                entry = KGEntry(
                    name=name,
                    kind=KGKind.from_str(f["kind"]),
                    repo_path=repo_dir,
                    venv_path=repo_dir / ".venv",
                    sqlite_path=f["sqlite"],
                    lancedb_path=f["lancedb"],
                    version=read_pyproject_version(repo_dir),
                    builder_version=read_builder_version(f["sqlite"]),
                    tags=[date.today().isoformat()],
                )
                reg.register(entry)
                console.print(f"[green]Registered[/green] [bold]{name}[/bold]")
    else:
        console.print("\nRun with [bold]--auto-register[/bold] to register all discovered KGs.")
