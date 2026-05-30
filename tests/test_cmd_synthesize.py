"""
test_cmd_synthesize.py

Tests for the kgrag synthesize command.

Covers:
  - _call_ollama: stream/non-stream success, HTTP error, ConnectError, URL construction
  - _call_openai_compat: stream/non-stream success, SSE parsing (blank lines,
    [DONE], malformed JSON), auth header, HTTP error, ConnectError, URL construction
  - synthesize CLI: backend routing, model defaults, option pass-through,
    env vars (OPENAI_API_KEY / OPENAI_BASE_URL), no-snippets path,
    --show-context, --no-stream, streaming default, --max-context truncation,
    invalid backend rejection
"""

from __future__ import annotations

import json
from unittest.mock import MagicMock, patch

import httpx
import pytest
from click.testing import CliRunner

from kg_rag.cli.cmd_synthesize import (
    _DEFAULT_MODEL,
    _DEFAULT_OPENAI_MODEL,
    _DEFAULT_OPENAI_URL,
    _call_ollama,
    _call_openai_compat,
)
from kg_rag.cli.main import cli
from kg_rag.primitives import CrossSnippet, CrossSnippetPack, KGKind

# ---------------------------------------------------------------------------
# Test helpers
# ---------------------------------------------------------------------------

_CONNECT_ERR = httpx.ConnectError("connection refused", request=None)


def _stream_ctx(status: int = 200, lines: list[str] | None = None) -> MagicMock:
    """Return a mock context manager for ``httpx.stream()``."""
    resp = MagicMock()
    resp.status_code = status
    resp.iter_lines.return_value = lines or []
    cm = MagicMock()
    cm.__enter__ = MagicMock(return_value=resp)
    cm.__exit__ = MagicMock(return_value=False)
    return cm


def _post_resp(status: int = 200, body: dict | None = None) -> MagicMock:
    """Return a mock for ``httpx.post()``."""
    resp = MagicMock()
    resp.status_code = status
    resp.json.return_value = body or {}
    return resp


def _make_snippets(n: int) -> list[CrossSnippet]:
    return [
        CrossSnippet(
            kg_name=f"kg-{i}",
            kg_kind=KGKind.CODE,
            node_id=f"node-{i}",
            source_path=f"src/file_{i}.py",
            content=f"Content for snippet {i}",
            score=round(0.9 - i * 0.05, 4),
        )
        for i in range(n)
    ]


def _pack_result(n: int = 2) -> CrossSnippetPack:
    return CrossSnippetPack(
        query="test",
        snippets=_make_snippets(n),
        total_tokens_approx=200,
        kgs_queried=max(n, 1),
    )


def _kg_mock(n: int = 2) -> MagicMock:
    """Return a mock KGRAG context manager with ``n`` snippets in pack result."""
    kg = MagicMock()
    kg.__enter__ = MagicMock(return_value=kg)
    kg.__exit__ = MagicMock(return_value=False)
    kg.pack.return_value = _pack_result(n)
    return kg


def _invoke(
    args: list[str],
    kg: MagicMock,
    ollama_ret: str = "Ollama answer.",
    openai_ret: str = "OpenAI answer.",
) -> tuple[object, MagicMock, MagicMock]:
    """Invoke ``kgrag synthesize`` with KGRAG and both call functions mocked.

    Returns (result, mock_call_ollama, mock_call_openai_compat).
    """
    with (
        patch("kg_rag.cli.cmd_synthesize.KGRAG", return_value=kg),
        patch("kg_rag.cli.cmd_synthesize._call_ollama", return_value=ollama_ret) as mock_ollama,
        patch(
            "kg_rag.cli.cmd_synthesize._call_openai_compat", return_value=openai_ret
        ) as mock_openai,
    ):
        result = CliRunner().invoke(cli, ["synthesize"] + args, catch_exceptions=False)
    return result, mock_ollama, mock_openai


# ---------------------------------------------------------------------------
# _call_ollama — unit tests
# ---------------------------------------------------------------------------


class TestCallOllama:
    def test_non_stream_returns_response_text(self):
        body = {"response": "Paris is the capital of France."}
        with patch("httpx.post", return_value=_post_resp(200, body)):
            result = _call_ollama("Q: capital?", "llama3", "http://localhost:11434", stream=False)
        assert result == "Paris is the capital of France."

    def test_non_stream_uses_api_generate_url(self):
        with patch("httpx.post", return_value=_post_resp(200, {"response": ""})) as mock_post:
            _call_ollama("Q", "llama3", "http://localhost:11434", stream=False)
        assert mock_post.call_args.args[0].endswith("/api/generate")

    def test_non_stream_http_error_raises_click_exception(self):
        with patch("httpx.post", return_value=_post_resp(503)):
            with pytest.raises(Exception, match="503"):
                _call_ollama("Q", "llama3", "http://localhost:11434", stream=False)

    def test_non_stream_connect_error_raises_click_exception(self):
        with patch("httpx.post", side_effect=_CONNECT_ERR):
            with pytest.raises(Exception, match="Cannot connect"):
                _call_ollama("Q", "llama3", "http://localhost:11434", stream=False)

    def test_stream_assembles_tokens(self):
        lines = [
            json.dumps({"response": "Hello", "done": False}),
            json.dumps({"response": " world", "done": False}),
            json.dumps({"response": "!", "done": True}),
        ]
        with patch("httpx.stream", return_value=_stream_ctx(200, lines)):
            result = _call_ollama("Q", "llama3", "http://localhost:11434", stream=True)
        assert result == "Hello world!"

    def test_stream_stops_at_done_true(self):
        lines = [
            json.dumps({"response": "stop here", "done": True}),
            json.dumps({"response": "never reached", "done": False}),
        ]
        with patch("httpx.stream", return_value=_stream_ctx(200, lines)):
            result = _call_ollama("Q", "llama3", "http://localhost:11434", stream=True)
        assert result == "stop here"

    def test_stream_skips_empty_lines(self):
        lines = [
            "",
            json.dumps({"response": "Hi", "done": False}),
            "",
            json.dumps({"response": "!", "done": True}),
        ]
        with patch("httpx.stream", return_value=_stream_ctx(200, lines)):
            result = _call_ollama("Q", "llama3", "http://localhost:11434", stream=True)
        assert result == "Hi!"

    def test_stream_http_error_raises_click_exception(self):
        with patch("httpx.stream", return_value=_stream_ctx(503)):
            with pytest.raises(Exception, match="503"):
                _call_ollama("Q", "llama3", "http://localhost:11434", stream=True)

    def test_stream_trailing_slash_stripped_from_url(self):
        with patch("httpx.post", return_value=_post_resp(200, {"response": ""})) as mock_post:
            _call_ollama("Q", "llama3", "http://localhost:11434/", stream=False)
        url = mock_post.call_args.args[0]
        assert not url.endswith("//api/generate")
        assert url.endswith("/api/generate")


# ---------------------------------------------------------------------------
# _call_openai_compat — unit tests
# ---------------------------------------------------------------------------


class TestCallOpenaiCompat:
    # ── non-streaming ────────────────────────────────────────────────────────

    def test_non_stream_returns_content(self):
        body = {"choices": [{"message": {"content": "OpenAI says hi."}}]}
        with patch("httpx.post", return_value=_post_resp(200, body)):
            result = _call_openai_compat("Q", "gpt-4", "http://host:8000/v1", stream=False)
        assert result == "OpenAI says hi."

    def test_non_stream_uses_chat_completions_url(self):
        body = {"choices": [{"message": {"content": ""}}]}
        with patch("httpx.post", return_value=_post_resp(200, body)) as mock_post:
            _call_openai_compat("Q", "model", "http://host:8000/v1", stream=False)
        assert mock_post.call_args.args[0].endswith("/chat/completions")

    def test_non_stream_api_key_sets_auth_header(self):
        body = {"choices": [{"message": {"content": ""}}]}
        with patch("httpx.post", return_value=_post_resp(200, body)) as mock_post:
            _call_openai_compat(
                "Q",
                "m",
                "http://host/v1",
                stream=False,
                api_key="tok123",  # pragma: allowlist secret
            )
        assert (
            mock_post.call_args.kwargs["headers"]["Authorization"] == "Bearer tok123"
        )  # pragma: allowlist secret

    def test_non_stream_no_api_key_omits_auth_header(self):
        body = {"choices": [{"message": {"content": ""}}]}
        with patch("httpx.post", return_value=_post_resp(200, body)) as mock_post:
            _call_openai_compat("Q", "m", "http://host/v1", stream=False)
        assert "Authorization" not in mock_post.call_args.kwargs["headers"]

    def test_non_stream_http_error_raises_click_exception(self):
        with patch("httpx.post", return_value=_post_resp(500)):
            with pytest.raises(Exception, match="500"):
                _call_openai_compat("Q", "m", "http://host/v1", stream=False)

    def test_non_stream_connect_error_raises_click_exception(self):
        with patch("httpx.post", side_effect=_CONNECT_ERR):
            with pytest.raises(Exception, match="Cannot connect"):
                _call_openai_compat("Q", "m", "http://host/v1", stream=False)

    # ── streaming ───────────────────────────────────────────────────────────

    def test_stream_assembles_tokens_from_sse(self):
        lines = [
            "data: " + json.dumps({"choices": [{"delta": {"content": "Tok1"}}]}),
            "data: " + json.dumps({"choices": [{"delta": {"content": " Tok2"}}]}),
            "data: [DONE]",
        ]
        with patch("httpx.stream", return_value=_stream_ctx(200, lines)):
            result = _call_openai_compat("Q", "m", "http://host/v1", stream=True)
        assert result == "Tok1 Tok2"

    def test_stream_skips_blank_lines(self):
        lines = [
            "",
            "data: " + json.dumps({"choices": [{"delta": {"content": "Hi"}}]}),
            "",
            "data: [DONE]",
        ]
        with patch("httpx.stream", return_value=_stream_ctx(200, lines)):
            result = _call_openai_compat("Q", "m", "http://host/v1", stream=True)
        assert result == "Hi"

    def test_stream_skips_done_sentinel(self):
        lines = [
            "data: " + json.dumps({"choices": [{"delta": {"content": "ok"}}]}),
            "data: [DONE]",
        ]
        with patch("httpx.stream", return_value=_stream_ctx(200, lines)):
            result = _call_openai_compat("Q", "m", "http://host/v1", stream=True)
        assert result == "ok"

    def test_stream_skips_malformed_json(self):
        lines = [
            "data: not-valid-json",
            "data: " + json.dumps({"choices": [{"delta": {"content": "valid"}}]}),
            "data: [DONE]",
        ]
        with patch("httpx.stream", return_value=_stream_ctx(200, lines)):
            result = _call_openai_compat("Q", "m", "http://host/v1", stream=True)
        assert result == "valid"

    def test_stream_handles_null_content_delta(self):
        lines = [
            "data: " + json.dumps({"choices": [{"delta": {}}]}),
            "data: " + json.dumps({"choices": [{"delta": {"content": "word"}}]}),
            "data: [DONE]",
        ]
        with patch("httpx.stream", return_value=_stream_ctx(200, lines)):
            result = _call_openai_compat("Q", "m", "http://host/v1", stream=True)
        assert result == "word"

    def test_stream_http_error_raises_click_exception(self):
        with patch("httpx.stream", return_value=_stream_ctx(401)):
            with pytest.raises(Exception, match="401"):
                _call_openai_compat("Q", "m", "http://host/v1", stream=True)

    def test_stream_connect_error_raises_click_exception(self):
        with patch("httpx.stream", side_effect=_CONNECT_ERR):
            with pytest.raises(Exception, match="Cannot connect"):
                _call_openai_compat("Q", "m", "http://host/v1", stream=True)

    def test_stream_api_key_sets_auth_header(self):
        lines = ["data: [DONE]"]
        with patch("httpx.stream", return_value=_stream_ctx(200, lines)) as mock_stream:
            _call_openai_compat(
                "Q",
                "m",
                "http://host/v1",
                stream=True,
                api_key="mykey",  # pragma: allowlist secret
            )
        assert (
            mock_stream.call_args.kwargs["headers"]["Authorization"] == "Bearer mykey"
        )  # pragma: allowlist secret

    def test_stream_trailing_slash_stripped_from_url(self):
        lines = ["data: [DONE]"]
        with patch("httpx.stream", return_value=_stream_ctx(200, lines)) as mock_stream:
            _call_openai_compat("Q", "m", "http://host/v1/", stream=True)
        url = mock_stream.call_args.args[1]
        assert url.endswith("/chat/completions")
        assert "//" not in url.split("://", 1)[1]


# ---------------------------------------------------------------------------
# synthesize CLI — integration tests (KGRAG + call functions mocked)
# ---------------------------------------------------------------------------


class TestSynthesizeCLI:
    # ── help text ────────────────────────────────────────────────────────────

    def test_help_shows_backend_option(self):
        r = CliRunner().invoke(cli, ["synthesize", "--help"])
        assert "--backend" in r.output

    def test_help_shows_openai_url_option(self):
        r = CliRunner().invoke(cli, ["synthesize", "--help"])
        assert "--openai-url" in r.output

    def test_help_shows_api_key_option(self):
        r = CliRunner().invoke(cli, ["synthesize", "--help"])
        assert "--api-key" in r.output

    def test_help_mentions_both_backends(self):
        r = CliRunner().invoke(cli, ["synthesize", "--help"])
        assert "ollama" in r.output
        assert "openai" in r.output

    # ── backend routing ──────────────────────────────────────────────────────

    def test_ollama_backend_calls_ollama(self):
        _, mock_ollama, mock_openai = _invoke(["hello"], _kg_mock())
        mock_ollama.assert_called_once()
        mock_openai.assert_not_called()

    def test_openai_backend_calls_openai_compat(self):
        _, mock_ollama, mock_openai = _invoke(["hello", "--backend", "openai"], _kg_mock())
        mock_openai.assert_called_once()
        mock_ollama.assert_not_called()

    def test_invalid_backend_exits_nonzero(self):
        r = CliRunner().invoke(cli, ["synthesize", "hello", "--backend", "bogus"])
        assert r.exit_code != 0

    # ── model defaults ───────────────────────────────────────────────────────

    def test_default_model_for_ollama(self):
        _, mock_ollama, _ = _invoke(["hello"], _kg_mock())
        assert mock_ollama.call_args.kwargs["model"] == _DEFAULT_MODEL

    def test_default_model_for_openai(self):
        _, _, mock_openai = _invoke(["hello", "--backend", "openai"], _kg_mock())
        assert mock_openai.call_args.kwargs["model"] == _DEFAULT_OPENAI_MODEL

    def test_explicit_model_overrides_ollama_default(self):
        _, mock_ollama, _ = _invoke(["hello", "--model", "mistral"], _kg_mock())
        assert mock_ollama.call_args.kwargs["model"] == "mistral"

    def test_explicit_model_overrides_openai_default(self):
        _, _, mock_openai = _invoke(
            ["hello", "--backend", "openai", "--model", "my-custom-model"], _kg_mock()
        )
        assert mock_openai.call_args.kwargs["model"] == "my-custom-model"

    # ── URL and API key pass-through ─────────────────────────────────────────

    def test_openai_url_forwarded(self):
        custom = "http://myserver:9000/v1"
        _, _, mock_openai = _invoke(
            ["hello", "--backend", "openai", "--openai-url", custom], _kg_mock()
        )
        assert mock_openai.call_args.kwargs["base_url"] == custom

    def test_default_openai_url_used_when_not_specified(self):
        _, _, mock_openai = _invoke(["hello", "--backend", "openai"], _kg_mock())
        assert mock_openai.call_args.kwargs["base_url"] == _DEFAULT_OPENAI_URL

    def test_api_key_forwarded_to_openai_compat(self):
        _, _, mock_openai = _invoke(
            ["hello", "--backend", "openai", "--api-key", "secret99"], _kg_mock()
        )
        assert mock_openai.call_args.kwargs["api_key"] == "secret99"  # pragma: allowlist secret

    def test_openai_api_key_env_var_picked_up(self):
        kg = _kg_mock()
        with (
            patch("kg_rag.cli.cmd_synthesize.KGRAG", return_value=kg),
            patch(
                "kg_rag.cli.cmd_synthesize._call_openai_compat", return_value="ok"
            ) as mock_openai,
        ):
            CliRunner(env={"OPENAI_API_KEY": "env-key-xyz"}).invoke(  # pragma: allowlist secret
                cli, ["synthesize", "hello", "--backend", "openai"], catch_exceptions=False
            )
        assert mock_openai.call_args.kwargs["api_key"] == "env-key-xyz"  # pragma: allowlist secret

    def test_openai_base_url_env_var_picked_up(self):
        kg = _kg_mock()
        with (
            patch("kg_rag.cli.cmd_synthesize.KGRAG", return_value=kg),
            patch(
                "kg_rag.cli.cmd_synthesize._call_openai_compat", return_value="ok"
            ) as mock_openai,
        ):
            CliRunner(env={"OPENAI_BASE_URL": "http://env-server:7777/v1"}).invoke(
                cli, ["synthesize", "hello", "--backend", "openai"], catch_exceptions=False
            )
        assert mock_openai.call_args.kwargs["base_url"] == "http://env-server:7777/v1"

    # ── streaming control ────────────────────────────────────────────────────

    def test_streaming_is_default(self):
        _, mock_ollama, _ = _invoke(["hello"], _kg_mock())
        assert mock_ollama.call_args.kwargs["stream"] is True

    def test_no_stream_flag_disables_streaming(self):
        _, mock_ollama, _ = _invoke(["hello", "--no-stream"], _kg_mock())
        assert mock_ollama.call_args.kwargs["stream"] is False

    def test_openai_backend_streaming_default(self):
        _, _, mock_openai = _invoke(["hello", "--backend", "openai"], _kg_mock())
        assert mock_openai.call_args.kwargs["stream"] is True

    def test_openai_no_stream_disables_streaming(self):
        _, _, mock_openai = _invoke(["hello", "--backend", "openai", "--no-stream"], _kg_mock())
        assert mock_openai.call_args.kwargs["stream"] is False

    # ── edge cases ───────────────────────────────────────────────────────────

    def test_no_snippets_exits_zero_with_message(self):
        result, _, _ = _invoke(["hello"], _kg_mock(n=0))
        assert result.exit_code == 0
        assert "No relevant content" in result.output

    def test_show_context_includes_snippet_content(self):
        result, _, _ = _invoke(["hello", "--show-context"], _kg_mock(n=1))
        assert result.exit_code == 0
        assert "Content for snippet 0" in result.output

    def test_max_context_limits_snippets_in_prompt(self):
        kg = _kg_mock(n=10)
        _, mock_ollama, _ = _invoke(["hello", "--max-context", "2"], kg)
        prompt = mock_ollama.call_args.kwargs["prompt"]
        assert "Content for snippet 0" in prompt
        assert "Content for snippet 1" in prompt
        assert "Content for snippet 2" not in prompt

    def test_exit_code_zero_on_success(self):
        result, _, _ = _invoke(["hello"], _kg_mock())
        assert result.exit_code == 0
