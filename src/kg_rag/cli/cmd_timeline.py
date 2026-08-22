"""
cmd_timeline.py

Chronological cross-KG query — what happened, in order.

Author: Eric G. Suchanek, PhD
License: Elastic 2.0
"""

from __future__ import annotations

from typing import Any

import click
from kg_utils.temporal import TemporalSpan, read_span
from rich import box
from rich.console import Console
from rich.table import Table

from kg_rag.cli.group import cli
from kg_rag.cli.options import k_option, kind_option, registry_option
from kg_rag.orchestrator import KGRAG
from kg_rag.primitives import CrossHit, KGKind, QueryScope

console = Console()


def _span_of(hit: CrossHit) -> TemporalSpan | None:
    """Read a hit's temporal span, or ``None`` when it carries no date."""
    return read_span(hit.metadata)


def _when(span: TemporalSpan, metadata: dict[str, Any] | None = None) -> str:
    """Render a span for a timeline column.

    Three things this gets right that a naive formatter does not:

    - **Precision is shown, not padded.** A book dated ``1876`` reads as
      ``1876``, never as a false midnight on the 1st of January.
    - **Only an explicit end becomes a range.** A year-precision span *implies*
      an end of 31 December, and printing that implied bound as ``1876 →
      1876-12-31`` would claim the source said something it did not. The arrow
      appears only when ``occurred_end`` was actually written.
    - **A recorded-only date is marked ``~``.** It says when the thing was
      written down, not when it happened, and a timeline that shows the two
      identically is lying about one of them.

    :param span: The hit's temporal span.
    :param metadata: The hit's raw metadata, consulted to tell an explicit
        ``occurred_end`` from one implied by precision.
    :return: Short display string.
    """
    if span.start is None:
        return f"~{span.recorded:%Y-%m-%d}" if span.recorded else "—"

    if span.precision == "year":
        text = f"{span.start:%Y}"
    elif span.precision == "month":
        text = f"{span.start:%Y-%m}"
    else:
        text = f"{span.start:%Y-%m-%d}"

    explicit_end = (metadata or {}).get("occurred_end")
    if explicit_end and span.end is not None and span.end.date() != span.start.date():
        text += f" → {span.end:%Y-%m-%d}"
    return text


@cli.command("timeline")
@click.argument("query_text")
@click.option(
    "--from", "date_from", default=None, help="Earliest date (ISO, e.g. 1876 or 2026-04)."
)
@click.option("--to", "date_to", default=None, help="Latest date (ISO). Open-ended if omitted.")
@k_option
@kind_option
@click.option("--json", "output_json", is_flag=True, help="Output as JSON.")
@click.option(
    "--min-score",
    "min_score",
    default=0.0,
    show_default=True,
    help="Drop hits with score below this threshold.",
)
@registry_option
def timeline(query_text, date_from, date_to, k, kind, output_json, min_score, registry):
    """Chronological cross-KG query — what happened, in order.

    Runs a federated query and orders the results by *when*, not by relevance.
    A diary entry, a photograph, a conversation topic and a book publication
    sort into one sequence, because every module writes the same temporal
    contract.

    \b
    QUERY_TEXT  Natural-language query string

    Dates accept any ISO precision, and the precision is meaningful: --from 1876
    means the whole of 1876, not its first midnight.

    \b
    Examples:
        kgrag timeline "fire"
        kgrag timeline "the office" --from 1666-09 --to 1666-10
        kgrag timeline "manifold work" --from 2026-04
        kgrag timeline "photographs" --from 1998 --kind filetree

    Hits that carry no date at all are counted and reported, never silently
    dropped — a module that has not adopted the temporal contract would
    otherwise look like a module with nothing to say.
    """
    scope = QueryScope(time_range=(date_from, date_to)) if (date_from or date_to) else None

    with KGRAG(registry_path=registry) as kg:
        result = kg.query(
            query_text,
            k=k,
            kinds=[KGKind.from_str(kind)] if kind else None,
            min_score=min_score,
            scope=scope,
        )

    if result.kgs_queried == 0:
        console.print("[yellow]No available KGs to query. Register and build some first.[/yellow]")
        return

    dated: list[tuple[TemporalSpan, CrossHit]] = []
    undated: list[CrossHit] = []
    for hit in result.hits:
        span = _span_of(hit)
        if span is None:
            undated.append(hit)
        else:
            dated.append((span, hit))

    dated.sort(key=lambda pair: pair[0].sort_key)

    if output_json:
        import json  # pylint: disable=import-outside-toplevel

        payload: dict[str, Any] = {
            "query": query_text,
            "time_range": [date_from, date_to],
            "dated": [
                {
                    "when": _when(span, hit.metadata),
                    "occurred_start": hit.metadata.get("occurred_start"),
                    "occurred_end": hit.metadata.get("occurred_end"),
                    "recorded_at": hit.metadata.get("recorded_at"),
                    "kg": hit.kg_name,
                    "kind": hit.kg_kind.value,
                    "node_id": hit.node_id,
                    "name": hit.name,
                    "score": round(hit.score, 4),
                    "summary": hit.summary,
                    "source_path": hit.source_path,
                }
                for span, hit in dated
            ],
            "undated_count": len(undated),
        }
        console.print_json(json.dumps(payload))
        return

    window = ""
    if date_from or date_to:
        window = f"  [{date_from or '…'} → {date_to or '…'}]"
    table = Table(
        title=f"Timeline: {query_text!r}{window}  "
        f"[{len(dated)} dated across {result.kgs_queried} KG(s)]",
        box=box.ROUNDED,
        show_lines=False,
    )
    table.add_column("When", style="green", width=24)
    table.add_column("KG", style="bold")
    table.add_column("Kind", style="magenta", width=8)
    table.add_column("Name")
    table.add_column("Summary")

    for span, hit in dated:
        table.add_row(
            _when(span, hit.metadata),
            hit.kg_name,
            hit.kg_kind.value,
            hit.name,
            (hit.summary[:60] + "…") if len(hit.summary) > 60 else hit.summary,
        )

    if not dated:
        console.print("[yellow]No dated results.[/yellow]")
    else:
        console.print(table)

    if undated:
        console.print(
            f"[dim]{len(undated)} undated hit(s) not shown — "
            f"their module does not write the temporal contract.[/dim]"
        )
