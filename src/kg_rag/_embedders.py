"""
_embedders.py — concrete Embedder implementations for KGRAG.

Extracted from embed.py so that model_coordinator.py can import
SentenceTransformerEmbedder without creating a circular dependency
(embed ↔ model_coordinator).

Do not import from kg_rag.embed or kg_rag.model_coordinator here.

Author: Eric G. Suchanek, PhD
License: Elastic 2.0
"""

from __future__ import annotations

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

    :param model_path: Path to the ``.gguf`` model file.
    :param n_ctx: Context window size. 512 is sufficient for query strings.
    :param n_batch: Batch size. Must not exceed 512.
    :param n_gpu_layers: GPU layers to offload. -1 = all, 0 = CPU-only.
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
            n_batch=min(n_batch, 512),
            n_gpu_layers=n_gpu_layers,
            verbose=verbose,
        )
        self.dim: int = self._llm.n_embd()

    def embed_texts(self, texts: list[str]) -> list[list[float]]:
        """Embed a batch of strings one at a time.

        :param texts: List of strings to embed.
        :return: List of float32 vectors.
        """
        return [self.embed_query(t) for t in texts]

    def embed_query(self, text: str) -> list[float]:
        """Embed a single query string.

        :param text: Query string to embed.
        :return: Dense float32 vector as a plain Python list.
        """
        result = self._llm.embed(text)
        if result and isinstance(result[0], list):
            return result[0]
        return result

    def __repr__(self) -> str:
        return f"LlamaCppEmbedder(model={self._model_path.name!r}, dim={self.dim})"


class SentenceTransformerEmbedder:
    """Thin shim around sentence-transformers for back-compat.

    Use this only when torch IS available and preferred. On ARM or Pi,
    use LlamaCppEmbedder instead.

    :param model_name: HuggingFace model name or local path,
        e.g. ``'BAAI/bge-small-en-v1.5'``.
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
        get_dim = getattr(self._model, "get_embedding_dimension", None) or getattr(
            self._model, "get_sentence_embedding_dimension", None
        )
        if get_dim is None:
            raise AttributeError("SentenceTransformer has no get_embedding_dimension method")
        self.dim: int = get_dim()

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
