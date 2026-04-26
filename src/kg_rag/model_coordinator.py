"""
model_coordinator.py — Centralized embedding model cache for KGRAG.

All KG modules (PyCodeKG, DocKG, DiaryKG, …) share a single model cache under
``~/.kgrag/models/`` rather than each maintaining their own ``models/``
directory.  The coordinator ensures each model is downloaded once and loaded
into memory once, regardless of how many KG adapters are active.

Architecture
------------
The coordinator sits between the :class:`~kg_rag.orchestrator.Orchestrator`
(which calls :func:`~kg_rag.embed.make_embedder`) and the individual KG
adapters.  When ``embed_backend = "sentence_transformers"`` is set in
``[tool.kgrag]`` (``pyproject.toml``), ``make_embedder()`` creates a
``ModelCoordinator`` and calls :meth:`ModelCoordinator.get_embedder`, which
returns a :class:`~kg_rag.embed.SentenceTransformerEmbedder` implementing the
``Embedder`` protocol.  The orchestrator then injects that single shared
instance into every adapter.

Model cache layout::

    ~/.kgrag/models/
        manifest.json               ← download registry
        BAAI/
            bge-small-en-v1.5/      ← model files
        BAAI/
            bge-large-en-v1.5/
        nomic-ai/
            nomic-embed-text-v1.5/

The cache root can be overridden with the ``KGRAG_MODEL_DIR`` environment
variable, or by passing ``model_dir`` to :class:`ModelCoordinator` directly.

Known aliases
-------------
Short aliases are resolved via :data:`KNOWN_MODELS` (see ``kgrag models aliases``):

- ``"default"`` / ``"bge-small"`` → ``BAAI/bge-small-en-v1.5``  (384-dim)
- ``"bge-large"``                  → ``BAAI/bge-large-en-v1.5``  (1024-dim)
- ``"nomic"``                      → ``nomic-ai/nomic-embed-text-v1.5``  (768-dim)

Usage
-----
::

    from kg_rag.model_coordinator import ModelCoordinator

    mc = ModelCoordinator()

    # Ensure a model is on disk and get its path
    path = mc.ensure("bge-small")

    # Get a protocol-compliant embedder (downloads + loads once, then cached)
    embedder = mc.get_embedder("bge-small")
    vectors = embedder.embed_texts(["hello world", "foo bar"])

    # Encode directly through the coordinator
    vectors = mc.encode(["hello world"], model_id="bge-small")

    # Module-level singleton (used by make_embedder)
    from kg_rag.model_coordinator import get_coordinator
    mc = get_coordinator()

CLI
---
``kgrag models {download,list,remove,path,env,aliases,cleanup,test-embed}``

Author: Eric G. Suchanek, PhD
License: Elastic 2.0
Last Revision: 2026-04-26 02:25:38
"""

from __future__ import annotations

import json
import logging
import os
import shutil
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from kg_rag._embedders import SentenceTransformerEmbedder

logger = logging.getLogger(__name__)


_DEFAULT_KGRAG_DIR = Path.home() / ".kgrag"
_DEFAULT_MODEL_DIR = _DEFAULT_KGRAG_DIR / "models"

# Well-known models used by KGRAG modules.
# Maps a short alias to its HuggingFace repo id.
KNOWN_MODELS: dict[str, str] = {
    "default": "BAAI/bge-small-en-v1.5",
    "bge-small": "BAAI/bge-small-en-v1.5",
    "bge-small-en-v1.5": "BAAI/bge-small-en-v1.5",
    "bge-large": "BAAI/bge-large-en-v1.5",
    "bge-large-en-v1.5": "BAAI/bge-large-en-v1.5",
    "all-MiniLM-L6-v2": "sentence-transformers/all-MiniLM-L6-v2",
    "all-mpnet-base-v2": "sentence-transformers/all-mpnet-base-v2",
    "nomic": "nomic-ai/nomic-embed-text-v1.5",
    "nomic-v1.5": "nomic-ai/nomic-embed-text-v1.5",
}


def default_model_dir() -> Path:
    """Return the model cache directory, respecting ``KGRAG_MODEL_DIR`` env var.

    :return: Absolute path to the model cache directory.
    """
    env = os.environ.get("KGRAG_MODEL_DIR")
    if env:
        return Path(env).resolve()
    return _DEFAULT_MODEL_DIR


@dataclass
class CachedModel:
    """Metadata for a cached model.

    :param repo_id: HuggingFace model repository ID.
    :param local_path: Absolute path to the local model directory.
    :param downloaded_at: When the model was downloaded.
    :param size_bytes: Total size in bytes (0 if unknown).
    :param metadata: Extra key-value data.
    """

    repo_id: str
    local_path: Path
    downloaded_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    size_bytes: int = 0
    metadata: dict[str, Any] = field(default_factory=dict)


class ModelCoordinator:
    """Centralized model download, cache, and embedder manager for KGRAG.

    Downloads embedding models from HuggingFace Hub and caches them under
    a single system-wide directory (``~/.kgrag/models/`` by default).
    Also manages loaded embedder instances so that each model is loaded into
    memory at most once across all modules.

    :param model_dir: Override the default model cache directory.
    """

    def __init__(self, model_dir: Path | None = None) -> None:
        self._model_dir = Path(model_dir).resolve() if model_dir else default_model_dir()
        self._model_dir.mkdir(parents=True, exist_ok=True)
        self._manifest_path = self._model_dir / "manifest.json"
        self._manifest: dict[str, Any] = self._load_manifest()
        # Loaded embedder instances, keyed by resolved repo_id.
        self._embedders: dict[str, Any] = {}

    @property
    def model_dir(self) -> Path:
        """Root directory for all cached models."""
        return self._model_dir

    # ------------------------------------------------------------------
    # Public API — Model download / cache
    # ------------------------------------------------------------------

    def ensure(self, model_id: str) -> Path:
        """Ensure a model is downloaded and return its local path.

        If the model is already cached, returns immediately. Otherwise
        downloads it from HuggingFace Hub using ``huggingface_hub``.

        :param model_id: HuggingFace repo ID or a known alias.
        :return: Path to the local model directory.
        """
        repo_id = self._resolve_alias(model_id)
        local_path = self._model_path(repo_id)

        if self._is_cached(repo_id, local_path):
            logger.debug("Model %s already cached at %s", repo_id, local_path)
            return local_path

        logger.info("Downloading model %s to %s ...", repo_id, local_path)
        self._download(repo_id, local_path)
        self._update_manifest(repo_id, local_path)
        return local_path

    def model_path(self, model_id: str) -> Path | None:
        """Return the cached path for a model, or None if not downloaded.

        :param model_id: HuggingFace repo ID or known alias.
        :return: Path if cached, None otherwise.
        """
        repo_id = self._resolve_alias(model_id)
        local_path = self._model_path(repo_id)
        if self._is_cached(repo_id, local_path):
            return local_path
        return None

    def list_cached(self) -> list[CachedModel]:
        """List all cached models.

        :return: List of CachedModel entries.
        """
        result = []
        for repo_id, info in self._manifest.get("models", {}).items():
            lp = Path(info["local_path"])
            result.append(
                CachedModel(
                    repo_id=repo_id,
                    local_path=lp,
                    downloaded_at=datetime.fromisoformat(info.get("downloaded_at", "")),
                    size_bytes=info.get("size_bytes", 0),
                    metadata=info.get("metadata", {}),
                )
            )
        return result

    def remove(self, model_id: str) -> bool:
        """Remove a cached model and unload its embedder.

        :param model_id: HuggingFace repo ID or known alias.
        :return: True if removed, False if not found.
        """
        repo_id = self._resolve_alias(model_id)
        local_path = self._model_path(repo_id)
        if local_path.exists():
            shutil.rmtree(local_path)
        # Unload embedder if loaded
        self._embedders.pop(repo_id, None)
        models = self._manifest.get("models", {})
        if repo_id in models:
            del models[repo_id]
            self._save_manifest()
            logger.info("Removed model %s", repo_id)
            return True
        return False

    def cleanup(self) -> int:
        """Remove models not referenced in the manifest.

        :return: Number of orphan directories removed.
        """
        if not self._model_dir.exists():
            return 0
        known_paths = set()
        for info in self._manifest.get("models", {}).values():
            known_paths.add(Path(info["local_path"]).resolve())
        removed = 0
        for child in self._model_dir.iterdir():
            if (
                child.is_dir()
                and child.name != "__pycache__"
                and child.resolve() not in known_paths
            ):
                # Check subdirectories too (org/model pattern)
                has_known = any(p.is_relative_to(child.resolve()) for p in known_paths)
                if not has_known and child.name != "manifest.json":
                    shutil.rmtree(child)
                    removed += 1
                    logger.info("Cleaned up orphan directory: %s", child)
        return removed

    def total_size(self) -> int:
        """Return total size of all cached models in bytes."""
        total = 0
        for info in self._manifest.get("models", {}).values():
            total += info.get("size_bytes", 0)
        return total

    # ------------------------------------------------------------------
    # Public API — Embedder management
    # ------------------------------------------------------------------

    def get_embedder(self, model_id: str = "default") -> Any:
        """Return a loaded SentenceTransformerEmbedder, downloading if needed.

        Returns a :class:`~kg_rag.embed.SentenceTransformerEmbedder` — implements
        the ``Embedder`` protocol and can be injected directly into any KGAdapter.
        Embedders are cached in memory so repeated calls return the same instance.

        :param model_id: HuggingFace repo ID or known alias.
        :param trust_remote_code: Whether to trust remote code (required for some models).
        :return: A ``SentenceTransformerEmbedder`` instance.
        """
        repo_id = self._resolve_alias(model_id)

        if repo_id in self._embedders:
            return self._embedders[repo_id]

        local_path = self.ensure(repo_id)
        embedder = self._load_embedder(str(local_path))
        self._embedders[repo_id] = embedder
        logger.info("Loaded embedder for %s from %s", repo_id, local_path)
        return embedder

    def encode(
        self,
        texts: list[str],
        model_id: str = "default",
    ) -> Any:
        """Encode texts into embeddings using a cached embedder.

        :param texts: List of strings to encode.
        :param model_id: HuggingFace repo ID or known alias.
        :return: List of float vectors.
        """
        repo_id = self._resolve_alias(model_id)
        model = self.get_embedder(repo_id)
        return model.embed_texts(texts)

    def unload_embedder(self, model_id: str) -> bool:
        """Unload an embedder from memory (model files remain on disk).

        :param model_id: HuggingFace repo ID or known alias.
        :return: True if an embedder was unloaded, False if not loaded.
        """
        repo_id = self._resolve_alias(model_id)
        if repo_id in self._embedders:
            del self._embedders[repo_id]
            logger.info("Unloaded embedder for %s", repo_id)
            return True
        return False

    def unload_all(self) -> int:
        """Unload all embedders from memory.

        :return: Number of embedders unloaded.
        """
        count = len(self._embedders)
        self._embedders.clear()
        if count:
            logger.info("Unloaded %d embedder(s)", count)
        return count

    def loaded_embedders(self) -> list[str]:
        """Return repo IDs of currently loaded embedders."""
        return list(self._embedders.keys())

    # ------------------------------------------------------------------
    # Environment variable helpers (backward compat with module env vars)
    # ------------------------------------------------------------------

    def export_env(self) -> dict[str, str]:
        """Return env vars that downstream modules can use.

        Sets ``CODEKG_MODEL_DIR`` and ``DOCKG_MODEL_DIR`` to point at
        the centralized cache so that ``codekg download-model`` and
        ``dockg download-model`` use the shared location.

        :return: Dict of environment variable name -> value.
        """
        return {
            "KGRAG_MODEL_DIR": str(self._model_dir),
            "CODEKG_MODEL_DIR": str(self._model_dir),
            "DOCKG_MODEL_DIR": str(self._model_dir),
        }

    def apply_env(self) -> None:
        """Set environment variables so downstream modules use the shared cache.

        Calls :meth:`export_env` and applies each variable to ``os.environ``,
        only if not already set by the user.
        """
        for key, value in self.export_env().items():
            if key not in os.environ:
                os.environ[key] = value
                logger.debug("Set %s=%s", key, value)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _resolve_alias(self, model_id: str) -> str:
        """Resolve a known alias to a full HuggingFace repo ID."""
        return KNOWN_MODELS.get(model_id, model_id)

    def _model_path(self, repo_id: str) -> Path:
        """Compute the local cache path for a given repo ID.

        Uses the repo ID as a subdirectory path, e.g.
        ``~/.kgrag/models/nomic-ai/nomic-embed-text-v1.5/``.
        """
        return self._model_dir / repo_id.replace("/", os.sep)

    def _is_cached(self, repo_id: str, local_path: Path) -> bool:
        """Check if a model is already cached and valid."""
        if not local_path.exists():
            return False
        # Must have at least a config file or model files
        has_files = any(local_path.iterdir())
        return has_files and repo_id in self._manifest.get("models", {})

    def _download(self, repo_id: str, local_path: Path) -> None:
        """Download a model from HuggingFace Hub.

        Uses ``huggingface_hub.snapshot_download`` which handles caching,
        resumable downloads, and integrity verification.
        """
        try:
            from huggingface_hub import snapshot_download  # pylint: disable=import-outside-toplevel
        except ImportError as e:
            raise ImportError(
                "huggingface_hub is required for model downloads. "
                "Install it with: pip install huggingface-hub"
            ) from e

        local_path.mkdir(parents=True, exist_ok=True)
        snapshot_download(
            repo_id=repo_id,
            local_dir=str(local_path),
            local_dir_use_symlinks=False,
            ignore_patterns=[
                "onnx/*",
                "onnx_quantized/*",
                "*.ot",
                "flax_model*",
                "tf_model*",
                "rust_model*",
            ],
        )
        logger.info("Downloaded model %s to %s", repo_id, local_path)

    @staticmethod
    def _load_embedder(model_path: str) -> Any:
        """Load a SentenceTransformerEmbedder from a local path.

        :param model_path: Local filesystem path to the model.
        :return: A ``SentenceTransformerEmbedder`` instance.
        """
        return SentenceTransformerEmbedder(model_path)

    def _dir_size(self, path: Path) -> int:
        """Recursively compute directory size in bytes."""
        total = 0
        if path.is_dir():
            for f in path.rglob("*"):
                if f.is_file():
                    total += f.stat().st_size
        return total

    def _update_manifest(self, repo_id: str, local_path: Path) -> None:
        """Record a downloaded model in the manifest."""
        models = self._manifest.setdefault("models", {})
        models[repo_id] = {
            "local_path": str(local_path),
            "downloaded_at": datetime.now(UTC).isoformat(),
            "size_bytes": self._dir_size(local_path),
            "metadata": {},
        }
        self._save_manifest()

    def _load_manifest(self) -> dict:
        """Load the manifest file, or return an empty structure."""
        if self._manifest_path.exists():
            try:
                with self._manifest_path.open() as f:
                    return json.load(f)
            except (json.JSONDecodeError, OSError):
                logger.warning("Corrupt manifest at %s, starting fresh", self._manifest_path)
        return {"version": 1, "models": {}}

    def _save_manifest(self) -> None:
        """Persist the manifest to disk."""
        self._manifest_path.parent.mkdir(parents=True, exist_ok=True)
        with self._manifest_path.open("w") as f:
            json.dump(self._manifest, f, indent=2, default=str)


# ------------------------------------------------------------------
# Module-level convenience
# ------------------------------------------------------------------

_coordinator: ModelCoordinator | None = None


def get_coordinator(model_dir: Path | None = None) -> ModelCoordinator:
    """Return the singleton ModelCoordinator instance.

    :param model_dir: Override the default model directory (only on first call).
    :return: The global ModelCoordinator.
    """
    global _coordinator  # noqa: PLW0603
    if _coordinator is None:
        _coordinator = ModelCoordinator(model_dir=model_dir)
    return _coordinator
