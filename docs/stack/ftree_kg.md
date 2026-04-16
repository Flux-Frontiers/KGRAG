# FTreeKG — Stack Reference
**Domain:** File system tree (repository structure)
**Package:** `ftree-kg` | `Flux-Frontiers/ftree_kg`
**CLI binary:** `ftreekg`
**MCP server:** None (no MCP entry point)
**Index location:** `<repo>/.filetreekg/`

## What It Does
Builds a knowledge graph of a file system tree — directories, files, modules,
and their dependency/import structure. Useful for understanding repository
layout, file relationships, and structural navigation.

## Node Types
`directory`, `file`, `module`, dependency nodes

## Key CLI Commands
```bash
ftreekg build           # build file tree KG
ftreekg query           # query the tree
ftreekg pack            # pack results
ftreekg analyze         # analysis report
ftreekg snapshot        # temporal snapshots
```

## Usage Rules
- No MCP server — not queryable via Claude tools
- Use for repository structure analysis from the CLI
- Available in `kgrag` venv at `/Users/egs/repos/kgrag/.venv/bin/ftreekg`
