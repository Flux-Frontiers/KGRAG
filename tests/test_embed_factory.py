"""Tests for kg_rag.embed.make_embedder — backend dispatch from [tool.kgrag] config.

The TEI branch is exercised with a stubbed HTTP layer, so no server and no
torch are needed.
"""

# pylint: disable=missing-function-docstring

from __future__ import annotations

import io
import json
import sys
from typing import Any
from unittest.mock import patch

import pytest

from kg_rag.embed import make_embedder

kg_utils_embedder = pytest.importorskip("kg_utils.embedder", reason="kgmodule-utils not installed")

if not hasattr(kg_utils_embedder, "TEIEmbedder"):  # pragma: no cover
    pytest.skip("installed kgmodule-utils predates TEIEmbedder", allow_module_level=True)


def _urlopen_stub(*payloads: Any):
    """Return a urlopen replacement replaying *payloads* as JSON responses."""
    queue = list(payloads)

    def _open(req: Any, timeout: float | None = None) -> io.BytesIO:  # noqa: ARG001
        nxt = queue.pop(0) if queue else []
        return io.BytesIO(json.dumps(nxt).encode())

    return _open


# ---------------------------------------------------------------------------
# Dispatch
# ---------------------------------------------------------------------------


def test_no_backend_returns_none() -> None:
    """No embed_backend means each KG library uses its own default."""
    assert make_embedder({}) is None


def test_unknown_backend_raises_and_lists_supported() -> None:
    with pytest.raises(ValueError, match="Unknown embed_backend") as exc:
        make_embedder({"embed_backend": "nope"})
    for name in ("sentence_transformers", "llama", "tei"):
        assert name in str(exc.value)


def test_llama_without_model_path_raises(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delenv("KGRAG_LLAMA_MODEL", raising=False)
    with pytest.raises(ValueError, match="llama_model_path"):
        make_embedder({"embed_backend": "llama"})


# ---------------------------------------------------------------------------
# TEI branch
# ---------------------------------------------------------------------------


def test_tei_uses_configured_endpoint_without_probing() -> None:
    """tei_dim short-circuits the startup probe, so construction is offline."""
    with patch("kg_utils.embedder.urlopen", side_effect=AssertionError("network!")):
        emb = make_embedder(
            {"embed_backend": "tei", "tei_endpoint": "http://tei:8080", "tei_dim": 384}
        )

    assert isinstance(emb, kg_utils_embedder.TEIEmbedder)
    assert emb.endpoint == "http://tei:8080"
    assert emb.dim == 384


def test_tei_falls_back_to_env_endpoint(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("KG_EMBED_ENDPOINT", "http://from-env:8080")
    with patch("kg_utils.embedder.urlopen", side_effect=AssertionError("network!")):
        emb = make_embedder({"embed_backend": "tei", "tei_dim": 384})
    assert emb.endpoint == "http://from-env:8080"


def test_tei_probes_when_dim_absent() -> None:
    with patch(
        "kg_utils.embedder.urlopen",
        _urlopen_stub({"max_client_batch_size": 64}, [[0.0] * 384]),
    ):
        emb = make_embedder({"embed_backend": "tei", "tei_endpoint": "http://tei:8080"})

    assert emb.dim == 384
    assert emb.max_batch == 64


def test_tei_passes_through_tuning_options() -> None:
    with patch("kg_utils.embedder.urlopen", side_effect=AssertionError("network!")):
        emb = make_embedder(
            {
                "embed_backend": "tei",
                "tei_endpoint": "http://tei:8080",
                "tei_dim": 768,
                "tei_api_key": "dummy-token",  # pragma: allowlist secret
                "tei_model": "BAAI/bge-base-en-v1.5",
                "tei_timeout": 30.0,
                "tei_max_retries": 5,
                "tei_max_batch": 16,
            }
        )

    assert (emb.api_key, emb.model_name) == ("dummy-token", "BAAI/bge-base-en-v1.5")
    assert (emb.timeout, emb.max_retries, emb.max_batch) == (30.0, 5, 16)


def test_tei_reports_missing_dependency_clearly() -> None:
    """A too-old kgmodule-utils must name the fix, not surface a bare ImportError."""
    with patch.dict(sys.modules, {"kg_utils.embedder": None}):
        with pytest.raises(ImportError, match="pip install -U kgmodule-utils"):
            make_embedder({"embed_backend": "tei", "tei_endpoint": "http://tei:8080"})
