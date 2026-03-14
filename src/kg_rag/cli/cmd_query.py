"""
cmd_query.py

Cross-KG query and pack commands.
"""

from __future__ import annotations

from pathlib import Path

import click
from rich import box
from rich.console import Console
from rich.table import Table

from kg_rag.cli.group import cli
from kg_rag.cli.options import context_option, k_option, kind_option, registry_option
from kg_rag.orchestrator import KGRAG
from kg_rag.primitives import KGKind

console = Console()


def _parse_kinds(kind: str | None) -> list[KGKind] | None:
    return [KGKind.from_str(kind)] if kind else None


@cli.command("query")
@click.argument("query_text")
@k_option
@kind_option
@click.option("--json", "output_json", is_flag=True, help="Output as JSON.")
@registry_option
def query(query_text, k, kind, output_json, registry):
    """Cross-KG semantic query — search all registered KGs.

    \b
    QUERY_TEXT  Natural-language query string

    Examples:

    \b
        kgrag query "knowledge graph extraction"
        kgrag query "metabolic pathway" --kind meta -k 5
        kgrag query "document chunking" --kind doc
    """
    reg_path = Path(registry).resolve() if registry else None
    with KGRAG(registry_path=reg_path) as kg:
        result = kg.query(query_text, k=k, kinds=_parse_kinds(kind))

    if result.kgs_queried == 0:
        console.print("[yellow]No available KGs to query. Register and build some first.[/yellow]")
        return

    if output_json:
        import json

        data = [
            {
                "kg": h.kg_name,
                "kind": h.kg_kind.value,
                "node_id": h.node_id,
                "name": h.name,
                "node_kind": h.kind,
                "score": round(h.score, 4),
                "summary": h.summary,
                "source_path": h.source_path,
            }
            for h in result.hits
        ]
        console.print_json(json.dumps(data))
        return

    table = Table(
        title=f"Query: {query_text!r}  [{result.total_hits} hits across {result.kgs_queried} KG(s)]",
        box=box.ROUNDED,
        show_lines=True,
    )
    table.add_column("Score", justify="right", style="cyan", width=6)
    table.add_column("KG", style="bold")
    table.add_column("Kind", style="magenta", width=8)
    table.add_column("Name")
    table.add_column("Type", width=10)
    table.add_column("Summary")

    for h in result.hits:
        table.add_row(
            f"{h.score:.3f}",
            h.kg_name,
            h.kg_kind.value,
            h.name,
            h.kind,
            (h.summary[:80] + "...") if len(h.summary) > 80 else h.summary,
        )

    console.print(table)


@cli.command("pack")
@click.argument("query_text")
@k_option
@context_option
@kind_option
@click.option("--out", default=None, metavar="FILE", help="Write pack to file instead of stdout.")
@registry_option
def pack(query_text, k, context, kind, out, registry):
    """Cross-KG snippet pack — extract source snippets for LLM ingestion.

    \b
    QUERY_TEXT  Natural-language query string

    Examples:

    \b
        kgrag pack "graph traversal logic"
        kgrag pack "API endpoints" --kind code --out snippets.md
    """
    reg_path = Path(registry).resolve() if registry else None
    with KGRAG(registry_path=reg_path) as kg:
        result = kg.pack(query_text, k=k, context=context, kinds=_parse_kinds(kind))

    if result.kgs_queried == 0:
        console.print("[yellow]No available KGs to query.[/yellow]")
        return

    rendered = result.render()

    if out:
        Path(out).write_text(rendered, encoding="utf-8")
        console.print(
            f"[green]Wrote[/green] {len(result.snippets)} snippets "
            f"(~{result.total_tokens_approx} tokens) to [bold]{out}[/bold]"
        )
    else:
        console.print(rendered)
        console.print(
            f"\n[dim]{len(result.snippets)} snippets | ~{result.total_tokens_approx} tokens "
            f"| {result.kgs_queried} KG(s)[/dim]"
        )
