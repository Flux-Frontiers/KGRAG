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

from kg_rag._embedders import Embedder, LlamaCppEmbedder, SentenceTransformerEmbedder

__all__ = ["Embedder", "make_embedder"]


def make_embedder(config: dict) -> Embedder | None:
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

    if backend == "sentence_transformers":
        from kg_rag.model_coordinator import (  # pylint: disable=import-outside-toplevel
            ModelCoordinator,
        )

        model_id = config.get("st_model", "default")
        mc = ModelCoordinator()
        local_path = mc.ensure(model_id)
        return SentenceTransformerEmbedder(str(local_path))

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

    raise ValueError(f"Unknown embed_backend: {backend!r}. Supported values: 'llama'.")
