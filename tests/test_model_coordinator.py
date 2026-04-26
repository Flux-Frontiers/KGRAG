"""
test_model_coordinator.py

Unit tests for kg_rag.model_coordinator.ModelCoordinator.

All HuggingFace downloads and SentenceTransformerEmbedder loads are mocked
so the suite runs without any heavyweight dependencies or network access.
"""

from __future__ import annotations

import os
from pathlib import Path
from unittest.mock import MagicMock, patch

import kg_rag.model_coordinator as _mc_mod
from kg_rag.model_coordinator import (
    KNOWN_MODELS,
    CachedModel,
    ModelCoordinator,
    default_model_dir,
    get_coordinator,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_mc(tmp_path: Path) -> ModelCoordinator:
    """Return a ModelCoordinator backed by a temp directory."""
    return ModelCoordinator(model_dir=tmp_path / "models")


def _fake_download(mc: ModelCoordinator, repo_id: str) -> Path:
    """Simulate a successful download by creating the model directory."""
    local = mc._model_path(repo_id)
    local.mkdir(parents=True, exist_ok=True)
    (local / "config.json").write_text("{}")
    return local


# ---------------------------------------------------------------------------
# KNOWN_MODELS / alias resolution
# ---------------------------------------------------------------------------


def test_default_model_is_bge_small():
    assert KNOWN_MODELS["default"] == "BAAI/bge-small-en-v1.5"


def test_known_aliases_resolve():
    mc = ModelCoordinator.__new__(ModelCoordinator)
    assert mc._resolve_alias("default") == "BAAI/bge-small-en-v1.5"
    assert mc._resolve_alias("bge-small") == "BAAI/bge-small-en-v1.5"
    assert mc._resolve_alias("nomic") == "nomic-ai/nomic-embed-text-v1.5"
    # Unknown alias passes through unchanged
    assert mc._resolve_alias("custom/model") == "custom/model"


# ---------------------------------------------------------------------------
# default_model_dir / env override
# ---------------------------------------------------------------------------


def test_default_model_dir_uses_home(monkeypatch):
    monkeypatch.delenv("KGRAG_MODEL_DIR", raising=False)
    p = default_model_dir()
    assert ".kgrag" in str(p)
    assert "models" in str(p)


def test_default_model_dir_env_override(monkeypatch, tmp_path):
    monkeypatch.setenv("KGRAG_MODEL_DIR", str(tmp_path / "custom"))
    p = default_model_dir()
    assert p == (tmp_path / "custom").resolve()


# ---------------------------------------------------------------------------
# ensure() — download + cache
# ---------------------------------------------------------------------------


def test_ensure_downloads_when_not_cached(tmp_path):
    mc = _make_mc(tmp_path)
    with patch.object(mc, "_download", side_effect=lambda r, p: _fake_download(mc, r)):
        path = mc.ensure("default")
    assert path.exists()
    assert "BAAI" in str(path)


def test_ensure_skips_download_when_cached(tmp_path):
    mc = _make_mc(tmp_path)
    repo_id = KNOWN_MODELS["default"]
    _fake_download(mc, repo_id)
    mc._update_manifest(repo_id, mc._model_path(repo_id))

    with patch.object(mc, "_download") as mock_dl:
        mc.ensure("default")
    mock_dl.assert_not_called()


def test_ensure_alias_and_full_id_same_result(tmp_path):
    mc = _make_mc(tmp_path)
    with patch.object(mc, "_download", side_effect=lambda r, p: _fake_download(mc, r)):
        p1 = mc.ensure("bge-small")
        p2 = mc.ensure("BAAI/bge-small-en-v1.5")
    assert p1 == p2


# ---------------------------------------------------------------------------
# model_path()
# ---------------------------------------------------------------------------


def test_model_path_returns_none_when_not_cached(tmp_path):
    mc = _make_mc(tmp_path)
    assert mc.model_path("default") is None


def test_model_path_returns_path_when_cached(tmp_path):
    mc = _make_mc(tmp_path)
    repo_id = KNOWN_MODELS["default"]
    _fake_download(mc, repo_id)
    mc._update_manifest(repo_id, mc._model_path(repo_id))
    assert mc.model_path("default") is not None


# ---------------------------------------------------------------------------
# list_cached() / remove() / cleanup()
# ---------------------------------------------------------------------------


def test_list_cached_empty_initially(tmp_path):
    mc = _make_mc(tmp_path)
    assert mc.list_cached() == []


def test_list_cached_after_download(tmp_path):
    mc = _make_mc(tmp_path)
    repo_id = KNOWN_MODELS["default"]
    _fake_download(mc, repo_id)
    mc._update_manifest(repo_id, mc._model_path(repo_id))
    cached = mc.list_cached()
    assert len(cached) == 1
    assert isinstance(cached[0], CachedModel)
    assert cached[0].repo_id == repo_id


def test_remove_deletes_dir_and_manifest_entry(tmp_path):
    mc = _make_mc(tmp_path)
    repo_id = KNOWN_MODELS["default"]
    local = _fake_download(mc, repo_id)
    mc._update_manifest(repo_id, local)
    assert mc.remove("default") is True
    assert not local.exists()
    assert mc.list_cached() == []


def test_remove_returns_false_for_unknown(tmp_path):
    mc = _make_mc(tmp_path)
    assert mc.remove("nonexistent/model") is False


def test_cleanup_removes_orphan_dirs(tmp_path):
    mc = _make_mc(tmp_path)
    orphan = mc.model_dir / "orphan-dir"
    orphan.mkdir(parents=True)
    removed = mc.cleanup()
    assert removed == 1
    assert not orphan.exists()


# ---------------------------------------------------------------------------
# get_embedder() — returns SentenceTransformerEmbedder, caches in memory
# ---------------------------------------------------------------------------


def test_get_embedder_returns_embedder_protocol(tmp_path):
    mc = _make_mc(tmp_path)
    repo_id = KNOWN_MODELS["default"]
    _fake_download(mc, repo_id)
    mc._update_manifest(repo_id, mc._model_path(repo_id))

    fake_embedder = MagicMock()
    fake_embedder.embed_query.return_value = [0.1, 0.2, 0.3]

    with patch("kg_rag.model_coordinator.SentenceTransformerEmbedder", return_value=fake_embedder):
        emb = mc.get_embedder("default")

    assert emb is fake_embedder
    assert callable(emb.embed_query)


def test_get_embedder_cached_in_memory(tmp_path):
    mc = _make_mc(tmp_path)
    repo_id = KNOWN_MODELS["default"]
    _fake_download(mc, repo_id)
    mc._update_manifest(repo_id, mc._model_path(repo_id))

    fake_embedder = MagicMock()
    with patch("kg_rag.model_coordinator.SentenceTransformerEmbedder", return_value=fake_embedder):
        e1 = mc.get_embedder("default")
        e2 = mc.get_embedder("default")

    assert e1 is e2


def test_unload_embedder(tmp_path):
    mc = _make_mc(tmp_path)
    repo_id = KNOWN_MODELS["default"]
    _fake_download(mc, repo_id)
    mc._update_manifest(repo_id, mc._model_path(repo_id))

    with patch("kg_rag.model_coordinator.SentenceTransformerEmbedder", return_value=MagicMock()):
        mc.get_embedder("default")

    assert mc.unload_embedder("default") is True
    assert mc.unload_embedder("default") is False  # already unloaded
    assert mc.loaded_embedders() == []


def test_unload_all(tmp_path):
    mc = _make_mc(tmp_path)
    mc._embedders["BAAI/bge-small-en-v1.5"] = MagicMock()
    mc._embedders["other/model"] = MagicMock()
    assert mc.unload_all() == 2
    assert mc.loaded_embedders() == []


# ---------------------------------------------------------------------------
# encode()
# ---------------------------------------------------------------------------


def test_encode_delegates_to_embedder(tmp_path):
    mc = _make_mc(tmp_path)
    repo_id = KNOWN_MODELS["default"]
    _fake_download(mc, repo_id)
    mc._update_manifest(repo_id, mc._model_path(repo_id))

    fake_embedder = MagicMock()
    fake_embedder.embed_texts.return_value = [[0.1, 0.2]]
    with patch("kg_rag.model_coordinator.SentenceTransformerEmbedder", return_value=fake_embedder):
        result = mc.encode(["hello"], model_id="default")

    fake_embedder.embed_texts.assert_called_once_with(["hello"])
    assert result == [[0.1, 0.2]]


# ---------------------------------------------------------------------------
# export_env() / apply_env()
# ---------------------------------------------------------------------------


def test_export_env_keys(tmp_path):
    mc = _make_mc(tmp_path)
    env = mc.export_env()
    assert "KGRAG_MODEL_DIR" in env
    assert "CODEKG_MODEL_DIR" in env
    assert "DOCKG_MODEL_DIR" in env
    assert all(str(mc.model_dir) == v for v in env.values())


def test_apply_env_does_not_override_existing(tmp_path, monkeypatch):
    mc = _make_mc(tmp_path)
    monkeypatch.setenv("KGRAG_MODEL_DIR", "/existing/path")
    mc.apply_env()
    assert os.environ["KGRAG_MODEL_DIR"] == "/existing/path"


# ---------------------------------------------------------------------------
# Manifest persistence
# ---------------------------------------------------------------------------


def test_manifest_persists_across_instances(tmp_path):
    model_dir = tmp_path / "models"
    mc1 = ModelCoordinator(model_dir=model_dir)
    repo_id = KNOWN_MODELS["default"]
    _fake_download(mc1, repo_id)
    mc1._update_manifest(repo_id, mc1._model_path(repo_id))

    mc2 = ModelCoordinator(model_dir=model_dir)
    assert len(mc2.list_cached()) == 1
    assert mc2.list_cached()[0].repo_id == repo_id


def test_corrupt_manifest_recovers(tmp_path):
    model_dir = tmp_path / "models"
    model_dir.mkdir()
    (model_dir / "manifest.json").write_text("NOT JSON {{{")
    mc = ModelCoordinator(model_dir=model_dir)  # should not raise
    assert mc.list_cached() == []


# ---------------------------------------------------------------------------
# get_coordinator() singleton
# ---------------------------------------------------------------------------


def test_get_coordinator_returns_same_instance(tmp_path, monkeypatch):
    monkeypatch.setattr(_mc_mod, "_coordinator", None)
    c1 = get_coordinator(model_dir=tmp_path / "models")
    c2 = get_coordinator()
    assert c1 is c2
    monkeypatch.setattr(_mc_mod, "_coordinator", None)  # reset for other tests
