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

  TEIEmbedder       — remote HuggingFace Text Embeddings Inference server,
                       supplied by kg_utils.embedder.  Stdlib HTTP only: no
                       torch and no model in this process.  See
                       docs/TEI_EVALUATION.md for when this is the right choice
                       (short version: it is not faster than in-process torch on
                       CPU, but it keeps the model out of the client).

Usage via config ([tool.kgrag] in pyproject.toml):

    [tool.kgrag]
    embed_backend    = "llama"
    llama_model_path = "~/.kgrag/bge-small-en-v1.5-Q8_0.gguf"

    # …or point at a running TEI server:
    embed_backend = "tei"
    tei_endpoint  = "http://localhost:8080"
    # tei_dim     = 384   # set to skip the startup probe entirely

Or via environment variable:

    KGRAG_LLAMA_MODEL=~/.kgrag/bge-small-en-v1.5-Q8_0.gguf kgrag query "..."
    KG_EMBED_ENDPOINT=http://localhost:8080 kgrag query "..."   # with embed_backend = "tei"

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

    * ``"sentence_transformers"`` — :class:`SentenceTransformerEmbedder`, with
      the model resolved through :class:`~kg_rag.model_coordinator.ModelCoordinator`.
    * ``"llama"`` — :class:`LlamaCppEmbedder`. Requires ``llama_model_path``
      in config or ``KGRAG_LLAMA_MODEL`` env var.
    * ``"tei"`` — ``kg_utils.embedder.TEIEmbedder`` against a running Text
      Embeddings Inference server. Reads ``tei_endpoint`` (or
      ``KG_EMBED_ENDPOINT``), and optionally ``tei_dim``, ``tei_model``,
      ``tei_api_key``, ``tei_timeout``, ``tei_max_retries``, ``tei_max_batch``.

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

    if backend == "tei":
        from kg_utils.embedder import (  # pylint: disable=import-outside-toplevel
            TEIEmbedder,
        )

        dim = config.get("tei_dim")
        max_batch = config.get("tei_max_batch")
        return TEIEmbedder(
            config.get("tei_endpoint") or os.environ.get("KG_EMBED_ENDPOINT"),
            dim=int(dim) if dim is not None else None,
            api_key=config.get("tei_api_key"),
            model_name=str(config.get("tei_model", "")),
            timeout=float(config.get("tei_timeout", 120.0)),
            max_retries=int(config.get("tei_max_retries", 3)),
            max_batch=int(max_batch) if max_batch is not None else None,
        )

    raise ValueError(
        f"Unknown embed_backend: {backend!r}. "
        "Supported values: 'sentence_transformers', 'llama', 'tei'."
    )
