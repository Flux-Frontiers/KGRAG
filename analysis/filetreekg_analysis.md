# FileTreeKG Analysis

## Summary

| Metric | Value |
|--------|-------|
| Total paths | 622 |
| Total links | 622 |
| Files | 579 |
| Directories | 43 |
| Symlinks | 0 |
| Total size (files) | 60.0 MB |

## Size by top-level directory

```
patents              ████████████████████     56.0 MB
docs                 ░░░░░░░░░░░░░░░░░░░░      1.0 MB
.agentkg             ░░░░░░░░░░░░░░░░░░░░    930.0 KB
.                    ░░░░░░░░░░░░░░░░░░░░    759.0 KB
src                  ░░░░░░░░░░░░░░░░░░░░    301.0 KB
.claude              ░░░░░░░░░░░░░░░░░░░░    266.0 KB
analysis             ░░░░░░░░░░░░░░░░░░░░     81.0 KB
scripts              ░░░░░░░░░░░░░░░░░░░░     69.0 KB
tests                ░░░░░░░░░░░░░░░░░░░░     68.0 KB
pepys                ░░░░░░░░░░░░░░░░░░░░     67.0 KB
articles             ░░░░░░░░░░░░░░░░░░░░     50.0 KB
books                ░░░░░░░░░░░░░░░░░░░░      3.0 KB
```

## Directory tree (depth ≤ 3)

```
├── .agentkg/
│   ├── graph.sqlite
│   ├── lancedb/
│   │   └── nodes.lance/
│   └── snapshots/
│       ├── 20260404T183702.json
│       ├── 20260406T221729.json
│       └── 20260406T222214.json
├── .claude/
│   ├── KGRAG_SKILL_MANIFEST.md
│   ├── METABOG_NAMING_NOTE.md
│   ├── agents/
│   │   ├── cco.md
│   │   ├── cw.md
│   │   ├── do.md
│   │   ├── doc.md
│   │   ├── kc.md
│   │   ├── me.md
│   │   ├── qa.md
│   │   ├── sd.md
│   │   ├── sec.md
│   │   ├── ta.md
│   │   ├── uid.md
│   │   ├── uids.md
│   │   └── … (1 more)
│   ├── claude_code_config.json
│   ├── commands/
│   │   ├── bump.md
│   │   ├── changelog-commit.md
│   │   ├── codekg.md
│   │   ├── continue.md
│   │   ├── protocol.md
│   │   ├── release.md
│   │   ├── setup-kgrag-mcp.md
│   │   └── sync-mcp-docs.md
│   ├── settings.json
│   ├── settings.json.template
│   ├── settings.local.json
│   └── skills/
│       ├── codekg/
│       ├── codekg-thorough-analysis/
│       ├── kgrag-usage/
│       ├── new-kg-module/
│       └── publish/
├── .mcp.json
├── .mcp.json.sav
├── .metabokg/
│   └── snapshots/
├── .pre-commit-config.yaml
├── .secrets.baseline
├── AGENT_PERSPECTIVE.md
├── CHANGELOG.md
├── CLAUDE.md
├── Claude.mcp.json
├── LICENSE
└── … (20 more)
```

## Path breakdown

| Kind | Count |
|------|-------|
| `directory` | 43 |
| `file` | 579 |

## Link breakdown

| Relation | Count |
|----------|-------|
| `CONTAINS` | 622 |
