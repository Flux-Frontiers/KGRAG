"""
cmd_mcp.py

Launch the KGRAG MCP server.
"""
from __future__ import annotations

from pathlib import Path

import click

from kg_rag.cli.main import cli
from kg_rag.cli.options import registry_option


@cli.command("mcp")
@click.option("--host", default="localhost", show_default=True, help="MCP server host.")
@click.option("--port", default=8765, show_default=True, help="MCP server port.")
@registry_option
def mcp(host, port, registry):
    """Launch the KGRAG MCP server (cross-KG tools for Claude/Cursor)."""
    from kg_rag.mcp_server import main as mcp_main
    mcp_main(host=host, port=port, registry_path=Path(registry) if registry else None)
