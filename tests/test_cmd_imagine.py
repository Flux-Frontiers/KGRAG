"""
test_cmd_imagine.py

Tests for the kgrag imagine command.

The registry, corpora, KGRAG orchestrator, retrieval, imagewright's backend
resolution and client, and kg_utils' rewrite and worker client are all real.
Only true external boundaries are faked: the KG adapters (a real one needs a
built KG in its own venv), the image model (a real HTTP server on an
ephemeral port speaking the image contract), the text model behind
``rewrite_for_image`` (the OpenAI client), the LAN worker (a real HTTP server
answering ``/runsync``), in-process FLUX, and the desktop viewer.
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
from click.testing import CliRunner, Result
from kg_utils.synthesis import IMAGE_REWRITE_SYSTEM, IMAGE_REWRITE_TECHNICAL_SYSTEM
from PIL import Image

from kg_rag.cli.main import cli
from kg_rag.corpus_registry import CorpusRegistry
from kg_rag.primitives import CorpusEntry, CrossSnippet, KGEntry, KGKind
from kg_rag.registry import KGRegistry

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
_SECRET = "worker-test-token"  # pragma: allowlist secret


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


@pytest.fixture(autouse=True)
def hermetic(monkeypatch: pytest.MonkeyPatch, tmp_path: Path) -> list[str]:
    """Keep every test off real models, the developer's shell and the desktop.

    Clears the image, text and worker env vars, points discovery at closed
    ports (a real FLUX server may be on localhost:8090), makes mflux and mlx
    unimportable, runs in ``tmp_path`` and records ``click.launch``.

    :return: The paths ``click.launch`` was called with.
    """
    for name in _ENV_VARS:
        monkeypatch.delenv(name, raising=False)
    monkeypatch.setattr(
        imagewright.discovery, "DEFAULT_IMAGE_ENDPOINTS", (_closed_port_url(), _closed_port_url())
    )
    for name in ("mflux", "mlx", "mlx.core"):
        monkeypatch.setitem(sys.modules, name, None)
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
    """A server answering ``/health``, ``/v1/models`` and ``POST /v1/images/generations``."""
    state = _Server()
    png = _png_b64()

    def answer(path: str, body: dict[str, Any]) -> tuple[int, dict[str, Any]]:
        if path != "/v1/images/generations":
            return 404, {"detail": "Not Found"}
        if state.status != 200:
            return state.status, {"detail": "render failed"}
        return 200, {"created": 0, "data": [{"b64_json": png}]}

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


def _messages(create: MagicMock) -> tuple[str, str]:
    """Return the (system, user) contents of the one text-model call."""
    create.assert_called_once()
    messages = create.call_args.kwargs["messages"]
    return messages[0]["content"], messages[1]["content"]


def _invoke(*args: str) -> Result:
    return CliRunner().invoke(cli, ["imagine", *args])


# ---------------------------------------------------------------------------
# PROMPT alone
# ---------------------------------------------------------------------------


def test_prompt_only_renders_as_given(image_server, text_model, hermetic, tmp_path):
    out = tmp_path / "lighthouse.png"
    result = _invoke(
        "a lighthouse",
        "--endpoint",
        image_server.url,
        "--size",
        "768x512",
        "--seed",
        "7",
        "--steps",
        "2",
        "-o",
        str(out),
        "--no-open",
    )
    assert result.exit_code == 0, result.output
    [post] = image_server.posts
    assert post["prompt"] == "a lighthouse"
    assert (post["size"], post["seed"], post["num_inference_steps"]) == ("768x512", 7, 2)
    assert Image.open(out).size == (4, 4)
    assert f"Saved {out}" in result.stdout
    text_model.assert_not_called()
    assert hermetic == []


def test_default_output_name_and_open(image_server, hermetic, tmp_path, monkeypatch):
    monkeypatch.setenv("IMAGE_ENDPOINT", image_server.url)
    result = _invoke("a lighthouse")
    assert result.exit_code == 0, result.output
    [png] = list(tmp_path.glob("imagine_*.png"))
    assert png.name[len("imagine_") : -len(".png")].replace("_", "").isdigit()
    assert hermetic == [png.name]


# ---------------------------------------------------------------------------
# --query: retrieval and rewrite
# ---------------------------------------------------------------------------


def test_query_prose_top_hit_uses_historical_prompt(reg_path, image_server, text_model):
    result = _invoke(
        "--query", "fire", "--registry", str(reg_path), "--endpoint", image_server.url, "--no-open"
    )
    assert result.exit_code == 0, result.output
    system, user = _messages(text_model)
    assert system == IMAGE_REWRITE_SYSTEM
    assert user.startswith("fire from doc-b #0")
    assert image_server.posts[0]["prompt"] == _REWRITTEN


def test_query_code_top_hit_uses_technical_prompt(reg_path, image_server, text_model):
    result = _invoke(
        "--query",
        "fire",
        "--kind",
        "code",
        "--registry",
        str(reg_path),
        "--endpoint",
        image_server.url,
        "--no-open",
    )
    assert result.exit_code == 0, result.output
    system, user = _messages(text_model)
    assert system == IMAGE_REWRITE_TECHNICAL_SYSTEM
    assert "doc-b" not in user and "fire from code-a #0" in user


def test_corpus_scopes_retrieval(reg_path, image_server, text_model):
    result = _invoke(
        "--query",
        "fire",
        "--corpus",
        "code-only",
        "--registry",
        str(reg_path),
        "--endpoint",
        image_server.url,
        "--no-open",
    )
    assert result.exit_code == 0, result.output
    system, user = _messages(text_model)
    assert system == IMAGE_REWRITE_TECHNICAL_SYSTEM
    assert "doc-b" not in user and "code-a" in user


def test_prompt_with_query_becomes_scene_notes(reg_path, image_server, text_model):
    result = _invoke(
        "woodcut",
        "--query",
        "fire",
        "--registry",
        str(reg_path),
        "--endpoint",
        image_server.url,
        "--no-open",
    )
    assert result.exit_code == 0, result.output
    _, user = _messages(text_model)
    assert user.endswith("\n\nAdditional style/scene notes: woodcut")


def test_rewrite_failure_falls_back_to_passages(reg_path, image_server, text_model):
    text_model.side_effect = RuntimeError("model offline")
    result = _invoke(
        "--query", "fire", "--registry", str(reg_path), "--endpoint", image_server.url, "--no-open"
    )
    assert result.exit_code == 0, result.output
    assert "Warning: rewrite failed" in result.stderr
    assert image_server.posts[0]["prompt"].startswith("fire from doc-b #0")


def test_no_rewrite_sends_passages(reg_path, image_server, text_model):
    result = _invoke(
        "--query",
        "fire",
        "--no-rewrite",
        "--registry",
        str(reg_path),
        "--endpoint",
        image_server.url,
        "--no-open",
    )
    assert result.exit_code == 0, result.output
    text_model.assert_not_called()
    prompt = image_server.posts[0]["prompt"]
    assert prompt.startswith("fire from doc-b #0") and "fire from code-a #0" in prompt


def test_context_only_prints_and_does_not_render(reg_path, text_model, tmp_path):
    # No image backend is available here, and none is needed.
    result = _invoke("--query", "fire", "--registry", str(reg_path), "--context-only")
    assert result.exit_code == 0, result.output
    assert "fire from doc-b #0" in result.stdout
    assert f"Rewritten prompt:\n{_REWRITTEN}" in result.stdout
    assert list(tmp_path.glob("*.png")) == []


def test_context_only_no_rewrite_skips_text_model(reg_path, text_model):
    result = _invoke(
        "--query", "fire", "--registry", str(reg_path), "--context-only", "--no-rewrite"
    )
    assert result.exit_code == 0, result.output
    assert "fire from doc-b #0" in result.stdout
    text_model.assert_not_called()


def test_unknown_corpus_is_clean_error(reg_path, image_server):
    result = _invoke(
        "--query",
        "fire",
        "--corpus",
        "nope",
        "--registry",
        str(reg_path),
        "--endpoint",
        image_server.url,
    )
    assert result.exit_code == 1
    assert "Corpus not found: 'nope'" in result.output


def test_no_passages_is_clean_error(reg_path, image_server):
    result = _invoke(
        "--query",
        "fire",
        "--kind",
        "memory",
        "--registry",
        str(reg_path),
        "--endpoint",
        image_server.url,
    )
    assert result.exit_code == 1
    assert "No passages found for 'fire'" in result.output
    assert image_server.posts == []


# ---------------------------------------------------------------------------
# Backends and their errors
# ---------------------------------------------------------------------------


def test_nothing_available_prints_the_fixes(reg_path, text_model):
    result = _invoke("--query", "fire", "--registry", str(reg_path))
    assert result.exit_code == 1
    assert "No image backend is available" in result.output
    assert "IMAGE_ENDPOINT" in result.output
    assert 'pip install "imagewright[flux]"' in result.output
    text_model.assert_not_called()


def test_discovered_server_is_used(image_server, monkeypatch, tmp_path):
    monkeypatch.setattr(
        imagewright.discovery, "DEFAULT_IMAGE_ENDPOINTS", (_closed_port_url(), image_server.url)
    )
    result = _invoke("a lighthouse", "--no-open")
    assert result.exit_code == 0, result.output
    assert image_server.posts[0]["prompt"] == "a lighthouse"


def _install_module(monkeypatch: pytest.MonkeyPatch, dotted: str) -> ModuleType:
    """Put a fake module and each of its parent packages into ``sys.modules``."""
    parts = dotted.split(".")
    for i in range(1, len(parts) + 1):
        name = ".".join(parts[:i])
        module = ModuleType(name)
        module.__spec__ = ModuleSpec(name, None)
        monkeypatch.setitem(sys.modules, name, module)
    return module


def test_in_process_flux_warns_on_stderr(monkeypatch, tmp_path):
    prompts: list[str] = []

    class Flux2Klein:
        def __init__(self, model_path: str) -> None:
            pass

        def generate_image(self, **kwargs: Any) -> SimpleNamespace:
            prompts.append(kwargs["prompt"])
            return SimpleNamespace(image=Image.new("RGB", (kwargs["width"], kwargs["height"])))

    klein = _install_module(monkeypatch, "mflux.models.flux2.variants.txt2img.flux2_klein")
    klein.Flux2Klein = Flux2Klein  # type: ignore[attr-defined]
    result = _invoke("a lighthouse", "--size", "8x6", "-o", "out.png", "--no-open")
    assert result.exit_code == 0, result.output
    assert "No image server found; loading FLUX in process" in result.stderr
    assert prompts == ["a lighthouse"]
    assert Image.open(tmp_path / "out.png").size == (8, 6)


def test_server_http_error_is_clean(image_server):
    image_server.status = 500
    result = _invoke("a lighthouse", "--endpoint", image_server.url, "--no-open")
    assert result.exit_code == 1
    assert "Image generation failed" in result.output and "500" in result.output
    assert isinstance(result.exception, SystemExit)


def test_missing_backend_extra_names_the_install(monkeypatch):
    monkeypatch.setitem(sys.modules, "openai", None)
    result = _invoke("a lighthouse", "--backend", "openai", "--no-open")
    assert result.exit_code == 1
    assert 'pip install "imagewright[openai]"' in result.output


def test_bad_image_backend_env_is_clean(monkeypatch):
    monkeypatch.setenv("IMAGE_BACKEND", "dalle")
    result = _invoke("a lighthouse", "--no-open")
    assert result.exit_code == 1
    assert "unknown image backend 'dalle'" in result.output


def test_imagewright_missing_names_the_extra(monkeypatch):
    monkeypatch.setitem(sys.modules, "imagewright", None)
    result = _invoke("a lighthouse")
    assert result.exit_code == 1
    assert result.output.strip() == (
        'Error: kgrag imagine needs the imagine extra: pip install "kg-rag[imagine]"'
    )


# ---------------------------------------------------------------------------
# --worker
# ---------------------------------------------------------------------------


def test_worker_rewrites_and_renders(reg_path, worker, text_model, monkeypatch, tmp_path):
    monkeypatch.setenv("HANDLER_SECRET", _SECRET)
    result = _invoke(
        "--query",
        "fire",
        "--kind",
        "code",
        "--registry",
        str(reg_path),
        "--worker",
        worker.url,
        "--size",
        "768x512",
        "-o",
        "w.png",
        "--no-open",
    )
    assert result.exit_code == 0, result.output
    rewrite, render = (post["input"] for post in worker.posts)
    assert rewrite["op"] == "rewrite" and rewrite["secret"] == _SECRET
    assert rewrite["system"] == IMAGE_REWRITE_TECHNICAL_SYSTEM
    assert rewrite["text"].startswith("fire from code-a #0")
    assert render["op"] == "imagine" and render["prompt"] == _REWRITTEN
    assert render["size"] == "768x512" and render["secret"] == _SECRET
    assert Image.open(tmp_path / "w.png").size == (4, 4)
    text_model.assert_not_called()


def test_worker_prose_hit_sends_no_system(reg_path, worker):
    result = _invoke(
        "--query", "fire", "--registry", str(reg_path), "--worker", worker.url, "--no-open"
    )
    assert result.exit_code == 0, result.output
    assert "system" not in worker.posts[0]["input"]


def test_worker_seed_is_warned_and_ignored(worker):
    result = _invoke("a lighthouse", "--worker", worker.url, "--seed", "3", "--no-open")
    assert result.exit_code == 0, result.output
    assert "--seed is ignored with --worker" in result.stderr
    assert "seed" not in worker.posts[0]["input"]


def test_worker_error_is_clean(worker):
    worker.status = 500
    result = _invoke("a lighthouse", "--worker", worker.url, "--no-open")
    assert result.exit_code == 1
    assert "failed: GPU busy" in result.output


# ---------------------------------------------------------------------------
# Usage errors
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("args", "message"),
    [
        ((), "Provide a PROMPT argument or --query."),
        (("x", "--worker", "http://w", "--backend", "openai"), "--worker cannot be combined"),
        (("x", "--worker", "http://w", "--endpoint", "http://e"), "--worker cannot be combined"),
        (("x", "--context-only"), "--context-only and --no-rewrite need --query."),
        (("x", "--no-rewrite"), "--context-only and --no-rewrite need --query."),
        (("x", "--size", "big"), "expected WIDTHxHEIGHT"),
    ],
)
def test_usage_errors(args, message):
    result = _invoke(*args)
    assert result.exit_code == 2
    assert message in result.output
