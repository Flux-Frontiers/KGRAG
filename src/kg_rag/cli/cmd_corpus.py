"""
cmd_corpus.py

Corpus management commands: create, delete, add, remove, list, info, query.

A corpus is a named collection of KG instances that can be queried as a group.
"""

from __future__ import annotations

from pathlib import Path

import click
from rich import box
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from kg_rag.cli.group import cli
from kg_rag.cli.options import context_option, k_option, registry_option
from kg_rag.corpus_registry import CorpusRegistry
from kg_rag.primitives import CorpusEntry
from kg_rag.registry import KGRegistry

console = Console()


# ---------------------------------------------------------------------------
# Helper: resolve KG name-or-id to a UUID using the KGRegistry
# ---------------------------------------------------------------------------


def _resolve_kg_id(kg_name_or_id: str, kg_registry: KGRegistry) -> str | None:
    """Return the KGEntry UUID for the given name or id, or None if not found."""
    entry = kg_registry.get(kg_name_or_id)
    return entry.id if entry else None


# ---------------------------------------------------------------------------
# Corpus subgroup
# ---------------------------------------------------------------------------


@cli.group("corpus")
def corpus_group():
    """Manage KG corpora — named collections of registered KG instances."""


# ---------------------------------------------------------------------------
# corpus create
# ---------------------------------------------------------------------------


@corpus_group.command("create")
@click.argument("name")
@click.option("--kg", "kg_refs", multiple=True, help="KG name or ID to include (repeatable).")
@click.option("--desc", "description", default="", help="Human-readable description.")
@click.option("--tag", "tags", multiple=True, help="Tags (repeatable: --tag foo --tag bar).")
@registry_option
def corpus_create(name, kg_refs, description, tags, registry):
    """Create a new corpus grouping one or more KGs.

    \b
    NAME  Human-readable name for this corpus (e.g. my-project)

    Examples:

    \b
        kgrag corpus create my-project --kg my-codekg --kg my-dockg
        kgrag corpus create research --kg codekg-1 --desc "Research project KGs"
    """
    db_path = Path(registry).resolve() if registry else None

    with KGRegistry(db_path=db_path) as kg_reg, CorpusRegistry(db_path=db_path) as corp_reg:
        # Resolve KG names/IDs to UUIDs
        kg_ids: list[str] = []
        for ref in kg_refs:
            kg_id = _resolve_kg_id(ref, kg_reg)
            if kg_id is None:
                console.print(f"[red]KG not found[/red]: {ref!r}")
                raise SystemExit(1)
            kg_ids.append(kg_id)

        entry = CorpusEntry(
            name=name,
            description=description,
            kg_ids=kg_ids,
            tags=list(tags),
        )
        corp_reg.create(entry)

    console.print(f"[green]Created corpus[/green] [bold]{name}[/bold] ({len(kg_ids)} KG(s))")
    if description:
        console.print(f"  Desc: {description}")
    for ref, kg_id in zip(kg_refs, kg_ids):
        console.print(f"  + {ref} ({kg_id})")


# ---------------------------------------------------------------------------
# corpus delete
# ---------------------------------------------------------------------------


@corpus_group.command("delete")
@click.argument("name_or_id")
@click.option("--yes", is_flag=True, help="Skip confirmation prompt.")
@registry_option
def corpus_delete(name_or_id, yes, registry):
    """Delete a corpus from the registry.

    \b
    NAME_OR_ID  Name or UUID of the corpus to delete
    """
    db_path = Path(registry).resolve() if registry else None

    with CorpusRegistry(db_path=db_path) as corp_reg:
        entry = corp_reg.get(name_or_id)
        if entry is None:
            console.print(f"[red]Corpus not found[/red]: {name_or_id!r}")
            raise SystemExit(1)
        if not yes:
            click.confirm(f"Delete corpus '{entry.name}' ({entry.size} KG(s))?", abort=True)
        corp_reg.delete(name_or_id)

    console.print(f"[green]Deleted corpus[/green] [bold]{entry.name}[/bold]")


# ---------------------------------------------------------------------------
# corpus add
# ---------------------------------------------------------------------------


@corpus_group.command("add")
@click.argument("corpus_name")
@click.argument("kg_ref")
@registry_option
def corpus_add(corpus_name, kg_ref, registry):
    """Add a KG to an existing corpus.

    \b
    CORPUS_NAME  Name or UUID of the corpus
    KG_REF       Name or UUID of the KG to add
    """
    db_path = Path(registry).resolve() if registry else None

    with KGRegistry(db_path=db_path) as kg_reg, CorpusRegistry(db_path=db_path) as corp_reg:
        kg_id = _resolve_kg_id(kg_ref, kg_reg)
        if kg_id is None:
            console.print(f"[red]KG not found[/red]: {kg_ref!r}")
            raise SystemExit(1)

        entry = corp_reg.add_kg(corpus_name, kg_id)
        if entry is None:
            console.print(f"[red]Corpus not found[/red]: {corpus_name!r}")
            raise SystemExit(1)

    console.print(f"[green]Added[/green] {kg_ref} to corpus [bold]{entry.name}[/bold]")


# ---------------------------------------------------------------------------
# corpus remove
# ---------------------------------------------------------------------------


@corpus_group.command("remove")
@click.argument("corpus_name")
@click.argument("kg_ref")
@registry_option
def corpus_remove(corpus_name, kg_ref, registry):
    """Remove a KG from a corpus.

    \b
    CORPUS_NAME  Name or UUID of the corpus
    KG_REF       Name or UUID of the KG to remove
    """
    db_path = Path(registry).resolve() if registry else None

    with KGRegistry(db_path=db_path) as kg_reg, CorpusRegistry(db_path=db_path) as corp_reg:
        kg_id = _resolve_kg_id(kg_ref, kg_reg)
        if kg_id is None:
            console.print(f"[red]KG not found[/red]: {kg_ref!r}")
            raise SystemExit(1)

        entry = corp_reg.remove_kg(corpus_name, kg_id)
        if entry is None:
            console.print(f"[red]Corpus not found[/red]: {corpus_name!r}")
            raise SystemExit(1)

    console.print(f"[green]Removed[/green] {kg_ref} from corpus [bold]{entry.name}[/bold]")


# ---------------------------------------------------------------------------
# corpus list
# ---------------------------------------------------------------------------


@corpus_group.command("list")
@registry_option
def corpus_list(registry):
    """List all corpora in the registry."""
    db_path = Path(registry).resolve() if registry else None

    with CorpusRegistry(db_path=db_path) as corp_reg:
        entries = corp_reg.list()
        stats = corp_reg.stats()

    if not entries:
        console.print("[yellow]No corpora defined yet.[/yellow]")
        console.print("Use [bold]kgrag corpus create[/bold] to create one.")
        return

    table = Table(title="KGRAG Corpora", box=box.ROUNDED, show_lines=False)
    table.add_column("Name", style="bold cyan")
    table.add_column("KGs", justify="right")
    table.add_column("Description")
    table.add_column("Tags")
    table.add_column("Updated")

    for e in entries:
        table.add_row(
            e.name,
            str(e.size),
            e.description or "[dim]-[/dim]",
            ", ".join(e.tags) if e.tags else "[dim]-[/dim]",
            e.updated_at.strftime("%Y-%m-%d"),
        )

    console.print(table)
    console.print(
        f"\n[dim]Total corpora: {stats.total}  |  "
        f"Total KG refs: {stats.total_kg_refs}  |  "
        f"Registry: {stats.registry_path}[/dim]"
    )


# ---------------------------------------------------------------------------
# corpus info
# ---------------------------------------------------------------------------


@corpus_group.command("info")
@click.argument("name_or_id")
@registry_option
def corpus_info(name_or_id, registry):
    """Show detailed information about a corpus.

    \b
    NAME_OR_ID  Name or UUID of the corpus
    """
    db_path = Path(registry).resolve() if registry else None

    with KGRegistry(db_path=db_path) as kg_reg, CorpusRegistry(db_path=db_path) as corp_reg:
        entry = corp_reg.get(name_or_id)
        if entry is None:
            console.print(f"[red]Corpus not found[/red]: {name_or_id!r}")
            raise SystemExit(1)

        # Resolve KG names for display
        kg_lines = []
        for kg_id in entry.kg_ids:
            kg_entry = kg_reg.get(kg_id)
            if kg_entry:
                kg_lines.append(f"  [{kg_entry.kind.value}] {kg_entry.name} ({kg_id})")
            else:
                kg_lines.append(f"  [dim]missing[/dim] {kg_id}")

    lines = [
        f"[bold]ID[/bold]          : {entry.id}",
        f"[bold]Name[/bold]        : {entry.name}",
        f"[bold]Description[/bold] : {entry.description or '(none)'}",
        f"[bold]KGs[/bold]         : {entry.size}",
    ]
    lines.extend(kg_lines)
    lines += [
        f"[bold]Tags[/bold]        : {', '.join(entry.tags) or '(none)'}",
        f"[bold]Created[/bold]     : {entry.created_at.strftime('%Y-%m-%d %H:%M UTC')}",
        f"[bold]Updated[/bold]     : {entry.updated_at.strftime('%Y-%m-%d %H:%M UTC')}",
    ]
    if entry.metadata:
        lines.append(f"[bold]Metadata[/bold]    : {entry.metadata}")

    console.print(Panel("\n".join(lines), title=f"[bold]Corpus: {entry.name}[/bold]", expand=False))


# ---------------------------------------------------------------------------
# corpus query
# ---------------------------------------------------------------------------


@corpus_group.command("query")
@click.argument("corpus_name")
@click.argument("query_text")
@k_option
@click.option("--json", "as_json", is_flag=True, help="Output results as JSON.")
@registry_option
def corpus_query(corpus_name, query_text, k, as_json, registry):
    """Run a federated query scoped to a named corpus.

    \b
    CORPUS_NAME  Name or UUID of the corpus to query
    QUERY_TEXT   Natural-language query string

    Example:

    \b
        kgrag corpus query my-project "how is authentication handled"
    """
    import json as _json

    from kg_rag.orchestrator import KGRAG

    db_path = Path(registry).resolve() if registry else None

    with KGRAG(registry_path=db_path) as orch:
        try:
            result = orch.query_corpus(corpus_name, query_text, k=k)
        except KeyError as e:
            console.print(f"[red]{e}[/red]")
            raise SystemExit(1)

    if as_json:
        out = {
            "query": result.query,
            "corpus": corpus_name,
            "total_hits": result.total_hits,
            "kgs_queried": result.kgs_queried,
            "hits": [
                {
                    "kg_name": h.kg_name,
                    "kg_kind": h.kg_kind.value,
                    "name": h.name,
                    "kind": h.kind,
                    "score": round(h.score, 4),
                    "summary": h.summary,
                    "source_path": h.source_path,
                }
                for h in result.hits
            ],
        }
        console.print_json(_json.dumps(out))
        return

    if not result.hits:
        console.print("[yellow]No results found.[/yellow]")
        return

    table = Table(
        title=f"Corpus query: {query_text!r} in '{corpus_name}'",
        box=box.SIMPLE,
    )
    table.add_column("KG", style="cyan")
    table.add_column("Kind", style="magenta")
    table.add_column("Name", style="bold")
    table.add_column("Score", justify="right")
    table.add_column("Summary")

    for h in result.hits:
        table.add_row(
            h.kg_name,
            h.kg_kind.value,
            h.name,
            f"{h.score:.3f}",
            (h.summary[:80] + "…") if len(h.summary) > 80 else h.summary,
        )

    console.print(table)
    console.print(
        f"\n[dim]Total hits: {result.total_hits}  |  KGs queried: {result.kgs_queried}[/dim]"
    )
