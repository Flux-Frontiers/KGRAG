"""
conftest.py

Shared fixtures for the KGRAG test suite.
"""

from __future__ import annotations

import base64
import json
import socket
import sys
import threading
from collections.abc import Iterator
from dataclasses import dataclass, field
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from importlib.machinery import ModuleSpec
from io import BytesIO
from pathlib import Path
from types import ModuleType, SimpleNamespace
from typing import Any
from unittest.mock import MagicMock, patch

import click
import imagewright.discovery
import pytest
from PIL import Image

import kg_rag.imagine
from kg_rag.corpus_registry import CorpusRegistry
from kg_rag.primitives import CorpusEntry, CrossSnippet, KGEntry, KGKind
from kg_rag.registry import KGRegistry


@pytest.fixture(autouse=True)
def no_embedder_downloads():
    """Keep the unit suite off the HuggingFace Hub.

    :class:`~kg_rag.orchestrator.KGRAG` resolves its shared embedder on the
    first adapter that needs one, and this repo configures
    ``embed_backend = "sentence_transformers"``, so that resolution would
    download ~130 MB on any machine (and every CI run) with a cold model
    cache. Every test that gets that far mocks its adapters, so ``None`` --
    the documented "let each KG use its own default embedder" answer -- is
    the faithful stand-in. Tests that assert on resolution itself patch this
    same target inside the test, which takes precedence.
    """
    with patch("kg_rag.orchestrator.make_embedder", return_value=None):
        yield


@pytest.fixture
def tmp_registry(tmp_path: Path) -> KGRegistry:
    """Isolated in-memory registry backed by a temp SQLite file."""
    reg = KGRegistry(db_path=tmp_path / "test_registry.sqlite")
    yield reg
    reg.close()


@pytest.fixture
def sample_entry(tmp_path: Path) -> KGEntry:
    """A minimal KGEntry pointing at real (temp) paths."""
    repo = tmp_path / "myrepo"
    repo.mkdir()
    venv = repo / ".venv"
    venv.mkdir()
    return KGEntry(
        name="my-code",
        kind=KGKind.CODE,
        repo_path=repo,
        venv_path=venv,
    )


@pytest.fixture
def built_entry(tmp_path: Path) -> KGEntry:
    """A KGEntry whose sqlite_path actually exists (is_built=True)."""
    repo = tmp_path / "builtrepo"
    repo.mkdir()
    venv = repo / ".venv"
    venv.mkdir()
    db_dir = repo / ".pycodekg"
    db_dir.mkdir()
    sqlite = db_dir / "graph.sqlite"
    sqlite.touch()
    return KGEntry(
        name="built-code",
        kind=KGKind.CODE,
        repo_path=repo,
        venv_path=venv,
        sqlite_path=sqlite,
    )


# ---------------------------------------------------------------------------
# Image generation: kgrag imagine (test_cmd_imagine.py) and the kg_imagine
# MCP tool (test_mcp_imagine.py). The registry, retrieval, imagewright and
# kg_utils are real; the image model, the text model and the LAN worker are
# faked at their wire boundaries.
# ---------------------------------------------------------------------------

_ENV_VARS = (
    "IMAGE_BACKEND",
    "IMAGE_ENDPOINT",
    "IMAGE_MODEL",
    "IMAGE_API_KEY",
    "IMAGE_STEPS",
    "GUTENKG_IMAGE_ENDPOINT",
    "GUTENKG_IMAGE_MODEL",
    "OPENAI_API_KEY",
    "SYNTH_BACKEND",
    "SYNTH_ENDPOINT",
    "SYNTH_API_KEY",
    "SYNTH_MODEL",
    "VLLM_ENDPOINT_URL",
    "VLLM_API_KEY",
    "VLLM_MODEL",
    "ANTHROPIC_API_KEY",
    "HANDLER_SECRET",
    "KGRAG_REGISTRY",
)

_SCORES = {"code-a": 0.5, "doc-b": 0.9}
_REWRITTEN = "A candlelit study, oil painting."


def _closed_port_url() -> str:
    """Return an http URL on a localhost port that nothing listens on."""
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        port = s.getsockname()[1]
    return f"http://127.0.0.1:{port}"


def _png_b64() -> str:
    buf = BytesIO()
    Image.new("RGB", (4, 4), color=(100, 150, 200)).save(buf, format="PNG")
    return base64.b64encode(buf.getvalue()).decode()


@pytest.fixture
def imagine_hermetic(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> list[str]:
    """Keep an image test off real models, the developer's shell and the desktop.

    Clears the image, text and worker env vars, points discovery at closed
    ports (a real FLUX server may be on localhost:8090), makes mflux and mlx
    unimportable, drops the synthesizer :mod:`kg_rag.imagine` keeps, runs in
    ``tmp_path`` and records ``click.launch``. Not autouse: each image test
    file turns it on for its own tests.

    :return: The paths ``click.launch`` was called with.
    """
    for name in _ENV_VARS:
        monkeypatch.delenv(name, raising=False)
    monkeypatch.setattr(
        imagewright.discovery, "DEFAULT_IMAGE_ENDPOINTS", (_closed_port_url(), _closed_port_url())
    )
    for name in ("mflux", "mlx", "mlx.core"):
        monkeypatch.setitem(sys.modules, name, None)
    monkeypatch.setattr(kg_rag.imagine, "_kept", None)
    monkeypatch.chdir(tmp_path)
    launched: list[str] = []
    monkeypatch.setattr(click, "launch", lambda url, **_: launched.append(url))
    return launched


# ---------------------------------------------------------------------------
# A registry with a code KG and a doc KG
# ---------------------------------------------------------------------------


class _FakeAdapter:
    """Stands in for a built KG: two snippets per pack, scored by KG."""

    def __init__(self, entry: KGEntry, embedder: object = None) -> None:
        self.entry = entry

    def is_available(self) -> bool:
        return True

    def pack(self, q: str, k: int = 8, context: int = 5, **_: object) -> list[CrossSnippet]:
        return [
            CrossSnippet(
                kg_name=self.entry.name,
                kg_kind=self.entry.kind,
                node_id=f"{self.entry.name}-{i}",
                source_path=f"{self.entry.name}/{i}.txt",
                content=f"{q} from {self.entry.name} #{i}",
                score=round(_SCORES[self.entry.name] - i * 0.01, 4),
            )
            for i in range(2)
        ]


@pytest.fixture
def reg_path(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    """A registry with code-a and doc-b, and a corpus holding only code-a."""
    monkeypatch.setattr("kg_rag.adapters.make_adapter", _FakeAdapter)
    monkeypatch.setattr("kg_rag.orchestrator.make_adapter", _FakeAdapter)
    db = tmp_path / "registry.sqlite"
    ids = {}
    with KGRegistry(db_path=db) as reg:
        for name, kind in {"code-a": KGKind.CODE, "doc-b": KGKind.DOC}.items():
            repo = tmp_path / name
            (repo / ".venv").mkdir(parents=True)
            sqlite = repo / "graph.sqlite"
            sqlite.touch()
            entry = KGEntry(
                name=name, kind=kind, repo_path=repo, venv_path=repo / ".venv", sqlite_path=sqlite
            )
            ids[name] = reg.register(entry).id
    with CorpusRegistry(db_path=db) as creg:
        creg.create(CorpusEntry(name="code-only", kg_ids=[ids["code-a"]]))
    return db


# ---------------------------------------------------------------------------
# Real HTTP servers: the image contract and a LAN worker
# ---------------------------------------------------------------------------


@dataclass
class _Server:
    url: str = ""
    status: int = 200
    png: str = ""
    posts: list[dict[str, Any]] = field(default_factory=list)


def _serve(handler: type[BaseHTTPRequestHandler]) -> Iterator[str]:
    server = ThreadingHTTPServer(("127.0.0.1", 0), handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield f"http://127.0.0.1:{server.server_address[1]}"
    finally:
        server.shutdown()
        server.server_close()


def _handler(state: _Server, answer_post: Any) -> type[BaseHTTPRequestHandler]:
    class Handler(BaseHTTPRequestHandler):
        def _reply(self, status: int, body: dict[str, Any]) -> None:
            data = json.dumps(body).encode()
            self.send_response(status)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)

        def do_GET(self) -> None:
            if self.path == "/health":
                self._reply(200, {"status": "ok", "backend": "flux", "loaded": False})
            elif self.path == "/v1/models":
                self._reply(200, {"data": [{"id": "flux2-klein-4b"}]})
            else:
                self._reply(404, {"detail": "Not Found"})

        def do_POST(self) -> None:
            body = json.loads(self.rfile.read(int(self.headers.get("Content-Length", "0"))))
            state.posts.append({"path": self.path, **body})
            self._reply(*answer_post(self.path, body))

        def log_message(self, format: str, *args: Any) -> None:
            pass

    return Handler


@pytest.fixture
def image_server() -> Iterator[_Server]:
    """A server answering ``/health``, ``/v1/models`` and ``POST /v1/images/generations``.

    It returns ``png`` (base64), by default a 4x4 image.
    """
    state = _Server(png=_png_b64())

    def answer(path: str, body: dict[str, Any]) -> tuple[int, dict[str, Any]]:
        if path != "/v1/images/generations":
            return 404, {"detail": "Not Found"}
        if state.status != 200:
            return state.status, {"detail": "render failed"}
        return 200, {"created": 0, "data": [{"b64_json": state.png}]}

    for url in _serve(_handler(state, answer)):
        state.url = url
        yield state


@pytest.fixture
def worker() -> Iterator[_Server]:
    """A LAN worker answering ``POST /runsync`` for ``op: rewrite`` and ``op: imagine``."""
    state = _Server()
    png = _png_b64()

    def answer(path: str, body: dict[str, Any]) -> tuple[int, dict[str, Any]]:
        op = body["input"]["op"]
        if op == "rewrite":
            return 200, {"output": {"prompt": _REWRITTEN}}
        if state.status != 200:
            return 200, {"output": {"error": "GPU busy"}}
        return 200, {"output": {"image_b64": png, "image_model": "flux", "image_backend": "x"}}

    for url in _serve(_handler(state, answer)):
        state.url = url
        yield state


@pytest.fixture
def text_model() -> Iterator[MagicMock]:
    """Patch the OpenAI client behind ``rewrite_for_image``; it answers ``_REWRITTEN``."""
    with patch("openai.OpenAI") as mock_cls:
        create = mock_cls.return_value.chat.completions.create
        create.return_value = SimpleNamespace(
            choices=[SimpleNamespace(message=SimpleNamespace(content=_REWRITTEN))]
        )
        yield create


def _install_module(monkeypatch: pytest.MonkeyPatch, dotted: str) -> ModuleType:
    """Put a fake module and each of its parent packages into ``sys.modules``."""
    parts = dotted.split(".")
    for i in range(1, len(parts) + 1):
        name = ".".join(parts[:i])
        module = ModuleType(name)
        module.__spec__ = ModuleSpec(name, None)
        monkeypatch.setitem(sys.modules, name, module)
    return module
