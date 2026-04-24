"""
cmd_corpus.py

Corpus management commands: create, delete, add, remove, list, info, query.
Person corpus sub-commands: person create/delete/add/remove/list/info/update.

A corpus is a named collection of KG instances that can be queried as a group.
A person corpus is a corpus enriched with personal metadata (birth year,
address, email, etc.) holding all KGs relevant to a specific individual.
"""

from __future__ import annotations

from pathlib import Path

import click
from rich import box
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from kg_rag.cli.group import cli
from kg_rag.cli.options import k_option, registry_option
from kg_rag.corpus_registry import CorpusRegistry
from kg_rag.person_registry import PersonCorpusRegistry
from kg_rag.primitives import CorpusEntry, PersonCorpusEntry
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
                kg_lines.append(
                    f"  [{kg_entry.kind.value}] {kg_entry.name} "
                    f"[dim]v{kg_entry.builder_version}[/dim] ({kg_id})"
                )
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
    import json as _json  # pylint: disable=import-outside-toplevel

    from kg_rag.orchestrator import KGRAG  # pylint: disable=import-outside-toplevel

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


# ===========================================================================
# Person corpus subgroup  (kgrag corpus person ...)
# ===========================================================================


@corpus_group.group("person")
def person_group():
    """Manage person corpora — KG collections enriched with personal metadata."""


# ---------------------------------------------------------------------------
# corpus person create
# ---------------------------------------------------------------------------


@person_group.command("create")
@click.argument("name")
@click.option("--kg", "kg_refs", multiple=True, help="KG name or ID to include (repeatable).")
@click.option("--birth-year", "birth_year", type=int, default=None, help="Year of birth.")
@click.option("--birth-date", "birth_date", default=None, help="Full birth date (YYYY-MM-DD).")
@click.option("--address", default="", help="Mailing/home address.")
@click.option("--email", default="", help="Primary email address.")
@click.option("--phone", default="", help="Primary phone number.")
@click.option("--notes", default="", help="Free-form notes.")
@click.option("--tag", "tags", multiple=True, help="Tags (repeatable).")
@registry_option
def person_create(
    name, kg_refs, birth_year, birth_date, address, email, phone, notes, tags, registry
):
    """Create a person corpus entry.

    \b
    NAME  Full name of the person

    Example:

    \b
        kgrag corpus person create "Jane Doe" --birth-year 1985 \\
            --kg jane-diary --kg jane-memories --email jane@example.com
    """
    db_path = Path(registry).resolve() if registry else None

    with KGRegistry(db_path=db_path) as kg_reg, PersonCorpusRegistry(db_path=db_path) as per_reg:
        kg_ids: list[str] = []
        for ref in kg_refs:
            entry = kg_reg.get(ref)
            if entry is None:
                console.print(f"[red]KG not found[/red]: {ref!r}")
                raise SystemExit(1)
            kg_ids.append(entry.id)

        person = PersonCorpusEntry(
            name=name,
            kg_ids=kg_ids,
            birth_year=birth_year,
            birth_date=birth_date,
            address=address,
            email=email,
            phone=phone,
            notes=notes,
            tags=list(tags),
        )
        per_reg.create(person)

    console.print(f"[green]Created person corpus[/green] [bold]{name}[/bold] ({len(kg_ids)} KG(s))")
    if birth_year:
        console.print(f"  Born : {birth_date or birth_year}")
    if address:
        console.print(f"  Addr : {address}")
    if email:
        console.print(f"  Email: {email}")


# ---------------------------------------------------------------------------
# corpus person delete
# ---------------------------------------------------------------------------


@person_group.command("delete")
@click.argument("name_or_id")
@click.option("--yes", is_flag=True, help="Skip confirmation prompt.")
@registry_option
def person_delete(name_or_id, yes, registry):
    """Delete a person corpus entry.

    \b
    NAME_OR_ID  Name or UUID of the person entry to delete
    """
    db_path = Path(registry).resolve() if registry else None

    with PersonCorpusRegistry(db_path=db_path) as per_reg:
        entry = per_reg.get(name_or_id)
        if entry is None:
            console.print(f"[red]Person not found[/red]: {name_or_id!r}")
            raise SystemExit(1)
        if not yes:
            click.confirm(f"Delete person corpus '{entry.name}'?", abort=True)
        per_reg.delete(name_or_id)

    console.print(f"[green]Deleted person corpus[/green] [bold]{entry.name}[/bold]")


# ---------------------------------------------------------------------------
# corpus person add / remove
# ---------------------------------------------------------------------------


@person_group.command("add")
@click.argument("person_name")
@click.argument("kg_ref")
@registry_option
def person_add(person_name, kg_ref, registry):
    """Add a KG to a person corpus.

    \b
    PERSON_NAME  Name or UUID of the person entry
    KG_REF       Name or UUID of the KG to add
    """
    db_path = Path(registry).resolve() if registry else None

    with KGRegistry(db_path=db_path) as kg_reg, PersonCorpusRegistry(db_path=db_path) as per_reg:
        kg_entry = kg_reg.get(kg_ref)
        if kg_entry is None:
            console.print(f"[red]KG not found[/red]: {kg_ref!r}")
            raise SystemExit(1)
        updated = per_reg.add_kg(person_name, kg_entry.id)
        if updated is None:
            console.print(f"[red]Person not found[/red]: {person_name!r}")
            raise SystemExit(1)

    console.print(f"[green]Added[/green] {kg_ref} to person corpus [bold]{updated.name}[/bold]")


@person_group.command("remove")
@click.argument("person_name")
@click.argument("kg_ref")
@registry_option
def person_remove(person_name, kg_ref, registry):
    """Remove a KG from a person corpus.

    \b
    PERSON_NAME  Name or UUID of the person entry
    KG_REF       Name or UUID of the KG to remove
    """
    db_path = Path(registry).resolve() if registry else None

    with KGRegistry(db_path=db_path) as kg_reg, PersonCorpusRegistry(db_path=db_path) as per_reg:
        kg_entry = kg_reg.get(kg_ref)
        if kg_entry is None:
            console.print(f"[red]KG not found[/red]: {kg_ref!r}")
            raise SystemExit(1)
        updated = per_reg.remove_kg(person_name, kg_entry.id)
        if updated is None:
            console.print(f"[red]Person not found[/red]: {person_name!r}")
            raise SystemExit(1)

    console.print(f"[green]Removed[/green] {kg_ref} from person corpus [bold]{updated.name}[/bold]")


# ---------------------------------------------------------------------------
# corpus person update
# ---------------------------------------------------------------------------


@person_group.command("update")
@click.argument("name_or_id")
@click.option("--birth-year", "birth_year", type=int, default=None, help="Year of birth.")
@click.option("--birth-date", "birth_date", default=None, help="Full birth date (YYYY-MM-DD).")
@click.option("--address", default=None, help="Mailing/home address.")
@click.option("--email", default=None, help="Primary email address.")
@click.option("--phone", default=None, help="Primary phone number.")
@click.option("--notes", default=None, help="Free-form notes.")
@registry_option
def person_update(name_or_id, birth_year, birth_date, address, email, phone, notes, registry):
    """Update personal metadata for a person corpus entry.

    \b
    NAME_OR_ID  Name or UUID of the person entry
    """
    db_path = Path(registry).resolve() if registry else None

    updates = {
        k: v
        for k, v in {
            "birth_year": birth_year,
            "birth_date": birth_date,
            "address": address,
            "email": email,
            "phone": phone,
            "notes": notes,
        }.items()
        if v is not None
    }

    if not updates:
        console.print("[yellow]No updates specified.[/yellow]")
        return

    with PersonCorpusRegistry(db_path=db_path) as per_reg:
        updated = per_reg.update(name_or_id, **updates)
        if updated is None:
            console.print(f"[red]Person not found[/red]: {name_or_id!r}")
            raise SystemExit(1)

    console.print(f"[green]Updated[/green] [bold]{updated.name}[/bold]")
    for k, v in updates.items():
        console.print(f"  {k}: {v}")


# ---------------------------------------------------------------------------
# corpus person list
# ---------------------------------------------------------------------------


@person_group.command("list")
@registry_option
def person_list(registry):
    """List all person corpus entries."""
    db_path = Path(registry).resolve() if registry else None

    with PersonCorpusRegistry(db_path=db_path) as per_reg:
        entries = per_reg.list()
        stats = per_reg.stats()

    if not entries:
        console.print("[yellow]No person corpora defined yet.[/yellow]")
        console.print("Use [bold]kgrag corpus person create[/bold] to add one.")
        return

    table = Table(title="Person Corpora", box=box.ROUNDED, show_lines=False)
    table.add_column("Name", style="bold cyan")
    table.add_column("Born", justify="right")
    table.add_column("KGs", justify="right")
    table.add_column("Email")
    table.add_column("Tags")
    table.add_column("Updated")

    for e in entries:
        born = str(e.birth_year) if e.birth_year else "[dim]-[/dim]"
        table.add_row(
            e.name,
            born,
            str(e.size),
            e.email or "[dim]-[/dim]",
            ", ".join(e.tags) if e.tags else "[dim]-[/dim]",
            e.updated_at.strftime("%Y-%m-%d"),
        )

    console.print(table)
    console.print(
        f"\n[dim]Total persons: {stats.total}  |  "
        f"Total KG refs: {stats.total_kg_refs}  |  "
        f"Registry: {stats.registry_path}[/dim]"
    )


# ---------------------------------------------------------------------------
# corpus person info
# ---------------------------------------------------------------------------


@person_group.command("info")
@click.argument("name_or_id")
@registry_option
def person_info(name_or_id, registry):
    """Show detailed information about a person corpus entry.

    \b
    NAME_OR_ID  Name or UUID of the person entry
    """
    db_path = Path(registry).resolve() if registry else None

    with KGRegistry(db_path=db_path) as kg_reg, PersonCorpusRegistry(db_path=db_path) as per_reg:
        entry = per_reg.get(name_or_id)
        if entry is None:
            console.print(f"[red]Person not found[/red]: {name_or_id!r}")
            raise SystemExit(1)

        kg_lines = []
        for kg_id in entry.kg_ids:
            kg_entry = kg_reg.get(kg_id)
            if kg_entry:
                kg_lines.append(
                    f"  [{kg_entry.kind.value}] {kg_entry.name} "
                    f"[dim]v{kg_entry.builder_version}[/dim] ({kg_id})"
                )
            else:
                kg_lines.append(f"  [dim]missing[/dim] {kg_id}")

    lines = [
        f"[bold]ID[/bold]         : {entry.id}",
        f"[bold]Name[/bold]       : {entry.name}",
        f"[bold]Birth Year[/bold] : {entry.birth_year or '(unknown)'}",
        f"[bold]Birth Date[/bold] : {entry.birth_date or '(unknown)'}",
        f"[bold]Address[/bold]    : {entry.address or '(none)'}",
        f"[bold]Email[/bold]      : {entry.email or '(none)'}",
        f"[bold]Phone[/bold]      : {entry.phone or '(none)'}",
        f"[bold]Notes[/bold]      : {entry.notes or '(none)'}",
        f"[bold]KGs[/bold]        : {entry.size}",
    ]
    lines.extend(kg_lines)
    lines += [
        f"[bold]Tags[/bold]       : {', '.join(entry.tags) or '(none)'}",
        f"[bold]Created[/bold]    : {entry.created_at.strftime('%Y-%m-%d %H:%M UTC')}",
        f"[bold]Updated[/bold]    : {entry.updated_at.strftime('%Y-%m-%d %H:%M UTC')}",
    ]
    if entry.metadata:
        lines.append(f"[bold]Metadata[/bold]   : {entry.metadata}")

    console.print(Panel("\n".join(lines), title=f"[bold]Person: {entry.name}[/bold]", expand=False))


# ---------------------------------------------------------------------------
# corpus person query
# ---------------------------------------------------------------------------


@person_group.command("query")
@click.argument("person_name")
@click.argument("query_text")
@k_option
@click.option("--json", "as_json", is_flag=True, help="Output results as JSON.")
@registry_option
def person_query(person_name, query_text, k, as_json, registry):
    """Run a federated query scoped to a person corpus.

    \b
    PERSON_NAME  Name or UUID of the person corpus
    QUERY_TEXT   Natural-language query string

    Example:

    \b
        kgrag corpus person query "Jane Doe" "childhood memories in Ohio"
    """
    import json as _json  # pylint: disable=import-outside-toplevel

    from kg_rag.orchestrator import KGRAG  # pylint: disable=import-outside-toplevel

    db_path = Path(registry).resolve() if registry else None

    with KGRAG(registry_path=db_path) as orch:
        try:
            result = orch.query_person(person_name, query_text, k=k)
        except KeyError as e:
            console.print(f"[red]{e}[/red]")
            raise SystemExit(1)

    if as_json:
        out = {
            "query": result.query,
            "person": person_name,
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
        title=f"Person query: {query_text!r} for '{person_name}'",
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
