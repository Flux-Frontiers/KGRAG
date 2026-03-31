# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- `src/kg_rag/cli/cmd_synthesize.py` — new `kgrag synthesize` CLI command: query
  registered KGs (or a named corpus) and stream an answer from a local Ollama model,
  with optional context display and configurable top-K snippet retrieval.
- `src/kg_rag/app.py` — Streamlit **Synthesize** tab: interactive RAG interface
  backed by `kgrag synthesize`, allowing corpus-scoped queries and Ollama streaming
  from the web UI.
- `docs/` — moved vision and roadmap documents (`ADAPTERS_ROADMAP.md`,
  `AGENTKGKG_IN_CLAUDE_VISION.md`, `OPEN_KNOWLEDGE_INSTITUTE_VISION.md`,
  `PARTNERSHIP_EXECUTIVE_SUMMARY.md`, `PITCH_DECK.md`, `TAGLINES_AND_POSITIONING.md`,
  `THE_FOREST_VISION.md`) from repo root into `docs/`.
- `patents/embedder_patent/` — PEPYS embedder patent application, CIP temporal
  extension, and pipeline technical disclosure (Markdown, LaTeX, PDF).
- `patents/haystack_patent/` — Haystack knowledge compiler patent suite: four patent
  drafts plus eight figures.

### Changed
- `src/kg_rag/app.py`: ruff-formatted; minor line-length fixes in Synthesize tab.
- `src/kg_rag/cli/cmd_synthesize.py`: ruff-formatted; import grouping and string
  concatenation cleaned up.

### Added
- `docs/graph_reasoner_spec/` — formal specification for GraphReasoner: a semantic
  reasoning engine that navigates knowledge graphs using an N-dimensional turtle
  navigator with heading-aware steering, lazy edge discovery, beam search, and
  backtracking. Includes full spec (`graph_reasoner_spec.md`) and summary.
- `docs/manifold_walker_spec/` — formal specification for ManifoldWalker: a
  gradient-based navigator for continuous embedding manifolds. Includes both
  Markdown and LaTeX sources (`manifold_walker_spec.md`, `manifold_walker_spec.tex`).
- `docs/waverider/` — WaveRider specification and infographic summary: a
  compressed-space navigator operating on latent manifolds.

### Changed
- `doc-kg` updated from `0.4.0` → `0.5.1` in `poetry.lock` (bump resolved git
  reference to `0b3088b`; gains `einops ^0.8.2` as a transitive dependency).
- `ftree-kg` local path dependency commented out in `pyproject.toml` (removes
  dependency on `../FTreeKG` sibling directory).

### Fixed
- `cmd_hooks.py`: Remove `--wipe` from `codekg build` in the generated pre-commit
  hook — `codekg build` always wipes and no longer accepts the flag (unlike `dockg`
  and `ftreekg` which still support `--wipe`). Prevents hook failure on `git commit`.

## [0.3.5] - 2026-03-20

### Added
- `kgrag init --corpus NAME` — after building and registering KG layers, automatically
  add every successfully registered KG to an existing corpus in one step. Eliminates the
  need for separate `kgrag corpus add` calls when initialising a repo into an existing
  corpus. Fails gracefully with a clear error if the corpus is not found.

### Changed
- **Dependency update**: `sentence-transformers` unpinned to `^5.2.0` (was `==4.1.0`);
  `transformers` updated to `^4.57.6`; `safetensors` pinned to `^0.5.0`. `poetry.lock`
  updated accordingly (`sentence-transformers` 4.1.0 → 5.3.0, `safetensors` 0.7.0 → 0.5.3).
- **docs/USAGE.md**: Updated `kgrag init` reference and Workflow 3 example to show
  `--corpus` usage; corpus-scoped query replaces the flat `kgrag query` call.
- **docs/FEATURES.md**: Added `--corpus NAME` to the `kgrag init` options line.

### Fixed
- `SnapshotManager._compute_delta` now converts `SnapshotMetrics` dataclass objects to
  plain dicts before calling `_compute_delta_from_metrics`, fixing an `AttributeError`
  raised when subclasses (e.g. FTreeKG) hydrate `snap.metrics` as a dataclass rather
  than a dict.

## [0.3.3] — 2026-03-18

### Added
- `src/kg_rag/cli/cmd_hooks.py` — new `kgrag install-hooks` CLI command that
  installs a KGRAG-aware pre-commit git hook into `.git/hooks/pre-commit`. The
  hook orchestrates rebuild + snapshot for all registered KG layers present in
  the workspace (CodeKG, DocKG, FTreeKG, DiaryKG) before running pre-commit
  framework checks. Supports `--repo` and `--force` flags. Skip with
  `KGRAG_SKIP_SNAPSHOT=1 git commit ...`.
- `src/kg_rag/cli/main.py` — imports `cmd_hooks` to register the new
  `install-hooks` command in the CLI dispatcher.

### Changed
- **Version bump**: `0.3.1` → `0.3.3` in `pyproject.toml` and `__init__.py`.
- **Dependency pinning**: `sentence-transformers` pinned to `==4.1.0` (was
  `>=2.7.0`) to avoid breaking changes in 5.x; added explicit `transformers
  <5.0.0` and `torch >=2.5.1` constraints for reproducible embedding behaviour.
- **`poetry.lock` updated**: `sentence-transformers` 5.3.0 → 4.1.0;
  `transformers` 5.3.0 → 4.57.6; `huggingface-hub` 1.6.0 → 0.36.2;
  `cuda-pathfinder` 1.4.2 → 1.4.3. Removed transitive deps no longer needed:
  `typer`, `shellingham`, `annotated-doc`.

## [0.3.1] — 2026-03-18

### Added
- `analysis/kgrag_analysis_20260318.md` — fresh architectural analysis report
  generated from the 0.3.1 codebase (grade C / 72, 3723 nodes · 4929 edges).
- `.mcp.json.sav` — saved MCP server configuration snapshot.

### Changed
- **Version bump**: `0.3.0` → `0.3.1` in `__init__.py` and `pyproject.toml`.
- **Python constraint corrected**: `>3.12` → `>=3.12` so Python 3.12.0 and later
  are properly included (the previous constraint accidentally excluded 3.12.x).
- **pyproject.toml cleanup**: added `viz2d` extras entry (alias for the `qt`
  group); renamed `meta-kg` extra to `metabo-kg` to match the package name;
  added inline comments grouping first-party adapter dependencies; diary-kg
  and metabo-kg deps moved to commented-out block.
- **Code formatting (Black)**: entire `src/kg_rag/` and `scripts/` tree
  reformatted — long dict literals, enum arrays in JSON schemas, factory
  method signatures, and comprehensions all split to multiple lines for
  readability. No logic changes.
- **Linting**: added `# pylint: disable=broad-exception-caught` on intentional
  bare-except blocks in `orchestrator.py`; added `# pylint: disable=import-outside-toplevel`
  for lazy imports in `config.py` and CLI commands; added `# type: ignore`
  annotations for known mypy edge cases in `adapters/__init__.py`,
  `corpus_registry.py`, and `person_registry.py`.
- **Type annotations modernised** in `scripts/textkg_analysis.py`: replaced
  `typing.Dict/List/Tuple/Optional` with built-in `dict/list/tuple` and `X | None`
  syntax; removed unused `defaultdict`, `Counter`, and legacy typing imports.
- **`_stub_adapter.py`**: `datetime.now(timezone.utc)` → `datetime.now(UTC)` for
  consistency with the rest of the codebase; minor whitespace fixes.
- **`corpus_registry.py` / `person_registry.py`**: `resolve_kg_entries` return
  type tightened to `list[KGEntry]`.
- **`orchestrator.py`**: removed unused `CorpusEntry` import.
- **`viz_qt.py`**: added `cyclic-import` to pylint disable list; added `Any` to
  typing imports; removed unused `KGEntry` TYPE_CHECKING import.
- **Pepys helper scripts**: import ordering and quote-style normalised by isort/
  Black (`hindsight_analysis.py`, `diary_transformer_example.py`,
  `pepys_proper_parse.py`, `topic_classifier.py`).
- **KG snapshots refreshed**: all `.codekg/snapshots/` and `.dockg/snapshots/`
  JSON files updated with current graph metrics.

### Removed
- **`pepys/diary_kg/`** package and all sub-modules (`__init__`, `cli`, `kg`,
  `snapshots`) — this was a bundled copy of the upstream `diary-kg` library;
  removed in favour of the proper `diary-kg` git dependency.
- **`pepys/diary_transformer/`** package and all sub-modules (`__init__`,
  `chunker`, `classifier`, `cli`, `features`, `models`, `parser`, `state`,
  `topic_classifier`, `topics.yaml`, `transformer`) — same rationale.
- **`pepys/tests/`** test suite (11 files, ~2000 lines) that covered the now-
  removed bundled packages.

### Changed
- **Pre-commit snapshot hook** — `.git/hooks/pre-commit` now captures snapshots
- **Pre-commit snapshot hook** — `.git/hooks/pre-commit` now captures snapshots
  for **both** CodeKG (`.codekg/snapshots/`) and DocKG (`.dockg/snapshots/`)
  before every commit. Previously only CodeKG was snapshotted. The hook also
  fixes a latent bug where a CodeKG snapshot failure would silently skip the
  DocKG snapshot entirely; both failures are now non-fatal and emit a warning
  instead. DocKG version is resolved from installed package metadata
  (`importlib.metadata`) rather than a hard-coded path. Seed the initial DocKG
  snapshot with `dockg snapshot save <version> --repo .` if `.dockg/snapshots/`
  does not yet exist.

### Added
- `src/kg_rag/app.py` — Streamlit visualizer: cross-KG registry manager and
  federated query explorer with three tabs (Registry, Query, Snippets) and
  per-KG-kind colour coding.
- `src/kg_rag/cli/cmd_viz.py` — `kgrag viz` CLI command that launches the
  Streamlit app (forwards unknown flags to `streamlit run`).
- `kgrag-viz` entry in `pyproject.toml` scripts so `poetry run kgrag viz`
  works without the full CLI dispatcher.
- `.claude/skills/kgrag-usage/` — new Claude Code skill with usage guide and
  CLI reference for KGRAG federated queries.
- `.vscode/settings.json` — workspace settings for the VSCode extension.

### Changed
- **Adapter API alignment** — all three adapters updated to match the new
  dict-based result objects returned by the current CodeKG/DocKG/MetaKG
  libraries:
  - `CodeKGAdapter`: `result.ranked_hits` → `result.nodes`; `pack.snippets`
    → `pack.nodes`; `store.node_count()/edge_count()` → `store.stats()`;
    constructor kwarg `lancedb_path` → `lancedb_dir`.
  - `DocKGAdapter`: same `result.nodes` / `pack.nodes` / `store.stats()`
    pattern; constructor `repo_root` → `corpus_root`, `lancedb_path` →
    `lancedb_dir`.
  - `MetaKGAdapter`: removed `repo_root`, `lancedb_path` → `lancedb_dir`.
- `cmd_registry.py` (`register`, `scan`) and `cmd_init.py` (`init`) now
  auto-read the version from the target repo's `pyproject.toml` via
  `read_pyproject_version()` (falls back to `"unknown"`) and default tags to
  the current datestamp when none are supplied.
- `.mcp.json` MCP server commands switched from absolute paths to relative
  `.venv/bin/` paths and `--repo .` for portability across machines.
- `pyproject.toml`: Python lower bound tightened to `>3.12` (excludes 3.12.0
  itself); `kgrag-viz` script entry added; extras stanzas added for `doc-kg`
  and `code-kg` optional groups.
- `tests/test_adapters.py` updated to match the new dict-based adapter
  interfaces (plain `dict` nodes instead of `MagicMock` attribute objects).
- `config.py`: extracted `_load_toml()` helper (DRY) and added
  `read_pyproject_version()` utility that reads `[project] version` (PEP 517)
  or `[tool.poetry] version` from any `pyproject.toml`.
- `orchestrator.py`, `registry.py`: `typing.Sequence` / `typing.Iterator`
  → `collections.abc` equivalents (modern Python standard).
- `README.md`: added *Knowledge Graph Snapshots* section documenting the
  pre-commit hook, seeding commands, and the `CODEKG_SKIP_SNAPSHOT` escape hatch.

### Fixed
- `primitives.py`, `registry.py`: replaced deprecated `datetime.utcnow()`
  with timezone-aware `datetime.now(UTC)` to avoid `DeprecationWarning` on
  Python 3.12+ and ensure correct UTC semantics.

## [0.2.0] — 2026-03-12

### Added
- `kgrag init` command (`src/kg_rag/cli/cmd_init.py`) — one-shot initialisation
  for a repository: auto-detects applicable KG layers (code/doc), builds each
  layer via the appropriate CLI (`codekg build` / `dockg build`), and registers
  every successfully-built layer in the KGRAG registry. Supports `--layer`,
  `--name`, `--wipe`, and `--registry` flags. Outputs a Rich summary table.
- `kgrag-init` CLI entrypoint wired up in `pyproject.toml`.
- `_find_kg_dirs()` helper in `cmd_registry.py` — shared walker that prunes
  hidden directories (`.git`, `.venv`, nested KG dirs) when scanning for KG
  databases; replaces the previous inline `rglob` loop in `scan`.
- `__version__ = "0.2.0"` exported from `kg_rag.__init__`.
- Comprehensive README rewrite: badges, overview, features, quick-start guide,
  CLI reference table, architecture diagram, installation instructions, and
  related-projects section.
- `docs/MCP.md` — full MCP server reference: architecture diagram, tool
  catalogue, client configuration examples (Claude Code, GitHub Copilot,
  Claude Desktop), and troubleshooting guide.
- `.claude/commands/setup-kgrag-mcp.md` — Claude Code slash-command for
  end-to-end KGRAG MCP setup (replaces the former `setup-mcp.md` which was
  CodeKG-only).
- `kgrag` entry in `.mcp.json` — wires the local KGRAG MCP server into
  Claude Code for this repository.
- `.pre-commit-config.yaml` and `.secrets.baseline` — pre-commit hooks
  (trailing-whitespace, pylint, mypy, pytest, detect-secrets, ruff) ported
  from `code_kg`; mypy/pytest hooks use `.venv/bin/` directly to avoid
  Python version conflicts with `poetry run`.

### Changed
- Bumped package version to `0.2.0` in `pyproject.toml` and `__init__.py`.
- `code-kg` and `doc-kg` promoted from dev/optional extras to required main
  dependencies; removed the `backends` extra group from `pyproject.toml`.
- `doc-kg` updated to 0.3.0 (resolved HEAD reference updated in `poetry.lock`).
- `code-kg` resolved HEAD reference updated to latest commit in `poetry.lock`.
- `src/kg_rag/cli/main.py` imports sorted alphabetically and `cmd_init` added.
- `KGRAG` import in `__init__.py` reordered before primitive imports (cosmetic).

### Added (prior)
- Full unit test suite (120 tests, all passing) covering:
  - `test_primitives.py` — `KGKind`, `KGEntry` (construction, path normalization, kind
    coercion, `is_built`, `label`), `RegistryStats`, `CrossHit`, `CrossQueryResult`,
    `CrossSnippet`, `CrossSnippetPack.render`
  - `test_registry.py` — `KGRegistry` CRUD (register, upsert, get, find, list, iter,
    update, unregister, stats, context manager), `default_registry_path` env override
  - `test_config.py` — `load_kgrag_config` with/without `pyproject.toml`, with/without
    `[tool.kgrag]` section, cwd default, string path input
  - `test_adapters.py` — `make_adapter` factory, `is_available` (import absent / not
    built / built), `query`/`pack`/`stats` with mocked KG libraries, graceful error handling
  - `test_orchestrator.py` — `KGRAG` init, `_resolve_entries` kind filtering,
    `_get_adapter` caching, strict vs permissive mode, federated `query`/`pack`/`stats`
  - `test_cli.py` — all CLI commands via `CliRunner`: `list`, `register`, `unregister`,
    `info`, `status`, `scan`, `--auto-register`
- `tests/conftest.py` with shared fixtures (`tmp_registry`, `sample_entry`, `built_entry`)
- `src/kg_rag/cli/group.py` — dedicated module for the top-level Click group
- `analysis/kgrag_analysis_20260312.md` — CodeKG architectural analysis snapshot

### Changed
- CLI command modules (`cmd_analyze`, `cmd_mcp`, `cmd_query`, `cmd_registry`) updated to
  import the Click group from `kg_rag.cli.group` instead of `kg_rag.cli.main`
- `src/kg_rag/cli/main.py` refactored to assemble the CLI from the extracted group module
