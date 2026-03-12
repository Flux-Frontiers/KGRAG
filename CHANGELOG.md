# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
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
