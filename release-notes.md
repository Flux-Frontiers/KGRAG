# Release Notes -- v0.17.1

> Released: 2026-10-14

A dependency fix that keeps `kgrag ingest` converting PDFs. kgmodule-utils
0.27.0, released the same day, made `pymupdf4llm` the fleet's one PDF
converter. kg-rag's `ingest` extra still named anydoc directly, so an install
with `kg-rag[ingest]` but not `[kg]` recorded every PDF as failed. This
release takes the converters from the SDK's own `[ingest]` extra instead.

## What changed

**Ingest dependencies come from the SDK.** `kg-rag[ingest]` now installs
`kgmodule-utils[ingest]`, so whichever converter the SDK assigns to a format
is installed with it. `kg-rag[all]` names `pymupdf4llm` and anydoc directly,
because Poetry cannot resolve a second `kgmodule-utils[ingest]` declaration
beside the core dependency.

**Three converters.** `kgrag ingest` converts PDF with `pymupdf4llm` (the
same call `dockg build` makes), office formats with anydoc, and `.tex` and
`.html` with `pandoc` when the `pandoc` program is installed. The help text
and the CLI and ingestion guides say so.

**A test that converts a real PDF.** Every earlier ingest test mocked the
pipeline, which is how the gap went unseen. A new test runs `kgrag ingest`
on a generated PDF, and another checks that the `ingest` extra comes from
the SDK.

**Newer floors.** kgmodule-utils 0.27.0 and vault-kg 0.3.0.

## Upgrading

```bash
pip install -U "kg-rag[ingest]"
```

Re-run `kgrag ingest` on any corpus whose PDFs were recorded as failed with
"pymupdf4llm is not installed". Install `pandoc` to ingest LaTeX and HTML.

---

_Full changelog: [CHANGELOG.md](CHANGELOG.md)_
