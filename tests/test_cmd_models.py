"""
test_cmd_models.py

Tests for ``kgrag models`` — centralized model cache management CLI.

Every command creates its own ``ModelCoordinator`` internally, so tests
either work against a real coordinator backed by a ``--model-dir`` temp
directory (populating its manifest directly, as
``test_model_coordinator.py`` does), or patch ``ModelCoordinator._download``
/ ``SentenceTransformerEmbedder`` at the class/module level so any instance
the CLI constructs picks up the fake behavior — no network access, no
heavyweight model loads.
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

from click.testing import CliRunner

from kg_rag.cli.main import cli
from kg_rag.model_coordinator import KNOWN_MODELS, ModelCoordinator

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _model_dir_opt(tmp_path: Path) -> list[str]:
    return ["--model-dir", str(tmp_path / "models")]


def _fake_download(mc: ModelCoordinator, repo_id: str) -> Path:
    """Simulate a successful download by creating the model directory."""
    local = mc._model_path(repo_id)
    local.mkdir(parents=True, exist_ok=True)
    (local / "config.json").write_text("{}")
    return local


def _precache(tmp_path: Path, repo_id: str = KNOWN_MODELS["default"]) -> ModelCoordinator:
    """Pre-populate a coordinator's manifest so it looks already cached."""
    mc = ModelCoordinator(model_dir=tmp_path / "models")
    local = _fake_download(mc, repo_id)
    mc._update_manifest(repo_id, local)
    return mc


def _download_side_effect(repo_id: str, local_path: Path) -> None:
    """``ModelCoordinator._download`` replacement for class-level patching.

    The CLI constructs its own ``ModelCoordinator`` internally, so the patch
    target is the class attribute rather than a specific instance. A
    ``MagicMock`` assigned onto a class is not a descriptor, so accessing it
    through ``self._download(...)`` does *not* bind ``self`` -- only the two
    explicit call args (``repo_id``, ``local_path``) arrive here.
    """
    local_path.mkdir(parents=True, exist_ok=True)
    (local_path / "config.json").write_text("{}")


ENV200 = {"COLUMNS": "200"}


# ---------------------------------------------------------------------------
# list
# ---------------------------------------------------------------------------


class TestListModels:
    def test_empty_cache_shows_hint(self, tmp_path):
        result = CliRunner().invoke(cli, ["models", "list"] + _model_dir_opt(tmp_path))
        assert result.exit_code == 0, result.output
        assert "No models cached yet." in result.output
        assert "Cache directory:" in result.output
        assert "kgrag models download" in result.output

    def test_lists_cached_model_with_size_and_path(self, tmp_path):
        mc = _precache(tmp_path)
        result = CliRunner().invoke(cli, ["models", "list"] + _model_dir_opt(tmp_path), env=ENV200)
        assert result.exit_code == 0, result.output
        assert KNOWN_MODELS["default"] in result.output
        assert "MB" in result.output
        assert str(mc.model_dir) in result.output
        assert "Total:" in result.output


# ---------------------------------------------------------------------------
# download
# ---------------------------------------------------------------------------


class TestDownloadModel:
    def test_known_alias_prints_resolution_and_caches(self, tmp_path):
        with patch.object(ModelCoordinator, "_download", side_effect=_download_side_effect):
            result = CliRunner().invoke(
                cli,
                ["models", "download", "default"] + _model_dir_opt(tmp_path),
                env=ENV200,
            )
        assert result.exit_code == 0, result.output
        assert "Alias" in result.output
        assert KNOWN_MODELS["default"] in result.output
        assert "Model cached at:" in result.output
        assert "Total cache size:" in result.output

    def test_full_repo_id_skips_alias_message(self, tmp_path):
        with patch.object(ModelCoordinator, "_download", side_effect=_download_side_effect):
            result = CliRunner().invoke(
                cli,
                ["models", "download", "some-org/some-model"] + _model_dir_opt(tmp_path),
                env=ENV200,
            )
        assert result.exit_code == 0, result.output
        assert "Alias" not in result.output
        assert "some-org/some-model" in result.output


# ---------------------------------------------------------------------------
# remove
# ---------------------------------------------------------------------------


class TestRemoveModel:
    def test_removes_cached_model(self, tmp_path):
        _precache(tmp_path)
        result = CliRunner().invoke(cli, ["models", "remove", "default"] + _model_dir_opt(tmp_path))
        assert result.exit_code == 0, result.output
        assert "Removed default" in result.output

    def test_reports_not_found_for_unknown_model(self, tmp_path):
        result = CliRunner().invoke(
            cli, ["models", "remove", "nonexistent/model"] + _model_dir_opt(tmp_path)
        )
        assert result.exit_code == 0, result.output
        assert "not found in cache" in result.output


# ---------------------------------------------------------------------------
# path
# ---------------------------------------------------------------------------


class TestModelPath:
    def test_prints_cached_path(self, tmp_path):
        mc = _precache(tmp_path)
        result = CliRunner().invoke(cli, ["models", "path", "default"] + _model_dir_opt(tmp_path))
        assert result.exit_code == 0, result.output
        assert result.output.strip() == str(mc._model_path(KNOWN_MODELS["default"]))

    def test_downloads_when_not_cached(self, tmp_path):
        with patch.object(ModelCoordinator, "_download", side_effect=_download_side_effect):
            result = CliRunner().invoke(
                cli, ["models", "path", "default"] + _model_dir_opt(tmp_path)
            )
        assert result.exit_code == 0, result.output
        assert "bge-small-en-v1.5" in result.output


# ---------------------------------------------------------------------------
# env
# ---------------------------------------------------------------------------


class TestShowEnv:
    def test_prints_export_lines_for_all_keys(self, tmp_path):
        result = CliRunner().invoke(cli, ["models", "env"] + _model_dir_opt(tmp_path), env=ENV200)
        assert result.exit_code == 0, result.output
        assert "export KGRAG_MODEL_DIR=" in result.output
        assert "export CODEKG_MODEL_DIR=" in result.output
        assert "export DOCKG_MODEL_DIR=" in result.output
        assert str(tmp_path / "models") in result.output


# ---------------------------------------------------------------------------
# aliases
# ---------------------------------------------------------------------------


class TestShowAliases:
    def test_lists_all_known_aliases_and_default(self):
        result = CliRunner().invoke(cli, ["models", "aliases"])
        assert result.exit_code == 0, result.output
        for alias, repo_id in KNOWN_MODELS.items():
            assert alias in result.output
            assert repo_id in result.output
        assert "Default:" in result.output
        assert KNOWN_MODELS["default"] in result.output


# ---------------------------------------------------------------------------
# cleanup
# ---------------------------------------------------------------------------


class TestCleanupModels:
    def test_removes_orphan_directory(self, tmp_path):
        mc = ModelCoordinator(model_dir=tmp_path / "models")
        orphan = mc.model_dir / "orphan-dir"
        orphan.mkdir(parents=True)
        result = CliRunner().invoke(cli, ["models", "cleanup"] + _model_dir_opt(tmp_path))
        assert result.exit_code == 0, result.output
        assert "Removed 1 orphan directory." in result.output
        assert not orphan.exists()

    def test_reports_no_orphans_found(self, tmp_path):
        result = CliRunner().invoke(cli, ["models", "cleanup"] + _model_dir_opt(tmp_path))
        assert result.exit_code == 0, result.output
        assert "No orphan directories found." in result.output


# ---------------------------------------------------------------------------
# test-embed
# ---------------------------------------------------------------------------


class TestTestEmbed:
    def test_prints_dimensions_values_and_norm(self, tmp_path):
        _precache(tmp_path)
        fake_embedder = MagicMock()
        fake_embedder.embed_texts.return_value = [[0.1, 0.2, 0.3, 0.4]]

        with patch(
            "kg_rag.model_coordinator.SentenceTransformerEmbedder", return_value=fake_embedder
        ):
            result = CliRunner().invoke(
                cli,
                ["models", "test-embed", "hello world", "--model-id", "default"]
                + _model_dir_opt(tmp_path),
            )
        assert result.exit_code == 0, result.output
        assert "Model:" in result.output
        assert KNOWN_MODELS["default"] in result.output
        assert "Dimensions:" in result.output
        assert "4" in result.output
        assert "First 8 values:" in result.output
        assert "Norm:" in result.output
