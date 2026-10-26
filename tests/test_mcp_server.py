"""
test_mcp_server.py

The KGRAG MCP server on the fleet's shared base, ``kg_utils.mcp``.

What step 5 of kgrag_priv's MCP centralization plan promises: off the
low-level ``Server``; the five canonical tools first, then the federation's
own, with the ``kgrag_`` prefix gone; ``stats`` in the fleet stats shape;
federated node ids that ``get_node`` and ``neighbors`` take straight from a
``query`` hit; ``--transport streamable-http`` instead of a ``--host`` /
``--port`` that did nothing; the manifest answering without a registry; and a
real stdio subprocess serving.

Registry tools run against a real temp registry. ``query``/``pack`` run
against a real doc KG built with a keyword embedder (no download), and the
corpus/person searches against a stubbed orchestrator.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock

import anyio
import pytest
from click.testing import CliRunner
from kg_utils.mcp import CANONICAL_TOOLS, manifest
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from mcp.shared.memory import create_connected_server_and_client_session

import kg_rag
from kg_rag.cli.main import cli
from kg_rag.corpus_registry import CorpusRegistry
from kg_rag.federation import SEP, join_id, split_id
from kg_rag.mcp_server import build_server
from kg_rag.person_registry import PersonCorpusRegistry
from kg_rag.primitives import (
    CorpusEntry,
    CrossHit,
    CrossQueryResult,
    CrossSnippet,
    CrossSnippetPack,
    KGKind,
    PersonCorpusEntry,
)
from kg_rag.registry import KGRegistry

_SRC = str(Path(kg_rag.__file__).resolve().parents[1])
_EXTRAS = [
    "list_kgs",
    "kg_info",
    "corpus_list",
    "corpus_info",
    "corpus_create",
    "corpus_delete",
    "corpus_add",
    "corpus_remove",
    "corpus_query",
    "corpus_pack",
    "person_list",
    "person_info",
    "person_create",
    "person_delete",
    "person_add",
    "person_remove",
    "person_update",
    "person_query",
    "person_pack",
]


@pytest.fixture
def registry_path(tmp_path: Path) -> Path:
    return tmp_path / "registry.sqlite"


def _session(server, fn):
    async def main():
        async with create_connected_server_and_client_session(server) as client:
            return await fn(client)

    return anyio.run(main)


def call(registry_path: Path, tool: str, args: dict | None = None) -> Any:
    return _session(build_server(registry_path), lambda c: c.call_tool(tool, args or {}))


def data(registry_path: Path, tool: str, args: dict | None = None) -> Any:
    """The structured result of a call that must succeed."""
    out = call(registry_path, tool, args)
    assert not out.isError, out.content[0].text
    sc = out.structuredContent
    return sc["result"] if set(sc) == {"result"} else sc


def error(registry_path: Path, tool: str, args: dict | None = None) -> str:
    out = call(registry_path, tool, args)
    assert out.isError, out.content
    return out.content[0].text


def register(registry_path: Path, entry):
    with KGRegistry(db_path=registry_path) as reg:
        return reg.register(entry)


# ---------------------------------------------------------------------------
# A real doc KG: graph built from a corpus with a deterministic keyword embedder
# ---------------------------------------------------------------------------


class _KeywordEmbedder:
    _words = ("whale", "rocket", "song", "fuel")
    dim = len(_words) + 1
    model_name = "keyword-test"

    def embed_texts(self, texts, encode_batch_size: int = 128):
        return [[float(w in t.lower()) for w in self._words] + [0.01] for t in texts]

    def embed_query(self, query: str):
        return self.embed_texts([query])[0]


@pytest.fixture
def doc_kg(tmp_path: Path, registry_path: Path, monkeypatch):
    """A built doc KG registered as ``notes``."""
    from doc_kg import DocKG

    from kg_rag.primitives import KGEntry

    monkeypatch.setattr("doc_kg.kg.make_embedder", lambda *_a, **_k: _KeywordEmbedder())
    repo = tmp_path / "notes"
    repo.mkdir()
    # Long enough to chunk: tiny files become a lone document node with no edges.
    whales = " ".join(["Humpback whales sing long songs across the cold sea."] * 12)
    rockets = " ".join(["Rockets burn fuel to climb past the clouds."] * 12)
    (repo / "whales.md").write_text(f"# Whales\n\n{whales}\n\n## Songs\n\n{whales}\n")
    (repo / "rockets.md").write_text(f"# Rockets\n\n{rockets}\n\n## Fuel\n\n{rockets}\n")
    kg = DocKG(
        repo,
        chunk_strategy="fixed",
        enable_topics=False,
        enable_entities=False,
        enable_keywords=False,
    )
    kg.build(wipe=True, discover_similar=False)
    kg.close()
    return register(
        registry_path,
        KGEntry(
            name="notes",
            kind=KGKind.DOC,
            repo_path=repo,
            venv_path=repo,
            sqlite_path=repo / ".dockg" / "graph.sqlite",
            vectors_path=repo / ".dockg" / "vectors.sqlite",
        ),
    )


# ---------------------------------------------------------------------------
# The tool surface
# ---------------------------------------------------------------------------


def test_canonical_tools_then_the_federation_tools(registry_path):
    names = [t["name"] for t in manifest(build_server(registry_path))["tools"]]
    assert names == [*CANONICAL_TOOLS, *_EXTRAS]
    assert not any(n.startswith("kgrag") for n in names)


def test_no_low_level_server():
    source = Path(_SRC, "kg_rag", "mcp_server.py").read_text(encoding="utf-8")
    assert "from mcp.server import Server" not in source and "call_tool()" not in source


def test_federated_ids_round_trip():
    assert split_id(join_id("notes", "chunk:a.md:0000")) == ("notes", "chunk:a.md:0000")
    for bad in ("chunk:a.md:0000", f"{SEP}x", f"kg{SEP}"):
        with pytest.raises(ValueError, match="node_id must be"):
            split_id(bad)


# ---------------------------------------------------------------------------
# stats: the fleet shape, across the federation
# ---------------------------------------------------------------------------


def test_stats_on_an_empty_registry(registry_path):
    s = data(registry_path, "stats")
    assert s["kind"] == "kgrag"
    assert s["nodes"] == {"total": 0, "by_kind": {}} and s["edges"] == {"total": 0, "by_rel": {}}
    assert s["registry"] == {
        "total": 0,
        "by_kind": {},
        "built": 0,
        "registry_path": str(registry_path),
    }


def test_stats_sums_each_kg_and_reports_the_unavailable(registry_path, doc_kg, sample_entry):
    register(registry_path, sample_entry)  # a code KG with nothing built
    s = data(registry_path, "stats")
    assert s["kgs"]["notes"]["available"] is True
    assert s["nodes"]["total"] == s["kgs"]["notes"]["nodes"] > 0
    assert s["nodes"]["by_kind"]["document"] == 2
    assert s["kgs"]["my-code"] == {"kind": "code", "available": False}
    assert s["registry"]["by_kind"] == {"code": 1, "doc": 1}


# ---------------------------------------------------------------------------
# query / pack / get_node / neighbors against a real doc KG
# ---------------------------------------------------------------------------


def test_query_hits_carry_federated_ids_that_get_node_and_neighbors_take(registry_path, doc_kg):
    found = data(registry_path, "query", {"q": "whale songs", "k": 3})
    top = found["hits"][0]
    assert (
        top["kg"] == "notes" and top["id"] == join_id("notes", top["node_id"]) and top["hop"] == 0
    )
    node = data(registry_path, "get_node", {"node_id": top["id"]})
    assert node["id"] == top["id"] and node["kg"] == "notes"
    near = data(registry_path, "neighbors", {"node_id": top["id"]})
    assert near["edges"] and all(top["id"] in (e["src"], e["dst"]) for e in near["edges"])
    assert all(n["id"].startswith(f"notes{SEP}") for n in near["nodes"])


def test_query_hop_brings_each_hits_neighbourhood(registry_path, doc_kg):
    seeds = data(registry_path, "query", {"q": "whale", "k": 1})["hits"]
    grown = data(registry_path, "query", {"q": "whale", "k": 1, "hop": 1})["hits"]
    assert grown[: len(seeds)] == seeds
    assert grown[len(seeds) :] and all(h["hop"] == 1 for h in grown[len(seeds) :])
    assert (
        len(data(registry_path, "query", {"q": "whale", "k": 1, "hop": 2, "max_nodes": 2})["hits"])
        == 2
    )


def test_pack_renders_and_hop_lists_the_neighbourhood(registry_path, doc_kg):
    plain = call(registry_path, "pack", {"q": "whale songs", "k": 2})
    assert not plain.isError and "Cross-KG Pack" in plain.content[0].text
    grown = call(registry_path, "pack", {"q": "whale songs", "k": 2, "hop": 1})
    assert "## Graph neighbourhood" in grown.content[0].text


def test_graph_tools_reject_unfederated_or_unknown_ids(registry_path, doc_kg):
    assert "node_id must be" in error(registry_path, "get_node", {"node_id": "chunk:x"})
    assert "no node with id" in error(registry_path, "get_node", {"node_id": "nokg::chunk:x"})
    assert "no node with id" in error(registry_path, "get_node", {"node_id": "notes::chunk:nope"})


def test_bad_kind_and_hop_are_tool_errors(registry_path):
    assert "Unknown KG kind" in error(registry_path, "query", {"q": "x", "kinds": ["bogus"]})
    assert "hop" in error(registry_path, "query", {"q": "x", "hop": 9})


# ---------------------------------------------------------------------------
# The registry tools
# ---------------------------------------------------------------------------


def test_list_kgs_and_kg_info(registry_path, sample_entry):
    assert data(registry_path, "list_kgs") == []
    register(registry_path, sample_entry)
    [row] = data(registry_path, "list_kgs")
    assert row["name"] == "my-code" and row["kind"] == "code" and "lancedb_path" not in row
    assert data(registry_path, "list_kgs", {"kind": "doc"}) == []
    info = data(registry_path, "kg_info", {"name": "my-code"})
    assert info["name"] == "my-code" and "created_at" in info
    assert "no KG named 'nope'" in error(registry_path, "kg_info", {"name": "nope"})


def test_corpus_lifecycle(registry_path, sample_entry):
    kg = register(registry_path, sample_entry)
    assert data(registry_path, "corpus_list")["total"] == 0
    assert data(registry_path, "corpus_create", {"name": "c1", "kg_names": ["my-code"]}) == {
        "created": "c1",
        "size": 1,
    }
    assert "KGs not found" in error(
        registry_path, "corpus_create", {"name": "c2", "kg_names": ["ghost"]}
    )
    info = data(registry_path, "corpus_info", {"name": "c1"})
    assert info["kgs"] == [{"id": kg.id, "name": "my-code", "kind": "code", "built": False}]
    assert data(registry_path, "corpus_remove", {"corpus": "c1", "kg": "my-code"})["size"] == 0
    assert data(registry_path, "corpus_add", {"corpus": "c1", "kg": "my-code"})["size"] == 1
    assert "no KG named" in error(registry_path, "corpus_add", {"corpus": "c1", "kg": "ghost"})
    assert "no corpus named" in error(
        registry_path, "corpus_add", {"corpus": "zz", "kg": "my-code"}
    )
    assert data(registry_path, "corpus_delete", {"name": "c1"}) == {"deleted": "c1"}
    assert "no corpus named" in error(registry_path, "corpus_delete", {"name": "c1"})
    assert "no corpus named" in error(registry_path, "corpus_info", {"name": "c1"})


def test_corpus_info_names_a_missing_member(registry_path):
    with CorpusRegistry(db_path=registry_path) as reg:
        reg.create(CorpusEntry(name="c1", kg_ids=["gone"]))
    assert data(registry_path, "corpus_info", {"name": "c1"})["kgs"] == [
        {"id": "gone", "name": None, "kind": None, "built": False}
    ]


def test_person_lifecycle(registry_path, sample_entry):
    register(registry_path, sample_entry)
    assert data(registry_path, "person_list")["total"] == 0
    assert data(
        registry_path, "person_create", {"name": "Ada", "kg_names": ["my-code"], "birth_year": 1815}
    ) == {"created": "Ada", "size": 1}
    assert "KGs not found" in error(
        registry_path, "person_create", {"name": "B", "kg_names": ["x"]}
    )
    assert data(registry_path, "person_info", {"name": "Ada"})["birth_year"] == 1815
    assert data(registry_path, "person_update", {"name": "Ada", "email": "a@b.c"}) == {
        "updated": "Ada",
        "fields": ["email"],
    }
    assert data(registry_path, "person_list")["persons"][0]["email"] == "a@b.c"
    assert data(registry_path, "person_remove", {"person": "Ada", "kg": "my-code"})["size"] == 0
    assert data(registry_path, "person_add", {"person": "Ada", "kg": "my-code"})["size"] == 1
    assert "no person named" in error(registry_path, "person_add", {"person": "Z", "kg": "my-code"})
    assert "no person named" in error(registry_path, "person_update", {"name": "Z"})
    assert data(registry_path, "person_delete", {"name": "Ada"}) == {"deleted": "Ada"}
    assert "no person named" in error(registry_path, "person_info", {"name": "Ada"})


# ---------------------------------------------------------------------------
# Corpus / person searches, against a stubbed orchestrator
# ---------------------------------------------------------------------------


def _hit() -> CrossHit:
    return CrossHit(
        kg_name="my-code",
        kg_kind=KGKind.CODE,
        node_id="n1",
        name="do_thing",
        kind="function",
        score=0.87654,
        summary="Does the thing.",
        source_path="src/thing.py",
    )


def _pack() -> CrossSnippetPack:
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
    return CrossSnippetPack(query="hi", snippets=[snippet], total_tokens_approx=5, kgs_queried=1)


@pytest.fixture
def stub_kgrag(monkeypatch):
    fake = MagicMock()
    fake._adapters = {}
    result = CrossQueryResult(query="hi", hits=[_hit()], by_kg={}, total_hits=1, kgs_queried=1)
    fake.query_corpus.return_value = fake.query_person.return_value = result
    fake.pack_corpus.return_value = fake.pack_person.return_value = _pack()
    monkeypatch.setattr("kg_rag.federation.KGRAG", lambda **_kw: fake)
    return fake


@pytest.mark.parametrize("scope", ["corpus", "person"])
def test_scoped_query_and_pack(registry_path, stub_kgrag, scope):
    found = data(registry_path, f"{scope}_query", {scope: "c1", "q": "hi", "k": 3})
    assert found[scope] == "c1" and found["total_hits"] == 1
    assert (
        found["hits"][0]["id"] == join_id("my-code", "n1") and found["hits"][0]["score"] == 0.8765
    )
    packed = call(registry_path, f"{scope}_pack", {scope: "c1", "q": "hi", "context": 2})
    assert "src/thing.py:1-3" in packed.content[0].text
    _, kwargs = getattr(stub_kgrag, f"pack_{scope}").call_args
    assert kwargs["context"] == 2


@pytest.mark.parametrize("scope", ["corpus", "person"])
def test_scoped_search_of_an_unknown_scope_is_a_tool_error(registry_path, stub_kgrag, scope):
    getattr(stub_kgrag, f"query_{scope}").side_effect = KeyError(f"{scope} 'nope' not found.")
    getattr(stub_kgrag, f"pack_{scope}").side_effect = KeyError(f"{scope} 'nope' not found.")
    assert "not found" in error(registry_path, f"{scope}_query", {scope: "nope", "q": "hi"})
    assert "not found" in error(registry_path, f"{scope}_pack", {scope: "nope", "q": "hi"})


def test_person_create_round_trips_metadata(registry_path):
    with PersonCorpusRegistry(db_path=registry_path) as reg:
        reg.create(PersonCorpusEntry(name="Ada", notes="first programmer"))
    assert data(registry_path, "person_info", {"name": "Ada"})["notes"] == "first programmer"


# ---------------------------------------------------------------------------
# The command
# ---------------------------------------------------------------------------


def test_manifest_answers_and_opens_no_registry(tmp_path):
    reg = tmp_path / "never.sqlite"
    result = CliRunner().invoke(cli, ["mcp", "--db", str(reg), "--manifest"])
    assert result.exit_code == 0, result.output
    assert json.loads(result.output)["canonical"] == list(CANONICAL_TOOLS)
    assert not reg.exists()


def test_standard_transport_flags(tmp_path):
    for flags in (["--transport", "sse"], ["--vectors", "x.sqlite"], ["--model", "m"]):
        result = CliRunner().invoke(cli, ["mcp", *flags, "--manifest"])
        assert result.exit_code == 2, (flags, result.output)


def test_old_registry_flag_is_mapped_to_db(tmp_path, monkeypatch):
    seen: list = []
    monkeypatch.setattr(
        "kg_rag.mcp_server.build_server",
        lambda reg, root: seen.append(reg) or build_server(reg, root),
    )
    result = CliRunner().invoke(
        cli, ["mcp", "--registry", str(tmp_path / "r.sqlite"), "--manifest"]
    )
    assert result.exit_code == 0, result.output
    assert seen == [tmp_path / "r.sqlite"]


def test_other_commands_do_not_import_mcp():
    out = subprocess.run(
        [sys.executable, "-c", "import sys, kg_rag.cli.main; print('mcp' in sys.modules)"],
        check=True,
        capture_output=True,
        text=True,
    ).stdout.strip()
    assert out == "False"


def test_stdio_subprocess_serves(registry_path, sample_entry, tmp_path):
    register(registry_path, sample_entry)
    params = StdioServerParameters(
        command=sys.executable,
        args=["-c", "from kg_rag.mcp_server import main; main()", "--db", str(registry_path)],
        env={**os.environ, "PYTHONPATH": _SRC},
    )

    async def run():
        with open(tmp_path / "stderr.log", "w", encoding="utf-8") as errlog:
            async with stdio_client(params, errlog=errlog) as (read, write):
                async with ClientSession(read, write) as client:
                    init = await client.initialize()
                    tools = await client.list_tools()
                    listed = await client.call_tool("list_kgs", {})
                    return init, tools, listed

    init, tools, listed = anyio.run(run)
    assert (init.serverInfo.name, init.serverInfo.version) == ("kgrag", kg_rag.__version__)
    assert [t.name for t in tools.tools] == [*CANONICAL_TOOLS, *_EXTRAS]
    assert listed.structuredContent["result"][0]["name"] == "my-code"
    err = (tmp_path / "stderr.log").read_text(encoding="utf-8")
    assert "kgrag MCP server starting (stdio)" in err and str(registry_path) in err


def test_the_documented_tool_reference_matches_the_manifest():
    """docs/MCP.md's tool reference is generated, never hand-kept (FLEET_STANDARDS)."""
    script = Path(_SRC).parent / "scripts" / "gen_mcp_reference.py"
    result = subprocess.run(
        [sys.executable, str(script), "--check"],
        capture_output=True,
        text=True,
        env={**os.environ, "PYTHONPATH": _SRC},
    )
    assert result.returncode == 0, result.stdout + result.stderr
