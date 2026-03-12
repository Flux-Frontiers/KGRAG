"""
main.py

Root Click group for the KGRAG CLI.

Usage::

    kgrag --help
    kgrag --version
"""
from __future__ import annotations

import importlib.metadata

import click

import kg_rag.cli.cmd_registry  # noqa: F401 — registers commands
import kg_rag.cli.cmd_query     # noqa: F401
import kg_rag.cli.cmd_analyze   # noqa: F401
import kg_rag.cli.cmd_mcp       # noqa: F401


@click.group()
@click.version_option(version=importlib.metadata.version("kg-rag"))
def cli():
    """KGRAG — cross-KG registry and federated query layer for CodeKG, DocKG, and MetaKG."""
    pass


if __name__ == "__main__":
    cli()
