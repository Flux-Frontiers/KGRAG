# KGRAG Troubleshooting Guide

## Quick Diagnostics

Run these first to understand your KGRAG state:

```bash
# Check version
kgrag --version

# Check registry health
kgrag status

# List all registered KGs
kgrag list

# Get detailed info on a specific KG
kgrag info myproject-code
```

---

## Registry & Initialization Issues

### ❌ "No KGs registered" or empty registry

**Symptoms:**
- `kgrag list` shows nothing
- `kgrag status` says "0 KGs registered"

**Solutions:**

1. **Initialize your first project:**
   ```bash
   kgrag init ~/repos/myproject
   ```

2. **Verify registry was created:**
   ```bash
   ls -la ~/.kgrag/registry.sqlite
   ```

3. **Check registry path:**
   ```bash
   echo $KGRAG_REGISTRY
   # Default: ~/.kgrag/registry.sqlite
   ```

4. **Initialize multiple projects:**
   ```bash
   kgrag init ~/repos/project1
   kgrag init ~/repos/project2
   kgrag list
   ```

---

### ❌ "KG not built" or marked invalid

**Symptoms:**
- `kgrag status` shows "not built"
- Visualizer shows "⚠️ Not built"

**Solutions:**

1. **Rebuild the KG:**
   ```bash
   kgrag init ~/repos/myproject --wipe
   ```

2. **Check if repo path exists:**
   ```bash
   ls ~/repos/myproject
   # If path is gone, KG entry is orphaned
   ```

3. **Remove orphaned entry:**
   ```bash
   kgrag unregister myproject-code
   # Then re-register from new path
   kgrag init ~/repos/myproject-new --name myproject-code
   ```

---

### ❌ "Registry corrupted" or database errors

**Symptoms:**
- Error: "database disk image is malformed"
- `kgrag list` fails with SQL errors

**Solutions:**

1. **Backup your registry:**
   ```bash
   cp ~/.kgrag/registry.sqlite ~/.kgrag/registry.sqlite.backup
   ```

2. **Delete and recreate:**
   ```bash
   rm ~/.kgrag/registry.sqlite
   kgrag init ~/repos/project1
   ```

3. **Re-register all projects:**
   ```bash
   kgrag init ~/repos/project1
   kgrag init ~/repos/project2
   kgrag list
   ```

---

## Querying Issues

### ❌ "No results found"

**Symptoms:**
- `kgrag query "term"` returns empty
- Visualizer shows "No results found"

**Troubleshooting steps:**

1. **Check registry health:**
   ```bash
   kgrag status
   ```
   Ensure:
   - KGs are registered
   - KGs are marked "built"
   - No "missing path" warnings

2. **If KG is not built, rebuild:**
   ```bash
   kgrag init ~/repos/myproject --wipe
   ```

3. **Verify KG has data:**
   ```bash
   kgrag info myproject-code
   # Check that node_count > 0
   ```

4. **Try a broader query:**
   ```bash
   # Instead of: "JWT token validation"
   # Try: "authentication" or "token"
   kgrag query "authentication"
   ```

5. **Remove filters to search all KGs:**
   ```bash
   # Instead of:
   kgrag query "error handling" --kind code

   # Try:
   kgrag query "error handling"  # all KGs
   ```

6. **Increase result count:**
   ```bash
   kgrag query "error handling" -k 12
   # Default is -k 8, try higher to see if more results exist
   ```

7. **Check if KG library is installed:**
   ```bash
   # For CodeKGs:
   python -c "import code_kg; print('CodeKG OK')"

   # For DocKGs:
   python -c "import doc_kg; print('DocKG OK')"
   ```

---

### ❌ "Results seem outdated or stale"

**Symptoms:**
- Query results mention code that's been deleted
- New code patterns don't show up

**Solutions:**

1. **Rebuild the KG (full wipe):**
   ```bash
   kgrag init ~/repos/myproject --wipe
   ```
   The `--wipe` flag deletes old data before rebuilding.

2. **Incremental rebuild (minor changes):**
   ```bash
   kgrag init ~/repos/myproject
   # Without --wipe, does incremental update
   ```

3. **Schedule monthly rebuilds:**
   ```bash
   # Add to crontab
   0 0 1 * * kgrag init ~/repos/myproject --wipe
   ```

---

### ❌ "Results are too broad or irrelevant"

**Symptoms:**
- Results don't match query closely
- Getting unrelated code

**Solutions:**

1. **Use more specific terms:**
   - ❌ "database" (too broad)
   - ✅ "transaction handling" (specific)

2. **Filter by KG kind:**
   ```bash
   # Code patterns only
   kgrag query "error handling" --kind code

   # Documentation only
   kgrag query "setup instructions" --kind doc
   ```

3. **Reduce result count (higher relevance threshold):**
   ```bash
   kgrag query "your term" -k 3
   # Lower k = higher relevance threshold
   ```

---

## Snippet Pack Issues

### ❌ "Pack is too large"

**Symptoms:**
- Output markdown is thousands of lines
- Won't fit in LLM context window

**Solutions:**

1. **Reduce results per KG:**
   ```bash
   kgrag pack "term" -k 3  # instead of default 8
   ```

2. **Reduce context lines:**
   ```bash
   kgrag pack "term" --context 2  # instead of default 5
   ```

3. **Filter to specific KG kind:**
   ```bash
   kgrag pack "term" --kind code  # exclude docs
   ```

4. **Combine all three:**
   ```bash
   kgrag pack "database patterns" --kind code -k 3 --context 2
   ```

---

### ❌ "Pack includes wrong snippets"

**Symptoms:**
- Code snippets are unrelated to query
- Missing relevant code

**Solutions:**

1. **Try different query terms:**
   - Original: `"database patterns"`
   - Try: `"transaction handling"` or `"SQL queries"`

2. **Check if KG is up-to-date:**
   ```bash
   kgrag info myproject-code | grep Updated
   # If old, rebuild: kgrag init ~/repos/myproject --wipe
   ```

3. **Increase k to see more options:**
   ```bash
   kgrag pack "term" -k 12  # see more results to filter
   ```

---

## Visualizer Issues

### ❌ "Registry not loading"

**Symptoms:**
- Visualizer shows "⚠️ No KGs registered"
- Even though `kgrag list` shows KGs

**Solutions:**

1. **Check registry path in visualizer:**
   In sidebar, look at "Registry path" field.
   Should match: `echo $KGRAG_REGISTRY`

2. **Click "🔄 Refresh Registry":**
   Button in sidebar refreshes loaded registry.

3. **If path is wrong, correct it:**
   Type correct path in "Registry path" field, click outside to reload.

4. **Restart visualizer:**
   ```bash
   # Kill current instance (Ctrl+C)
   # Restart:
   kgrag viz
   ```

---

### ❌ "Stats unavailable" for a KG

**Symptoms:**
- KG card shows "Stats unavailable: [error]"

**Solutions:**

1. **Check if KG library is installed:**
   ```bash
   python -c "import code_kg"  # for CodeKGs
   python -c "import doc_kg"   # for DocKGs
   ```
   If import fails, install: `pip install code-kg` or `pip install doc-kg`

2. **Check if databases exist:**
   ```bash
   ls ~/.codekg/graph.sqlite
   ls ~/.codekg/lancedb
   ```

3. **Rebuild the KG:**
   ```bash
   kgrag init ~/repos/myproject --wipe
   ```

---

### ❌ "Visualizer is slow or unresponsive"

**Symptoms:**
- Long delays loading results
- UI feels sluggish

**Solutions:**

1. **Reduce query scope:**
   - In "KG Selection", unselect large projects
   - Filter by kind (code/doc)

2. **Reduce result count:**
   - Set "Top-K results per KG" to 3–5

3. **Clear browser cache:**
   - Hard refresh: Cmd+Shift+R (macOS) or Ctrl+Shift+R (Linux/Windows)

4. **Restart visualizer:**
   ```bash
   kgrag viz --port 8502  # use different port if 8501 busy
   ```

---

## MCP Integration Issues

### ❌ "MCP tools not appearing" in Claude Code

**Symptoms:**
- `kgrag_query`, `kgrag_pack` don't autocomplete
- Tools don't show in menu

**Solutions:**

1. **Verify `.mcp.json` exists:**
   ```bash
   ls -la .mcp.json
   # Should be in project root
   ```

2. **Check `.mcp.json` format:**
   ```bash
   cat .mcp.json
   ```
   Must have:
   ```json
   {
     "mcpServers": {
       "kgrag": {
         "command": "kgrag",
         "args": ["mcp", "--registry", "/ABSOLUTE/PATH/to/registry.sqlite"]
       }
     }
   }
   ```
   ⚠️ **Paths must be absolute (not `~`)**

3. **Use the setup script:**
   ```bash
   bash ~/.claude/skills/kgrag/scripts/setup-kgrag-mcp.sh
   ```

4. **Restart Claude Code:**
   - Fully quit Claude Code (not just close tab)
   - Reopen project
   - Tools should appear

5. **Test MCP server:**
   ```bash
   kgrag mcp --help
   # Should show "MCP server starting..."
   ```

---

### ❌ "MCP tools fail" with errors

**Symptoms:**
- Tool call returns error: "Registry not found"
- Other MCP errors

**Solutions:**

1. **Check registry path in `.mcp.json`:**
   ```bash
   grep registry .mcp.json
   # Path must be absolute (e.g., /home/user/.kgrag/registry.sqlite)
   # NOT /home/user/~/.kgrag/registry.sqlite
   ```

2. **Verify registry file exists:**
   ```bash
   ls -la /absolute/path/to/registry.sqlite
   ```

3. **If registry path is wrong, update `.mcp.json`:**
   ```bash
   echo $KGRAG_REGISTRY
   # Copy this path to .mcp.json
   ```

4. **Restart Claude Code after editing `.mcp.json`.**

---

## Performance Issues

### ❌ "Build takes too long"

**Symptoms:**
- `kgrag init` runs for 10+ minutes
- Appears stuck

**Solutions:**

1. **Be patient (builds are slow):**
   Large codebases (10k+ files) take 5–15 minutes.

2. **Check if process is alive:**
   ```bash
   ps aux | grep codekg
   # Should show active process
   ```

3. **If truly stuck (no activity for 30 min):**
   ```bash
   pkill -f "codekg build"
   # Retry with smaller scope:
   kgrag init ~/repos/myproject --layer code  # skip doc layer if huge
   ```

4. **Reduce batch size (if available):**
   ```bash
   CODEKG_BATCH_SIZE=50 kgrag init ~/repos/myproject
   ```

---

### ❌ "High memory usage"

**Symptoms:**
- System runs out of memory during build
- Process killed or system freezes

**Solutions:**

1. **Close other applications** to free RAM.

2. **Build in background:**
   ```bash
   nohup kgrag init ~/repos/myproject > build.log 2>&1 &
   tail -f build.log  # monitor progress
   ```

3. **Build layers separately:**
   ```bash
   kgrag init --layer code
   # Wait for completion, then:
   kgrag init --layer doc
   ```

---

## Installation Issues

### ❌ "Command not found: kgrag"

**Solutions:**

1. **Install KGRAG:**
   ```bash
   pip install kgrag
   ```

2. **If using Poetry:**
   ```bash
   poetry add kgrag
   poetry run kgrag list
   ```

3. **Add to PATH (if local venv):**
   ```bash
   export PATH="$HOME/.venv/bin:$PATH"
   # Add to ~/.bashrc or ~/.zshrc for persistence
   ```

---

### ❌ "Wrong Python environment"

**Solutions:**

1. **Check which `kgrag` is running:**
   ```bash
   which kgrag
   ```

2. **Activate correct venv:**
   ```bash
   source ~/.venv/bin/activate
   # or for Poetry:
   poetry shell
   ```

3. **Ensure consistent environment:**
   ```bash
   export KGRAG_REGISTRY=$HOME/.kgrag/registry.sqlite
   # Add to ~/.bashrc or ~/.zshrc
   ```

---

## Getting Additional Help

### Check KGRAG logs

```bash
# Most commands output errors with context
kgrag init --wipe 2>&1 | tail -50
```

### Run with verbose output

```bash
python -m kgrag query "term" -v
```

### Check registry integrity

```bash
sqlite3 ~/.kgrag/registry.sqlite ".tables"
# Should show: entries, kgs
```

### Open an issue

Include:
- `kgrag --version`
- `kgrag status` output
- Steps to reproduce
- Full error messages

---

## See Also

- [INSTALLATION.md](INSTALLATION.md) — Setup instructions
- [USAGE.md](USAGE.md) — Commands and workflows
- [VISION.md](VISION.md) — Philosophy and design
