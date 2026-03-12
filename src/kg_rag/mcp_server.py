"""
mcp_server.py

KGRAG MCP server — exposes cross-KG tools for Claude Code, Cursor, and other
MCP-compatible agents.

Tools exposed:
    kgrag_stats()               — Registry summary and per-KG stats
    kgrag_query(q, k, kinds)    — Federated semantic query
    kgrag_pack(q, k, kinds)     — Federated snippet pack
    kgrag_list()                — List all registered KGs
    kgrag_info(name)            — Detailed info for a single KG
"""
from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import TextContent, Tool

from kg_rag.orchestrator import KGRAG
from kg_rag.registry import KGRegistry, default_registry_path


def _make_server(registry_path: Path | None = None) -> Server:
    server = Server("kgrag")
    reg_path = registry_path or default_registry_path()

    @server.list_tools()
    async def list_tools() -> list[Tool]:
        return [
            Tool(
                name="kgrag_stats",
                description="Registry summary: total KGs, per-kind counts, built status.",
                inputSchema={"type": "object", "properties": {}, "required": []},
            ),
            Tool(
                name="kgrag_list",
                description="List all registered KG instances with paths and build status.",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "kind": {
                            "type": "string",
                            "enum": ["code", "doc", "meta"],
                            "description": "Optional filter by KG kind.",
                        }
                    },
                    "required": [],
                },
            ),
            Tool(
                name="kgrag_info",
                description="Detailed information about a registered KG by name or id.",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "name": {"type": "string", "description": "KG name or UUID."}
                    },
                    "required": ["name"],
                },
            ),
            Tool(
                name="kgrag_query",
                description=(
                    "Federated semantic query across all (or selected) registered KGs. "
                    "Returns ranked hits from code, doc, and metabolic KGs."
                ),
                inputSchema={
                    "type": "object",
                    "properties": {
                        "q": {"type": "string", "description": "Natural-language query."},
                        "k": {"type": "integer", "default": 8, "description": "Hits per KG."},
                        "kinds": {
                            "type": "array",
                            "items": {"type": "string", "enum": ["code", "doc", "meta"]},
                            "description": "Restrict to these KG kinds.",
                        },
                    },
                    "required": ["q"],
                },
            ),
            Tool(
                name="kgrag_pack",
                description=(
                    "Federated snippet pack across all registered KGs. "
                    "Returns source snippets suitable for LLM context."
                ),
                inputSchema={
                    "type": "object",
                    "properties": {
                        "q": {"type": "string", "description": "Natural-language query."},
                        "k": {"type": "integer", "default": 8, "description": "Snippets per KG."},
                        "context": {
                            "type": "integer",
                            "default": 5,
                            "description": "Lines of context for code snippets.",
                        },
                        "kinds": {
                            "type": "array",
                            "items": {"type": "string", "enum": ["code", "doc", "meta"]},
                            "description": "Restrict to these KG kinds.",
                        },
                    },
                    "required": ["q"],
                },
            ),
        ]

    @server.call_tool()
    async def call_tool(name: str, arguments: dict[str, Any]) -> list[TextContent]:
        if name == "kgrag_stats":
            with KGRegistry(db_path=reg_path) as reg:
                stats = reg.stats()
            result = {
                "total": stats.total,
                "by_kind": stats.by_kind,
                "built": stats.built,
                "registry_path": str(stats.registry_path),
            }
            return [TextContent(type="text", text=json.dumps(result, indent=2))]

        if name == "kgrag_list":
            kind_filter = arguments.get("kind")
            with KGRegistry(db_path=reg_path) as reg:
                from kg_rag.primitives import KGKind
                entries = reg.list(kind=KGKind.from_str(kind_filter) if kind_filter else None)
            data = [
                {
                    "name": e.name,
                    "kind": e.kind.value,
                    "built": e.is_built,
                    "version": e.version,
                    "repo_path": str(e.repo_path),
                    "venv_path": str(e.venv_path),
                    "sqlite_path": str(e.sqlite_path) if e.sqlite_path else None,
                    "lancedb_path": str(e.lancedb_path) if e.lancedb_path else None,
                    "tags": e.tags,
                }
                for e in entries
            ]
            return [TextContent(type="text", text=json.dumps(data, indent=2))]

        if name == "kgrag_info":
            name_or_id = arguments["name"]
            with KGRegistry(db_path=reg_path) as reg:
                entry = reg.get(name_or_id)
            if entry is None:
                return [TextContent(type="text", text=json.dumps({"error": f"Not found: {name_or_id}"}))]
            data = {
                "id": entry.id,
                "name": entry.name,
                "kind": entry.kind.value,
                "built": entry.is_built,
                "version": entry.version,
                "repo_path": str(entry.repo_path),
                "venv_path": str(entry.venv_path),
                "sqlite_path": str(entry.sqlite_path) if entry.sqlite_path else None,
                "lancedb_path": str(entry.lancedb_path) if entry.lancedb_path else None,
                "tags": entry.tags,
                "metadata": entry.metadata,
                "created_at": entry.created_at.isoformat(),
                "updated_at": entry.updated_at.isoformat(),
            }
            return [TextContent(type="text", text=json.dumps(data, indent=2))]

        if name == "kgrag_query":
            q = arguments["q"]
            k = int(arguments.get("k", 8))
            kinds_raw = arguments.get("kinds")
            from kg_rag.primitives import KGKind
            kinds = [KGKind.from_str(kk) for kk in kinds_raw] if kinds_raw else None
            with KGRAG(registry_path=reg_path) as kgrag:
                result = kgrag.query(q, k=k, kinds=kinds)
            data = {
                "query": result.query,
                "total_hits": result.total_hits,
                "kgs_queried": result.kgs_queried,
                "hits": [
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
                ],
            }
            return [TextContent(type="text", text=json.dumps(data, indent=2))]

        if name == "kgrag_pack":
            q = arguments["q"]
            k = int(arguments.get("k", 8))
            context = int(arguments.get("context", 5))
            kinds_raw = arguments.get("kinds")
            from kg_rag.primitives import KGKind
            kinds = [KGKind.from_str(kk) for kk in kinds_raw] if kinds_raw else None
            with KGRAG(registry_path=reg_path) as kgrag:
                result = kgrag.pack(q, k=k, context=context, kinds=kinds)
            return [TextContent(type="text", text=result.render())]

        return [TextContent(type="text", text=json.dumps({"error": f"Unknown tool: {name}"}))]

    return server


def main(host: str = "localhost", port: int = 8765, registry_path: Path | None = None) -> None:
    """Entry point for the KGRAG MCP server.

    :param host: Server host (unused for stdio transport).
    :param port: Server port (unused for stdio transport).
    :param registry_path: Override registry path.
    """
    import asyncio

    server = _make_server(registry_path=registry_path)

    async def _run():
        async with stdio_server() as (r, w):
            await server.run(r, w, server.create_initialization_options())

    asyncio.run(_run())


if __name__ == "__main__":
    main()
