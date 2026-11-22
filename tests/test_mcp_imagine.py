"""
test_mcp_imagine.py

Tests for the kg_imagine MCP tool.

The server, registry, corpora, federation, retrieval, imagewright's backend
resolution, client and MCP image helper, and kg_utils' rewrite are all real,
driven through an in-memory MCP client session. Only true external
boundaries are faked, with the fixtures in conftest: the KG adapters, the
image model (a real HTTP server on an ephemeral port), and the text model
behind ``rewrite_for_image`` (the OpenAI client).
"""

from __future__ import annotations

import base64
import os
import subprocess
import sys
from io import BytesIO
from pathlib import Path
from typing import Any

import anyio
import imagewright
import pytest
from conftest import _REWRITTEN
from kg_utils.synthesis import IMAGE_REWRITE_SYSTEM, IMAGE_REWRITE_TECHNICAL_SYSTEM
from mcp.shared.memory import create_connected_server_and_client_session
from PIL import Image

import kg_rag
from kg_rag.corpus_registry import CorpusRegistry
from kg_rag.mcp_server import build_server
from kg_rag.primitives import CorpusEntry

_SRC = str(Path(kg_rag.__file__).resolve().parents[1])


@pytest.fixture(autouse=True)
def hermetic(imagine_hermetic: list[str]) -> list[str]:
    """Run every test here hermetically; see ``imagine_hermetic`` in conftest."""
    return imagine_hermetic


def _call(registry: Path, args: dict[str, Any]) -> tuple[Any, list[str]]:
    """Call kg_imagine; return the result and the log messages the client received."""
    logs: list[str] = []

    async def log(params: Any) -> None:
        logs.append(f"{params.level}: {params.data}")

    async def main() -> Any:
        async with create_connected_server_and_client_session(
            build_server(registry), logging_callback=log
        ) as client:
            return await client.call_tool("kg_imagine", args)

    return anyio.run(main), logs


def _image(registry: Path, args: dict[str, Any]) -> tuple[Any, list[str]]:
    """Call kg_imagine, which must succeed; return the image content and the logs."""
    out, logs = _call(registry, args)
    assert not out.isError, out.content[0].text
    [content] = out.content
    assert content.type == "image"
    return content, logs


def _error(registry: Path, args: dict[str, Any]) -> str:
    out, _ = _call(registry, args)
    assert out.isError, out.content
    return out.content[0].text


def _messages(create: Any) -> tuple[str, str]:
    """Return the (system, user) contents of the one text-model call."""
    create.assert_called_once()
    messages = create.call_args.kwargs["messages"]
    return messages[0]["content"], messages[1]["content"]


def _png(content: Any) -> Image.Image:
    return Image.open(BytesIO(base64.b64decode(content.data)))


@pytest.fixture
def endpoint(image_server, monkeypatch: pytest.MonkeyPatch):
    """Point the tool at the contract image server through ``IMAGE_ENDPOINT``."""
    monkeypatch.setenv("IMAGE_ENDPOINT", image_server.url)
    return image_server


# ---------------------------------------------------------------------------
# Listing and the prompt alone
# ---------------------------------------------------------------------------


def test_listed_by_the_server(tmp_path):
    names = [t["name"] for t in build_server(tmp_path / "r.sqlite").tool_specs()]
    assert names[-1] == "kg_imagine"


def test_prompt_only_returns_the_image(tmp_path, endpoint, text_model):
    content, logs = _image(
        tmp_path / "r.sqlite",
        {"prompt": "a lighthouse", "size": "768x512", "seed": 7, "steps": 2},
    )
    assert content.mimeType == "image/png"
    assert _png(content).size == (4, 4)
    [post] = endpoint.posts
    assert post["prompt"] == "a lighthouse"
    assert (post["size"], post["seed"], post["num_inference_steps"]) == ("768x512", 7, 2)
    assert "info: Prompt: a lighthouse" in logs
    text_model.assert_not_called()


# ---------------------------------------------------------------------------
# A query: retrieval through the federation, then the rewrite
# ---------------------------------------------------------------------------


def test_query_prose_top_hit_uses_historical_prompt(reg_path, endpoint, text_model):
    _image(reg_path, {"query": "fire"})
    system, user = _messages(text_model)
    assert system == IMAGE_REWRITE_SYSTEM
    assert user.startswith("fire from doc-b #0")
    assert endpoint.posts[0]["prompt"] == _REWRITTEN


def test_query_code_kind_uses_technical_prompt(reg_path, endpoint, text_model):
    _image(reg_path, {"query": "fire", "kinds": ["code"], "prompt": "woodcut"})
    system, user = _messages(text_model)
    assert system == IMAGE_REWRITE_TECHNICAL_SYSTEM
    assert "doc-b" not in user and user.startswith("fire from code-a #0")
    assert user.endswith("\n\nAdditional style/scene notes: woodcut")


def test_corpus_scopes_retrieval(reg_path, endpoint, text_model):
    _image(reg_path, {"query": "fire", "corpus": "code-only", "k": 1})
    system, user = _messages(text_model)
    assert system == IMAGE_REWRITE_TECHNICAL_SYSTEM
    assert user == "fire from code-a #0"


def test_rewrite_failure_is_logged_and_falls_back(reg_path, endpoint, text_model):
    text_model.side_effect = RuntimeError("model offline")
    _, logs = _image(reg_path, {"query": "fire"})
    assert any(line.startswith("warning: rewrite failed") for line in logs)
    assert endpoint.posts[0]["prompt"].startswith("fire from doc-b #0")


def test_large_image_comes_back_under_the_limit(tmp_path, endpoint):
    noise = Image.frombytes("RGB", (1400, 1000), os.urandom(1400 * 1000 * 3))
    buf = BytesIO()
    noise.save(buf, format="PNG")
    assert buf.tell() > imagewright.MCP_IMAGE_MAX_BYTES
    endpoint.png = base64.b64encode(buf.getvalue()).decode()
    content, _ = _image(tmp_path / "r.sqlite", {"prompt": "static"})
    assert len(base64.b64decode(content.data)) <= imagewright.MCP_IMAGE_MAX_BYTES
    assert content.mimeType == "image/jpeg"


# ---------------------------------------------------------------------------
# Errors
# ---------------------------------------------------------------------------


def test_no_backend_lists_the_fixes(tmp_path):
    message = _error(tmp_path / "r.sqlite", {"prompt": "a lighthouse"})
    assert "No image backend is available" in message
    assert "IMAGE_ENDPOINT" in message
    assert 'pip install "kg-rag[imagine-local]"' in message


def test_missing_flux_names_both_installs(tmp_path, monkeypatch):
    monkeypatch.setenv("IMAGE_BACKEND", "mflux-local")
    message = _error(tmp_path / "r.sqlite", {"prompt": "a lighthouse"})
    assert 'pip install "imagewright[flux]"' in message
    assert 'pip install "kg-rag[imagine-local]"' in message


def test_without_the_extra_names_kg_rag_imagine(tmp_path, monkeypatch):
    monkeypatch.setitem(sys.modules, "imagewright", None)
    message = _error(tmp_path / "r.sqlite", {"prompt": "a lighthouse"})
    assert 'pip install "kg-rag[imagine]"' in message


def test_unknown_corpus(reg_path, endpoint):
    assert "Corpus 'nope' not found" in _error(reg_path, {"query": "fire", "corpus": "nope"})
    assert endpoint.posts == []


@pytest.mark.parametrize(
    "args",
    [
        {"query": "fire", "kinds": ["memory"]},
        {"query": "fire", "corpus": "empty"},
        {"query": "fire", "corpus": "code-only", "kinds": ["doc"]},
    ],
)
def test_no_passages(reg_path, endpoint, args):
    with CorpusRegistry(db_path=reg_path) as creg:
        creg.create(CorpusEntry(name="empty", kg_ids=[]))
    assert "No passages found for 'fire'" in _error(reg_path, args)
    assert endpoint.posts == []


@pytest.mark.parametrize(
    ("args", "message"),
    [
        ({}, "give a prompt, a query, or both"),
        ({"prompt": "  "}, "prompt is empty"),
        ({"prompt": "x" * 4001}, "prompt is longer than 4000 characters"),
        ({"query": "x" * 2001}, "q must be at most 2000 characters"),
        ({"prompt": "x", "corpus": "c"}, "corpus and kinds need a query"),
        ({"prompt": "x", "k": 0}, "k must be between 1 and 100"),
        ({"prompt": "x", "steps": 51}, "steps must be between 1 and 50"),
        ({"prompt": "x", "size": "big"}, "size 'big' is not WIDTHxHEIGHT"),
        ({"query": "fire", "kinds": ["nope"]}, "Unknown KG kind: 'nope'"),
    ],
)
def test_bad_arguments_are_rejected(reg_path, endpoint, args, message):
    assert message in _error(reg_path, args)
    assert endpoint.posts == []


# ---------------------------------------------------------------------------
# A core-only server
# ---------------------------------------------------------------------------


def test_server_does_not_import_imagewright():
    script = (
        "import sys\n"
        "from kg_rag.mcp_server import build_server\n"
        "names = [t['name'] for t in build_server().tool_specs()]\n"
        "print('kg_imagine' in names, 'imagewright' in sys.modules)\n"
    )
    out = subprocess.run(
        [sys.executable, "-c", script],
        check=True,
        capture_output=True,
        text=True,
        env={**os.environ, "PYTHONPATH": _SRC},
    ).stdout.strip()
    assert out == "True False"
