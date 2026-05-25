# Release Notes - v0.8.0

> Released: 2026-05-25

## Added

- **`kgrag export` / `kgrag import` CLI commands**
  (`src/kg_rag/cli/cmd_corpus_io.py`, registered in
  `src/kg_rag/cli/main.py`) — make a registered KG portable as a single
  `.kgrag.tar.gz` archive containing the SQLite graph, LanceDB index, and a
  manifest (`manifest_version`, `name`, `kind`, `version`, `builder_version`,
  `tags`, `metadata`, `exported_at`). `kgrag import` peeks at the manifest,
  unpacks to `~/.kgrag/corpora/<name>/` (or `--dest`), and re-registers the
  KG with `imported` tagged in `metadata`. Supports `--force`, `--name` for
  rename-on-import, and `--no-register` for unpack-only. Mirror tests live
  in `tests/test_cmd_corpus_io.py` (round-trip, manifest-version mismatch,
  collision handling, archive validation).
- **`local/` — local development environment for the KGRAG worker** — complete
  stack for running and testing the worker without a RunPod account:
  - **`local/handler.py`** — RunPod serverless handler configured for local
    use; includes `.diarykg/` bootstrap support and `max_tokens: 2048` for
    synthesis (mirrors the changes made to `runpod/handler.py` this session).
  - **`local/docker-compose.yml`** — mounts GutenbergKG `corpus/` and MetaboKG
    directories, exposes the RunPod serverless API on `http://localhost:8000`,
    and live-reloads `handler.py` from the working tree via a bind mount.
  - **`local/.env.example`** — template `.env`; documents `GUTENBERG_CORPUS`,
    `METABO_REPO`, optional `HANDLER_SECRET`, and Ollama synthesis variables.
  - **`local/chat.py`** — Streamlit chat UI that sends queries to the running
    `kgrag-worker` container and renders synthesized answers with collapsible
    source-hit cards (KG-kind badges, score bars, source paths).
- **`docs/haystacks_to_forests.{md,tex,pdf}`** — public-facing technical
  article (*"We Have Been Building Haystacks When We Need Forests of
  Knowledge Trees"*) framing KGRAG as a federated forest of domain-specific
  knowledge graphs and contrasting it with monolithic-LLM retrieval.
- **`docs/COMPLETE_TECHNICAL_ARTICLE_internal.md`** — internal long-form
  write-up of the prose-to-conversational-memory pipeline (Pepys validation,
  5-phase NLP transformation, direct temporal-DB writes that unblock local
  4B-model execution).

## Changed

- **`poetry.lock`** — dev-dependency refresh (notably `ast-serialize`
  `0.4.0 → 0.5.0`); regenerated after the `0.8.0` version bump in
  `pyproject.toml` / `src/kg_rag/__init__.py`.
- **`src/kg_rag/cli/cmd_corpus_io.py`** — narrow `entry.sqlite_path` /
  `entry.lancedb_path` to non-`None` locals before passing to
  `TarFile.add()`, eliminating two `mypy` `arg-type` errors on the export
  path.

## Fixed

- **`.diarykg/` support in `_bootstrap_registry()`** (`runpod/handler.py`) —
  the bootstrap previously hard-coded `.dockg/graph.sqlite` as the only index
  location; diary books (Pepys, Evelyn Vol 1 & 2, Boswell) were therefore
  invisible to the worker at startup.  The loop now tries `.diarykg/` first,
  then falls back to `.dockg/`, so both diary and standard Gutenberg books are
  registered correctly.

- **`max_tokens` raised 512 → 2048** (`runpod/handler.py`) — synthesis answers
  were being cut off mid-sentence; both `runpod/handler.py` and the new
  `local/handler.py` now pass `"max_tokens": 2048` to the vLLM endpoint.

---

_Full changelog: [CHANGELOG.md](CHANGELOG.md)_
