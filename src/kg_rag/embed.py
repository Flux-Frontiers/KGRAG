"""
embed.py

Pluggable embedding backend for KGRAG.

Defines the Embedder protocol (intentionally compatible with
pycode_kg.index.Embedder) and provides two concrete implementations:

  LlamaCppEmbedder  — llama-cpp-python, GGUF models, CPU/Metal/ARM-native.
                       No torch dependency. Works on Raspberry Pi, Apple Silicon,
                       Snapdragon, and x86 alike.

  SentenceTransformerEmbedder — thin shim around the sentence-transformers
                       library for back-compat with existing torch environments.
                       Not used by default; present so callers can construct one
                       explicitly when torch IS available and preferred.

Usage via config ([tool.kgrag] in pyproject.toml):

    [tool.kgrag]
    embed_backend    = "llama"
    llama_model_path = "~/.kgrag/bge-small-en-v1.5-Q8_0.gguf"

Or via environment variable:

    KGRAG_LLAMA_MODEL=~/.kgrag/bge-small-en-v1.5-Q8_0.gguf kgrag query "..."

Author: Eric G. Suchanek, PhD
Last Revision: 2026-04-25
License: Elastic 2.0
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any, Protocol, runtime_checkable


@runtime_checkable
class Embedder(Protocol):
    """Minimal embedding protocol — compatible with pycode_kg.index.Embedder.

    Any object with an ``embed_query(text) -> list[float]`` method satisfies
    this protocol and can be injected into a KGModule-based KG backend.
    """

    def embed_query(self, text: str) -> list[float]:
        """Embed a single query string into a float vector.

        :param text: The query string to embed.
        :return: Dense float32 vector as a plain Python list.
        """
        ...


class LlamaCppEmbedder:
    """Embedding backend powered by llama-cpp-python.

    Loads a GGUF model file (e.g. ``bge-small-en-v1.5-Q8_0.gguf``) and
    generates embeddings via CPU inference with optional Metal (macOS) or
    OpenBLAS (Linux/ARM) acceleration — no CUDA or torch required.

    Recommended GGUF model for KGRAG: ``BAAI/bge-small-en-v1.5`` (Q8_0, ~34 MB,
    384 dims, MTEB ~62). Available at ``ggml-org/bge-small-en-v1.5-Q8_0-GGUF``
    on HuggingFace.

    :param model_path: Path to the ``.gguf`` model file.
    :param n_ctx: Context window size. 512 is sufficient for query strings.
    :param n_batch: Batch size. Must not exceed 512 — known crash in
        llama-cpp-python when n_batch > 512 in embedding mode.
    :param n_gpu_layers: GPU layers to offload. -1 = all (Metal/CUDA),
        0 = CPU-only (default, safe on all platforms including Pi).
    :param verbose: Whether to print llama.cpp load messages.
    """

    def __init__(
        self,
        model_path: str | Path,
        *,
        n_ctx: int = 512,
        n_batch: int = 512,
        n_gpu_layers: int = 0,
        verbose: bool = False,
    ) -> None:
        try:
            from llama_cpp import Llama  # pylint: disable=import-outside-toplevel
        except ImportError as exc:
            raise ImportError(
                "llama-cpp-python is not installed. "
                "Install with: pip install llama-cpp-python  "
                "(ARM/Pi: CMAKE_ARGS='-DGGML_BLAS=ON -DGGML_BLAS_VENDOR=OpenBLAS' "
                "pip install llama-cpp-python --no-binary :all:)"
            ) from exc

        resolved = Path(model_path).expanduser().resolve()
        if not resolved.exists():
            raise FileNotFoundError(
                f"GGUF model not found: {resolved}\n"
                "Download bge-small-en-v1.5-Q8_0.gguf from "
                "https://huggingface.co/ggml-org/bge-small-en-v1.5-Q8_0-GGUF"
            )

        self._model_path = resolved
        self._llm: Any = Llama(
            model_path=str(resolved),
            embedding=True,
            n_ctx=n_ctx,
            n_batch=min(n_batch, 512),  # guard against >512 crash
            n_gpu_layers=n_gpu_layers,
            verbose=verbose,
        )
        # Resolve embedding dimension from model metadata so .dim matches
        # pycode_kg's Embedder interface (used by SemanticIndex at build time).
        self.dim: int = self._llm.n_embd()

    def embed_texts(self, texts: list[str]) -> list[list[float]]:
        """Embed a batch of strings.

        :param texts: List of strings to embed.
        :return: List of float32 vectors.
        """
        result = self._llm.embed(texts)
        # llm.embed(list) returns list[list[float]]; normalise single-item edge case.
        if texts and not isinstance(result[0], list):
            return [result]
        return result

    def embed_query(self, text: str) -> list[float]:
        """Embed a single query string.

        :param text: Query string to embed.
        :return: Dense float32 vector as a plain Python list.
        """
        result = self._llm.embed(text)
        # llm.embed("single string") returns list[float] directly;
        # llm.embed(["a", "b"]) returns list[list[float]].
        # Normalise both shapes to list[float].
        if result and isinstance(result[0], list):
            return result[0]
        return result

    def __repr__(self) -> str:
        return f"LlamaCppEmbedder(model={self._model_path.name!r}, dim={self.dim})"


class SentenceTransformerEmbedder:
    """Thin shim around sentence-transformers for back-compat.

    Use this only when torch IS available and preferred. On ARM or Pi,
    use LlamaCppEmbedder instead.

    :param model_name: HuggingFace model name, e.g. ``'BAAI/bge-small-en-v1.5'``.
    """

    def __init__(self, model_name: str) -> None:
        try:
            from sentence_transformers import (  # pylint: disable=import-outside-toplevel
                SentenceTransformer,
            )
        except ImportError as exc:
            raise ImportError(
                "sentence-transformers is not installed. "
                "Install with: pip install sentence-transformers  "
                "or switch to embed_backend='llama'."
            ) from exc
        self._model = SentenceTransformer(model_name)
        self.dim: int = self._model.get_sentence_embedding_dimension()

    def embed_texts(self, texts: list[str]) -> list[list[float]]:
        """Embed a batch of strings.

        :param texts: List of strings to embed.
        :return: List of float32 vectors.
        """
        return self._model.encode(texts, convert_to_numpy=True).tolist()

    def embed_query(self, text: str) -> list[float]:
        """Embed a single query string.

        :param text: Query string to embed.
        :return: Dense float32 vector as a plain Python list.
        """
        return self._model.encode(text, convert_to_numpy=True).tolist()

    def __repr__(self) -> str:
        return f"SentenceTransformerEmbedder(model={self._model!r}, dim={self.dim})"


def make_embedder(config: dict) -> "Embedder | None":
    """Instantiate the correct embedder from ``[tool.kgrag]`` config.

    Returns ``None`` if no ``embed_backend`` is configured, meaning each KG
    library will use its own default embedder (sentence-transformers).

    Supported backends:

    * ``"llama"`` — :class:`LlamaCppEmbedder`. Requires ``llama_model_path``
      in config or ``KGRAG_LLAMA_MODEL`` env var.

    :param config: Dict from :func:`kg_rag.config.load_kgrag_config`.
    :return: Embedder instance, or None to use each KG's built-in default.
    :raises ValueError: If backend name is unknown or required config is missing.
    :raises FileNotFoundError: If the GGUF model file cannot be found.
    """
    backend = config.get("embed_backend")
    if backend is None:
        return None

    if backend == "llama":
        model_path = config.get("llama_model_path") or os.environ.get("KGRAG_LLAMA_MODEL")
        if not model_path:
            raise ValueError(
                "embed_backend = 'llama' requires either:\n"
                "  llama_model_path = '~/.kgrag/model.gguf'  in [tool.kgrag]\n"
                "  or KGRAG_LLAMA_MODEL env var pointing to a .gguf file."
            )
        return LlamaCppEmbedder(
            model_path,
            n_ctx=int(config.get("llama_n_ctx", 512)),
            n_batch=int(config.get("llama_n_batch", 512)),
            n_gpu_layers=int(config.get("llama_n_gpu_layers", 0)),
            verbose=bool(config.get("llama_verbose", False)),
        )

    raise ValueError(
        f"Unknown embed_backend: {backend!r}. "
        "Supported values: 'llama'."
    )
