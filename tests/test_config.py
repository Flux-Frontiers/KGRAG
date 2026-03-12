"""
test_config.py

Unit tests for kg_rag.config.load_kgrag_config.
"""
from __future__ import annotations

from pathlib import Path

import pytest

from kg_rag.config import load_kgrag_config


class TestLoadKgragConfig:
    def test_no_pyproject_returns_empty(self, tmp_path):
        result = load_kgrag_config(tmp_path)
        assert result == {}

    def test_pyproject_without_kgrag_section(self, tmp_path):
        (tmp_path / "pyproject.toml").write_text(
            "[tool.poetry]\nname = 'myproject'\n", encoding="utf-8"
        )
        result = load_kgrag_config(tmp_path)
        assert result == {}

    def test_pyproject_with_kgrag_section(self, tmp_path):
        (tmp_path / "pyproject.toml").write_text(
            '[tool.kgrag]\ninclude = ["src"]\n', encoding="utf-8"
        )
        result = load_kgrag_config(tmp_path)
        assert result == {"include": ["src"]}

    def test_pyproject_with_multiple_tool_sections(self, tmp_path):
        content = (
            "[tool.poetry]\nname = 'foo'\n\n"
            '[tool.kgrag]\ninclude = ["src"]\nexclude = ["tests"]\n'
        )
        (tmp_path / "pyproject.toml").write_text(content, encoding="utf-8")
        result = load_kgrag_config(tmp_path)
        assert result["include"] == ["src"]
        assert result["exclude"] == ["tests"]

    def test_defaults_to_cwd(self, tmp_path, monkeypatch):
        (tmp_path / "pyproject.toml").write_text(
            '[tool.kgrag]\nfoo = "bar"\n', encoding="utf-8"
        )
        monkeypatch.chdir(tmp_path)
        result = load_kgrag_config()
        assert result.get("foo") == "bar"

    def test_string_path_accepted(self, tmp_path):
        (tmp_path / "pyproject.toml").write_text(
            '[tool.kgrag]\nx = 1\n', encoding="utf-8"
        )
        result = load_kgrag_config(str(tmp_path))
        assert result.get("x") == 1
