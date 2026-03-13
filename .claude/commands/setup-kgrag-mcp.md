# KGRAG MCP Setup & Verification

Set up the KGRAG MCP server, register a target repository, and configure it for use with Claude Code and/or Claude Desktop. Execute the following steps in sequence.

## Command Argument Handling

This command accepts an optional repository path argument:

**Usage:**
- `/setup-kgrag-mcp` — Interactive mode; prompts for the target repository path
- `/setup-kgrag-mcp /path/to/repo` — Register and configure the specified repository

---

## Step 0: Resolve the Target Repository

1. If a path argument was provided, use it as `REPO_ROOT`.
2. If no argument was provided, ask the user:
   > "Which repository do you want to register with KGRAG? Please provide the absolute path."
3. Verify the path exists and is a directory:
   ```bash
   ls "$REPO_ROOT"
   ```
4. If the path does not exist, stop and report the issue.

---

## Step 1: Verify KGRAG Installation

Prefer `poetry run` for all CLI calls. If `poetry run` fails with a **Python version
conflict** (e.g. "Current Python version is not allowed by the project"), fall back to
the `.venv` binaries directly — they are already built against the correct interpreter.

Establish the runner upfront:

```bash
# Try poetry run first
poetry run kgrag --version 2>&1
```

If that prints a version, set `RUNNER="poetry run"`. If it errors with a Python version
conflict, set `RUNNER=""` and use `.venv/bin/kgrag` directly for all subsequent calls:

```bash
# Fallback — use .venv binaries directly
$REPO_ROOT/.venv/bin/kgrag --version
```

Use whichever runner succeeds for all remaining steps. Document which runner was used in
the final report.

1. Check that the `kgrag` entry point resolves:
   ```bash
   $RUNNER kgrag --version   # or $REPO_ROOT/.venv/bin/kgrag --version
   ```
2. If not found, check whether the package is installed:
   ```bash
   $RUNNER python -m pip show kg-rag 2>/dev/null   # or .venv/bin/pip show kg-rag
   ```
3. If missing, instruct the user to install it:
   ```bash
   poetry add "kg-rag @ git+https://github.com/Flux-Frontiers/KGRAG.git"
   ```
   Then stop — the user must install before continuing.

4. Confirm the `mcp` Python package is importable (it is a required dependency, not an optional extra):
   ```bash
   $RUNNER python -c "import mcp; print('mcp OK')"
   ```
   If this fails, run `poetry install` and retry. There is no `[mcp]` extra to add.

5. Check the KGRAG version:
   ```bash
   $RUNNER python -c "import kg_rag; print(kg_rag.__version__)"
   ```

---

## Step 2: Run `kgrag init` on the Target Repository

`kgrag init` auto-detects applicable KG layers (code, doc), builds each one using the
appropriate backend CLI (`codekg build` / `dockg build`), and registers the results.

1. Check whether KG databases already exist:
   ```bash
   ls "$REPO_ROOT/.codekg" 2>/dev/null
   ls "$REPO_ROOT/.dockg"  2>/dev/null
   ```

2. If they exist, ask the user:
   > "KG databases already exist for this repository. Rebuild from scratch (--wipe), or re-register the existing databases without rebuilding?"
   - **Wipe**: proceed with `--wipe`
   - **Re-register only**: skip to Step 3

3. Run `kgrag init`:
   ```bash
   poetry run kgrag init "$REPO_ROOT" --wipe
   ```
   To force specific layers only:
   ```bash
   poetry run kgrag init "$REPO_ROOT" --layer code --layer doc --wipe
   ```

4. Review the summary table printed by the command. Each layer should show status `registered`.

5. If a layer shows `skipped` (backend CLI not on PATH), warn the user:
   - Missing `codekg`: install code-kg (`poetry add "code-kg @ git+https://github.com/Flux-Frontiers/code_kg.git"`)
   - Missing `dockg`: install doc-kg (`poetry add "doc-kg @ git+https://github.com/Flux-Frontiers/doc_kg.git"`)

---

## Step 3: Smoke-Test the Registry

Confirm that the layers were registered successfully:

1. List all registered KGs:
   ```bash
   poetry run kgrag list
   ```
   Each registered layer should appear with `built: true`.

2. Run a quick stats check:
   ```bash
   poetry run python -c "
   from kg_rag import KGRegistry
   with KGRegistry() as reg:
       s = reg.stats()
       print(f'total={s.total} built={s.built} by_kind={s.by_kind}')
   "
   ```

3. If `built` is 0 or a layer shows `built: false`, the database was not created.
   Re-run `kgrag init` with `--wipe` and inspect the build output for errors.

---

## Step 4: Configure MCP Clients

Configure `.mcp.json` (Claude Code / Kilo Code), `.vscode/mcp.json` (GitHub Copilot),
and `claude_desktop_config.json` (Claude Desktop) as applicable.

The KGRAG MCP server is started with `kgrag mcp`. It reads the registry automatically —
no `--repo` or `--db` flag is needed unless a non-default registry path is used.

### MCP config by agent — quick reference

| Agent | Config file | Per-repo? | Key name |
|-------|-------------|-----------|----------|
| **GitHub Copilot** | `.vscode/mcp.json` | ✅ Yes | `"servers"` |
| **Kilo Code** | `.mcp.json` (project root) | ✅ Yes | `"mcpServers"` |
| **Claude Code** | `.mcp.json` (project root) | ✅ Yes | `"mcpServers"` |
| **Cline** | `~/...saoudrizwan.claude-dev/settings/cline_mcp_settings.json` | ❌ Global only | `"mcpServers"` |
| **Claude Desktop** | `~/Library/Application Support/Claude/claude_desktop_config.json` | ❌ Global only | `"mcpServers"` |

### 4a: Kilo Code / Claude Code (.mcp.json)

1. Check if `.mcp.json` exists in `$REPO_ROOT`:
   ```bash
   cat "$REPO_ROOT/.mcp.json" 2>/dev/null
   ```

2. If a `kgrag` entry already exists, ask the user to replace or keep it.

3. The `kgrag` entry to add/update:
   ```json
   "kgrag": {
     "command": "<venv_path>/bin/kgrag",
     "args": ["mcp"]
   }
   ```
   Get `<venv_path>` with:
   ```bash
   poetry env info --path
   ```

4. To use a non-default registry, add `--registry`:
   ```json
   "kgrag": {
     "command": "<venv_path>/bin/kgrag",
     "args": ["mcp", "--registry", "/abs/path/to/registry.sqlite"]
   }
   ```

5. Merge into the existing `mcpServers` object — do not overwrite other entries.

### 4b: GitHub Copilot (.vscode/mcp.json)

Note: uses `"servers"` key and requires `"type": "stdio"`.

1. Check if `.vscode/mcp.json` exists:
   ```bash
   cat "$REPO_ROOT/.vscode/mcp.json" 2>/dev/null
   ```

2. The `kgrag` entry to add/update:
   ```json
   {
     "servers": {
       "kgrag": {
         "type": "stdio",
         "command": "<venv_path>/bin/kgrag",
         "args": ["mcp"]
       }
     }
   }
   ```

3. Merge into the existing `servers` object. After saving, VS Code will prompt to **Trust** the server.

### 4c: Claude Desktop (claude_desktop_config.json)

Claude Desktop does not have Poetry on its PATH — use the absolute venv binary.

1. Config path:
   - **macOS**: `~/Library/Application Support/Claude/claude_desktop_config.json`
   - **Linux**: `~/.config/Claude/claude_desktop_config.json`
   - **Windows**: `%APPDATA%\Claude\claude_desktop_config.json`

2. Get the venv binary path:
   ```bash
   poetry env info --path
   # binary: <venv_path>/bin/kgrag
   ```

3. The `kgrag` entry to add/update:
   ```json
   "kgrag": {
     "command": "<venv_path>/bin/kgrag",
     "args": ["mcp"]
   }
   ```

4. Merge into the existing `mcpServers` object — do not overwrite other entries.

---

## Step 5: Final Report

Present a summary of everything that was done:

```
✓ KGRAG version:        <version>
✓ Repository:           <REPO_ROOT>
✓ KG layers registered: <list of name/kind pairs>
✓ Registry stats:       total=<N> built=<N>
✓ Smoke test:           passed
✓ Claude Code config:   <REPO_ROOT>/.mcp.json  (kgrag entry)
✓ Claude Desktop config: <CONFIG_PATH>  (kgrag entry)

Restart Claude Code / Claude Desktop to activate the kgrag MCP server.

Available tools once active:
  • kgrag_stats()              — registry summary (total KGs, built status)
  • kgrag_list([kind])         — list registered KGs, optionally filtered by kind
  • kgrag_info(name)           — full detail for a single registered KG
  • kgrag_query(q, [k, kinds]) — federated semantic query across all registered KGs
  • kgrag_pack(q, [k, kinds])  — federated snippet pack for LLM context

Suggested first query after restart:
  kgrag_stats()
```

---

## Important Rules

- **Do NOT modify source files** in the target repository.
- **Do NOT run `git commit`** or any destructive git operations.
- Use **absolute paths** everywhere — relative paths will break MCP clients.
- Prefer `poetry run` for CLI calls; fall back to `.venv/bin/kgrag` if Poetry reports a Python version conflict.
- `mcp` is a **required main dependency** of KGRAG — there is no `[mcp]` extra to add.
- If any step fails, stop and report the error clearly before proceeding.

| Error | Fix |
|-------|-----|
| `Current Python version is not allowed by the project` | Use `.venv/bin/kgrag` directly instead of `poetry run kgrag` |
| `kgrag: command not found` | Run `poetry install`; if venv exists use `.venv/bin/kgrag` |
| `ModuleNotFoundError: No module named 'mcp'` | Run `poetry install` — `mcp` is a required dep, not an extra |
| Layer shows `built: false` after `kgrag list` | Re-run `kgrag init "$REPO_ROOT" --wipe` and check build output |
| `kgrag mcp` server not appearing in Claude Code | Use absolute venv path in `.mcp.json`; restart Claude Code |

---

## Re-registering After Rebuilding KGs

When the underlying CodeKG or DocKG databases are rebuilt, re-run `kgrag init` to
refresh the registry entries (sqlite/lancedb paths are re-verified):

```bash
$RUNNER kgrag init "$REPO_ROOT"   # or $REPO_ROOT/.venv/bin/kgrag init "$REPO_ROOT"
```

Add `--wipe` to also rebuild the KG databases from scratch:

```bash
$RUNNER kgrag init "$REPO_ROOT" --wipe
```

The MCP client configs do not need to change — they point to the shared registry,
not to individual database files.
