"""tests/test_mcp_server.py

Regression tests for kg_rag.mcp_server against the installed ``mcp`` release.

KGRAG uses the **low-level** MCP API — ``Server`` plus the
``@server.list_tools()`` / ``@server.call_tool()`` decorators. mcp 2.0 kept the
``Server`` class importable but removed those decorators, so the break shows up
as an ``AttributeError`` when :func:`_make_server` runs rather than at import
time. A plain "does the module import" test would pass while ``kgrag-mcp``
remained completely broken, so these tests build the server for real.

That distinction matters across the fleet: sibling packages using ``FastMCP``
fail at *import* under mcp 2.0 (the ``mcp.server.fastmcp`` module was unbundled
into the standalone ``fastmcp`` package), while KGRAG fails at *call* time.
`pyproject.toml` pins ``mcp<2`` for this reason.
"""

from __future__ import annotations

import importlib
from pathlib import Path


def test_server_module_imports():
    """The module must import cleanly against the installed mcp release."""
    importlib.import_module("kg_rag.mcp_server")


def test_lowlevel_decorator_api_exists():
    """``Server`` must still expose the decorators mcp 2.0 removed.

    Asserted directly so a future incompatibility names the missing API instead
    of surfacing as an opaque AttributeError from inside _make_server().
    """
    from mcp.server import Server

    server = Server("probe")
    for attr in ("list_tools", "call_tool"):
        assert hasattr(server, attr), (
            f"mcp.server.Server has no {attr!r} — the low-level decorator API "
            "was removed in mcp 2.0; kg_rag.mcp_server cannot register handlers"
        )


def test_make_server_registers_handlers(tmp_path: Path):
    """Building the server must run both decorators and register handlers.

    This is the test that actually catches mcp 2.0: the decorators execute here,
    not at import.
    """
    mcp_server = importlib.import_module("kg_rag.mcp_server")
    server = mcp_server._make_server(tmp_path / "registry.sqlite")
    assert server.request_handlers, "no request handlers registered"


def test_entry_point_target_exists():
    """``kgrag-mcp`` resolves to kg_rag.mcp_server:main."""
    mcp_server = importlib.import_module("kg_rag.mcp_server")
    assert callable(mcp_server.main)


def test_tools_are_registered(tmp_path: Path):
    """The advertised tool list survives registration and is non-empty."""
    import asyncio

    from mcp.types import ListToolsRequest

    mcp_server = importlib.import_module("kg_rag.mcp_server")
    server = mcp_server._make_server(tmp_path / "registry.sqlite")

    handler = server.request_handlers[ListToolsRequest]
    result = asyncio.run(handler(ListToolsRequest(method="tools/list")))
    names = {t.name for t in result.root.tools}
    assert names, "no tools registered"
    assert "kgrag_stats" in names
