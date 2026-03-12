"""
cmd_analyze.py

Cross-KG analysis command.
"""
from __future__ import annotations

from pathlib import Path

import click
from rich.console import Console
from rich import box

from kg_rag.cli.group import cli
from kg_rag.cli.options import kind_option, registry_option
from kg_rag.orchestrator import KGRAG
from kg_rag.primitives import KGKind

console = Console()


@cli.command("analyze")
@kind_option
@registry_option
def analyze(kind, registry):
    """Cross-KG analysis: show statistics across all registered KGs.

    Queries each available KG for statistics and renders a summary report.
    """
    reg_path = Path(registry).resolve() if registry else None

    with KGRAG(registry_path=reg_path) as kg:
        registry_obj = kg.registry
        entries = registry_obj.list(kind=KGKind.from_str(kind) if kind else None)
        stats_map = kg.stats(kinds=[KGKind.from_str(kind)] if kind else None)

    if not entries:
        console.print("[yellow]No KGs registered. Use 'kgrag register' to add some.[/yellow]")
        return

    from rich.table import Table
    table = Table(title="Cross-KG Analysis", box=box.ROUNDED, show_lines=True)
    table.add_column("Name", style="bold cyan")
    table.add_column("Kind", style="magenta")
    table.add_column("Available", justify="center")
    table.add_column("Nodes", justify="right")
    table.add_column("Edges", justify="right")
    table.add_column("Repo")

    for e in entries:
        s = stats_map.get(e.name, {})
        avail = "[green]yes[/green]" if s.get("available") else "[red]no[/red]"
        nodes = str(s.get("node_count", "-"))
        edges = str(s.get("edge_count", "-"))
        table.add_row(e.name, e.kind.value, avail, nodes, edges, str(e.repo_path))

    console.print(table)

    total_nodes = sum(
        v.get("node_count", 0)
        for v in stats_map.values()
        if isinstance(v.get("node_count"), int)
    )
    console.print(f"\n[bold]Total indexed nodes across all KGs:[/bold] {total_nodes}")
