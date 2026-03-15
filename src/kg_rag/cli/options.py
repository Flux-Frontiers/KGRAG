"""
options.py

Shared Click option decorators for the KGRAG CLI.
"""

from __future__ import annotations

import click

from kg_rag.primitives import KGKind

_KIND_CHOICES = [k.value for k in KGKind]

registry_option = click.option(
    "--registry",
    default=None,
    metavar="PATH",
    help="Path to the KGRAG registry SQLite file. Overrides KGRAG_REGISTRY env var.",
    envvar="KGRAG_REGISTRY",
)

kind_option = click.option(
    "--kind",
    type=click.Choice(_KIND_CHOICES, case_sensitive=False),
    default=None,
    help=f"Filter by KG kind: {', '.join(_KIND_CHOICES)}.",
)

k_option = click.option(
    "-k",
    default=8,
    show_default=True,
    help="Number of results per KG.",
)

context_option = click.option(
    "--context",
    default=5,
    show_default=True,
    help="Lines of context around code snippets.",
)
