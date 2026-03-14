"""
conftest.py

Shared fixtures for the KGRAG test suite.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from kg_rag.primitives import KGEntry, KGKind
from kg_rag.registry import KGRegistry


@pytest.fixture
def tmp_registry(tmp_path: Path) -> KGRegistry:
    """Isolated in-memory registry backed by a temp SQLite file."""
    reg = KGRegistry(db_path=tmp_path / "test_registry.sqlite")
    yield reg
    reg.close()


@pytest.fixture
def sample_entry(tmp_path: Path) -> KGEntry:
    """A minimal KGEntry pointing at real (temp) paths."""
    repo = tmp_path / "myrepo"
    repo.mkdir()
    venv = repo / ".venv"
    venv.mkdir()
    return KGEntry(
        name="my-code",
        kind=KGKind.CODE,
        repo_path=repo,
        venv_path=venv,
    )


@pytest.fixture
def built_entry(tmp_path: Path) -> KGEntry:
    """A KGEntry whose sqlite_path actually exists (is_built=True)."""
    repo = tmp_path / "builtrepo"
    repo.mkdir()
    venv = repo / ".venv"
    venv.mkdir()
    db_dir = repo / ".codekg"
    db_dir.mkdir()
    sqlite = db_dir / "graph.sqlite"
    sqlite.touch()
    return KGEntry(
        name="built-code",
        kind=KGKind.CODE,
        repo_path=repo,
        venv_path=venv,
        sqlite_path=sqlite,
    )
