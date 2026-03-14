---
name: kgrag-usage
description: "Use KGRAG to query across federated knowledge graphs (code, docs, metabolic) and manage cross-KG registries. Triggers when: searching multiple repos/KGs simultaneously, initializing KGs in new repos, querying code patterns across projects, extracting multi-KG snippets, or managing registry status."
---

# KGRAG Usage

## Overview

KGRAG is the **federated query layer** for CodeKG, DocKG, and MetaKG. It maintains a central registry of all knowledge graphs across all repositories and enables cross-KG semantic search, snippet extraction, and batch operations. Use KGRAG when you need to search or analyze code/docs across multiple projects simultaneously.

## Core Commands

### Query Across KGs
Search all registered knowledge graphs with a natural-language query:

```bash
kgrag query "database connection pooling"
kgrag query "API authentication" --kind code -k 5
kgrag query "metabolic pathway" --kind meta --json
```

**Use when:** You're searching for patterns, implementations, or documentation across all registered repos. Returns top N results per KG kind (code/doc/meta).

### Extract Snippets Across KGs
Get source code snippets ready for LLM context:

```bash
kgrag pack "graph traversal logic" --out snippets.md
kgrag pack "authentication middleware" --kind code --context 3
```

**Use when:** You need actual source code with context from multiple KGs for analysis or refactoring.

### Initialize a Repo with KGRAG
Detect, build, and register all KG layers (code and doc) in a single command:

```bash
kgrag init ~/repos/myproject
kgrag init . --layer code --layer doc --wipe
kgrag init ~/repos/myproject --name custom-name
```

**Use when:** Setting up a new repo for the first time. Auto-detects which layers (code/doc) apply and registers them in the central registry.

### Manage the Registry

**List all registered KGs:**
```bash
kgrag list
kgrag list --kind code
```

**Check registry health:**
```bash
kgrag status
```

Returns counts, built/unbuilt status, and missing paths. **Use this before querying** to ensure all repos are indexed.

**Register a new KG manually:**
```bash
kgrag register ~/repos/project --kind code --name project-code
```

**Remove a KG:**
```bash
kgrag unregister project-code
```

**Scan for unregistered KGs:**
```bash
kgrag scan ~/repos --register
```

### Analyze Registry Health

```bash
kgrag analyze
```

Shows cross-KG statistics, coverage, and structural metrics across all registered knowledge graphs.

## Common Workflows

### Workflow: Find patterns across all repos

1. Check registry: `kgrag status`
2. Query: `kgrag query "your pattern here"`
3. Extract snippets: `kgrag pack "pattern" --out file.md`
4. Analyze: Read the snippet file with context

### Workflow: Initialize a new repo

1. Navigate to repo: `cd ~/repos/myproject`
2. Initialize: `kgrag init .`
3. Verify: `kgrag status` (should show the new KGs)
4. Query: `kgrag query "your search" --kind code` to test

### Workflow: Rebuild stale KGs

1. Check status: `kgrag status` (look for "Built: no")
2. If stale: `kgrag init /path/to/repo --wipe`
3. Verify: `kgrag status`

## Registry Location

The central KGRAG registry is stored at:
```
~/.kgrag/registry.sqlite
```

Override with `--registry /path/to/registry.sqlite` on any command, or set `KGRAG_REGISTRY` environment variable.
