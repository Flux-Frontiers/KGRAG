"""
group.py

Root Click group for the KGRAG CLI. Extracted here to avoid circular imports
between main.py and the cmd_* modules that decorate commands onto the group.
"""

from __future__ import annotations

import importlib.metadata

import click


@click.group()
@click.version_option(version=importlib.metadata.version("kg-rag"))
def cli():
    """KGRAG — cross-KG registry and federated query layer for CodeKG, DocKG, and MetaKG."""
    pass
