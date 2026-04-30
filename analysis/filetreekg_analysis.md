# FileTreeKG Analysis

## Summary

| Metric | Value |
|--------|-------|
| Total paths | 8,765 |
| Total links | 8,765 |
| Files | 8,712 |
| Directories | 53 |
| Symlinks | 0 |
| Total size (files) | 261.0 MB |

## Size by top-level directory

```
.agentkg             ████████████████████    128.0 MB
patents              █████████░░░░░░░░░░░     62.0 MB
.memorykg            ████████░░░░░░░░░░░░     57.0 MB
.pycodekg            █░░░░░░░░░░░░░░░░░░░     10.0 MB
docs                 ░░░░░░░░░░░░░░░░░░░░      1.0 MB
.                    ░░░░░░░░░░░░░░░░░░░░    839.0 KB
src                  ░░░░░░░░░░░░░░░░░░░░    385.0 KB
analysis             ░░░░░░░░░░░░░░░░░░░░    129.0 KB
tests                ░░░░░░░░░░░░░░░░░░░░    119.0 KB
.claude              ░░░░░░░░░░░░░░░░░░░░    114.0 KB
scripts              ░░░░░░░░░░░░░░░░░░░░     73.0 KB
articles             ░░░░░░░░░░░░░░░░░░░░     73.0 KB
pepys                ░░░░░░░░░░░░░░░░░░░░     67.0 KB
books                ░░░░░░░░░░░░░░░░░░░░      3.0 KB
```

## Directory tree (depth ≤ 3)

```
├── .agentkg/
│   ├── graph.sqlite
│   ├── lancedb/
│   │   └── nodes.lance/
│   └── snapshots/
│       ├── 20260417T145635.json
│       ├── 20260417T145823.json
│       ├── 20260417T152611.json
│       ├── 20260417T154823.json
│       ├── 20260417T155022.json
│       ├── 20260417T155218.json
│       ├── 20260417T155348.json
│       ├── 20260417T160404.json
│       ├── 20260417T160450.json
│       ├── 20260417T161149.json
│       ├── 20260417T163027.json
│       ├── 20260417T163105.json
│       └── … (245 more)
├── .claude/
│   ├── KGRAG_SKILL_MANIFEST.md
│   ├── METABOG_NAMING_NOTE.md
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
│       ├── codekg-thorough-analysis/
│       ├── kgrag-usage/
│       ├── new-kg-module/
│       └── publish/
├── .mcp.json
├── .mcp.json.sav
├── .memorykg/
│   ├── graph.sqlite
│   ├── graph.sqlite-shm
│   ├── graph.sqlite-wal
│   └── lancedb/
│       └── memorykg_nodes.lance/
├── .pre-commit-config.yaml
├── .pycodekg/
│   ├── graph.sqlite
│   ├── lancedb/
│   │   └── pycodekg_nodes.lance/
│   └── snapshots/
│       ├── 8e729568f36f5e815332823308147a73aa252903.json
│       ├── a072575cd129773289eb7e37829bf5e0ddb24b5b.json
│       └── manifest.json
├── .secrets.baseline
├── ADAPTER_AUDIT.md
├── AGENT_PERSPECTIVE.md
├── CHANGELOG.md
├── CITATION.cff
└── … (24 more)
```

## Path breakdown

| Kind | Count |
|------|-------|
| `directory` | 53 |
| `file` | 8,712 |

## Link breakdown

| Relation | Count |
|----------|-------|
| `CONTAINS` | 8,765 |
