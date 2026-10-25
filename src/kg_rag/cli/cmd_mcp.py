"""
cmd_mcp.py

``kgrag mcp`` -- the fleet's standard MCP command, from :mod:`kg_utils.mcp`::

    kgrag mcp [--db REGISTRY] [--repo DIR] [--transport stdio|streamable-http]
              [--host H] [--port N] [--manifest]

For KGRAG, ``--db`` is the registry (default: ``KGRAG_REGISTRY``, else
``~/.kgrag/registry.sqlite``) and ``--repo`` is where ``[tool.kgrag]``
config is read. ``--vectors`` and ``--model`` belong to a single KG and are
refused: each registered KG uses its own. ``--registry PATH``, the old
spelling of ``--db``, is accepted until 0.19.

Registering the command imports neither ``mcp`` nor the server module.
"""

from __future__ import annotations

import sys
from collections.abc import Callable
from pathlib import Path
from typing import TYPE_CHECKING, Any

import click
from kg_utils.mcp import add_mcp_command

from kg_rag.cli.group import cli

if TYPE_CHECKING:
    from kg_utils.mcp import KGServer


def _build_server(repo: Path, db: Path | None, vectors: Path | None, model: str | None) -> KGServer:
    from kg_rag.mcp_server import build_server  # pylint: disable=import-outside-toplevel

    for flag, value in (("--vectors", vectors), ("--model", model)):
        if value is not None:
            raise click.UsageError(
                f"{flag} does not apply to kgrag: it serves a registry, and each "
                "registered KG uses its own store and model"
            )
    return build_server(db, repo)


mcp_command = add_mcp_command(cli, _build_server)

# `--registry`, the pre-0.18 spelling of --db: hidden, mapped, for one minor.
if mcp_command.callback is None:  # pragma: no cover - add_mcp_command always sets one
    raise RuntimeError("kgrag mcp: the standard command has no callback")
_serve: Callable[..., Any] = mcp_command.callback
mcp_command.params.append(
    click.Option(["--registry"], default=None, hidden=True, help="Old name for --db.")
)


def _serve_with_registry(registry: str | None = None, **kwargs: Any) -> Any:
    if registry is not None:
        print("kgrag mcp: --registry is now --db; accepted until 0.19", file=sys.stderr)
        kwargs["db"] = kwargs.get("db") or Path(registry)
    return _serve(**kwargs)


mcp_command.callback = _serve_with_registry
