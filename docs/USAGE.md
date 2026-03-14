# KGRAG Usage Guide

## Quick Start (5 minutes)

```bash
# 1. Initialize KGRAG for a project
cd ~/repos/myproject
kgrag init

# 2. Query all registered KGs
kgrag query "database connection setup"

# 3. Launch interactive visualizer
kgrag viz
# Open http://localhost:8501 in browser
```

That's it! KGRAG is now managing your KGs and you can start querying.

---

## Core Workflows

### Workflow 1: Federated Search

Query across all registered KGs simultaneously:

```bash
# Search all KGs
kgrag query "authentication flow"

# Search code KGs only
kgrag query "error handling" --kind code -k 5

# Search documentation only
kgrag query "REST API" --kind doc

# Get more results
kgrag query "transaction patterns" -k 12
```

**What happens:**
1. KGRAG searches all matching KGs
2. Results are ranked globally by relevance
3. Output shows KG source + node details + score

### Workflow 2: Extracting Context for LLM

Prepare markdown snippets for LLM analysis:

```bash
# Extract snippets across all KGs
kgrag pack "database transaction patterns"

# Extract to file
kgrag pack "error handling" --out context.md

# Code only, with minimal context
kgrag pack "API design" --kind code --context 2 -k 5

# High volume for comprehensive context
kgrag pack "authentication" -k 12 --context 10 --out auth_context.md
```

**Output:** Markdown file with:
- Source code snippets with line numbers
- File paths and KG names
- Relevance scores
- Ready to paste into LLM prompts

### Workflow 3: Setting Up Multiple Projects

Federate multiple projects under one registry:

```bash
# Initialize each project
kgrag init ~/repos/backend --name backend
kgrag init ~/repos/frontend --name frontend
kgrag init ~/repos/docs --name docs

# Or use batch script
bash ~/.claude/skills/kgrag/scripts/batch-init.sh \
  ~/repos/backend ~/repos/frontend ~/repos/docs

# Verify all registered
kgrag status
kgrag list

# Now queries search all projects
kgrag query "caching strategy"
```

**Result:** All projects are federated. One query searches all.

### Workflow 4: Interactive Exploration with Visualizer

Use the Streamlit UI for interactive exploration:

```bash
# Launch visualizer
kgrag viz

# Open http://localhost:8501
```

**Features:**
- 📋 **Registry tab** — Browse all KGs, view metadata, check build status
- 🔍 **Federated Query** — Search all KGs, display results ranked or by KG
- 🧪 **Analysis** — Run architectural analysis on CodeKGs
- 📦 **Snippet Pack** — Extract snippets with configurable parameters

### Workflow 5: Architectural Analysis

Analyze a CodeKG for complexity, dependencies, and patterns:

```bash
# Quick overview
kgrag analyze

# Or use visualizer
kgrag viz
# → Go to 🧪 Analysis tab
# → Select a CodeKG
# → Click "Run Analysis"
```

**Output includes:**
- Complexity hotspots (most important nodes)
- High fan-out functions (API entry points)
- Module architecture and coupling
- Critical issues (circular dependencies, orphaned code)
- Docstring coverage percentage

---

## Command Reference

### Basic Commands

```bash
# List all registered KGs
kgrag list

# Quick health check
kgrag status

# Detailed info for a specific KG
kgrag info myproject-code

# Get KG statistics
kgrag analyze
```

### Query Commands

```bash
# Semantic search
kgrag query "your search term"
kgrag query "term" --kind code -k 5
kgrag query "term" --kind doc
kgrag query "term" --json  # JSON output

# Extract snippets
kgrag pack "term"
kgrag pack "term" --out file.md
kgrag pack "term" --context 3 -k 5
```

### Management Commands

```bash
# Initialize/rebuild
kgrag init ~/repos/myproject
kgrag init ~/repos/myproject --wipe  # Full rebuild

# Manual registration (rarely needed)
kgrag register --name mykg --kind code --repo ~/repos/myproject

# Remove from registry
kgrag unregister mykg

# Auto-discover existing KGs
kgrag scan ~/repos
```

### Integration Commands

```bash
# Launch visualizer
kgrag viz
kgrag viz --port 8502  # Custom port

# Start MCP server (for Claude Code)
kgrag mcp
```

---

## Environment & Configuration

### Registry Path

By default, KGRAG uses `~/.kgrag/registry.sqlite`. To use a custom path:

```bash
# Set environment variable
export KGRAG_REGISTRY=/custom/path/registry.sqlite

# Or pass to each command
kgrag init ~/repos/myproject --registry /custom/path/registry.sqlite
```

### KG Layers

By default, `kgrag init` auto-detects applicable layers (code, doc). To be explicit:

```bash
# Code layer only
kgrag init --layer code

# Both layers
kgrag init --layer code --layer doc

# Custom name
kgrag init --name myproject-code
```

### Rebuilding KGs

```bash
# After refactoring: full rebuild (wipe old data)
kgrag init --wipe

# Minor changes: incremental update (no wipe)
kgrag init
```

---

## Tips & Best Practices

### Querying Effectively

✅ **Do:**
- Use specific terms: "JWT validation" not "auth"
- Filter by kind when appropriate: `--kind code`
- Start with small k: `-k 3` for focused results
- Adjust k upward for broad surveys: `-k 12`

❌ **Don't:**
- Use vague terms: "database" (too broad)
- Query everything simultaneously (use filters)
- Assume first result is best (check top 5)

### Managing the Registry

✅ **Do:**
- Keep one registry (`~/.kgrag/registry.sqlite`) for your workspace
- Use meaningful names: `project-name-code`, `project-name-doc`
- Run `kgrag status` monthly to catch issues
- Rebuild quarterly: `kgrag init --wipe`

❌ **Don't:**
- Create multiple registries (confusing)
- Use ambiguous names
- Ignore "not built" warnings
- Let data get stale (9+ months old)

### MCP Integration

✅ **Do:**
- Use absolute paths in `.mcp.json`
- Restart Claude Code after creating `.mcp.json`
- Test with `kgrag mcp --help`
- Use in prompts: `kgrag_query("term", k=8)`

❌ **Don't:**
- Use relative paths like `~`
- Assume tools appear without restart
- Hardcode paths in `.mcp.json`

### Preparing LLM Context

✅ **Do:**
- Extract focused snippets: `-k 5 --context 3`
- Filter by kind: `--kind code`
- Review output before sharing
- Set aside large files: `wc -l context.md`

❌ **Don't:**
- Extract everything at once (`-k 100`)
- Mix all KG types (code + docs separately)
- Share without reviewing
- Exceed LLM context window

---

## Automation & Scripting

### Batch Initialization

```bash
# Use the provided script
bash ~/.claude/skills/kgrag/scripts/batch-init.sh \
  ~/repos/project1 \
  ~/repos/project2 \
  ~/repos/project3
```

### JSON Output for Parsing

```bash
# Get results as JSON
kgrag query "term" --json > results.json

# Parse with jq
jq '.hits | length' results.json
jq '.hits[0]' results.json

# Process in Python
python << 'EOF'
import json
with open('results.json') as f:
    data = json.load(f)
    for hit in data['hits']:
        print(f"{hit['kg_name']}: {hit['name']} ({hit['score']:.3f})")
EOF
```

### Scheduled Rebuilds

```bash
# Add to crontab for monthly rebuilds
0 0 1 * * kgrag init ~/repos/myproject --wipe

# Or use a shell alias
alias kgrag-refresh='kgrag init ~/repos/project1 --wipe && kgrag init ~/repos/project2 --wipe'
```

---

## Troubleshooting Common Issues

### "No results found"

```bash
# Check registry health
kgrag status

# If KG is "not built", rebuild
kgrag init ~/repos/myproject --wipe

# Try broader query
kgrag query "your search"  # remove --kind filter

# Increase result count
kgrag query "term" -k 12
```

### "Registry not loading" in visualizer

```bash
# Check registry path
echo $KGRAG_REGISTRY

# Click "🔄 Refresh Registry" in sidebar
# Or restart visualizer
```

### "MCP tools not appearing" in Claude Code

```bash
# Verify .mcp.json exists and has absolute paths
cat .mcp.json

# Verify registry path is absolute
grep registry .mcp.json

# Restart Claude Code (fully quit and reopen)

# Test MCP server
kgrag mcp --help
```

For more troubleshooting, see [TROUBLESHOOTING.md](TROUBLESHOOTING.md).

---

## See Also

- [INSTALLATION.md](INSTALLATION.md) — Setup and configuration
- [TROUBLESHOOTING.md](TROUBLESHOOTING.md) — Issues and solutions
- [VISION.md](VISION.md) — Philosophy and design
