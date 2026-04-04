"""summarize.py — Configurable LLM summarization backend for KG Context Pruning.

Supports two backends:
  ``primary``  — Anthropic Claude via the ``anthropic`` SDK (default).
  ``local``    — Ollama-compatible HTTP endpoint (air-gapped / cost-sensitive).

Configuration via ``agentkg.toml`` or environment variables:
  AGENTKG_SUMMARIZER_BACKEND   = "primary" | "local"
  AGENTKG_SUMMARIZER_ENDPOINT  = "http://localhost:11434/api/generate"
  AGENTKG_SUMMARIZER_MODEL     = "llama3.2"
"""

from __future__ import annotations

import json
import os
from dataclasses import dataclass
from typing import Literal


@dataclass
class SummarizerConfig:
    """Configuration for the summarization backend.

    :param backend: ``"primary"`` (Anthropic) or ``"local"`` (Ollama).
    :param local_endpoint: Ollama-compatible API URL.
    :param local_model: Model name for the local endpoint.
    :param primary_model: Claude model ID for the primary backend.
    :param temperature: Sampling temperature (lower = more deterministic).
    :param max_tokens: Maximum tokens in the summary.
    """

    backend: Literal["primary", "local"] = "primary"
    local_endpoint: str = "http://localhost:11434/api/generate"
    local_model: str = "llama3.2"
    primary_model: str = "claude-haiku-4-5-20251001"
    temperature: float = 0.2
    max_tokens: int = 512

    @classmethod
    def from_env(cls) -> "SummarizerConfig":
        """Load configuration from environment variables."""
        return cls(
            backend=os.environ.get("AGENTKG_SUMMARIZER_BACKEND", "primary"),  # type: ignore[arg-type]
            local_endpoint=os.environ.get(
                "AGENTKG_SUMMARIZER_ENDPOINT", "http://localhost:11434/api/generate"
            ),
            local_model=os.environ.get("AGENTKG_SUMMARIZER_MODEL", "llama3.2"),
            primary_model=os.environ.get("AGENTKG_SUMMARIZER_PRIMARY_MODEL", "claude-haiku-4-5-20251001"),
        )


_SUMMARY_PROMPT = """\
Summarize the following conversation segment into 2–5 sentences.
Preserve all decisions made, open questions, and key facts.
Do not add new information. Write in third-person past tense.

CONVERSATION:
{text}

SUMMARY:"""


class Summarizer:
    """LLM-backed text summarizer with Anthropic + Ollama support.

    :param config: Summarization backend configuration.
    """

    def __init__(self, config: SummarizerConfig | None = None) -> None:
        self._config = config or SummarizerConfig.from_env()

    def summarize(self, text: str) -> str:
        """Summarize ``text`` using the configured backend.

        Falls back to the local backend if the primary raises, and to a
        simple extractive fallback if both fail.

        :param text: Conversation text to summarize.
        :return: Summary string.
        """
        if not text or not text.strip():
            return ""
        prompt = _SUMMARY_PROMPT.format(text=text[:4000])
        if self._config.backend == "primary":
            result = self._call_primary(prompt)
            if result:
                return result
        result = self._call_local(prompt)
        if result:
            return result
        # Extractive fallback: first + last sentence(s)
        return self._extractive_fallback(text)

    def _call_primary(self, prompt: str) -> str | None:
        """Call the Anthropic API via the anthropic SDK."""
        try:
            import anthropic  # noqa: PLC0415
            client = anthropic.Anthropic()
            msg = client.messages.create(
                model=self._config.primary_model,
                max_tokens=self._config.max_tokens,
                temperature=self._config.temperature,
                messages=[{"role": "user", "content": prompt}],
            )
            return msg.content[0].text.strip() if msg.content else None
        except Exception:  # pylint: disable=broad-exception-caught
            return None

    def _call_local(self, prompt: str) -> str | None:
        """POST to an Ollama-compatible local endpoint."""
        try:
            import urllib.request  # noqa: PLC0415
            payload = json.dumps({
                "model": self._config.local_model,
                "prompt": prompt,
                "stream": False,
                "options": {"temperature": self._config.temperature},
            }).encode()
            req = urllib.request.Request(
                self._config.local_endpoint,
                data=payload,
                headers={"Content-Type": "application/json"},
                method="POST",
            )
            with urllib.request.urlopen(req, timeout=30) as resp:
                data = json.loads(resp.read())
                return data.get("response", "").strip() or None
        except Exception:  # pylint: disable=broad-exception-caught
            return None

    @staticmethod
    def _extractive_fallback(text: str) -> str:
        """Return the first and last sentence of ``text`` as a stub summary."""
        import re  # noqa: PLC0415
        sentences = [s.strip() for s in re.split(r"(?<=[.!?])\s+", text) if s.strip()]
        if not sentences:
            return text[:200]
        if len(sentences) == 1:
            return sentences[0]
        return f"{sentences[0]} … {sentences[-1]}"
