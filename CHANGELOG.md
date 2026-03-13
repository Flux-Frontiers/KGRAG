# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

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
