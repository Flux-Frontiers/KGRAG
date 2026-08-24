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

The tool-handler tests below invoke the registered ``CallToolRequest`` handler
directly (never a live stdio/socket transport), which round-trips arguments
through the real ``inputSchema`` validation exactly as a live MCP client would.
Registry-backed tools (kgrag_list/info, corpus_*, person_*) run against a real
``KGRegistry``/``CorpusRegistry``/``PersonCorpusRegistry`` on a temp SQLite
file — that's cheap and exercises the real read/write paths. The federated
query/pack tools (kgrag_query, kgrag_corpus_query, kgrag_person_query, and
their *_pack siblings) mock ``kg_rag.mcp_server.KGRAG`` itself, since a real
federation run requires installed adapter libraries and a built vector index;
the mock returns real ``CrossQueryResult``/``CrossSnippetPack`` dataclasses so
the response-shaping code in mcp_server.py still runs for real.
"""

from __future__ import annotations

import asyncio
import importlib
import json
from contextlib import asynccontextmanager
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from mcp.types import CallToolRequest, CallToolRequestParams

from kg_rag.corpus_registry import CorpusRegistry
from kg_rag.person_registry import PersonCorpusRegistry
from kg_rag.primitives import (
    CorpusEntry,
    CrossHit,
    CrossQueryResult,
    CrossSnippet,
    CrossSnippetPack,
    KGEntry,
    KGKind,
    PersonCorpusEntry,
)
from kg_rag.registry import KGRegistry


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


# ---------------------------------------------------------------------------
# call_tool() handler tests
# ---------------------------------------------------------------------------


@pytest.fixture
def registry_path(tmp_path: Path) -> Path:
    return tmp_path / "registry.sqlite"


@pytest.fixture
def server(registry_path: Path):
    mcp_server = importlib.import_module("kg_rag.mcp_server")
    return mcp_server._make_server(registry_path)


def call_tool(server, name: str, arguments: dict | None = None):
    """Invoke the registered CallToolRequest handler directly.

    Round-trips through the same jsonschema ``inputSchema`` validation a live
    MCP client would hit, then returns the raw ``CallToolResult``.
    """
    handler = server.request_handlers[CallToolRequest]
    req = CallToolRequest(params=CallToolRequestParams(name=name, arguments=arguments or {}))
    return asyncio.run(handler(req)).root


def call_tool_json(server, name: str, arguments: dict | None = None):
    """Like :func:`call_tool` but parses the single TextContent as JSON."""
    result = call_tool(server, name, arguments)
    assert not result.isError, result.content[0].text
    return json.loads(result.content[0].text)


def register_kg(registry_path: Path, entry: KGEntry) -> KGEntry:
    """Register a KGEntry directly against the server's registry file."""
    with KGRegistry(db_path=registry_path) as reg:
        return reg.register(entry)


def create_corpus(registry_path: Path, entry: CorpusEntry) -> CorpusEntry:
    with CorpusRegistry(db_path=registry_path) as reg:
        return reg.create(entry)


def create_person(registry_path: Path, entry: PersonCorpusEntry) -> PersonCorpusEntry:
    with PersonCorpusRegistry(db_path=registry_path) as reg:
        return reg.create(entry)


# ------ kgrag_stats ------


def test_kgrag_stats_empty_registry(server, registry_path):
    data = call_tool_json(server, "kgrag_stats")
    assert data["total"] == 0
    assert data["by_kind"] == {}
    assert data["built"] == 0
    assert data["registry_path"] == str(registry_path)


def test_kgrag_stats_with_entries(server, registry_path, sample_entry):
    register_kg(registry_path, sample_entry)
    data = call_tool_json(server, "kgrag_stats")
    assert data["total"] == 1
    assert data["by_kind"] == {"code": 1}


# ------ kgrag_list ------


def test_kgrag_list_empty(server):
    data = call_tool_json(server, "kgrag_list")
    assert data == []


def test_kgrag_list_no_filter_returns_entry(server, registry_path, sample_entry):
    register_kg(registry_path, sample_entry)
    data = call_tool_json(server, "kgrag_list")
    assert len(data) == 1
    assert data[0]["name"] == "my-code"
    assert data[0]["kind"] == "code"
    assert data[0]["built"] is False


def test_kgrag_list_kind_filter_matches(server, registry_path, sample_entry):
    register_kg(registry_path, sample_entry)
    data = call_tool_json(server, "kgrag_list", {"kind": "code"})
    assert len(data) == 1


def test_kgrag_list_kind_filter_excludes(server, registry_path, sample_entry):
    register_kg(registry_path, sample_entry)
    data = call_tool_json(server, "kgrag_list", {"kind": "doc"})
    assert data == []


# ------ kgrag_info ------


def test_kgrag_info_not_found(server):
    data = call_tool_json(server, "kgrag_info", {"name": "nope"})
    assert data["error"] == "Not found: nope"


def test_kgrag_info_found(server, registry_path, sample_entry):
    entry = register_kg(registry_path, sample_entry)
    data = call_tool_json(server, "kgrag_info", {"name": "my-code"})
    assert data["id"] == entry.id
    assert data["name"] == "my-code"
    assert data["kind"] == "code"
    assert data["sqlite_path"] is None


# ------ kgrag_query / kgrag_pack (mocked KGRAG) ------


def _fake_hit(kg_name="my-code") -> CrossHit:
    return CrossHit(
        kg_name=kg_name,
        kg_kind=KGKind.CODE,
        node_id="n1",
        name="do_thing",
        kind="function",
        score=0.87654,
        summary="Does the thing.",
        source_path="src/thing.py",
    )


def test_kgrag_query_empty_registry(server):
    """No KGs registered: federation runs but finds nothing to query."""
    data = call_tool_json(server, "kgrag_query", {"q": "hello"})
    assert data["query"] == "hello"
    assert data["total_hits"] == 0
    assert data["kgs_queried"] == 0
    assert data["hits"] == []


def test_kgrag_query_with_hits(server):
    hit = _fake_hit()
    fake_result = CrossQueryResult(
        query="hello", hits=[hit], by_kg={"my-code": [hit]}, total_hits=1, kgs_queried=1
    )
    fake_kgrag = MagicMock()
    fake_kgrag.__enter__.return_value = fake_kgrag
    fake_kgrag.__exit__.return_value = False
    fake_kgrag.query.return_value = fake_result
    with patch("kg_rag.mcp_server.KGRAG", return_value=fake_kgrag):
        data = call_tool_json(server, "kgrag_query", {"q": "hello", "k": 3})
    assert data["total_hits"] == 1
    assert data["hits"][0]["kg"] == "my-code"
    assert data["hits"][0]["kind"] == "code"
    assert data["hits"][0]["node_kind"] == "function"
    assert data["hits"][0]["score"] == 0.8765  # rounded to 4 places
    fake_kgrag.query.assert_called_once()
    _, kwargs = fake_kgrag.query.call_args
    assert kwargs["k"] == 3


def test_kgrag_query_with_kinds_filter(server):
    fake_result = CrossQueryResult(query="q", hits=[], by_kg={}, total_hits=0, kgs_queried=0)
    fake_kgrag = MagicMock()
    fake_kgrag.__enter__.return_value = fake_kgrag
    fake_kgrag.__exit__.return_value = False
    fake_kgrag.query.return_value = fake_result
    with patch("kg_rag.mcp_server.KGRAG", return_value=fake_kgrag):
        call_tool_json(server, "kgrag_query", {"q": "q", "kinds": ["code", "doc"]})
    _, kwargs = fake_kgrag.query.call_args
    assert kwargs["kinds"] == [KGKind.CODE, KGKind.DOC]


def test_kgrag_pack_empty_registry(server):
    result = call_tool(server, "kgrag_pack", {"q": "hello"})
    assert not result.isError
    assert "Cross-KG Pack" in result.content[0].text


def test_kgrag_pack_with_snippets(server):
    snippet = CrossSnippet(
        kg_name="my-code",
        kg_kind=KGKind.CODE,
        node_id="n1",
        source_path="src/thing.py",
        content="def do_thing():\n    return 42\n    # padding to pass the 30-char filter\n",
        score=0.5,
        lineno=1,
        end_lineno=3,
    )
    fake_pack = CrossSnippetPack(
        query="hello", snippets=[snippet], total_tokens_approx=10, kgs_queried=1
    )
    fake_kgrag = MagicMock()
    fake_kgrag.__enter__.return_value = fake_kgrag
    fake_kgrag.__exit__.return_value = False
    fake_kgrag.pack.return_value = fake_pack
    with patch("kg_rag.mcp_server.KGRAG", return_value=fake_kgrag):
        result = call_tool(server, "kgrag_pack", {"q": "hello", "context": 2})
    assert "src/thing.py:1-3" in result.content[0].text
    _, kwargs = fake_kgrag.pack.call_args
    assert kwargs["context"] == 2


# ------ kgrag_corpus_* ------


def test_kgrag_corpus_list_empty(server):
    data = call_tool_json(server, "kgrag_corpus_list")
    assert data["total"] == 0
    assert data["corpora"] == []


def test_kgrag_corpus_list_with_entry(server, registry_path):
    create_corpus(registry_path, CorpusEntry(name="my-corpus", kg_ids=["a", "b"]))
    data = call_tool_json(server, "kgrag_corpus_list")
    assert data["total"] == 1
    assert data["total_kg_refs"] == 2
    assert data["corpora"][0]["name"] == "my-corpus"


def test_kgrag_corpus_info_not_found(server):
    data = call_tool_json(server, "kgrag_corpus_info", {"name": "nope"})
    assert data["error"] == "Corpus not found: nope"


def test_kgrag_corpus_info_found_with_missing_and_present_kg(server, registry_path, sample_entry):
    kg = register_kg(registry_path, sample_entry)
    create_corpus(registry_path, CorpusEntry(name="c1", kg_ids=[kg.id, "ghost-id"]))
    data = call_tool_json(server, "kgrag_corpus_info", {"name": "c1"})
    assert data["name"] == "c1"
    assert len(data["kgs"]) == 2
    present = next(k for k in data["kgs"] if k["id"] == kg.id)
    assert present["name"] == "my-code"
    ghost = next(k for k in data["kgs"] if k["id"] == "ghost-id")
    assert ghost["name"] is None
    assert ghost["built"] is False


def test_kgrag_corpus_create_success(server, registry_path, sample_entry):
    kg = register_kg(registry_path, sample_entry)
    data = call_tool_json(server, "kgrag_corpus_create", {"name": "c1", "kg_names": [kg.id]})
    assert data == {"created": "c1", "size": 1}


def test_kgrag_corpus_create_missing_kg(server):
    data = call_tool_json(server, "kgrag_corpus_create", {"name": "c1", "kg_names": ["ghost"]})
    assert data["error"] == "KGs not found: ['ghost']"


def test_kgrag_corpus_delete_success(server, registry_path):
    create_corpus(registry_path, CorpusEntry(name="c1"))
    data = call_tool_json(server, "kgrag_corpus_delete", {"name": "c1"})
    assert data == {"deleted": "c1"}


def test_kgrag_corpus_delete_not_found(server):
    data = call_tool_json(server, "kgrag_corpus_delete", {"name": "nope"})
    assert data["error"] == "Corpus not found: nope"


def test_kgrag_corpus_add_kg_not_found(server, registry_path):
    create_corpus(registry_path, CorpusEntry(name="c1"))
    data = call_tool_json(server, "kgrag_corpus_add", {"corpus": "c1", "kg": "ghost"})
    assert data["error"] == "KG not found: ghost"


def test_kgrag_corpus_add_corpus_not_found(server, registry_path, sample_entry):
    kg = register_kg(registry_path, sample_entry)
    data = call_tool_json(server, "kgrag_corpus_add", {"corpus": "nope", "kg": kg.id})
    assert data["error"] == "Corpus not found: nope"


def test_kgrag_corpus_add_success(server, registry_path, sample_entry):
    kg = register_kg(registry_path, sample_entry)
    create_corpus(registry_path, CorpusEntry(name="c1"))
    data = call_tool_json(server, "kgrag_corpus_add", {"corpus": "c1", "kg": kg.id})
    assert data == {"corpus": "c1", "added": kg.id, "size": 1}


def test_kgrag_corpus_remove_kg_not_found(server, registry_path):
    create_corpus(registry_path, CorpusEntry(name="c1"))
    data = call_tool_json(server, "kgrag_corpus_remove", {"corpus": "c1", "kg": "ghost"})
    assert data["error"] == "KG not found: ghost"


def test_kgrag_corpus_remove_corpus_not_found(server, registry_path, sample_entry):
    kg = register_kg(registry_path, sample_entry)
    data = call_tool_json(server, "kgrag_corpus_remove", {"corpus": "nope", "kg": kg.id})
    assert data["error"] == "Corpus not found: nope"


def test_kgrag_corpus_remove_success(server, registry_path, sample_entry):
    kg = register_kg(registry_path, sample_entry)
    create_corpus(registry_path, CorpusEntry(name="c1", kg_ids=[kg.id]))
    data = call_tool_json(server, "kgrag_corpus_remove", {"corpus": "c1", "kg": kg.id})
    assert data == {"corpus": "c1", "removed": kg.id, "size": 0}


def test_kgrag_corpus_query_not_found(server):
    fake_kgrag = MagicMock()
    fake_kgrag.__enter__.return_value = fake_kgrag
    fake_kgrag.__exit__.return_value = False
    fake_kgrag.query_corpus.side_effect = KeyError("Corpus 'nope' not found.")
    with patch("kg_rag.mcp_server.KGRAG", return_value=fake_kgrag):
        data = call_tool_json(server, "kgrag_corpus_query", {"corpus": "nope", "q": "hi"})
    assert "not found" in data["error"]


def test_kgrag_corpus_query_success(server):
    hit = _fake_hit()
    fake_result = CrossQueryResult(
        query="hi", hits=[hit], by_kg={"my-code": [hit]}, total_hits=1, kgs_queried=1
    )
    fake_kgrag = MagicMock()
    fake_kgrag.__enter__.return_value = fake_kgrag
    fake_kgrag.__exit__.return_value = False
    fake_kgrag.query_corpus.return_value = fake_result
    with patch("kg_rag.mcp_server.KGRAG", return_value=fake_kgrag):
        data = call_tool_json(server, "kgrag_corpus_query", {"corpus": "c1", "q": "hi"})
    assert data["corpus"] == "c1"
    assert data["total_hits"] == 1
    assert data["hits"][0]["name"] == "do_thing"


def test_kgrag_corpus_pack_not_found(server):
    fake_kgrag = MagicMock()
    fake_kgrag.__enter__.return_value = fake_kgrag
    fake_kgrag.__exit__.return_value = False
    fake_kgrag.pack_corpus.side_effect = KeyError("Corpus 'nope' not found.")
    with patch("kg_rag.mcp_server.KGRAG", return_value=fake_kgrag):
        data = call_tool_json(server, "kgrag_corpus_pack", {"corpus": "nope", "q": "hi"})
    assert "not found" in data["error"]


def test_kgrag_corpus_pack_success(server):
    snippet = CrossSnippet(
        kg_name="my-code",
        kg_kind=KGKind.CODE,
        node_id="n1",
        source_path="src/thing.py",
        content="def do_thing():\n    return 42\n    # padding to pass the 30-char filter\n",
        score=0.5,
    )
    fake_pack = CrossSnippetPack(
        query="hi", snippets=[snippet], total_tokens_approx=5, kgs_queried=1
    )
    fake_kgrag = MagicMock()
    fake_kgrag.__enter__.return_value = fake_kgrag
    fake_kgrag.__exit__.return_value = False
    fake_kgrag.pack_corpus.return_value = fake_pack
    with patch("kg_rag.mcp_server.KGRAG", return_value=fake_kgrag):
        result = call_tool(server, "kgrag_corpus_pack", {"corpus": "c1", "q": "hi"})
    assert "src/thing.py" in result.content[0].text


# ------ kgrag_person_* ------


def test_kgrag_person_list_empty(server):
    data = call_tool_json(server, "kgrag_person_list")
    assert data["total"] == 0
    assert data["persons"] == []


def test_kgrag_person_list_with_entry(server, registry_path):
    create_person(
        registry_path, PersonCorpusEntry(name="Ada", kg_ids=["a"], email="ada@example.com")
    )
    data = call_tool_json(server, "kgrag_person_list")
    assert data["total"] == 1
    assert data["persons"][0]["name"] == "Ada"
    assert data["persons"][0]["email"] == "ada@example.com"


def test_kgrag_person_info_not_found(server):
    data = call_tool_json(server, "kgrag_person_info", {"name": "nope"})
    assert data["error"] == "Person not found: nope"


def test_kgrag_person_info_found(server, registry_path, sample_entry):
    kg = register_kg(registry_path, sample_entry)
    create_person(registry_path, PersonCorpusEntry(name="Ada", kg_ids=[kg.id, "ghost"]))
    data = call_tool_json(server, "kgrag_person_info", {"name": "Ada"})
    assert data["name"] == "Ada"
    present = next(k for k in data["kgs"] if k["id"] == kg.id)
    assert present["name"] == "my-code"
    ghost = next(k for k in data["kgs"] if k["id"] == "ghost")
    assert ghost["name"] is None


def test_kgrag_person_create_success(server, registry_path, sample_entry):
    kg = register_kg(registry_path, sample_entry)
    data = call_tool_json(
        server, "kgrag_person_create", {"name": "Ada", "kg_names": [kg.id], "birth_year": 1815}
    )
    assert data == {"created": "Ada", "size": 1}


def test_kgrag_person_create_missing_kg(server):
    data = call_tool_json(server, "kgrag_person_create", {"name": "Ada", "kg_names": ["ghost"]})
    assert data["error"] == "KGs not found: ['ghost']"


def test_kgrag_person_delete_success(server, registry_path):
    create_person(registry_path, PersonCorpusEntry(name="Ada"))
    data = call_tool_json(server, "kgrag_person_delete", {"name": "Ada"})
    assert data == {"deleted": "Ada"}


def test_kgrag_person_delete_not_found(server):
    data = call_tool_json(server, "kgrag_person_delete", {"name": "nope"})
    assert data["error"] == "Person not found: nope"


def test_kgrag_person_add_kg_not_found(server, registry_path):
    create_person(registry_path, PersonCorpusEntry(name="Ada"))
    data = call_tool_json(server, "kgrag_person_add", {"person": "Ada", "kg": "ghost"})
    assert data["error"] == "KG not found: ghost"


def test_kgrag_person_add_person_not_found(server, registry_path, sample_entry):
    kg = register_kg(registry_path, sample_entry)
    data = call_tool_json(server, "kgrag_person_add", {"person": "nope", "kg": kg.id})
    assert data["error"] == "Person not found: nope"


def test_kgrag_person_add_success(server, registry_path, sample_entry):
    kg = register_kg(registry_path, sample_entry)
    create_person(registry_path, PersonCorpusEntry(name="Ada"))
    data = call_tool_json(server, "kgrag_person_add", {"person": "Ada", "kg": kg.id})
    assert data == {"person": "Ada", "added": kg.id, "size": 1}


def test_kgrag_person_remove_kg_not_found(server, registry_path):
    create_person(registry_path, PersonCorpusEntry(name="Ada"))
    data = call_tool_json(server, "kgrag_person_remove", {"person": "Ada", "kg": "ghost"})
    assert data["error"] == "KG not found: ghost"


def test_kgrag_person_remove_person_not_found(server, registry_path, sample_entry):
    kg = register_kg(registry_path, sample_entry)
    data = call_tool_json(server, "kgrag_person_remove", {"person": "nope", "kg": kg.id})
    assert data["error"] == "Person not found: nope"


def test_kgrag_person_remove_success(server, registry_path, sample_entry):
    kg = register_kg(registry_path, sample_entry)
    create_person(registry_path, PersonCorpusEntry(name="Ada", kg_ids=[kg.id]))
    data = call_tool_json(server, "kgrag_person_remove", {"person": "Ada", "kg": kg.id})
    assert data == {"person": "Ada", "removed": kg.id, "size": 0}


def test_kgrag_person_update_not_found(server):
    data = call_tool_json(server, "kgrag_person_update", {"name": "nope", "email": "x@y.com"})
    assert data["error"] == "Person not found: nope"


def test_kgrag_person_update_success(server, registry_path):
    create_person(registry_path, PersonCorpusEntry(name="Ada"))
    data = call_tool_json(
        server, "kgrag_person_update", {"name": "Ada", "email": "ada@example.com"}
    )
    assert data["updated"] == "Ada"
    assert data["fields"] == ["email"]
    with PersonCorpusRegistry(db_path=registry_path) as reg:
        assert reg.get("Ada").email == "ada@example.com"


def test_kgrag_person_query_not_found(server):
    fake_kgrag = MagicMock()
    fake_kgrag.__enter__.return_value = fake_kgrag
    fake_kgrag.__exit__.return_value = False
    fake_kgrag.query_person.side_effect = KeyError("Person corpus 'nope' not found.")
    with patch("kg_rag.mcp_server.KGRAG", return_value=fake_kgrag):
        data = call_tool_json(server, "kgrag_person_query", {"person": "nope", "q": "hi"})
    assert "not found" in data["error"]


def test_kgrag_person_query_success(server):
    hit = _fake_hit()
    fake_result = CrossQueryResult(
        query="hi", hits=[hit], by_kg={"my-code": [hit]}, total_hits=1, kgs_queried=1
    )
    fake_kgrag = MagicMock()
    fake_kgrag.__enter__.return_value = fake_kgrag
    fake_kgrag.__exit__.return_value = False
    fake_kgrag.query_person.return_value = fake_result
    with patch("kg_rag.mcp_server.KGRAG", return_value=fake_kgrag):
        data = call_tool_json(server, "kgrag_person_query", {"person": "Ada", "q": "hi"})
    assert data["person"] == "Ada"
    assert data["total_hits"] == 1


def test_kgrag_person_pack_not_found(server):
    fake_kgrag = MagicMock()
    fake_kgrag.__enter__.return_value = fake_kgrag
    fake_kgrag.__exit__.return_value = False
    fake_kgrag.pack_person.side_effect = KeyError("Person corpus 'nope' not found.")
    with patch("kg_rag.mcp_server.KGRAG", return_value=fake_kgrag):
        data = call_tool_json(server, "kgrag_person_pack", {"person": "nope", "q": "hi"})
    assert "not found" in data["error"]


def test_kgrag_person_pack_success(server):
    snippet = CrossSnippet(
        kg_name="my-code",
        kg_kind=KGKind.CODE,
        node_id="n1",
        source_path="src/thing.py",
        content="def do_thing():\n    return 42\n    # padding to pass the 30-char filter\n",
        score=0.5,
    )
    fake_pack = CrossSnippetPack(
        query="hi", snippets=[snippet], total_tokens_approx=5, kgs_queried=1
    )
    fake_kgrag = MagicMock()
    fake_kgrag.__enter__.return_value = fake_kgrag
    fake_kgrag.__exit__.return_value = False
    fake_kgrag.pack_person.return_value = fake_pack
    with patch("kg_rag.mcp_server.KGRAG", return_value=fake_kgrag):
        result = call_tool(server, "kgrag_person_pack", {"person": "Ada", "q": "hi"})
    assert "src/thing.py" in result.content[0].text


# ------ unknown tool ------


def test_unknown_tool_name_bypasses_schema_validation(server):
    """An unrecognized tool name falls through to the final catch-all branch.

    ``call_tool()`` only validates against a *known* tool's inputSchema (see
    ``mcp.server.lowlevel.server.Server.call_tool``), so an unregistered name
    reaches the handler body directly and hits the ``Unknown tool`` branch at
    the end of the if/elif chain rather than being rejected by the framework.
    """
    result = call_tool(server, "totally_bogus_tool", {})
    assert not result.isError
    data = json.loads(result.content[0].text)
    assert data["error"] == "Unknown tool: totally_bogus_tool"


# ------ main() lifecycle ------


def test_main_runs_server_lifecycle(tmp_path: Path, monkeypatch):
    """main() must build the server and drive it through the stdio transport.

    The real ``stdio_server()`` blocks on stdin/stdout, so both it and
    ``Server.run`` (which loops reading requests until EOF) are replaced with
    lightweight stand-ins; ``asyncio.run`` itself runs for real so the
    ``async with`` / ``await`` lines in ``main()`` actually execute.
    """
    from mcp.server import Server

    import kg_rag.mcp_server as mcp_server

    @asynccontextmanager
    async def fake_stdio_server():
        yield (None, None)

    monkeypatch.setattr(mcp_server, "stdio_server", fake_stdio_server)
    monkeypatch.setattr(Server, "run", AsyncMock(return_value=None))

    mcp_server.main(registry_path=tmp_path / "registry.sqlite")
    Server.run.assert_awaited_once()
