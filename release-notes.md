# Release Notes — v0.9.1

> Released: 2026-06-05

### Changed

- **PyPI dependency cleanup** (`pyproject.toml`, `poetry.lock`) — removed
  `agent-kg`, `memory-kg`, and `metabo-kg` git-URL optional dependencies (not
  on PyPI; install separately via `uv add git+...`); converted `diary-kg` from
  a git source to a PyPI version specifier (`>=0.92.4`); dropped the `kg-git`
  extra; added `diary-kg` to the `kg` and `all` extras. This unblocks PyPI
  publishing, which rejects packages with direct-URL dependencies.
- **Linter: pylint → ruff** (`pyproject.toml`, `.pre-commit-config.yaml`) —
  removed `pylint` dev dependency and its pre-commit hook; extended ruff rule
  set from `["E","F","W","I","UP"]` to add `B` (flake8-bugbear), `BLE`
  (blind-except), and `PLC` (pylint-convention). `BLE001`, `PLC0415`, and
  `PLC0414` are globally ignored as intentional patterns (boundary catches,
  lazy CLI imports, `X as X` re-exports); `B017` suppressed in tests.

### Fixed

- **Exception chaining** (`src/kg_rag/cli/cmd_corpus.py` ×4,
  `src/kg_rag/primitives.py`) — `raise ... from None` on `SystemExit` and
  `ValueError` raises inside `except` blocks (B904).
- **`zip()` missing `strict=`** (`src/kg_rag/cli/cmd_corpus.py`) — added
  `strict=False` to `zip(kg_refs, kg_ids)` (B905).
- **Unused loop variable** (`src/kg_rag/cli/cmd_init.py`) — renamed `dirpath`
  → `_dirpath` in `os.walk` loop (B007).
- **Type checker: mypy → ty** (`pyproject.toml`, `.pre-commit-config.yaml`,
  `.github/workflows/ci.yml`) — replaced `mypy` with Astral's `ty` (`^0.0.41`)
  across the dev tooling. Config migrated from `[tool.mypy]` to
  `[tool.ty.environment]` and `[tool.ty.rules]`.
- **Pre-commit ruff bumped `v0.9.10` → `v0.15.13`** (`.pre-commit-config.yaml`).
- **`_probe_kg` parameter type** (`src/kg_rag/cli/cmd_health.py`) — annotated
  `entry` as `KGEntry`, removing four `# type: ignore[attr-defined]` suppressions.
- **Qt label references** (`src/kg_rag/viz_qt.py`) — labels held directly on
  creation, dropping two `# type: ignore[union-attr]` suppressions.
- **`ty` false positives on shadowed `list` return types** (`registry.py`,
  `corpus_registry.py`, `person_registry.py`) — suppressed with
  `# ty: ignore[invalid-type-form]`.
- **`.secrets.baseline`** — regenerated, clearing stale entries that caused
  non-convergent pre-commit rewrites.

### Added

- **OpenAI-compatible inference backend for `kgrag synthesize`**
  (`src/kg_rag/cli/cmd_synthesize.py`) — `--backend openai` routes synthesis
  through any `/v1/chat/completions`-compatible server (omlx, LM Studio, vLLM,
  llama.cpp, etc.). New options: `--backend ollama|openai`, `--openai-url`,
  `--api-key`. SSE streaming with graceful error handling.
- **`tests/test_cmd_synthesize.py`** — 48-test suite covering both backends,
  all error paths, and all CLI options.
- **`scripts/install-kgs.sh`** — one-shot script to install the full KGRAG
  fleet as `uv tool --editable` global commands.
- **`.claude/skills/kgrag/SKILL.md`** — KGRAG orchestrator skill with complete
  tool decision tree and CLI reference for the full fleet.
- **Streamlit Synthesize tab** (`src/kg_rag/app.py`) — dual-backend radio,
  OpenAI-compat URL/API-key fields, max-context input, single-source-of-truth
  streaming generators shared with the CLI.

### Removed

- **`[tool.poetry.group.kgdeps]`** (`pyproject.toml`) — removed; git-sourced
  adapters now documented as `uv add git+...` installs.

---

_Full changelog: [CHANGELOG.md](CHANGELOG.md)_
