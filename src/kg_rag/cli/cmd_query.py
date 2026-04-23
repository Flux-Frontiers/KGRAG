"""
cmd_query.py

Cross-KG query and pack commands.

Author: Eric G. Suchanek, PhD
Last Revision: 2026-04-22 19:27:45
License: Elastic 2.0
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


def _known_scopes(kg: KGRAG) -> str:
    """Return a human-readable list of all registered corpus and person names.

    Used in --scope error messages so the user can see valid choices without
    running a separate list command.

    :param kg: Open KGRAG instance.
    :return: Comma-separated quoted names, or '(none registered)'.
    """
    corpora = [c.name for c in kg.corpus_registry.list()]
    persons = [p.name for p in kg.person_registry.list()]
    names = sorted(corpora + persons)
    return ", ".join(f"'{n}'" for n in names) if names else "(none registered)"


def _resolve_scoped_query(
    kg: KGRAG, scope: str, q: str, k: int, min_score: float, semantic_floor: float
):
    """Route a query through the corpus or person registry by scope name.

    Resolution order:
      1. CorpusRegistry  — ``query_corpus(scope)``
      2. PersonCorpusRegistry — ``query_person(scope)``
      3. click.UsageError listing all known scope names.

    Corpus lookup is tried first because corpora are the primary grouping
    mechanism; person corpora are checked second as a fallback.

    :param kg: Open KGRAG instance.
    :param scope: Corpus or person-corpus name to restrict the query to.
    :param q: Natural-language query string.
    :param k: Max hits per KG.
    :param min_score: Minimum relevance score; hits below this are dropped.
    :param semantic_floor: Per-KG gate; KGs whose best hit is below this are
        silenced entirely.
    :return: CrossQueryResult from the matched scope.
    :raises click.UsageError: If scope matches neither a corpus nor a person.
    """
    try:
        return kg.query_corpus(scope, q, k=k, min_score=min_score, semantic_floor=semantic_floor)
    except KeyError:
        pass
    try:
        return kg.query_person(scope, q, k=k, min_score=min_score, semantic_floor=semantic_floor)
    except KeyError:
        pass
    raise click.UsageError(f"--scope {scope!r} not found. Known scopes: {_known_scopes(kg)}")


def _resolve_scoped_pack(
    kg: KGRAG, scope: str, q: str, k: int, context: int, semantic_floor: float
):
    """Route a pack through the corpus or person registry by scope name.

    Resolution order:
      1. CorpusRegistry  — ``pack_corpus(scope)``
      2. PersonCorpusRegistry — ``pack_person(scope)``
      3. click.UsageError listing all known scope names.

    Mirrors the resolution order of :func:`_resolve_scoped_query` so that
    ``--scope`` behaves identically across both commands.

    :param kg: Open KGRAG instance.
    :param scope: Corpus or person-corpus name to restrict the pack to.
    :param q: Natural-language query string.
    :param k: Max snippets per KG.
    :param context: Lines of context for code snippets.
    :param semantic_floor: Per-KG gate; KGs whose best snippet is below this
        are silenced entirely.
    :return: CrossSnippetPack from the matched scope.
    :raises click.UsageError: If scope matches neither a corpus nor a person.
    """
    try:
        return kg.pack_corpus(scope, q, k=k, context=context, semantic_floor=semantic_floor)
    except KeyError:
        pass
    try:
        return kg.pack_person(scope, q, k=k, context=context, semantic_floor=semantic_floor)
    except KeyError:
        pass
    raise click.UsageError(f"--scope {scope!r} not found. Known scopes: {_known_scopes(kg)}")


_scope_option = click.option(
    "--scope",
    default=None,
    metavar="NAME",
    help=(
        "Restrict the query to a named corpus or person corpus. "
        "Resolution order: CorpusRegistry first, PersonCorpusRegistry second. "
        "Omit to search the full flat registry. "
        "Cannot be combined with --kind."
    ),
)

_semantic_floor_option = click.option(
    "--semantic-floor",
    "semantic_floor",
    default=0.0,
    show_default=True,
    help=(
        "Per-KG noise gate: if the best hit from a KG scores below this value, "
        "that KG's entire result set is discarded.  Dense embedding models produce "
        "cosine similarity ~0.45–0.55 for unrelated English text, so use e.g. 0.55 "
        "to silence KGs with no genuine domain overlap with the query."
    ),
)


@cli.command("query")
@click.argument("query_text")
@k_option
@kind_option
@_scope_option
@click.option("--json", "output_json", is_flag=True, help="Output as JSON.")
@click.option(
    "--min-score",
    "min_score",
    default=0.0,
    show_default=True,
    help="Drop hits with score below this threshold (e.g. 0.35 to suppress off-topic KGs).",
)
@_semantic_floor_option
@registry_option
def query(query_text, k, kind, scope, output_json, min_score, semantic_floor, registry):
    """Cross-KG semantic query — search all registered KGs.

    \b
    QUERY_TEXT  Natural-language query string

    Scope routing (--scope takes precedence over --kind):
      --scope NAME  targets a named corpus or person corpus; --kind is ignored.
      --kind TYPE   filters the flat registry by KGKind (code/doc/meta/…).
      (neither)     searches all registered KGs.

    Examples:

    \b
        kgrag query "knowledge graph extraction"
        kgrag query "metabolic pathway" --kind meta -k 5
        kgrag query "document chunking" --kind doc
        kgrag query "what did Twain think about justice" --min-score 0.35
        kgrag query "graph traversal" --scope KGRAG_repos
        kgrag query "diary entry about rivers" --scope john
        kgrag query "what did Twain think about justice" --semantic-floor 0.55
    """
    if scope and kind:
        raise click.UsageError("--scope and --kind are mutually exclusive; use one or the other.")
    reg_path = Path(registry).resolve() if registry else None
    with KGRAG(registry_path=reg_path) as kg:
        if scope:
            result = _resolve_scoped_query(kg, scope, query_text, k, min_score, semantic_floor)
        else:
            result = kg.query(
                query_text,
                k=k,
                kinds=_parse_kinds(kind),
                min_score=min_score,
                semantic_floor=semantic_floor,
            )

    if result.kgs_queried == 0:
        console.print("[yellow]No available KGs to query. Register and build some first.[/yellow]")
        return

    if output_json:
        import json  # pylint: disable=import-outside-toplevel

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
@_scope_option
@click.option("--out", default=None, metavar="FILE", help="Write pack to file instead of stdout.")
@_semantic_floor_option
@registry_option
def pack(query_text, k, context, kind, scope, out, semantic_floor, registry):
    """Cross-KG snippet pack — extract source snippets for LLM ingestion.

    \b
    QUERY_TEXT  Natural-language query string

    Scope routing (--scope takes precedence over --kind):
      --scope NAME  targets a named corpus or person corpus; --kind is ignored.
      --kind TYPE   filters the flat registry by KGKind (code/doc/meta/…).
      (neither)     packs from all registered KGs.

    Examples:

    \b
        kgrag pack "graph traversal logic"
        kgrag pack "API endpoints" --kind code --out snippets.md
        kgrag pack "relevance scoring" --scope KGRAG_repos --out context.md
        kgrag pack "journal entries about travel" --scope alice
        kgrag pack "what did Twain think about justice" --semantic-floor 0.55
    """
    if scope and kind:
        raise click.UsageError("--scope and --kind are mutually exclusive; use one or the other.")
    reg_path = Path(registry).resolve() if registry else None
    with KGRAG(registry_path=reg_path) as kg:
        if scope:
            result = _resolve_scoped_pack(kg, scope, query_text, k, context, semantic_floor)
        else:
            result = kg.pack(
                query_text,
                k=k,
                context=context,
                kinds=_parse_kinds(kind),
                semantic_floor=semantic_floor,
            )

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
