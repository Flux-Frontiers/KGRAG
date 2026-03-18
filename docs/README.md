# KGRAG Documentation

**KGRAG is the unified abstraction over CodeKG, DocKG, and MetaKG.**

> One registry. Many KGs. Infinite queries.

This directory contains comprehensive documentation for KGRAG users and developers.

---

## 🎯 Quick Start

**New to KGRAG?** Start here:

1. **[VISION.md](VISION.md)** (5 min read)
   - What KGRAG is and what it achieves
   - Design philosophy and roadmap
   - High-level overview

2. **[INSTALLATION.md](INSTALLATION.md)** (10 min setup)
   - Prerequisites and installation
   - Initial setup (5-minute quickstart)
   - MCP configuration for Claude Code

3. **[USAGE.md](USAGE.md)** (reference)
   - Core workflows with examples
   - Command reference
   - Tips and best practices

4. **[TROUBLESHOOTING.md](TROUBLESHOOTING.md)** (as needed)
   - Common issues and solutions
   - Diagnostic steps
   - Getting help

---

## 📚 Documentation Map

### For Understanding KGRAG

| Document | Purpose | Read Time |
|----------|---------|-----------|
| [FEATURES.md](FEATURES.md) | Complete feature list — all capabilities, commands, and data types | 5 min |
| [VISION.md](VISION.md) | Strategic vision, philosophy, roadmap, Forest of Knowledge | 8 min |
| [INSTALLATION.md](INSTALLATION.md) | Setup, configuration, and verification | 10 min |
| [USAGE.md](USAGE.md) | Commands, workflows, examples, best practices | 20 min |
| [TROUBLESHOOTING.md](TROUBLESHOOTING.md) | Common issues and solutions | Reference |
| [SEMANTIC_CHUNKING.md](SEMANTIC_CHUNKING.md) | Chunking strategies, parameters, and storage layout | 5 min |

### For AI Agents

The **KGRAG Skill** at `~/.claude/skills/kgrag/` provides:
- Lean core guidance (SKILL.md)
- Detailed CLI reference (cli-reference.md)
- 10 practical workflows (workflows.md)
- Comprehensive troubleshooting (troubleshooting.md)

Agents automatically trigger this skill when asked about KGRAG setup, usage, integration, or troubleshooting.

---

## 🎓 Learning Paths

### Path 1: Five-Minute Intro
1. Read this README
2. Read [VISION.md](VISION.md) intro
3. Run the quick start in [INSTALLATION.md](INSTALLATION.md)
4. Try: `kgrag query "your search term"`

**Time:** 5 minutes
**Outcome:** KGRAG initialized and working

### Path 2: Complete Setup
1. Read [VISION.md](VISION.md) — understand the philosophy
2. Follow [INSTALLATION.md](INSTALLATION.md) — step by step
3. Set up MCP for Claude Code (INSTALLATION.md section)
4. Try workflows in [USAGE.md](USAGE.md)

**Time:** 30 minutes
**Outcome:** Fully configured KGRAG with MCP integration

### Path 3: Mastery
1. Complete Path 2
2. Read [USAGE.md](USAGE.md) thoroughly — all workflows and tips
3. Review Skill references: `~/.claude/skills/kgrag/references/`
4. Practice automation examples (USAGE.md scripting section)
5. Bookmark [TROUBLESHOOTING.md](TROUBLESHOOTING.md) for reference

**Time:** 2 hours
**Outcome:** Confident usage of all KGRAG features

### Path 4: Troubleshooting
1. Run: `kgrag status`
2. Describe your issue
3. Find it in [TROUBLESHOOTING.md](TROUBLESHOOTING.md)
4. Follow the solutions

**Time:** 5–15 minutes
**Outcome:** Issue resolved

---

## 🚀 Common Workflows

### Initialize KGRAG
```bash
cd ~/repos/myproject
kgrag init
```
**See:** [INSTALLATION.md](INSTALLATION.md#1-initialize-your-first-project)

### Query Across KGs
```bash
kgrag query "your search term"
kgrag query "term" --kind code -k 5
```
**See:** [USAGE.md](USAGE.md#workflow-1-federated-search)

### Extract Context for LLM
```bash
kgrag pack "pattern" --out context.md
```
**See:** [USAGE.md](USAGE.md#workflow-2-extracting-context-for-llm)

### Set Up MCP for Claude Code
```bash
bash ~/.claude/skills/kgrag/scripts/setup-kgrag-mcp.sh
# Restart Claude Code
```
**See:** [INSTALLATION.md](INSTALLATION.md#configure-mcp-for-claude-code)

### Run Architectural Analysis
```bash
kgrag viz
# → 🧪 Analysis tab → Select KG → Run Analysis
```
**See:** [USAGE.md](USAGE.md#workflow-4-interactive-exploration-with-visualizer)

### Troubleshoot Missing Results
```bash
kgrag status
kgrag query "term"
```
**See:** [TROUBLESHOOTING.md](TROUBLESHOOTING.md#-no-results-found)

---

## 🔧 The Vision Realized

KGRAG achieves:

✅ **Single Registry** manages CodeKG, DocKG, MetaKG instances
- Centralized discovery and metadata
- Consistent entry points across projects
- Cross-project knowledge federation

✅ **Federated Queries** across all KGs simultaneously
- One query string, results from all KGs
- Global relevance ranking
- Cross-domain pattern discovery

✅ **Knowledge Compiler Model** — build cost paid once, queries are free
- Embedding is the slow step, like compiling a large Fortran program
- Post-build queries run in under a second on commodity hardware
- Snapshot system enables differential queries: *what changed since last week?*

✅ **Unified CLI** for initialization, querying, analysis, visualization
- Same commands work across all KG types
- Consistent flags, options, and output
- Seamless workflow from discovery to analysis

✅ **MCP Integration** for Claude Code/Desktop
- Knowledge graphs become agent tools
- Semantic search in prompts
- Context extraction for LLM tasks

✅ **Incremental Ingestion with Restart**
- Large corpora ingest in batches with diversity-preserving sampling
- Resumable state: each run picks up where the last left off
- Corpus is queryable throughout — no waiting for full ingestion

✅ **Complete Documentation** for users and agents
- Comprehensive guides and references
- Skills and helper scripts
- Strategic vision and design philosophy

**Users and agents now have everything they need to leverage the power of multiple knowledge graph backends under one abstraction.** 🕸️

---

## 📖 Document Summaries

### VISION.md
**What:** Strategic philosophy and long-term roadmap
**For whom:** Decision makers, architects, new users wanting context
**Length:** ~10 minutes
**Key sections:**
- What KGRAG achieves
- Design philosophy
- Multi-phase roadmap
- Getting started

### INSTALLATION.md
**What:** Step-by-step setup and configuration
**For whom:** First-time users, DevOps engineers
**Length:** ~10 minutes setup, reference thereafter
**Key sections:**
- Installation options (pip, Poetry, source)
- Initial setup (5-minute quickstart)
- Multi-project federation
- MCP configuration
- Offline installation
- Troubleshooting

### USAGE.md
**What:** Comprehensive usage guide with examples
**For whom:** Regular users, power users, automation engineers
**Length:** ~20 minutes to read, ongoing reference
**Key sections:**
- Quick start (5 min)
- Core workflows (search, snippets, analysis, exploration)
- Command reference
- Configuration options
- Best practices and tips
- Automation & scripting
- Troubleshooting common issues

### TROUBLESHOOTING.md
**What:** Problem diagnosis and resolution
**For whom:** Users encountering issues, support team
**Length:** Reference (consult as needed)
**Key sections:**
- Quick diagnostics
- Registry & initialization issues
- Querying problems
- Visualizer issues
- MCP integration
- Performance troubleshooting
- Installation issues

---

## 🆘 Getting Help

### Before Opening an Issue

1. **Check [TROUBLESHOOTING.md](TROUBLESHOOTING.md)** — your issue is likely documented there
2. **Run diagnostics:**
   ```bash
   kgrag --version
   kgrag status
   kgrag list
   ```
3. **Check your setup:**
   ```bash
   echo $KGRAG_REGISTRY
   ls ~/.grag/registry.sqlite
   ```

### Opening an Issue

Include:
- `kgrag --version` output
- `kgrag status` output
- Steps to reproduce
- Full error messages
- What you expect vs. what happened

**See [TROUBLESHOOTING.md](TROUBLESHOOTING.md#getting-additional-help) for more.**

---

## 📋 Related Resources

- **KGRAG Repository:** https://github.com/flux-frontiers/kgrag
- **KGRAG Skill:** `~/.claude/skills/kgrag/`
- **Skill Manifest:** `.claude/KGRAG_SKILL_MANIFEST.md`
- **CodeKG Documentation:** CodeKG skill in Claude Code
- **DocKG Documentation:** DocKG skill in Claude Code

---

## ✨ Key Concepts

### The Registry
Central SQLite database tracking all registered KGs (`~/.kgrag/registry.sqlite`).

### KG Layers
Individual knowledge graphs for a repository:
- **Code layer** — Python code analysis (CodeKG)
- **Doc layer** — Markdown analysis (DocKG)
- **Meta layers** — Domain-specific graphs (MetaKG)

One repository can have multiple layers.

### The Compilation Model
Build = compile. Embedding nodes into vectors is the expensive step, paid once at build time. Queries execute against the pre-built index in milliseconds — exactly like running a compiled binary.

### Federated Query
Single query searches all registered KGs simultaneously. Results are ranked globally by relevance.

### Differential Query
Compare two snapshots to ask *what changed?* — new nodes, new edges, new topics. Enables questions like "what new ideas entered the Pepys corpus this week?" via differential federated search.

### Adapters
Uniform interface over CodeKG, DocKG, MetaKG. Handles library presence, error conditions, and consistent output.

### Forest of Knowledge
Planned visual rendering: each KG as a fractal tree whose size, colour, and branching encode its graph properties. Corpora render as groves; the TreeOfKnowledge(tm) is the full forest. See [VISION.md](VISION.md) and [TREE_VISUALIZER_PLAN.md](TREE_VISUALIZER_PLAN.md).

---

## 🎯 Next Steps

1. **Just starting?** → Read [VISION.md](VISION.md), then [INSTALLATION.md](INSTALLATION.md)
2. **Ready to use?** → Jump to [USAGE.md](USAGE.md)
3. **Hit an issue?** → Check [TROUBLESHOOTING.md](TROUBLESHOOTING.md)
4. **Need agent help?** → Ask Claude Code about "KGRAG setup" or "KGRAG query"

---

**Last updated:** 2026-03-14
**KGRAG Version:** Latest
**Status:** Actively maintained
