"""
conftest.py

Shared fixtures for the KGRAG test suite.
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

import pytest

from kg_rag.primitives import KGEntry, KGKind
from kg_rag.registry import KGRegistry


@pytest.fixture(autouse=True)
def no_embedder_downloads():
    """Keep the unit suite off the HuggingFace Hub.

    :class:`~kg_rag.orchestrator.KGRAG` resolves its shared embedder on the
    first adapter that needs one, and this repo configures
    ``embed_backend = "sentence_transformers"``, so that resolution would
    download ~130 MB on any machine (and every CI run) with a cold model
    cache. Every test that gets that far mocks its adapters, so ``None`` --
    the documented "let each KG use its own default embedder" answer -- is
    the faithful stand-in. Tests that assert on resolution itself patch this
    same target inside the test, which takes precedence.
    """
    with patch("kg_rag.orchestrator.make_embedder", return_value=None):
        yield


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
    db_dir = repo / ".pycodekg"
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
