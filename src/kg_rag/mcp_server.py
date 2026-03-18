"""
mcp_server.py

KGRAG MCP server — exposes cross-KG tools for Claude Code, Cursor, and other
MCP-compatible agents.

Tools exposed:
    kgrag_stats()                          — Registry summary and per-KG stats
    kgrag_query(q, k, kinds)               — Federated semantic query
    kgrag_pack(q, k, kinds)                — Federated snippet pack
    kgrag_list()                           — List all registered KGs
    kgrag_info(name)                       — Detailed info for a single KG
    kgrag_corpus_list()                    — List all corpora
    kgrag_corpus_info(name)                — Detailed info for a corpus
    kgrag_corpus_create(name, kg_names)    — Create a corpus
    kgrag_corpus_delete(name)              — Delete a corpus
    kgrag_corpus_add(corpus, kg)           — Add KG to corpus
    kgrag_corpus_remove(corpus, kg)        — Remove KG from corpus
    kgrag_corpus_query(corpus, q, k)       — Query within a corpus
    kgrag_corpus_pack(corpus, q, k)        — Snippet pack within a corpus
    kgrag_person_list()                    — List all person corpus entries
    kgrag_person_info(name)                — Detailed info for a person corpus
    kgrag_person_create(name, ...)         — Create a person corpus entry
    kgrag_person_delete(name)              — Delete a person corpus entry
    kgrag_person_add(person, kg)           — Add KG to a person corpus
    kgrag_person_remove(person, kg)        — Remove KG from a person corpus
    kgrag_person_update(name, ...)         — Update personal metadata
    kgrag_person_query(person, q, k)       — Query within a person corpus
    kgrag_person_pack(person, q, k)        — Snippet pack within a person corpus
"""

from __future__ import annotations

import asyncio
import json
from pathlib import Path
from typing import Any

from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import TextContent, Tool

from kg_rag.corpus_registry import CorpusRegistry
from kg_rag.orchestrator import KGRAG
from kg_rag.person_registry import PersonCorpusRegistry
from kg_rag.primitives import CorpusEntry, KGKind, PersonCorpusEntry
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
                            "enum": [
                                "code",
                                "doc",
                                "meta",
                                "diary",
                                "verse",
                                "memory",
                                "disulfide",
                                "pdbfile",
                                "legal",
                                "person",
                            ],
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
                    "properties": {"name": {"type": "string", "description": "KG name or UUID."}},
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
                            "items": {
                                "type": "string",
                                "enum": [
                                    "code",
                                    "doc",
                                    "meta",
                                    "diary",
                                    "verse",
                                    "memory",
                                    "disulfide",
                                    "pdbfile",
                                    "legal",
                                    "person",
                                ],
                            },
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
                            "items": {
                                "type": "string",
                                "enum": [
                                    "code",
                                    "doc",
                                    "meta",
                                    "diary",
                                    "verse",
                                    "memory",
                                    "disulfide",
                                    "pdbfile",
                                    "legal",
                                    "person",
                                ],
                            },
                            "description": "Restrict to these KG kinds.",
                        },
                    },
                    "required": ["q"],
                },
            ),
            # ------ Corpus tools ------
            Tool(
                name="kgrag_corpus_list",
                description="List all corpora in the KGRAG registry.",
                inputSchema={"type": "object", "properties": {}, "required": []},
            ),
            Tool(
                name="kgrag_corpus_info",
                description="Detailed information about a corpus by name or id.",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "name": {"type": "string", "description": "Corpus name or UUID."}
                    },
                    "required": ["name"],
                },
            ),
            Tool(
                name="kgrag_corpus_create",
                description="Create a new corpus grouping one or more registered KGs.",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "name": {"type": "string", "description": "Corpus name."},
                        "kg_names": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "List of KG names or UUIDs to include.",
                        },
                        "description": {
                            "type": "string",
                            "default": "",
                            "description": "Optional description.",
                        },
                        "tags": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "Optional tags.",
                        },
                    },
                    "required": ["name"],
                },
            ),
            Tool(
                name="kgrag_corpus_delete",
                description="Delete a corpus from the registry (KGs themselves are not removed).",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "name": {"type": "string", "description": "Corpus name or UUID."}
                    },
                    "required": ["name"],
                },
            ),
            Tool(
                name="kgrag_corpus_add",
                description="Add a KG to an existing corpus.",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "corpus": {"type": "string", "description": "Corpus name or UUID."},
                        "kg": {"type": "string", "description": "KG name or UUID to add."},
                    },
                    "required": ["corpus", "kg"],
                },
            ),
            Tool(
                name="kgrag_corpus_remove",
                description="Remove a KG from a corpus.",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "corpus": {"type": "string", "description": "Corpus name or UUID."},
                        "kg": {"type": "string", "description": "KG name or UUID to remove."},
                    },
                    "required": ["corpus", "kg"],
                },
            ),
            Tool(
                name="kgrag_corpus_query",
                description="Federated semantic query scoped to a named corpus.",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "corpus": {"type": "string", "description": "Corpus name or UUID."},
                        "q": {"type": "string", "description": "Natural-language query."},
                        "k": {"type": "integer", "default": 8, "description": "Hits per KG."},
                    },
                    "required": ["corpus", "q"],
                },
            ),
            Tool(
                name="kgrag_corpus_pack",
                description="Federated snippet pack scoped to a named corpus.",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "corpus": {"type": "string", "description": "Corpus name or UUID."},
                        "q": {"type": "string", "description": "Natural-language query."},
                        "k": {"type": "integer", "default": 8, "description": "Snippets per KG."},
                        "context": {
                            "type": "integer",
                            "default": 5,
                            "description": "Lines of context.",
                        },
                    },
                    "required": ["corpus", "q"],
                },
            ),
            # ------ Person corpus tools ------
            Tool(
                name="kgrag_person_list",
                description="List all person corpus entries in the registry.",
                inputSchema={"type": "object", "properties": {}, "required": []},
            ),
            Tool(
                name="kgrag_person_info",
                description="Detailed info about a person corpus entry including personal metadata and KG list.",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "name": {"type": "string", "description": "Person name or UUID."}
                    },
                    "required": ["name"],
                },
            ),
            Tool(
                name="kgrag_person_create",
                description="Create a person corpus entry grouping KGs relevant to an individual.",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "name": {"type": "string", "description": "Full name of the person."},
                        "kg_names": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "KG names or UUIDs to include.",
                        },
                        "birth_year": {"type": "integer", "description": "Year of birth."},
                        "birth_date": {
                            "type": "string",
                            "description": "Full birth date (YYYY-MM-DD).",
                        },
                        "address": {"type": "string", "description": "Mailing/home address."},
                        "email": {"type": "string", "description": "Primary email address."},
                        "phone": {"type": "string", "description": "Primary phone number."},
                        "notes": {"type": "string", "description": "Free-form notes."},
                        "tags": {
                            "type": "array",
                            "items": {"type": "string"},
                            "description": "Optional tags.",
                        },
                    },
                    "required": ["name"],
                },
            ),
            Tool(
                name="kgrag_person_delete",
                description="Delete a person corpus entry (KGs are not removed).",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "name": {"type": "string", "description": "Person name or UUID."}
                    },
                    "required": ["name"],
                },
            ),
            Tool(
                name="kgrag_person_add",
                description="Add a KG to an existing person corpus.",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "person": {"type": "string", "description": "Person name or UUID."},
                        "kg": {"type": "string", "description": "KG name or UUID to add."},
                    },
                    "required": ["person", "kg"],
                },
            ),
            Tool(
                name="kgrag_person_remove",
                description="Remove a KG from a person corpus.",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "person": {"type": "string", "description": "Person name or UUID."},
                        "kg": {"type": "string", "description": "KG name or UUID to remove."},
                    },
                    "required": ["person", "kg"],
                },
            ),
            Tool(
                name="kgrag_person_update",
                description="Update personal metadata for a person corpus entry.",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "name": {"type": "string", "description": "Person name or UUID."},
                        "birth_year": {"type": "integer", "description": "Year of birth."},
                        "birth_date": {
                            "type": "string",
                            "description": "Full birth date (YYYY-MM-DD).",
                        },
                        "address": {"type": "string", "description": "Mailing/home address."},
                        "email": {"type": "string", "description": "Primary email address."},
                        "phone": {"type": "string", "description": "Primary phone number."},
                        "notes": {"type": "string", "description": "Free-form notes."},
                    },
                    "required": ["name"],
                },
            ),
            Tool(
                name="kgrag_person_query",
                description="Federated semantic query scoped to a person corpus.",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "person": {"type": "string", "description": "Person name or UUID."},
                        "q": {"type": "string", "description": "Natural-language query."},
                        "k": {"type": "integer", "default": 8, "description": "Hits per KG."},
                    },
                    "required": ["person", "q"],
                },
            ),
            Tool(
                name="kgrag_person_pack",
                description="Federated snippet pack scoped to a person corpus.",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "person": {"type": "string", "description": "Person name or UUID."},
                        "q": {"type": "string", "description": "Natural-language query."},
                        "k": {"type": "integer", "default": 8, "description": "Snippets per KG."},
                        "context": {
                            "type": "integer",
                            "default": 5,
                            "description": "Lines of context.",
                        },
                    },
                    "required": ["person", "q"],
                },
            ),
        ]

    @server.call_tool()
    async def call_tool(name: str, arguments: dict[str, Any]) -> list[TextContent]:
        entries: Any
        stats: Any
        entry: Any
        result: Any
        data: Any
        updated: Any
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
                entries = reg.list(kind=KGKind.from_str(kind_filter) if kind_filter else None)
            list_data = [
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
            return [TextContent(type="text", text=json.dumps(list_data, indent=2))]

        if name == "kgrag_info":
            name_or_id = arguments["name"]
            with KGRegistry(db_path=reg_path) as reg:
                entry = reg.get(name_or_id)
            if entry is None:
                return [
                    TextContent(type="text", text=json.dumps({"error": f"Not found: {name_or_id}"}))
                ]
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
            kinds = [KGKind.from_str(kk) for kk in kinds_raw] if kinds_raw else None
            with KGRAG(registry_path=reg_path) as kgrag:
                query_result = kgrag.query(q, k=k, kinds=kinds)
            query_data = {
                "query": query_result.query,
                "total_hits": query_result.total_hits,
                "kgs_queried": query_result.kgs_queried,
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
                    for h in query_result.hits
                ],
            }
            return [TextContent(type="text", text=json.dumps(query_data, indent=2))]

        if name == "kgrag_pack":
            q = arguments["q"]
            k = int(arguments.get("k", 8))
            context = int(arguments.get("context", 5))
            kinds_raw = arguments.get("kinds")
            kinds = [KGKind.from_str(kk) for kk in kinds_raw] if kinds_raw else None
            with KGRAG(registry_path=reg_path) as kgrag:
                pack_result = kgrag.pack(q, k=k, context=context, kinds=kinds)
            return [TextContent(type="text", text=pack_result.render())]

        # ------ Corpus tools ------

        if name == "kgrag_corpus_list":
            with CorpusRegistry(db_path=reg_path) as corp_reg:
                entries = corp_reg.list()
                stats = corp_reg.stats()
            data = {
                "total": stats.total,
                "total_kg_refs": stats.total_kg_refs,
                "corpora": [
                    {
                        "id": e.id,
                        "name": e.name,
                        "description": e.description,
                        "size": e.size,
                        "kg_ids": e.kg_ids,
                        "tags": e.tags,
                        "updated_at": e.updated_at.isoformat(),
                    }
                    for e in entries
                ],
            }
            return [TextContent(type="text", text=json.dumps(data, indent=2))]

        if name == "kgrag_corpus_info":
            corpus_name = arguments["name"]
            with (
                KGRegistry(db_path=reg_path) as kg_reg,
                CorpusRegistry(db_path=reg_path) as corp_reg,
            ):
                entry = corp_reg.get(corpus_name)
                if entry is None:
                    return [
                        TextContent(
                            type="text",
                            text=json.dumps({"error": f"Corpus not found: {corpus_name}"}),
                        )
                    ]
                kg_details = []
                for kg_id in entry.kg_ids:
                    kg_entry = kg_reg.get(kg_id)
                    if kg_entry:
                        kg_details.append(
                            {
                                "id": kg_id,
                                "name": kg_entry.name,
                                "kind": kg_entry.kind.value,
                                "built": kg_entry.is_built,
                            }
                        )
                    else:
                        kg_details.append({"id": kg_id, "name": None, "kind": None, "built": False})
            data = {
                "id": entry.id,
                "name": entry.name,
                "description": entry.description,
                "size": entry.size,
                "kgs": kg_details,
                "tags": entry.tags,
                "metadata": entry.metadata,
                "created_at": entry.created_at.isoformat(),
                "updated_at": entry.updated_at.isoformat(),
            }
            return [TextContent(type="text", text=json.dumps(data, indent=2))]

        if name == "kgrag_corpus_create":
            corpus_name = arguments["name"]
            kg_names = arguments.get("kg_names", [])
            description = arguments.get("description", "")
            tags = arguments.get("tags", [])
            with (
                KGRegistry(db_path=reg_path) as kg_reg,
                CorpusRegistry(db_path=reg_path) as corp_reg,
            ):
                kg_ids = []
                missing = []
                for ref in kg_names:
                    kg_entry = kg_reg.get(ref)
                    if kg_entry:
                        kg_ids.append(kg_entry.id)
                    else:
                        missing.append(ref)
                if missing:
                    return [
                        TextContent(
                            type="text", text=json.dumps({"error": f"KGs not found: {missing}"})
                        )
                    ]
                corpus = CorpusEntry(
                    name=corpus_name, description=description, kg_ids=kg_ids, tags=tags
                )
                corp_reg.create(corpus)
            return [
                TextContent(
                    type="text", text=json.dumps({"created": corpus_name, "size": len(kg_ids)})
                )
            ]

        if name == "kgrag_corpus_delete":
            corpus_name = arguments["name"]
            with CorpusRegistry(db_path=reg_path) as corp_reg:
                deleted = corp_reg.delete(corpus_name)
            result = (
                {"deleted": corpus_name}
                if deleted
                else {"error": f"Corpus not found: {corpus_name}"}
            )
            return [TextContent(type="text", text=json.dumps(result))]

        if name == "kgrag_corpus_add":
            corpus_name = arguments["corpus"]
            kg_ref = arguments["kg"]
            with (
                KGRegistry(db_path=reg_path) as kg_reg,
                CorpusRegistry(db_path=reg_path) as corp_reg,
            ):
                kg_entry = kg_reg.get(kg_ref)
                if kg_entry is None:
                    return [
                        TextContent(
                            type="text", text=json.dumps({"error": f"KG not found: {kg_ref}"})
                        )
                    ]
                updated = corp_reg.add_kg(corpus_name, kg_entry.id)
                if updated is None:
                    return [
                        TextContent(
                            type="text",
                            text=json.dumps({"error": f"Corpus not found: {corpus_name}"}),
                        )
                    ]
            return [
                TextContent(
                    type="text",
                    text=json.dumps({"corpus": corpus_name, "added": kg_ref, "size": updated.size}),
                )
            ]

        if name == "kgrag_corpus_remove":
            corpus_name = arguments["corpus"]
            kg_ref = arguments["kg"]
            with (
                KGRegistry(db_path=reg_path) as kg_reg,
                CorpusRegistry(db_path=reg_path) as corp_reg,
            ):
                kg_entry = kg_reg.get(kg_ref)
                if kg_entry is None:
                    return [
                        TextContent(
                            type="text", text=json.dumps({"error": f"KG not found: {kg_ref}"})
                        )
                    ]
                updated = corp_reg.remove_kg(corpus_name, kg_entry.id)
                if updated is None:
                    return [
                        TextContent(
                            type="text",
                            text=json.dumps({"error": f"Corpus not found: {corpus_name}"}),
                        )
                    ]
            return [
                TextContent(
                    type="text",
                    text=json.dumps(
                        {"corpus": corpus_name, "removed": kg_ref, "size": updated.size}
                    ),
                )
            ]

        if name == "kgrag_corpus_query":
            corpus_name = arguments["corpus"]
            q = arguments["q"]
            k = int(arguments.get("k", 8))
            with KGRAG(registry_path=reg_path) as kgrag:
                try:
                    result = kgrag.query_corpus(corpus_name, q, k=k)
                except KeyError as e:
                    return [TextContent(type="text", text=json.dumps({"error": str(e)}))]
            data = {
                "query": result.query,
                "corpus": corpus_name,
                "total_hits": result.total_hits,
                "kgs_queried": result.kgs_queried,
                "hits": [
                    {
                        "kg": h.kg_name,
                        "kind": h.kg_kind.value,
                        "name": h.name,
                        "score": round(h.score, 4),
                        "summary": h.summary,
                        "source_path": h.source_path,
                    }
                    for h in result.hits
                ],
            }
            return [TextContent(type="text", text=json.dumps(data, indent=2))]

        if name == "kgrag_corpus_pack":
            corpus_name = arguments["corpus"]
            q = arguments["q"]
            k = int(arguments.get("k", 8))
            context = int(arguments.get("context", 5))
            with KGRAG(registry_path=reg_path) as kgrag:
                try:
                    pack_result = kgrag.pack_corpus(corpus_name, q, k=k, context=context)
                except KeyError as e:
                    return [TextContent(type="text", text=json.dumps({"error": str(e)}))]
            return [TextContent(type="text", text=pack_result.render())]

        # ------ Person corpus tools ------

        if name == "kgrag_person_list":
            with PersonCorpusRegistry(db_path=reg_path) as per_reg:
                entries = per_reg.list()
                stats = per_reg.stats()
            data = {
                "total": stats.total,
                "total_kg_refs": stats.total_kg_refs,
                "persons": [
                    {
                        "id": e.id,
                        "name": e.name,
                        "birth_year": e.birth_year,
                        "birth_date": e.birth_date,
                        "email": e.email,
                        "size": e.size,
                        "tags": e.tags,
                        "updated_at": e.updated_at.isoformat(),
                    }
                    for e in entries
                ],
            }
            return [TextContent(type="text", text=json.dumps(data, indent=2))]

        if name == "kgrag_person_info":
            person_name = arguments["name"]
            with (
                KGRegistry(db_path=reg_path) as kg_reg,
                PersonCorpusRegistry(db_path=reg_path) as per_reg,
            ):
                entry = per_reg.get(person_name)
                if entry is None:
                    return [
                        TextContent(
                            type="text",
                            text=json.dumps({"error": f"Person not found: {person_name}"}),
                        )
                    ]
                kg_details = []
                for kg_id in entry.kg_ids:
                    kg_entry = kg_reg.get(kg_id)
                    if kg_entry:
                        kg_details.append(
                            {"id": kg_id, "name": kg_entry.name, "kind": kg_entry.kind.value}
                        )
                    else:
                        kg_details.append({"id": kg_id, "name": None, "kind": None})
            data = {
                "id": entry.id,
                "name": entry.name,
                "birth_year": entry.birth_year,
                "birth_date": entry.birth_date,
                "address": entry.address,
                "email": entry.email,
                "phone": entry.phone,
                "notes": entry.notes,
                "size": entry.size,
                "kgs": kg_details,
                "tags": entry.tags,
                "metadata": entry.metadata,
                "created_at": entry.created_at.isoformat(),
                "updated_at": entry.updated_at.isoformat(),
            }
            return [TextContent(type="text", text=json.dumps(data, indent=2))]

        if name == "kgrag_person_create":
            person_name = arguments["name"]
            kg_names = arguments.get("kg_names", [])
            with (
                KGRegistry(db_path=reg_path) as kg_reg,
                PersonCorpusRegistry(db_path=reg_path) as per_reg,
            ):
                kg_ids, missing = [], []
                for ref in kg_names:
                    kg_entry = kg_reg.get(ref)
                    if kg_entry:
                        kg_ids.append(kg_entry.id)
                    else:
                        missing.append(ref)
                if missing:
                    return [
                        TextContent(
                            type="text", text=json.dumps({"error": f"KGs not found: {missing}"})
                        )
                    ]
                person = PersonCorpusEntry(
                    name=person_name,
                    kg_ids=kg_ids,
                    birth_year=arguments.get("birth_year"),
                    birth_date=arguments.get("birth_date"),
                    address=arguments.get("address", ""),
                    email=arguments.get("email", ""),
                    phone=arguments.get("phone", ""),
                    notes=arguments.get("notes", ""),
                    tags=arguments.get("tags", []),
                )
                per_reg.create(person)
            return [
                TextContent(
                    type="text", text=json.dumps({"created": person_name, "size": len(kg_ids)})
                )
            ]

        if name == "kgrag_person_delete":
            person_name = arguments["name"]
            with PersonCorpusRegistry(db_path=reg_path) as per_reg:
                deleted = per_reg.delete(person_name)
            result = (
                {"deleted": person_name}
                if deleted
                else {"error": f"Person not found: {person_name}"}
            )
            return [TextContent(type="text", text=json.dumps(result))]

        if name == "kgrag_person_add":
            person_name = arguments["person"]
            kg_ref = arguments["kg"]
            with (
                KGRegistry(db_path=reg_path) as kg_reg,
                PersonCorpusRegistry(db_path=reg_path) as per_reg,
            ):
                kg_entry = kg_reg.get(kg_ref)
                if kg_entry is None:
                    return [
                        TextContent(
                            type="text", text=json.dumps({"error": f"KG not found: {kg_ref}"})
                        )
                    ]
                updated = per_reg.add_kg(person_name, kg_entry.id)
                if updated is None:
                    return [
                        TextContent(
                            type="text",
                            text=json.dumps({"error": f"Person not found: {person_name}"}),
                        )
                    ]
            return [
                TextContent(
                    type="text",
                    text=json.dumps({"person": person_name, "added": kg_ref, "size": updated.size}),
                )
            ]

        if name == "kgrag_person_remove":
            person_name = arguments["person"]
            kg_ref = arguments["kg"]
            with (
                KGRegistry(db_path=reg_path) as kg_reg,
                PersonCorpusRegistry(db_path=reg_path) as per_reg,
            ):
                kg_entry = kg_reg.get(kg_ref)
                if kg_entry is None:
                    return [
                        TextContent(
                            type="text", text=json.dumps({"error": f"KG not found: {kg_ref}"})
                        )
                    ]
                updated = per_reg.remove_kg(person_name, kg_entry.id)
                if updated is None:
                    return [
                        TextContent(
                            type="text",
                            text=json.dumps({"error": f"Person not found: {person_name}"}),
                        )
                    ]
            return [
                TextContent(
                    type="text",
                    text=json.dumps(
                        {"person": person_name, "removed": kg_ref, "size": updated.size}
                    ),
                )
            ]

        if name == "kgrag_person_update":
            person_name = arguments["name"]
            fields = {k: v for k, v in arguments.items() if k != "name" and v is not None}
            with PersonCorpusRegistry(db_path=reg_path) as per_reg:
                updated = per_reg.update(person_name, **fields)
                if updated is None:
                    return [
                        TextContent(
                            type="text",
                            text=json.dumps({"error": f"Person not found: {person_name}"}),
                        )
                    ]
            return [
                TextContent(
                    type="text",
                    text=json.dumps({"updated": person_name, "fields": list(fields.keys())}),
                )
            ]

        if name == "kgrag_person_query":
            person_name = arguments["person"]
            q = arguments["q"]
            k = int(arguments.get("k", 8))
            with KGRAG(registry_path=reg_path) as kgrag:
                try:
                    result = kgrag.query_person(person_name, q, k=k)
                except KeyError as e:
                    return [TextContent(type="text", text=json.dumps({"error": str(e)}))]
            data = {
                "query": result.query,
                "person": person_name,
                "total_hits": result.total_hits,
                "kgs_queried": result.kgs_queried,
                "hits": [
                    {
                        "kg": h.kg_name,
                        "kind": h.kg_kind.value,
                        "name": h.name,
                        "score": round(h.score, 4),
                        "summary": h.summary,
                        "source_path": h.source_path,
                    }
                    for h in result.hits
                ],
            }
            return [TextContent(type="text", text=json.dumps(data, indent=2))]

        if name == "kgrag_person_pack":
            person_name = arguments["person"]
            q = arguments["q"]
            k = int(arguments.get("k", 8))
            context = int(arguments.get("context", 5))
            with KGRAG(registry_path=reg_path) as kgrag:
                try:
                    pack_result = kgrag.pack_person(person_name, q, k=k, context=context)
                except KeyError as e:
                    return [TextContent(type="text", text=json.dumps({"error": str(e)}))]
            return [TextContent(type="text", text=pack_result.render())]

        return [TextContent(type="text", text=json.dumps({"error": f"Unknown tool: {name}"}))]

    return server


def main(host: str = "localhost", port: int = 8765, registry_path: Path | None = None) -> None:
    """Entry point for the KGRAG MCP server.

    :param host: Server host (unused for stdio transport).
    :param port: Server port (unused for stdio transport).
    :param registry_path: Override registry path.
    """
    server = _make_server(registry_path=registry_path)

    async def _run():
        async with stdio_server() as (r, w):
            await server.run(r, w, server.create_initialization_options())

    asyncio.run(_run())


if __name__ == "__main__":
    main()
