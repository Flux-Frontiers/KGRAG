# Document Ingestion

This document describes how KGRAG turns loose source documents — PDFs, Word
files, EPUBs, spreadsheets, slide decks, plain Markdown — into a registered,
queryable knowledge graph.

Ingestion is the stage *in front of* every KG builder.  Before it existed a
corpus had to already be Markdown or plain text on disk; `dockg build` walked a
directory and indexed whatever was already in a format it understood.  The
ingestion pipeline supplies the missing front end: it converts heterogeneous
sources into a **staging corpus** that the existing builders consume unchanged.

---

## Overview

The pipeline has three stages, each independently skippable:

| Stage | What it does | Where it lives |
|-------|--------------|----------------|
| **stage** | Convert sources to Markdown, write a staging corpus, record provenance | `kg_utils.ingest` (kgmodule-utils) |
| **build** | Run `dockg build` over the staged corpus | shelled out from `kgrag ingest` |
| **register** | Record the built KG in the KGRAG registry | `kg_rag.registry` |

Two design decisions shape everything below.

**The staged corpus is materialized, not streamed.**  Conversion writes real
`.md` files to disk rather than feeding nodes straight into a graph.  This
costs a second copy of the corpus as text, and buys three things: the
intermediate is inspectable and diffable, a rebuild does not require
re-conversion, and **no builder internals had to change** to gain multi-format
ingestion.  DocKG, MemoryKG and every other `KGModule` get it for free.

**Every file examined is accounted for.**  Not just the ones that convert.  A
corpus that quietly omits three PDFs is indistinguishable from one that was
never shown them, so each run writes a manifest recording what it staged,
skipped, and failed on — with reasons.

---

## Pipeline

```
Sources: ~/Documents/specs/, report.pdf, notes.docx, …
        │
        ▼
┌─ stage ─────────────────────────────────────────────────┐
│ IngestPipeline.run()                                    │
│   ├─ Walk sources        (dirs recursively, SKIP_DIRS   │
│   │                       and dotfiles pruned)          │
│   ├─ For each file:                                     │
│   │    ├─ sha256(source bytes)      → dedup key         │
│   │    ├─ resolve converter         → passthrough|anydoc│
│   │    ├─ convert                   → Markdown          │
│   │    └─ write staged file         → collision-safe    │
│   └─ Write manifest                 → .ingest/          │
└─────────────────────────────────────────────────────────┘
        │
        ▼
   Staging corpus/
     ├─ guide.md          (was guide.md      — passthrough)
     ├─ notes.txt         (was notes.txt     — suffix preserved)
     ├─ paper.md          (was paper.pdf     — anydoc)
     ├─ parts.md          (was parts.csv     — anydoc)
     └─ .ingest/manifest.json
        │
        ▼
┌─ build ─────────────────────────────────────────────────┐
│ dockg build --repo <staging>                            │
│   → document / section / chunk / entity nodes           │
│   → .dockg/graph.sqlite + vectors.sqlite                │
└─────────────────────────────────────────────────────────┘
        │
        ▼
┌─ register ──────────────────────────────────────────────┐
│ KGRegistry.register(KGEntry(kind=doc, …))               │
│   optionally: CorpusRegistry.add_kg(--corpus NAME)      │
└─────────────────────────────────────────────────────────┘
        │
        ▼
   kgrag query "…"   ·   kgrag pack "…"   ·   MCP tools
```

---

## Stage 1 — Conversion

A **converter** turns one source file into Markdown plus the provenance needed
to reproduce that conversion.  Converters are tried in order, most specific
first; the first one whose `handles()` returns `True` wins.

### `PassthroughConverter`

Already-textual formats.  Bytes are decoded, not transformed.

| Extension | Staged as |
|-----------|-----------|
| `.md` | `.md` |
| `.markdown` | `.md` |
| `.txt` | `.txt` |
| `.rst` | `.rst` |

**The source suffix is preserved deliberately.**  A `.txt` stays `.txt` rather
than becoming `.md`, because DocKG parses the two differently — headings for
Markdown, flat for text.  Promoting flat text to Markdown would invent a
heading hierarchy the document never had.

Undecodable bytes are replaced rather than raising: a mostly-readable document
is worth more to a corpus than a dropped one, and the substitution is visible
in the staged output.

### `AnydocConverter`

Everything else, via [anydoc](https://github.com/firecrawl/anydoc) (PyPI:
`firecrawl-anydoc`) — a Rust library with Python bindings that emits consistent
GitHub-Flavored Markdown across formats.

| Family | Extensions |
|--------|-----------|
| Word | `.doc` `.docx` `.docm` |
| PowerPoint | `.ppt` `.pps` `.pot` `.pptx` `.pptm` `.ppsx` `.ppsm` |
| Excel | `.xls` `.xlsx` `.xlsm` `.xlsb` |
| OpenDocument | `.odt` `.ods` `.odp` |
| Other | `.rtf` `.epub` `.csv` `.pdf` |

21 extensions, all staged as `.md`.  Conversion is fast — a 40-page text PDF
converts in roughly 20 ms.

The `anydoc` import is **lazy**, deferred to first use.  This keeps the
`kgmodule-utils` core install dependency-free and lets
`supported_extensions()` answer without the optional dependency present.

### Failure modes

Nothing is dropped silently.  Every outcome produces a manifest record.

| Situation | Status | Reason recorded |
|-----------|--------|-----------------|
| No converter handles the suffix | `skipped` | `unsupported format: .jpeg` |
| `anydoc` rejects the file | `failed` | `MalformedError: …`, `EncryptedError: …`, … |
| Conversion yields empty output | `failed` | `converted to empty output (likely a scanned/image-only document needing OCR)` |
| Source unreadable | `failed` | `cannot read source: …` |
| Staged file unwritable | `failed` | `cannot write staged file: …` |
| `anydoc` not installed | `failed` | install hint for the `ingest` extra |

All five `anydoc` exception types (`UnsupportedError`, `MalformedError`,
`EncryptedError`, `ResourceLimitError`, `MissingPartError`) are wrapped as
`ConversionError` with the original type name preserved in the reason.

---

## Staging layout

Sources are flattened into the staging root; the source's own filename is kept
so the corpus stays readable.

```
<staging_root>/
    guide.md
    notes.txt
    report.md
    report-a1b2c3d4.md          ← different document, same basename
    .ingest/
        manifest.json
```

Filename stems are sanitised (`[^A-Za-z0-9._-]+` → `-`).  When two **different**
documents would land on the same staged name, the second gets a short digest
suffix rather than overwriting the first; in the pathological case of a shared
stem *and* shared digest prefix, the full digest is used.

A digest that already has a record owns its staged path and reuses it, so
re-staging a deleted file restores the original name instead of colliding with
the entry it replaces.

### Walk rules

- Directories are walked recursively; named files are always included, even if
  their suffix is unsupported — naming a file and getting no explanation is
  impossible by construction.
- Pruned directories: `.git` `.hg` `.svn` `.venv` `venv` `node_modules`
  `__pycache__` `.mypy_cache` `.pytest_cache` `.ruff_cache` `.ingest`, plus any
  dotted directory.
- Dotfiles are skipped.
- Symlinked directories are not followed by default (a symlink loop would
  otherwise walk forever).
- A staging root nested inside a source tree is never fed its own output.

---

## The manifest

The provenance ledger, at `<staging_root>/.ingest/manifest.json`.  Plain JSON —
diffable in review, readable without this library, written atomically so an
interrupted run cannot leave a half-written ledger.

### Record schema

| Field | Meaning |
|-------|---------|
| `source_path` | Absolute path of the source document |
| `sha256` | Hex digest of the source **bytes** — the dedup key |
| `size_bytes` | Source size |
| `status` | `ingested` · `skipped` · `failed` |
| `staged_path` | Staging-root-relative path of the written file; empty unless ingested |
| `converter` | `passthrough` or `anydoc` |
| `converter_version` | Version of the converting library, for reproducibility |
| `reason` | Why a file was skipped or failed; empty when ingested |
| `ingested_at` | ISO 8601 UTC timestamp |
| `metadata` | Converter extras, e.g. `{"source_format": "pdf"}` |

### Example

```json
{
  "manifest_version": 1,
  "updated_at": "2026-08-18T03:21:08+00:00",
  "records": [
    {
      "source_path": "/corpora/src/paper.pdf",
      "sha256": "c7734dc332fa871a9b4231112fbcad448dfec64397e7cfa7cd8899c2ac2fc7b5",
      "size_bytes": 271065,
      "status": "ingested",
      "staged_path": "paper.md",
      "converter": "anydoc",
      "converter_version": "0.1.9",
      "reason": "",
      "ingested_at": "2026-08-18T03:21:08+00:00",
      "metadata": { "source_format": "pdf" }
    },
    {
      "source_path": "/corpora/src/photo.jpeg",
      "sha256": "0409f016cf09c9e58b468001287d6a49554a6a10da2da57a9a1c1ae43df1960b",
      "size_bytes": 400,
      "status": "skipped",
      "staged_path": "",
      "converter": "",
      "converter_version": "",
      "reason": "unsupported format: .jpeg",
      "ingested_at": "2026-08-18T03:21:08+00:00",
      "metadata": {}
    },
    {
      "source_path": "/corpora/src/scan.pdf",
      "sha256": "65e36298f893122ce79f9d5b237ce5a4f4b62bb7c967485cdd94272df242d2d7",
      "size_bytes": 14,
      "status": "failed",
      "staged_path": "",
      "converter": "anydoc",
      "converter_version": "",
      "reason": "MalformedError: malformed document: not a PDF: file appears to be plain text",
      "ingested_at": "2026-08-18T03:21:08+00:00",
      "metadata": {}
    }
  ]
}
```

### Reading it back

```python
from kg_utils.ingest import IngestPipeline

pipeline = IngestPipeline(staging_root="corpora/specs")

for record in pipeline.manifest().problems():
    print(f"{record.source_path}: {record.status} — {record.reason}")
```

`problems()` returns exactly the documents the KG does **not** contain, and
why.  `summary()` returns counts by status.

### Robustness

- A corrupt or unreadable manifest yields an **empty** manifest rather than
  raising.  The staged files are still on disk; a fresh ledger lets the next
  run rebuild rather than dead-end.
- Unknown record keys are ignored on load, so a manifest written by a newer
  version stays loadable by an older one.

---

## Re-run semantics

A run **rebuilds the staged corpus from nothing** by default.  `--update`
(`update=True`) selects the incremental path.

This matches the contract the fleet's builders already use — `dockg build` /
`dockg build --update`, `pycodekg build` / `pycodekg update` — where the wipe is
implicit and the incremental path is the named opt-in.

| | Default (rebuild) | `--update` |
|---|---|---|
| Staging corpus | Deleted first | Kept |
| Already-converted sources | Re-converted | Skipped by digest |
| Source deleted upstream | Disappears from corpus | **Staged copy retained** |
| Converter upgrade | Picked up automatically | Needs a default run |
| Cost | Full re-conversion | Only what is new |

Defaulting to a rebuild is what keeps the corpus honest, for the same reason
pycode_kg gave when it made the equivalent change: it eliminates the phantom
footgun where deleted or renamed sources silently persist.  Observed directly:

```
initial staged : ['guide.md', 'notes.md', 'paper.md']
deleted guide.md upstream
after --update  : ['guide.md', 'notes.md', 'paper.md']   ← orphan retained
after default   : ['notes.md', 'paper.md']               ← orphan gone
```

### Deduplication

Keyed on the SHA-256 of source **bytes**, not the filename, so the same
document arriving twice under different names is ingested once.

Dedup needs no flag of its own.  A rebuild starts from an empty manifest, so a
single unconditional check against it deduplicates *within* a run and, in
update mode, *across* runs.

---

## CLI

```bash
kgrag ingest SOURCE... --into PATH [OPTIONS]
```

| Option | Default | Effect |
|--------|---------|--------|
| `--into PATH` | *required* | Staging corpus directory |
| `--name NAME` | `<staging-dir>-doc` | Name to register the KG under |
| `--update` | off | Incremental — keep existing staged documents |
| `--build` / `--no-build` | build | Run `dockg build` |
| `--register` / `--no-register` | register | Write to the KGRAG registry |
| `--corpus NAME` | — | Add the registered KG to an existing corpus |
| `--show-skipped` / `--no-show-skipped` | show | Print the "Not ingested" table |
| `--registry PATH` | `$KGRAG_REGISTRY` | Registry override |

### Examples

```bash
# A directory of mixed formats
kgrag ingest ~/Documents/specs --into ~/corpora/specs

# Named files, registered under a chosen name
kgrag ingest report.pdf notes.docx --into ~/corpora/mixed --name mixed-docs

# Convert only — no build, no registry write
kgrag ingest ~/Downloads --into ~/corpora/inbox --no-build

# Add the result to an existing corpus in the same run
kgrag ingest ~/papers --into ~/corpora/papers --corpus research

# Incremental: convert only what is new
kgrag ingest ~/papers --into ~/corpora/papers --update
```

### Output

Documents that could not be ingested are reported, not dropped:

```
────────────── stage — converting sources to Markdown ──────────────
  5 staged · 1 skipped · 1 failed (of 7 examined)

                          Not ingested
╭────────────┬─────────┬──────────────────────────────────────────╮
│ Document   │ Status  │ Reason                                   │
├────────────┼─────────┼──────────────────────────────────────────┤
│ photo.jpeg │ skipped │ unsupported format: .jpeg                │
│ scan.pdf   │ failed  │ MalformedError: not a PDF: file appears  │
│            │         │ to be plain text                         │
╰────────────┴─────────┴──────────────────────────────────────────╯
```

### Degradation

- `dockg` missing from `PATH` → build is skipped with an install hint; staging
  still completes and the manifest is written.
- Build fails → nothing is registered (there is no successful build to point a
  registry entry at).
- Nothing staged **and** the corpus is empty → the run stops before build
  rather than building an empty KG.

---

## Library API

The staging half is usable directly, independent of KGRAG:

```python
from kg_utils.ingest import IngestPipeline

pipeline = IngestPipeline(staging_root="corpora/specs")
stats = pipeline.run(["~/Documents/specs", "handbook.docx"])

print(f"{stats.ingested} staged, {stats.skipped} skipped, {stats.failed} failed")
```

Then build over the staged corpus as usual: `dockg build --repo corpora/specs`.

| Symbol | Purpose |
|--------|---------|
| `IngestPipeline(staging_root, converters=, skip_dirs=, follow_symlinks=)` | The pipeline |
| `.run(sources, update=False, on_progress=None)` → `IngestStats` | Execute a run |
| `.manifest()` → `IngestManifest` | Read the ledger on disk |
| `ingest(sources, staging_root, …)` → `IngestStats` | One-call form |
| `Converter` / `ConversionResult` / `ConversionError` | Converter protocol |
| `PassthroughConverter` / `AnydocConverter` | Shipped converters |
| `supported_extensions()` → `frozenset[str]` | All 25 accepted suffixes |
| `IngestRecord` / `IngestManifest` / `IngestStats` | Provenance types |

`on_progress` is called with `(source_path, record)` after each file — for
progress bars and logging.

### Custom converters

`Converter` is a `Protocol`: implement `name`, `handles(path)` and
`convert(path)` returning a `ConversionResult`, then pass a chain to
`IngestPipeline(converters=[...])`.  Order matters — most specific first.

---

## Installation

Conversion of non-textual formats needs the optional extra.  Markdown, plain
text and reStructuredText ingest with **no extra dependency at all**.

```bash
pip install 'kg-rag[ingest]'            # via KGRAG
pip install 'kgmodule-utils[ingest]'    # library only
```

`kgrag ingest` requires `kg_utils.ingest`, which ships in kgmodule-utils
0.17.0.  While that release is pending on PyPI the import is guarded and
reports the upgrade command rather than a traceback.

---

## Limitations

**No OCR.**  `anydoc` extracts text layers; it does not read pixels.  Scanned
and image-only PDFs are recorded as failed with a reason naming OCR as the
cause, which makes the manifest a queryable worklist if an OCR stage is added
later.

**Images are not extracted.**  Figures inside converted documents are dropped;
only text and tables survive into Markdown.

**The staged corpus is flat.**  Source directory structure is not mirrored into
the staging root, so provenance for "which folder did this come from" lives in
the manifest's `source_path` rather than in the layout.

**Disk cost.**  Materializing means roughly a second copy of the corpus as
text, on top of the graph and vector index.

**`converter_version` is not recorded on failed records.**  Successful records
carry it; a failure notes the converter but not its version, so "which version
rejected this file" is not answerable from the manifest alone.

---

## See also

- [CLI_REFERENCE.md](CLI_REFERENCE.md) — `kgrag ingest` in the full command reference
- [SEMANTIC_CHUNKING.md](SEMANTIC_CHUNKING.md) — what happens to staged text once DocKG indexes it
- [KGMODULE.md](KGMODULE.md) — the builder contract the staging corpus feeds
- [ADAPTER_SPEC.md](ADAPTER_SPEC.md) — how a registered KG is queried
