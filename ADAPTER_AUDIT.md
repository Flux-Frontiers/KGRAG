# Adapter Audit Checklist — codekg → pycodekg Migration

Generated: 2026-04-17
Scope: pyproject.toml, pre-commit hooks, .gitignore, tool config sections

---

## Summary of Issues Found

| Repo | pyproject dep | hook binary | .gitignore | [tool.X] section |
|------|--------------|-------------|------------|-------------------|
| `code_kg` | ⚠️ still `code-kg` (this IS the old repo — archive/deprecate) | ❌ uses `codekg` | ❌ `.codekg` only | n/a |
| `pycode_kg` | ✅ `pycode-kg` | ✅ `pycodekg` | ✅ `.pycodekg` | ✅ |
| `doc_kg` | ✅ `pycode-kg` | ✅ no codekg hook | ⚠️ 1 stale `.codekg` ref | ✅ `[tool.pycodekg]` |
| `agent_kg` | ✅ `pycode-kg` | ❌ calls `codekg` binary | ⚠️ 1 stale `.codekg` ref | ✅ `[tool.pycodekg]` |
| `diary_kg` | ✅ `pycode-kg` (optional) | ❌ calls `codekg` binary | ⚠️ 1 stale `.codekg` ref | ❌ missing `[tool.pycodekg]` |
| `metabo_kg` | ❌ `code-kg` (old repo!) | ❌ calls `codekg` binary | ❌ `.codekg` only | ❌ missing `[tool.pycodekg]` |
| `memory_kg` | ✅ `pycode-kg` | ✅ no codekg hook | ⚠️ 1 stale `.codekg` ref | ✅ `[tool.pycodekg]` |
| `kgrag` | ✅ `pycode-kg` (optional) | ✅ fixed this session | ✅ fixed this session | ⚠️ `[tool.codekg]` → rename to `[tool.pycodekg]` |
| `ftree_kg` | n/a (not found at ~/repos/) | n/a | n/a | n/a |

---

## Per-Repo Action Items

### `metabo_kg` — CRITICAL (2 issues)
- [ ] `pyproject.toml`: change `code-kg = { git = ".../code_kg.git" }` → `pycode-kg = { git = ".../pycode_kg.git" }`
- [ ] `pyproject.toml`: add `[tool.pycodekg]` section (with appropriate include/exclude)
- [ ] `.git/hooks/pre-commit`: change `.venv/bin/codekg` → `.venv/bin/pycodekg` and `.codekg` dir → `.pycodekg`
- [ ] `.gitignore`: replace `.codekg/` patterns with `.pycodekg/` patterns

### `agent_kg` — 2 issues
- [ ] `.git/hooks/pre-commit`: change `codekg` binary refs → `pycodekg`; change `.codekg` dir check → `.pycodekg`
- [ ] `.gitignore`: remove stale `.codekg` ref (1 remaining)

### `diary_kg` — 2 issues
- [ ] `.git/hooks/pre-commit`: change `.venv/bin/codekg` → `.venv/bin/pycodekg`; `.codekg` → `.pycodekg`
- [ ] `pyproject.toml`: add `[tool.pycodekg]` section
- [ ] `.gitignore`: remove stale `.codekg` ref (1 remaining)

### `doc_kg` — 1 issue
- [ ] `.gitignore`: remove stale `.codekg` ref (1 remaining)

### `memory_kg` — 1 issue
- [ ] `.gitignore`: remove stale `.codekg` ref (1 remaining)

### `kgrag` (this repo) — 1 remaining issue
- [ ] `pyproject.toml`: rename `[tool.codekg]` → `[tool.pycodekg]`

### `code_kg` — deprecation decision needed
- [ ] Decision: archive/deprecate the old `code_kg` repo or keep for historical reference?
- [ ] If keeping: add deprecation notice in README pointing to `pycode_kg`

---

## Checklist: What "Correct" Looks Like Per File

### pyproject.toml
```toml
# Dependency entry (optional adapter)
pycode-kg = {git = "https://github.com/Flux-Frontiers/pycode_kg.git", optional = true}

# Tool config section
[tool.pycodekg]
include = ["src"]
# exclude = ["tests"]
```

### .git/hooks/pre-commit (PyCodeKG block)
```bash
if [ -d "$REPO_ROOT/.pycodekg" ]; then
    (cd "$REPO_ROOT" && .venv/bin/pycodekg build --repo . || exit 1)
    (cd "$REPO_ROOT" && .venv/bin/pycodekg snapshot save \
        --repo . --tree-hash "$TREE_HASH" --branch "$BRANCH") \
      || { echo "[kgrag] pycodekg snapshot skipped" >&2; }
    git add .pycodekg/snapshots/ 2>/dev/null || true
fi
```

### .gitignore (PyCodeKG block)
```
# PyCodeKG generated artifacts — snapshots are tracked
.pycodekg/lancedb/
.pycodekg/lancedb-*
.pycodekg/graph.sqlite
.pycodekg/graph.sqlite*
.pycodekg/models
```

### .pre-commit-config.yaml (detect-secrets exclusion)
```yaml
args: ['--baseline', '.secrets.baseline', '--exclude-files',
       '\.(kgrag|pycodekg|dockg|filetreekg|diarykg|memorykg|agentkg)/.*']
```

---

## Skills Audit

- [ ] Check `~/.claude/skills/codekg/SKILL.md` — verify all CLI examples use `pycodekg` not `codekg`
- [ ] Check `/Users/egs/repos/kgrag/.claude/skills/` — same
- [ ] Check `/Users/egs/repos/code_kg/.claude/skills/codekg/` — update or deprecate
- [ ] Verify MCP server name is `codekg` (MCP tool names like `mcp__codekg__*` don't change — only the CLI binary name changed)

---

## Priority Order
1. **`metabo_kg`** — wrong dependency pulls old `code-kg` transitively (caused the original bug)
2. **`agent_kg`** / **`diary_kg`** — hook calls wrong binary, will break on commit
3. **`kgrag`** — `[tool.codekg]` rename (cosmetic but inconsistent)
4. **`doc_kg`** / **`memory_kg`** — stale gitignore refs (low risk)
5. **`code_kg`** — deprecation decision
