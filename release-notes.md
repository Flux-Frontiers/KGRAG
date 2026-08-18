# Release Notes — v0.13.0

> Released: 2026-08-18

This release gives KGRAG a front door for documents that don't start life as
Markdown. `kgrag ingest` takes PDFs, Word files, EPUBs, spreadsheets, and slide
decks straight to a registered, queryable KG in one command, and a new TEI
embedding backend lets the embedding step run outside the client process
entirely.

## What changed

**`kgrag ingest` — loose documents to a registered KG, in one command.**
Point it at a directory of mixed formats, or a handful of specific files, and
it stages them to Markdown, builds a DocKG over the result, and registers
that KG — the staging, build, and register stages are each independently
skippable, so the command doubles as a pure converter when that's all you
need. Documents that can't be converted are reported by name and reason
rather than silently dropped, and `--corpus NAME` folds the result into an
existing corpus in the same run. A run rebuilds the staged corpus from
nothing by default, matching the wipe-by-default convention the rest of the
fleet's builders already use; `--update` opts into the incremental path
instead. Conversion itself comes from `kg_utils.ingest` (kgmodule-utils
0.17.0), so this capability is shared with every other KGModule builder
rather than living as a private copy here.

**An embedding backend that doesn't need torch in the client.** Setting
`embed_backend = "tei"` routes embedding calls to a Text Embeddings Inference
server instead of loading a model in-process — no torch, no
sentence-transformers, and a client footprint of roughly 176 MiB instead of
1.5 GiB RSS. It's roughly half the throughput of in-process CPU embedding, so
it isn't the default, but the vectors it produces are interchangeable with
the sentence-transformers backend (cosine similarity ≥ 0.999997), so
switching backends doesn't require re-embedding anything already indexed.
See `docs/TEI_EVALUATION.md` for the full evaluation.

**Housekeeping.** The `kgmodule-utils` floor moves to `>=0.17.0` for the
ingest support, and backend dispatch — including the TEI path — now has
dedicated test coverage.

## Upgrading

Run `poetry update` (or reinstall) to pick up `kgmodule-utils >=0.17.0`. If
you want document ingestion, install the `ingest` extra
(`pip install -U 'kgmodule-utils[ingest]'` reports this automatically when
it's missing). Everything else is opt-in: existing embedding configuration is
unaffected unless you set `embed_backend = "tei"` explicitly.

---

_Full changelog: [CHANGELOG.md](CHANGELOG.md)_
