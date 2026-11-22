"""
retrieval.py

Federated passage retrieval shared by CLI commands that ground an LLM call in
registered KGs (``kgrag synthesize``).
"""

from __future__ import annotations

import sys
from pathlib import Path

import click
from rich.console import Console

from kg_rag.orchestrator import KGRAG
from kg_rag.primitives import CrossSnippet, KGKind

console = Console()


def retrieve_snippets(
    kg: KGRAG,
    query_text: str,
    *,
    k: int,
    kinds: list[KGKind] | None,
    corpus: str | None,
    reg_path: Path | None,
    context_lines: int,
    max_context: int,
) -> tuple[list[CrossSnippet], int]:
    """Retrieve the top passages for a query from all registered KGs or one corpus.

    With ``corpus``, each member KG's adapter is packed directly, the
    snippets are ranked by score and the top ``max_context`` are kept.
    Without it, :meth:`KGRAG.pack` federates over the registry.

    :param kg: Open KGRAG orchestrator for the registry.
    :param query_text: Natural-language query.
    :param k: Snippets per KG.
    :param kinds: Keep only KGs of these kinds, or None for all.
    :param corpus: Corpus name to scope retrieval to, or None for all KGs.
    :param reg_path: Registry SQLite path, or None for the default.
    :param context_lines: Lines of surrounding context per snippet.
    :param max_context: Most snippets to return (top-N by score).
    :return: ``(snippets, kgs_queried)``. Each snippet's ``kg_kind`` names
        the kind of KG it came from.
    :raises click.ClickException: If ``corpus`` is not in the registry.
    """
    if corpus:
        # Scoped corpus query -- use the corpus registry
        from kg_rag.corpus_registry import (  # pylint: disable=import-outside-toplevel
            CorpusRegistry,
        )
        from kg_rag.registry import (  # pylint: disable=import-outside-toplevel
            KGRegistry,
        )

        with KGRegistry(db_path=reg_path) as kreg, CorpusRegistry(db_path=reg_path) as creg:
            corpus_entry = creg.get(corpus)
            if corpus_entry is None:
                raise click.ClickException(f"Corpus not found: {corpus!r}")
            kg_ids = corpus_entry.kg_ids
            entries = [kreg.get(gid) for gid in kg_ids]
            entries = [e for e in entries if e is not None]

        if not entries:
            console.print(f"[yellow]Corpus {corpus!r} has no registered KGs.[/yellow]")
            sys.exit(0)

        from kg_rag.adapters import (  # pylint: disable=import-outside-toplevel
            make_adapter,
        )

        snippets: list[CrossSnippet] = []
        for entry in entries:
            if kinds and entry.kind not in kinds:
                continue
            adapter = make_adapter(entry)
            if adapter.is_available():
                snippets.extend(adapter.pack(query_text, k=k, context=context_lines))
        snippets.sort(key=lambda s: s.score, reverse=True)
        snippets = snippets[:max_context]
        kgs_queried = len(entries)
    else:
        pack_result = kg.pack(query_text, k=k, context=context_lines, kinds=kinds)
        snippets = pack_result.snippets[:max_context]
        kgs_queried = pack_result.kgs_queried
    return snippets, kgs_queried
