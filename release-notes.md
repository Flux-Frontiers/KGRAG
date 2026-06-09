# Release Notes - v0.10.0

> Released: 2026-06-09

## Highlights

- Query results can now be scoped directly inside supported KGs, so focused
  questions (for example, one subdirectory/genre in a large corpus) return more
  relevant top hits instead of being drowned out by global matches.
- The orchestrator now threads scope through query and pack operations across
  global, corpus, and person federation paths.
- Dependency constraints were aligned to keep Poetry resolution stable with the
  latest `kgmodule-utils` line.

## Added

- **`QueryScope` primitive** (`src/kg_rag/primitives.py`):
  a frozen, hashable scope object with:
  - `source_path_prefixes`
  - `node_kinds`
  - reserved `metadata_eq`
  - `matches()` helper for post-filtering
- **Scope-aware query APIs in orchestrator** (`src/kg_rag/orchestrator.py`):
  `query`, `pack`, `query_corpus`, and `pack_corpus` now accept optional scope.
- **Scope support in adapter contract** (`src/kg_rag/adapters/base.py`):
  adapter `query`/`pack` signatures accept optional scope, plus
  `supports_scope` capability flag.
- **Pushdown support in DocKG and Gutenberg adapters**:
  `DocKGAdapter` and `GutenbergKGAdapter` forward scope filters into backend
  query/pack operations for in-database filtering.

## Changed

- **Federation internals refactored** (`src/kg_rag/orchestrator.py`):
  shared `_federate_query`, `_federate_pack`, and `_federate_stats` engines now
  power global/corpus/person execution paths.
- **DocKG minimum version raised to `>=0.15.7`** (`pyproject.toml`):
  required for `source_path_prefixes` / `node_kinds` pushdown support.
- **Version bumped to `0.10.0`** (`pyproject.toml`).

## Fixed

- **Poetry resolver conflict with `ty`** (`pyproject.toml`, `poetry.lock`):
  aligned `ty` to `>=0.0.44,<0.0.45` to match `kgmodule-utils >=0.4.0`
  requirements.
- **Graceful compatibility fallback for older adapters**:
  if a backend rejects scoped kwargs, orchestrator retries without scope
  instead of hard failing.

## Validation

- CI-equivalent checks on merged `main` passed:
  - `ruff format --check`
  - `ruff check`
  - `ty check src/`
  - `pytest` (430 passed)

---

Full changelog: [CHANGELOG.md](CHANGELOG.md)
