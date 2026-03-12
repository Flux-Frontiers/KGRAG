# Sync MCP Documentation

You are updating all CodeKG MCP documentation and provider instructions to reflect the
current state of `src/code_kg/mcp_server.py`. Execute the following steps in order.

---

## Step 0: Establish the Source of Truth

Read `src/code_kg/mcp_server.py` and extract the **authoritative tool list**:

1. Find every `@mcp.tool()` decorated function — these are the live MCP tools.
2. For each tool, record:
   - **Name** and **signature** (function name + parameters with defaults)
   - **One-line description** from the first line of its docstring
   - **Return type** (JSON vs Markdown)
   - **When to use** (from the docstring)
3. Print the complete tool inventory before proceeding. This is your ground truth.

**Example format:**
```
TOOL INVENTORY (from mcp_server.py):
  1. graph_stats()                          → JSON   — node/edge counts by kind/relation
  2. query_codebase(q, k, hop, rels, ...)   → JSON   — hybrid semantic + structural search
  3. pack_snippets(q, k, hop, ...)          → MD     — source-grounded snippet extraction
  4. get_node(node_id, include_edges)       → JSON   — single node lookup + optional neighborhood
  5. callers(node_id, rel, paths)           → JSON   — reverse edge lookup / fan-in analysis
  6. explain(node_id)                       → MD     — natural-language node explanation
  7. analyze_repo()                         → MD     — full nine-phase architectural analysis
  8. snapshot_list(limit)                   → JSON   — temporal snapshots, newest first
  9. snapshot_show(key)                     → JSON   — full snapshot details
 10. snapshot_diff(key_a, key_b)            → JSON   — side-by-side snapshot comparison
```

---

## Step 1: Update Primary Documentation

### 1a. `docs/MCP.md`

This is the full MCP reference guide. Update:

- **Overview table** — Must list every tool with correct signature and one-line description.
  Count must match actual tool count ("Once configured, the agent gains N tools").
- **Section 11 "Available Tools Reference"** — Each tool must have its own `###` subsection with:
  - Correct heading (function signature)
  - "When to use" guidance
  - Full parameter table (name, type, default, description)
  - Return value description
- **Add any missing tool sections.** If a tool has no section, add one after the existing sections,
  following the existing format exactly.
- **Remove or update stale sections** for tools that were renamed or removed.
- **Section 9 `/setup-mcp` example output** — The "Available tools once active:" bullet list
  must include all tools.
- **Section 12 "Typical agent workflow"** — Update to show new tools at appropriate steps.
- **Summary table** at the bottom — Update the tool count and comma-separated tool list.

### 1b. `docs/CHEATSHEET.md`

- **Header table** ("The N Tools at a Glance") — Update N and add/remove rows to match
  the tool inventory. Each row: tool name+signature | best for | return format.
- **Per-tool sections** — Ensure a dedicated section exists for every tool.
  For tools without sections, add compact examples-first sections (see existing style).
- **Section intro line** ("A practical reference for the N MCP tools") — Update N.
- **Section numbering** — Renumber sections sequentially after any insertions.

---

## Step 2: Update Provider-Specific Files

Work through each file below. For each, apply only the changes relevant to that file's format.
Do NOT homogenize formats — each file has its own style.

### 2a. `README.md`

- **Features list** — The `- **MCP server** —` bullet must list the correct count ("Ten tools")
  and all tool names in the parenthetical.
- **"Available Tools" table** (in the MCP section) — Each tool needs a row with correct
  signature and description. Add missing tools; update changed signatures.

### 2b. `.claude/skills/codekg/SKILL.md`

- **Frontmatter `description:` field** — The `using the graph_stats / ... MCP tools` list
  must include all tools by name (slash-separated).
- **"## MCP Tools" table** — Two-column (Tool | When to use). Every tool must appear with
  correct signature. Missing tools: add a row. Changed signatures: update in place.
- **"### Typical session workflow"** code block — Update numbered steps to reflect the
  recommended tool sequence including any new tools.

### 2c. `.claude/skills/codekg/references/CHEATSHEET.md`

This is the portable cheatsheet for use in other repos. It mirrors `docs/CHEATSHEET.md`
but uses generic examples (not code_kg-specific node IDs where possible).

- Apply the same changes as `docs/CHEATSHEET.md`:
  - Header table N and rows
  - Missing tool sections (use compact style)
  - Section numbering

### 2d. `.claude/skills/codekg/clinerules.md`

This is a template for `.clinerules` in repos using Cline. It contains an "Available tools"
bulleted list inside a code fence. Update:

- Add missing tools as new bullet points following the existing verbose style:
  ```
  - **tool_name(params)** — What it does. When to use it.
  ```
- Update signatures for any changed tools.
- Do NOT change the surrounding structure (it's a copy-paste template).

### 2e. `.vscode/copilot-instructions.md`

GitHub Copilot instructions. Update the "## MCP Integration" bulleted list:

- Each tool gets one line: `` - `tool_name(params)` — description ``
- Add missing tools; update signatures; remove removed tools.

---

## Step 3: Update CLAUDE.md MCP Instructions (if present)

Check `CLAUDE.md` in the repo root for any MCP tool tables or lists. If found, apply the
same updates (tool count, signatures, descriptions) following that file's existing format.

---

## Step 4: Consistency Check

After all edits, verify consistency:

1. **Tool count** — The count in each file matches the actual number of `@mcp.tool()` functions.
2. **Signatures** — Every file uses the same parameter names and defaults as `mcp_server.py`.
3. **No phantom tools** — No file references a tool name that no longer exists in `mcp_server.py`.
4. **No missing tools** — Every tool in `mcp_server.py` appears in every file.

If inconsistencies are found, fix them before proceeding.

---

## Step 5: Stage and Prepare Commit

1. Stage all modified documentation files:
   ```bash
   git add docs/MCP.md docs/CHEATSHEET.md README.md \
           .claude/skills/codekg/SKILL.md \
           .claude/skills/codekg/references/CHEATSHEET.md \
           .claude/skills/codekg/clinerules.md \
           .vscode/copilot-instructions.md
   ```
   Add `CLAUDE.md` if it was modified.

2. Write `commit.txt` with a conventional commit message:
   ```
   docs(mcp): sync all provider docs to N-tool MCP surface

   Updated tool inventory: [list added/removed/changed tools]

   Files updated:
   - docs/MCP.md: ...
   - docs/CHEATSHEET.md: ...
   - README.md: ...
   - .claude/skills/codekg/SKILL.md: ...
   - .claude/skills/codekg/references/CHEATSHEET.md: ...
   - .claude/skills/codekg/clinerules.md: ...
   - .vscode/copilot-instructions.md: ...

   Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>
   ```

---

## Completion

After all steps, print a summary:

```
✓ Source of truth: N tools extracted from mcp_server.py
✓ docs/MCP.md          — updated (N tools, M sections)
✓ docs/CHEATSHEET.md   — updated (N tools, sections renumbered)
✓ README.md            — updated (features list + tools table)
✓ SKILL.md             — updated (frontmatter + MCP Tools table)
✓ references/CHEATSHEET.md — updated (N tools, compact style)
✓ clinerules.md        — updated (N tools in template block)
✓ copilot-instructions.md  — updated (MCP Integration list)

Files staged. Ready to commit with: git commit -F commit.txt
```

---

## Rules

- **mcp_server.py is always the source of truth.** Never invent tool names or parameters.
- **Preserve each file's style.** Don't homogenize formats across files.
- **Minimal diffs.** Only change what is wrong or missing. Don't rewrite sections that are correct.
- **Compact style in clinerules and SKILL.md.** One line per tool in tables; multi-line bullets in clinerules.
- **Full reference style in MCP.md.** Every tool gets a complete `###` section.
- **Examples style in CHEATSHEET.md.** Show actual call syntax, not just descriptions.
