# CodeKG MCP Setup & Verification

Set up the CodeKG MCP server for a target repository and configure it for use with Claude Code and/or Claude Desktop. Execute the following steps in sequence.

## Command Argument Handling

This command accepts an optional repository path argument:

**Usage:**
- `/setup-mcp` — Interactive mode; prompts for the target repository path
- `/setup-mcp /path/to/repo` — Set up CodeKG MCP for the specified repository

---

## Step 0: Resolve the Target Repository

1. If a path argument was provided, use it as `REPO_ROOT`.
2. If no argument was provided, ask the user:
   > "Which repository do you want to index? Please provide the absolute path."
3. Verify the path exists and contains at least one `.py` file:
   ```bash
   find "$REPO_ROOT" -name "*.py" -not -path "*/.venv/*" -not -path "*/__pycache__/*" | head -5
   ```
4. If no Python files are found, stop and report the issue.

All artifact paths use the defaults relative to `REPO_ROOT`:
- `DB_PATH` → `$REPO_ROOT/.codekg/graph.sqlite`
- `LANCEDB_DIR` → `$REPO_ROOT/.codekg/lancedb`

Do not pass `--db` or `--lancedb` flags — the commands default to `.codekg/` automatically.

---

## Step 1: Verify CodeKG Installation

The package is managed via Poetry, so all checks use `poetry run`.

1. Check that the `codekg-mcp` entry point is available in the venv:
   ```bash
   poetry run which codekg-mcp
   ```
2. If not found, check whether the package is installed:
   ```bash
   poetry show code-kg 2>/dev/null || pip show code-kg 2>/dev/null
   ```
3. If the package is missing, instruct the user to install it:
   ```bash
   poetry add "code-kg[mcp]"
   ```
   Then stop — the user must install before continuing.

4. If the package is installed but `codekg-mcp` is missing, the `mcp` extra is likely absent:
   ```bash
   poetry add mcp
   ```

5. Confirm the `mcp` Python package is importable:
   ```bash
   poetry run python -c "import mcp; print('mcp OK')"
   ```
   If this fails, report the error and stop.

---

## Step 2: Build the Knowledge Graph (SQLite)

1. Check whether `DB_PATH` already exists:
   ```bash
   ls -lh "$REPO_ROOT/.codekg/graph.sqlite" 2>/dev/null
   ```
2. If it exists, ask the user:
   > "A knowledge graph already exists at `$REPO_ROOT/.codekg/graph.sqlite`. Rebuild it from scratch (wipe), or keep the existing graph?"
   - **Wipe**: proceed with `--wipe`
   - **Keep**: skip to Step 3

3. Run the static analysis build:
   ```bash
   poetry run codekg-build-sqlite --repo "$REPO_ROOT" --wipe
   ```
4. Verify the database was created and is non-empty:
   ```bash
   sqlite3 "$REPO_ROOT/.codekg/graph.sqlite" "SELECT COUNT(*) FROM nodes; SELECT COUNT(*) FROM edges;"
   ```
5. Report the node and edge counts. If both are zero, warn the user — the repo may have no indexable Python files.

---

## Step 3: Build the Semantic Index (LanceDB)

1. Check whether `LANCEDB_DIR` already exists and is non-empty:
   ```bash
   ls "$REPO_ROOT/.codekg/lancedb" 2>/dev/null
   ```
2. If it exists and the user chose to keep the SQLite graph (Step 2), ask:
   > "A vector index already exists at `$REPO_ROOT/.codekg/lancedb`. Rebuild it?"
   - **Yes**: proceed with `--wipe`
   - **No**: skip to Step 4

3. Run the embedding build:
   ```bash
   poetry run codekg-build-lancedb --repo "$REPO_ROOT" --wipe
   ```
4. Confirm the LanceDB directory was populated:
   ```bash
   ls -lh "$LANCEDB_DIR"
   ```
5. Report the number of indexed vectors (shown in the command output).

---

## Step 4: Smoke-Test the Query Pipeline

Run a quick end-to-end test to confirm the full pipeline works before configuring any agent:

1. Run a graph stats check:
   ```bash
   poetry run python -c "
   from code_kg import CodeKG
   kg = CodeKG(repo_root='$REPO_ROOT')
   import json; print(json.dumps(kg.stats(), indent=2))
   "
   ```

2. Run a sample query (must be run from `$REPO_ROOT` so `.codekg/` defaults resolve):
   ```bash
   cd "$REPO_ROOT" && poetry run codekg-query --q "module structure"
   ```

3. If either command errors, diagnose and report the issue before proceeding.

---

## Step 5: Configure MCP Clients

Configure the per-repo `.mcp.json`, Claude Desktop (`claude_desktop_config.json`) if applicable, and install the CodeKG skill globally.

### MCP config by agent — quick reference

| Agent | Config file | Per-repo? | Key name |
|-------|-------------|-----------|----------|
| **GitHub Copilot** | `.vscode/mcp.json` | ✅ Yes | `"servers"` |
| **Kilo Code** | `.mcp.json` (project root) | ✅ Yes | `"mcpServers"` |
| **Claude Code** | `.mcp.json` (project root) | ✅ Yes | `"mcpServers"` |
| **Cline** | `~/...saoudrizwan.claude-dev/settings/cline_mcp_settings.json` | ❌ Global only | `"mcpServers"` |
| **Claude Desktop** | `~/Library/Application Support/Claude/claude_desktop_config.json` | ❌ Global only | `"mcpServers"` |

> ⚠️ **Do NOT add `codekg` to any global settings file** (Kilo Code `mcp_settings.json`, Cline `cline_mcp_settings.json`).
> Global files are shared across all windows — hardcoded paths will point every window to the same repo.
> Use per-repo config files (`.vscode/mcp.json` for Copilot, `.mcp.json` for Kilo Code/Claude Code) instead.

> ⚠️ **Cline does NOT support per-repo config.**
> Options: use Kilo Code instead, or add a uniquely-named entry per repo in `cline_mcp_settings.json` and toggle via the Cline MCP panel.

### 5a: GitHub Copilot (.vscode/mcp.json)

GitHub Copilot in VS Code reads MCP servers from `.vscode/mcp.json` in the workspace root. Note the key differences from `.mcp.json`:
- Uses `"servers"` (not `"mcpServers"`)
- Requires `"type": "stdio"` for local servers
- Can be committed to source control to share with the team

1. Check if `.vscode/mcp.json` exists in `$REPO_ROOT`:
   ```bash
   cat "$REPO_ROOT/.vscode/mcp.json" 2>/dev/null
   ```

2. If it exists, check for an existing `codekg` entry under `servers`.
   - If one exists, ask the user to replace or keep it.

3. The `codekg` entry to add/update:
   ```json
   {
     "servers": {
       "codekg": {
         "type": "stdio",
         "command": "poetry",
         "args": [
           "run", "codekg-mcp",
           "--repo", "<REPO_ROOT>"
         ],
         "env": {
           "POETRY_VIRTUALENVS_IN_PROJECT": "false"
         }
       }
     }
   }
   ```

4. Merge into the existing `servers` object — do not overwrite other entries.

5. After saving, VS Code will prompt you to trust the MCP server — click **Trust** to activate it.

### 5b: Kilo Code / Claude Code (.mcp.json)

Both Kilo Code and Claude Code read MCP servers from `.mcp.json` in the project root. Use `poetry run` so the entry point resolves correctly regardless of venv path.

1. Check if `.mcp.json` exists in `$REPO_ROOT`:
   ```bash
   cat "$REPO_ROOT/.mcp.json" 2>/dev/null
   ```

2. If it exists, check for an existing `codekg` entry under `mcpServers`.
   - If one exists, ask the user to replace or keep it.

3. The `codekg` entry to add/update:
   ```json
   "codekg": {
     "command": "poetry",
     "args": [
       "run", "codekg-mcp",
       "--repo", "<REPO_ROOT>"
     ],
     "env": {
       "POETRY_VIRTUALENVS_IN_PROJECT": "false"
     }
   }
   ```

4. Merge into the existing `mcpServers` object — do not overwrite other entries.

5. **Verify the global settings file does NOT contain a `codekg` entry:**
   - Kilo Code global config: `~/Library/Application Support/Code/User/globalStorage/kilocode.kilo-code/settings/mcp_settings.json`
   - Claude Code global config: `~/.claude/settings.json` (or `~/Library/Application Support/Claude/settings.json`)
   - If a `codekg` entry exists in either global file, remove it and leave `"mcpServers": {}`.
   - This prevents the static-path conflict where all windows point to the same repo.

### 5c: Claude Desktop (claude_desktop_config.json)

Claude Desktop does not have Poetry on its PATH, so use the absolute path to the venv binary.

1. Determine the config path:
   - **macOS**: `~/Library/Application Support/Claude/claude_desktop_config.json`
   - **Linux**: `~/.config/Claude/claude_desktop_config.json`
   - **Windows**: `%APPDATA%\Claude\claude_desktop_config.json`

2. Get the venv binary path:
   ```bash
   poetry env info --path
   ```
   The binary is at `<venv_path>/bin/codekg-mcp`.

3. Check whether the config file exists and read it:
   ```bash
   cat "$CONFIG_PATH" 2>/dev/null
   ```

4. If a `codekg` entry already exists, ask the user to replace or keep it.

5. The `codekg` entry to add/update (use the absolute venv path):
   ```json
   "codekg": {
     "command": "<venv_path>/bin/codekg-mcp",
     "args": [
       "--repo", "<REPO_ROOT>"
     ]
   }
   ```

6. Merge into the existing `mcpServers` object — do not overwrite other entries.

7. Show the user the final `codekg` block that was written.

### 5d: Install the CodeKG Skill (Global)

The CodeKG skill provides AI agents with expert knowledge about CodeKG installation and usage. It must be installed to the correct directory for each agent:

| Agent | Skill directory |
|-------|----------------|
| **Kilo Code** | `~/.kilocode/skills/codekg/` |
| **Claude Code** | `~/.claude/skills/codekg/` (served by `skills-copilot` MCP server) |
| **Other agents** | `~/.agents/skills/codekg/` |

> ⚠️ **Kilo Code does NOT use `~/.claude/skills/` or `~/.agents/skills/`** — it reads from `~/.kilocode/skills/` only.

The easiest way to install to all locations at once is the install script:

```bash
bash <CODE_KG_REPO>/scripts/install-skill.sh
```

Or manually:

1. Locate the skill source in the `code_kg` repo:
   ```bash
   poetry run python -c "import code_kg; import pathlib; print(pathlib.Path(code_kg.__file__).parent.parent.parent)"
   ```

2. Check if already installed for Kilo Code:
   ```bash
   ls ~/.kilocode/skills/codekg/SKILL.md 2>/dev/null && echo "ALREADY_INSTALLED" || echo "NOT_INSTALLED"
   ```

3. Install/update to all locations:
   ```bash
   # Kilo Code
   mkdir -p ~/.kilocode/skills/codekg/references
   cp "<CODE_KG_REPO>/.claude/skills/codekg/SKILL.md" ~/.kilocode/skills/codekg/SKILL.md
   cp "<CODE_KG_REPO>/.claude/skills/codekg/references/installation.md" ~/.kilocode/skills/codekg/references/installation.md

   # Claude Code
   mkdir -p ~/.claude/skills/codekg/references
   cp "<CODE_KG_REPO>/.claude/skills/codekg/SKILL.md" ~/.claude/skills/codekg/SKILL.md
   cp "<CODE_KG_REPO>/.claude/skills/codekg/references/installation.md" ~/.claude/skills/codekg/references/installation.md
   ```

4. **Reload VS Code** (`Cmd+Shift+P` → "Developer: Reload Window") for Kilo Code to pick up the new skill.

5. Verify the skill is loaded by asking the agent: "Do you have access to the codekg skill?"

---

## Step 6: Final Report

Present a summary of everything that was done:

```
✓ Repository indexed:   <REPO_ROOT>
✓ SQLite graph:         <REPO_ROOT>/.codekg/graph.sqlite  (<N> nodes, <M> edges)
✓ LanceDB index:        <REPO_ROOT>/.codekg/lancedb  (<V> vectors)
✓ Smoke test:           passed
✓ Claude Code config:   <REPO_ROOT>/.mcp.json
✓ Claude Desktop config: <CONFIG_PATH>
✓ CodeKG skill:         ~/.claude/skills/codekg/  (installed/updated/skipped)

Restart Claude Code / Claude Desktop to activate the codekg MCP server.

Available tools once active:
  • graph_stats()          — codebase size and shape
  • query_codebase(q)      — semantic + structural exploration
  • pack_snippets(q)       — source-grounded code snippets
  • get_node(node_id)      — single node metadata lookup

Suggested first query after restart:
  graph_stats()
```

---

## Important Rules

- **Do NOT modify source files** in the target repository.
- **Do NOT run `git commit`** or any destructive git operations.
- Use **absolute paths** everywhere — relative paths will break MCP clients.
- Always use `poetry run` for CLI calls — the package is not installed globally.
- If any step fails, stop and report the error clearly before proceeding.
- If the user's repo is very large (>50k lines of Python), warn that the build and embedding steps may take several minutes.

---

## Rebuilding After Code Changes

When the target codebase changes, the graph must be rebuilt. Remind the user:

```bash
# Rebuild both artifacts (idempotent — safe to re-run)
poetry run codekg-build-sqlite  --repo "$REPO_ROOT" --wipe
poetry run codekg-build-lancedb --repo "$REPO_ROOT" --wipe
```

The MCP client configs do not need to change — they point to the same file paths.
