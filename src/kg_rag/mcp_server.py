"""
mcp_server.py

KGRAG MCP server: the registry's knowledge graphs, federated, for Claude Code,
Cursor and other MCP agents, on the fleet's shared server base,
:mod:`kg_utils.mcp`.

The server answers the fleet's canonical tools -- ``stats``, ``query``,
``pack``, ``get_node``, ``neighbors`` -- across every registered KG, with the
same names and meanings as on a single KG's server (see
:mod:`kg_rag.federation` for federated node ids). Its own tools:

    list_kgs(kind)                      — registered KGs, with paths and build status
    kg_info(name)                       — one registered KG in detail
    corpus_list / corpus_info / corpus_create / corpus_delete
    corpus_add / corpus_remove          — manage corpora (named groups of KGs)
    corpus_query / corpus_pack          — query or pack within a corpus
    person_list / person_info / person_create / person_delete
    person_add / person_remove / person_update
    person_query / person_pack          — the same for person corpora

The tool list is generated from the tools: ``kgrag mcp --manifest`` prints it
as JSON without opening the registry. ``kgrag-mcp`` is the same command.

Usage::

    kgrag mcp                                   # stdio, the default registry
    kgrag mcp --db /path/to/registry.sqlite     # another registry
    kgrag mcp --transport streamable-http --port 8765
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from kg_utils.mcp import Context, KGServer, kg_from, make_server

from kg_rag import __version__
from kg_rag.federation import Federation
from kg_rag.primitives import CorpusEntry, KGKind, PersonCorpusEntry

PREAMBLE = (
    "KGRAG federates every knowledge graph in a registry: code, documents, diaries, "
    "memory, metabolic and the rest. The canonical tools work across all of them. "
    "Node ids are qualified with their KG, '<kg>::<node id>', exactly as query returns "
    "them; pass them to get_node and neighbors unchanged.\n\n"
    "## Recommended workflows\n\n"
    "- **Orientation**: stats (totals, and each KG), list_kgs\n"
    "- **Search everything**: query → get_node; pack for the text; narrow with "
    "kinds=['code'] or ['doc', 'diary']\n"
    "- **Search one group**: corpus_query / person_query\n"
    "- **Walk from a result**: neighbors(id) inside its own KG; hop=1 on query brings "
    "each hit's neighbourhood along"
)

_KINDS = [k.value for k in KGKind]


# ---------------------------------------------------------------------------
# Canonical query / pack: KGRAG's federated versions
# ---------------------------------------------------------------------------


def query(
    q: str,
    k: int = 8,
    hop: int = 0,
    max_nodes: int = 25,
    rels: list[str] | None = None,
    kinds: list[str] | None = None,
    min_score: float = 0.0,
    *,
    ctx: Context,
) -> dict[str, Any]:
    """
    Federated semantic search across every registered KG (or the kinds named), ranked together.

    Each hit carries a federated ``id`` ("<kg>::<node id>") for get_node and
    neighbors.

    :param q: Natural-language query.
    :param k: Hits per KG (default 8).
    :param hop: Hops to walk from each hit inside its own KG (0-5, default 0: hits only).
    :param max_nodes: Most results, hits first (default 25).
    :param rels: Edge types to walk when hop > 0; omit for all.
    :param kinds: Restrict to these KG kinds, e.g. ["code", "doc"].
    :param min_score: Drop hits scoring below this (default 0).
    """
    return kg_from(ctx).query(
        q, k, hop=hop, max_nodes=max_nodes, rels=rels, kinds=kinds, min_score=min_score
    )


def pack(
    q: str,
    k: int = 8,
    hop: int = 0,
    max_nodes: int = 15,
    rels: list[str] | None = None,
    kinds: list[str] | None = None,
    context: int = 5,
    *,
    ctx: Context,
) -> str:
    """
    Federated snippet pack: source text from every registered KG, as Markdown ready for a prompt.

    :param q: Natural-language query.
    :param k: Snippets per KG (default 8).
    :param hop: Hops to walk from each snippet (0-5, default 0); what is reached is listed after.
    :param max_nodes: Most snippets (default 15).
    :param rels: Edge types to walk when hop > 0; omit for all.
    :param kinds: Restrict to these KG kinds.
    :param context: Lines of context around code snippets (default 5).
    """
    return kg_from(ctx).pack(
        q, k, hop=hop, max_nodes=max_nodes, rels=rels, kinds=kinds, context=context
    )


# ---------------------------------------------------------------------------
# The registry
# ---------------------------------------------------------------------------


def _entry_dict(e: Any, *, detail: bool = False) -> dict[str, Any]:
    out = {
        "id": e.id,
        "name": e.name,
        "kind": e.kind.value,
        "built": e.is_built,
        "version": e.version,
        "repo_path": str(e.repo_path),
        "venv_path": str(e.venv_path),
        "sqlite_path": str(e.sqlite_path) if e.sqlite_path else None,
        "vectors_path": str(e.vectors_path) if e.vectors_path else None,
        "tags": e.tags,
    }
    if detail:
        out |= {
            "metadata": e.metadata,
            "created_at": e.created_at.isoformat(),
            "updated_at": e.updated_at.isoformat(),
        }
    return out


def list_kgs(kind: str | None = None, *, ctx: Context) -> list[dict[str, Any]]:
    """
    Every registered KG, with its kind, paths and build status.

    :param kind: Only KGs of this kind, e.g. "code".
    """
    reg = kg_from(ctx).kgrag.registry
    return [_entry_dict(e) for e in reg.list(kind=KGKind.from_str(kind) if kind else None)]


def kg_info(name: str, *, ctx: Context) -> dict[str, Any]:
    """
    One registered KG in detail.

    :param name: KG name or UUID.
    """
    entry = kg_from(ctx).kgrag.registry.get(name)
    if entry is None:
        raise ValueError(f"no KG named {name!r}")
    return _entry_dict(entry, detail=True)


def _resolve_kgs(fed: Federation, refs: list[str]) -> list[str]:
    ids, missing = [], []
    for ref in refs:
        entry = fed.kgrag.registry.get(ref)
        (ids.append(entry.id) if entry else missing.append(ref))
    if missing:
        raise ValueError(f"KGs not found: {missing}")
    return ids


def _kg_id(fed: Federation, ref: str) -> str:
    entry = fed.kgrag.registry.get(ref)
    if entry is None:
        raise ValueError(f"no KG named {ref!r}")
    return entry.id


def _member_kgs(fed: Federation, kg_ids: list[str]) -> list[dict[str, Any]]:
    out = []
    for kg_id in kg_ids:
        e = fed.kgrag.registry.get(kg_id)
        out.append(
            {"id": kg_id, "name": e.name, "kind": e.kind.value, "built": e.is_built}
            if e
            else {"id": kg_id, "name": None, "kind": None, "built": False}
        )
    return out


def _hits(result: Any) -> list[dict[str, Any]]:
    from kg_rag.federation import _hit  # pylint: disable=import-outside-toplevel

    return [_hit(h) for h in result.hits]


# ---------------------------------------------------------------------------
# Corpora
# ---------------------------------------------------------------------------


def corpus_list(*, ctx: Context) -> dict[str, Any]:
    """
    Every corpus (a named group of KGs) in the registry.
    """
    reg = kg_from(ctx).kgrag.corpus_registry
    stats = reg.stats()
    return {
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
            for e in reg.list()
        ],
    }


def corpus_info(name: str, *, ctx: Context) -> dict[str, Any]:
    """
    One corpus in detail, with its member KGs.

    :param name: Corpus name or UUID.
    """
    fed = kg_from(ctx)
    entry = fed.kgrag.corpus_registry.get(name)
    if entry is None:
        raise ValueError(f"no corpus named {name!r}")
    return {
        "id": entry.id,
        "name": entry.name,
        "description": entry.description,
        "size": entry.size,
        "kgs": _member_kgs(fed, entry.kg_ids),
        "tags": entry.tags,
        "metadata": entry.metadata,
        "created_at": entry.created_at.isoformat(),
        "updated_at": entry.updated_at.isoformat(),
    }


def corpus_create(
    name: str,
    kg_names: list[str] | None = None,
    description: str = "",
    tags: list[str] | None = None,
    *,
    ctx: Context,
) -> dict[str, Any]:
    """
    Create a corpus grouping registered KGs.

    :param name: Corpus name.
    :param kg_names: KG names or UUIDs to include.
    :param description: What the corpus is for.
    :param tags: Tags for grouping.
    """
    fed = kg_from(ctx)
    kg_ids = _resolve_kgs(fed, kg_names or [])
    fed.kgrag.corpus_registry.create(
        CorpusEntry(name=name, description=description, kg_ids=kg_ids, tags=tags or [])
    )
    return {"created": name, "size": len(kg_ids)}


def corpus_delete(name: str, *, ctx: Context) -> dict[str, Any]:
    """
    Delete a corpus; its KGs stay registered.

    :param name: Corpus name or UUID.
    """
    if not kg_from(ctx).kgrag.corpus_registry.delete(name):
        raise ValueError(f"no corpus named {name!r}")
    return {"deleted": name}


def corpus_add(corpus: str, kg: str, *, ctx: Context) -> dict[str, Any]:
    """
    Add a registered KG to a corpus.

    :param corpus: Corpus name or UUID.
    :param kg: KG name or UUID.
    """
    fed = kg_from(ctx)
    updated = fed.kgrag.corpus_registry.add_kg(corpus, _kg_id(fed, kg))
    if updated is None:
        raise ValueError(f"no corpus named {corpus!r}")
    return {"corpus": corpus, "added": kg, "size": updated.size}


def corpus_remove(corpus: str, kg: str, *, ctx: Context) -> dict[str, Any]:
    """
    Remove a KG from a corpus.

    :param corpus: Corpus name or UUID.
    :param kg: KG name or UUID.
    """
    fed = kg_from(ctx)
    updated = fed.kgrag.corpus_registry.remove_kg(corpus, _kg_id(fed, kg))
    if updated is None:
        raise ValueError(f"no corpus named {corpus!r}")
    return {"corpus": corpus, "removed": kg, "size": updated.size}


def corpus_query(corpus: str, q: str, k: int = 8, *, ctx: Context) -> dict[str, Any]:
    """
    Federated semantic search within one corpus.

    :param corpus: Corpus name or UUID.
    :param q: Natural-language query.
    :param k: Hits per KG (default 8).
    """
    try:
        result = kg_from(ctx).kgrag.query_corpus(corpus, q, k=k)
    except KeyError as exc:
        raise ValueError(str(exc).strip("'\"")) from None
    return {
        "query": result.query,
        "corpus": corpus,
        "total_hits": result.total_hits,
        "kgs_queried": result.kgs_queried,
        "hits": _hits(result),
    }


def corpus_pack(corpus: str, q: str, k: int = 8, context: int = 5, *, ctx: Context) -> str:
    """
    Federated snippet pack within one corpus, as Markdown.

    :param corpus: Corpus name or UUID.
    :param q: Natural-language query.
    :param k: Snippets per KG (default 8).
    :param context: Lines of context around code snippets (default 5).
    """
    try:
        return kg_from(ctx).kgrag.pack_corpus(corpus, q, k=k, context=context).render()
    except KeyError as exc:
        raise ValueError(str(exc).strip("'\"")) from None


# ---------------------------------------------------------------------------
# Person corpora
# ---------------------------------------------------------------------------


def person_list(*, ctx: Context) -> dict[str, Any]:
    """
    Every person corpus (the KGs relevant to one individual) in the registry.
    """
    reg = kg_from(ctx).kgrag.person_registry
    stats = reg.stats()
    return {
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
            for e in reg.list()
        ],
    }


def person_info(name: str, *, ctx: Context) -> dict[str, Any]:
    """
    One person corpus in detail: personal metadata and member KGs.

    :param name: Person name or UUID.
    """
    fed = kg_from(ctx)
    entry = fed.kgrag.person_registry.get(name)
    if entry is None:
        raise ValueError(f"no person named {name!r}")
    return {
        "id": entry.id,
        "name": entry.name,
        "birth_year": entry.birth_year,
        "birth_date": entry.birth_date,
        "address": entry.address,
        "email": entry.email,
        "phone": entry.phone,
        "notes": entry.notes,
        "size": entry.size,
        "kgs": _member_kgs(fed, entry.kg_ids),
        "tags": entry.tags,
        "metadata": entry.metadata,
        "created_at": entry.created_at.isoformat(),
        "updated_at": entry.updated_at.isoformat(),
    }


def person_create(
    name: str,
    kg_names: list[str] | None = None,
    birth_year: int | None = None,
    birth_date: str | None = None,
    address: str = "",
    email: str = "",
    phone: str = "",
    notes: str = "",
    tags: list[str] | None = None,
    *,
    ctx: Context,
) -> dict[str, Any]:
    """
    Create a person corpus grouping the KGs relevant to one individual.

    :param name: The person's full name.
    :param kg_names: KG names or UUIDs to include.
    :param birth_year: Year of birth.
    :param birth_date: Date of birth, YYYY-MM-DD.
    :param address: Mailing or home address.
    :param email: Primary email address.
    :param phone: Primary phone number.
    :param notes: Free-form notes.
    :param tags: Tags for grouping.
    """
    fed = kg_from(ctx)
    kg_ids = _resolve_kgs(fed, kg_names or [])
    fed.kgrag.person_registry.create(
        PersonCorpusEntry(
            name=name,
            kg_ids=kg_ids,
            birth_year=birth_year,
            birth_date=birth_date,
            address=address,
            email=email,
            phone=phone,
            notes=notes,
            tags=tags or [],
        )
    )
    return {"created": name, "size": len(kg_ids)}


def person_delete(name: str, *, ctx: Context) -> dict[str, Any]:
    """
    Delete a person corpus; its KGs stay registered.

    :param name: Person name or UUID.
    """
    if not kg_from(ctx).kgrag.person_registry.delete(name):
        raise ValueError(f"no person named {name!r}")
    return {"deleted": name}


def person_add(person: str, kg: str, *, ctx: Context) -> dict[str, Any]:
    """
    Add a registered KG to a person corpus.

    :param person: Person name or UUID.
    :param kg: KG name or UUID.
    """
    fed = kg_from(ctx)
    updated = fed.kgrag.person_registry.add_kg(person, _kg_id(fed, kg))
    if updated is None:
        raise ValueError(f"no person named {person!r}")
    return {"person": person, "added": kg, "size": updated.size}


def person_remove(person: str, kg: str, *, ctx: Context) -> dict[str, Any]:
    """
    Remove a KG from a person corpus.

    :param person: Person name or UUID.
    :param kg: KG name or UUID.
    """
    fed = kg_from(ctx)
    updated = fed.kgrag.person_registry.remove_kg(person, _kg_id(fed, kg))
    if updated is None:
        raise ValueError(f"no person named {person!r}")
    return {"person": person, "removed": kg, "size": updated.size}


def person_update(
    name: str,
    birth_year: int | None = None,
    birth_date: str | None = None,
    address: str | None = None,
    email: str | None = None,
    phone: str | None = None,
    notes: str | None = None,
    *,
    ctx: Context,
) -> dict[str, Any]:
    """
    Update a person corpus's personal metadata; omitted fields are left alone.

    :param name: Person name or UUID.
    :param birth_year: Year of birth.
    :param birth_date: Date of birth, YYYY-MM-DD.
    :param address: Mailing or home address.
    :param email: Primary email address.
    :param phone: Primary phone number.
    :param notes: Free-form notes.
    """
    fields = {
        k: v
        for k, v in {
            "birth_year": birth_year,
            "birth_date": birth_date,
            "address": address,
            "email": email,
            "phone": phone,
            "notes": notes,
        }.items()
        if v is not None
    }
    if kg_from(ctx).kgrag.person_registry.update(name, **fields) is None:
        raise ValueError(f"no person named {name!r}")
    return {"updated": name, "fields": list(fields)}


def person_query(person: str, q: str, k: int = 8, *, ctx: Context) -> dict[str, Any]:
    """
    Federated semantic search within one person corpus.

    :param person: Person name or UUID.
    :param q: Natural-language query.
    :param k: Hits per KG (default 8).
    """
    try:
        result = kg_from(ctx).kgrag.query_person(person, q, k=k)
    except KeyError as exc:
        raise ValueError(str(exc).strip("'\"")) from None
    return {
        "query": result.query,
        "person": person,
        "total_hits": result.total_hits,
        "kgs_queried": result.kgs_queried,
        "hits": _hits(result),
    }


def person_pack(person: str, q: str, k: int = 8, context: int = 5, *, ctx: Context) -> str:
    """
    Federated snippet pack within one person corpus, as Markdown.

    :param person: Person name or UUID.
    :param q: Natural-language query.
    :param k: Snippets per KG (default 8).
    :param context: Lines of context around code snippets (default 5).
    """
    try:
        return kg_from(ctx).kgrag.pack_person(person, q, k=k, context=context).render()
    except KeyError as exc:
        raise ValueError(str(exc).strip("'\"")) from None


EXTRA_TOOLS = (
    list_kgs,
    kg_info,
    corpus_list,
    corpus_info,
    corpus_create,
    corpus_delete,
    corpus_add,
    corpus_remove,
    corpus_query,
    corpus_pack,
    person_list,
    person_info,
    person_create,
    person_delete,
    person_add,
    person_remove,
    person_update,
    person_query,
    person_pack,
)


def build_server(registry_path: Path | None = None, project_root: Path | None = None) -> KGServer:
    """Build the KGRAG MCP server, without opening the registry.

    :param registry_path: Registry file; ``None`` for ``KGRAG_REGISTRY`` or
        ``~/.kgrag/registry.sqlite``.
    :param project_root: Where ``[tool.kgrag]`` (embedder) config is read.
    :return: The server; serve it with :func:`kg_utils.mcp.run`.
    """
    server = make_server(
        lambda: Federation(registry_path, project_root),
        name="kgrag",
        kind="kgrag",
        version=__version__,
        instructions=PREAMBLE,
    )
    server.canonical("query")(query)
    server.canonical("pack")(pack)
    for tool in EXTRA_TOOLS:
        server.tool()(tool)
    return server


def main(argv: list[str] | None = None) -> None:
    """Entry point for ``kgrag-mcp``: the same command as ``kgrag mcp``.

    :param argv: Arguments; ``None`` for ``sys.argv[1:]``.
    """
    from kg_rag.cli.cmd_mcp import mcp_command  # pylint: disable=import-outside-toplevel

    mcp_command.main(args=argv, prog_name="kgrag-mcp")


if __name__ == "__main__":
    main()
