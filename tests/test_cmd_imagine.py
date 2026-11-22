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

import sys
from types import SimpleNamespace
from typing import Any
from unittest.mock import MagicMock

import imagewright.discovery
import pytest
from click.testing import CliRunner, Result
from conftest import _REWRITTEN, _closed_port_url, _install_module
from kg_utils.synthesis import IMAGE_REWRITE_SYSTEM, IMAGE_REWRITE_TECHNICAL_SYSTEM
from PIL import Image

from kg_rag.cli.main import cli
from kg_rag.corpus_registry import CorpusRegistry
from kg_rag.primitives import CorpusEntry

_SECRET = "worker-test-token"  # pragma: allowlist secret


@pytest.fixture(autouse=True)
def hermetic(imagine_hermetic: list[str]) -> list[str]:
    """Run every test here hermetically; see ``imagine_hermetic`` in conftest.

    :return: The paths ``click.launch`` was called with.
    """
    return imagine_hermetic


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


def test_empty_corpus_is_an_error(reg_path, image_server, tmp_path):
    with CorpusRegistry(db_path=reg_path) as creg:
        creg.create(CorpusEntry(name="empty", kg_ids=[]))
    result = _invoke(
        "--query",
        "fire",
        "--corpus",
        "empty",
        "--registry",
        str(reg_path),
        "--endpoint",
        image_server.url,
    )
    assert result.exit_code == 1
    assert "No passages found for 'fire'" in result.output
    assert image_server.posts == [] and list(tmp_path.glob("*.png")) == []


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


def test_install_errors_name_the_kg_rag_extras():
    nothing = _invoke("a lighthouse", "--no-open")
    no_flux = _invoke("a lighthouse", "--backend", "mflux-local", "--no-open")
    assert 'pip install "imagewright[flux]"' in no_flux.output
    for result in (nothing, no_flux):
        assert result.exit_code == 1
        assert 'pip install "kg-rag[imagine-local]"' in result.output


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
