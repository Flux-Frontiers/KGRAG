"""`kgrag ingest` on a real PDF, end to end through the staging step.

The other ingest tests mock the pipeline, so none of them converted a PDF.
That hid a gap: kgmodule-utils 0.27.0 moved PDF from anydoc to pymupdf4llm,
and kg-rag's ``[ingest]`` extra still named anydoc directly, so a
``kg-rag[ingest]`` install recorded every PDF as failed. These tests convert
a PDF generated at test time and check that the extra comes from the SDK.
"""

from __future__ import annotations

import importlib.metadata as md
import json
from pathlib import Path

import pytest
from click.testing import CliRunner

from kg_rag.cli.main import cli

pymupdf = pytest.importorskip("pymupdf", reason="needs the ingest extra (pymupdf4llm)")
pytest.importorskip("pymupdf4llm", reason="needs the ingest extra (pymupdf4llm)")


def _pdf(path: Path, text: str) -> Path:
    doc = pymupdf.open()
    doc.new_page().insert_text((72, 72), text, fontsize=12)
    doc.save(str(path))
    doc.close()
    return path


def test_ingest_stages_a_real_pdf(tmp_path: Path) -> None:
    src = tmp_path / "src"
    src.mkdir()
    _pdf(src / "paper.pdf", "Disulfide bonds stabilize protein structure.")
    staged = tmp_path / "staged"

    result = CliRunner().invoke(cli, ["ingest", str(src), "--into", str(staged), "--no-build"])

    assert result.exit_code == 0, result.output
    manifest = json.loads((staged / ".ingest" / "manifest.json").read_text(encoding="utf-8"))
    records = manifest["records"]
    records = list(records.values()) if isinstance(records, dict) else records
    (record,) = records
    assert record["status"] == "ingested", record
    assert record["converter"] == "pymupdf4llm"
    text = (staged / record["staged_path"]).read_text(encoding="utf-8")
    assert "Disulfide" in text


def test_ingest_extra_takes_converters_from_the_sdk() -> None:
    """kg-rag[ingest] must pull kgmodule-utils[ingest], not name a converter."""
    reqs = [r.replace(" ", "") for r in md.requires("kg-rag") or []]
    ingest = [r for r in reqs if 'extra=="ingest"' in r]
    assert any(r.startswith("kgmodule-utils[ingest]") for r in ingest), ingest
    assert not any(r.startswith("firecrawl-anydoc") for r in ingest), ingest
