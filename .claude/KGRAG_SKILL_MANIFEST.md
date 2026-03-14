# KGRAG Skill Manifest

## Overview

**KGRAG is the unified abstraction over CodeKG, DocKG, and MetaKG.**

> One registry. Many KGs. Infinite queries.

This manifest tracks the KGRAG skill and related documentation created to support its adoption and usage.

---

## The Vision Realized

KGRAG achieves:

✅ **Single Registry** manages CodeKG, DocKG, MetaKG instances
- Centralized discovery and metadata
- Consistent entry points across projects
- Cross-project knowledge federation

✅ **Federated Queries** across all KGs simultaneously
- One query string, results from all KGs
- Global relevance ranking
- Cross-domain pattern discovery

✅ **Unified CLI** for initialization, querying, analysis, visualization
- Same commands work across all KG types
- Consistent flags, options, and output
- Seamless workflow from discovery to analysis

✅ **MCP Integration** for Claude Code/Desktop
- Knowledge graphs become agent tools
- Semantic search in prompts
- Context extraction for LLM tasks

✅ **Complete Documentation & Skills** for users and agents
- Comprehensive skill with progressive disclosure
- Installation, usage, troubleshooting guides
- Helper scripts and automation examples

---

## Skill Location

**Local skill:** `~/.claude/skills/kgrag/`

### Structure

```
kgrag/
├── SKILL.md (6.7K)
│   • Lean core guidance with quick start
│   • Core concepts (registry, KG layers, federation)
│   • CLI summary with environment variables
│   • Best practices and troubleshooting links
│
├── references/
│   ├── cli-reference.md (8.5K)
│   │   • All 12 commands documented
│   │   • Options, examples, output formats
│   │   • Global options and environment variables
│   │
│   ├── workflows.md (9.5K)
│   │   • 10 practical multi-step procedures
│   │   • Setup, querying, LLM context, analysis
│   │   • MCP integration, multi-project federation
│   │   • Debugging and automation patterns
│   │
│   └── troubleshooting.md (12K)
│       • Common issues and solutions
│       • Registry & initialization issues
│       • Querying, snippets, visualizer problems
│       • MCP integration, performance troubleshooting
│
└── scripts/
    ├── batch-init.sh (1.5K)
    │   • Initialize multiple projects at once
    │   • Colored output with success/failure counts
    │
    └── setup-kgrag-mcp.sh (1.9K)
        • Configure .mcp.json for Claude Code
        • Auto-detect registry path
        • Verify MCP server availability
```

### Usage

The skill is automatically discovered by Claude Code and other MCP clients. It triggers when users ask about:
- Setting up KGRAG in projects
- Querying across multiple KGs
- Extracting code/doc snippets for LLM context
- Integrating with Claude Code or Claude Desktop
- Running architectural analyses
- Managing the KG registry
- Troubleshooting KG-related issues

---

## Documentation

**Location:** `/Users/egs/repos/kgrag/docs/`

### Vision Document

**File:** `docs/VISION.md`

Captures the strategic vision and philosophy:
- What KGRAG achieves
- Design philosophy (one contract, progressive disclosure, composability, resilience)
- Multi-phase roadmap (foundation, integration, documentation, ecosystem)
- Getting started guide

**Audience:** Strategic understanding, architectural decision-making, stakeholder communication

### Installation Guide

**File:** `docs/INSTALLATION.md`

Step-by-step setup instructions:
- Prerequisites and installation options
- Initial setup (5-minute quickstart)
- Multi-project federation
- MCP configuration for Claude Code
- Environment variables
- Offline installation
- Troubleshooting installation issues

**Audience:** New users, operators, DevOps

### Usage Guide

**File:** `docs/USAGE.md`

Comprehensive usage documentation:
- 5-minute quick start
- Core workflows (search, LLM context, multi-project, analysis, exploration)
- Command reference
- Configuration options
- Tips & best practices
- Automation & scripting examples
- Common troubleshooting

**Audience:** Regular users, power users, automation engineers

### Troubleshooting Guide

**File:** `docs/TROUBLESHOOTING.md`

Problem-solving reference:
- Quick diagnostics commands
- Registry & initialization issues
- Querying problems
- Snippet pack issues
- Visualizer issues
- MCP integration problems
- Performance issues
- Installation issues
- Getting additional help

**Audience:** Users encountering issues, support team, debugging

---

## Documentation Strategy

### Progressive Disclosure

1. **Quick Start** (`VISION.md` intro, `INSTALLATION.md` quick setup)
   - Get running in 5 minutes
   - Minimal configuration

2. **Core Workflows** (`USAGE.md`)
   - Common tasks and patterns
   - Configuration options
   - Best practices

3. **Deep Reference** (Skill `cli-reference.md`, `workflows.md`)
   - All commands documented
   - Advanced workflows
   - Automation examples

4. **Problem-Solving** (`TROUBLESHOOTING.md`, Skill `troubleshooting.md`)
   - Common issues and solutions
   - Diagnostic steps
   - Error messages explained

### Information Architecture

```
docs/ (Repository documentation)
├── VISION.md — Strategic vision & philosophy
├── INSTALLATION.md — Setup & configuration
├── USAGE.md — Commands, workflows, examples
└── TROUBLESHOOTING.md — Issues & solutions

~/.claude/skills/kgrag/ (Skill documentation)
├── SKILL.md — Lean core guidance (triggers skill)
└── references/
    ├── cli-reference.md — Detailed command reference
    ├── workflows.md — 10 practical procedures
    └── troubleshooting.md — Skill-level troubleshooting
```

**Key distinction:**
- `docs/` → Project-wide documentation for all users
- `skills/kgrag/` → AI agent knowledge for Claude Code, Cursor, etc.

---

## Helper Scripts

Located at: `~/.claude/skills/kgrag/scripts/`

### batch-init.sh

Multi-project initialization helper.

**Usage:**
```bash
bash ~/.claude/skills/kgrag/scripts/batch-init.sh \
  ~/repos/project1 \
  ~/repos/project2 \
  ~/repos/project3
```

**Features:**
- Initialize multiple projects
- Color-coded output (success/failure)
- Summary report
- Optional `--wipe` flag for full rebuild

### setup-kgrag-mcp.sh

MCP configuration helper for Claude Code.

**Usage:**
```bash
cd ~/repos/myproject
bash ~/.claude/skills/kgrag/scripts/setup-kgrag-mcp.sh
```

**Features:**
- Auto-detect registry path
- Create `.mcp.json` with absolute paths
- Test MCP server availability
- Backup existing `.mcp.json`

---

## Relation to Core KGRAG

This skill and documentation complement the core KGRAG CLI:

**Core KGRAG** (`src/kg_rag/`)
- Registry management
- Adapter orchestration
- CLI commands
- MCP server
- Streamlit visualizer

**KGRAG Skill & Docs**
- Knowledge base for users and agents
- Progressive disclosure of complexity
- Automation helpers
- Strategic vision and design philosophy

Together, they form the complete KGRAG ecosystem.

---

## Version History

- **v1.0** (2026-03-14)
  - Initial skill creation with comprehensive references
  - Four documentation guides (Vision, Installation, Usage, Troubleshooting)
  - Two helper scripts (batch-init, setup-kgrag-mcp)
  - Integration with local KGRAG repository

---

## Maintenance

### Regular Updates

1. **Skill & References:** Update when CLI commands change
2. **Docs:** Update when workflows or configuration changes
3. **Scripts:** Test when KGRAG dependencies update
4. **This Manifest:** Update with significant changes

### Review Checklist

- [ ] CLI commands match docs
- [ ] Examples still work
- [ ] Links are valid
- [ ] Version numbers are current
- [ ] Scripts are tested

---

## Related Resources

- **Project:** https://github.com/flux-frontiers/kgrag
- **CodeKG Skill:** `~/.claude/skills/codekg/`
- **DocKG Skill:** `~/.claude/skills/dockg/`
- **KGRAG CLI:** `poetry run kgrag --help`

---

## See Also

- [VISION.md](../../docs/VISION.md) — Strategic vision
- [INSTALLATION.md](../../docs/INSTALLATION.md) — Setup guide
- [USAGE.md](../../docs/USAGE.md) — Usage guide
- [TROUBLESHOOTING.md](../../docs/TROUBLESHOOTING.md) — Troubleshooting
