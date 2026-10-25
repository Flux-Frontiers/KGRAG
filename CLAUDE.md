# KGRAG Project — Claude Code Instructions

## KG-First Code & Docs Search (MANDATORY)

Always use the KG servers **before** Grep/Glob/Read. Every fleet server answers
the same five tools -- `stats`, `query`, `pack`, `get_node`, `neighbors` -- so
the tool names below are the same on each; only the server differs.

- **Code understanding** → the `pycodekg` server: `pack`, `query`, `get_node`,
  `neighbors`, plus its own `callers`, `explain`
- **Docs understanding** → the `dockg` server: `pack`, `query`, `get_node`
- **Cross-KG search** → the `kgrag` server: `query` / `pack` across every
  registered KG, `corpus_query` / `corpus_pack` within one corpus. Its node
  ids are `<kg>::<node id>`; pass them to `get_node` / `neighbors` unchanged.
- **Grep/Glob/Read** → only when KG tools lack coverage or for precise line-level edits

### Tool Priority

1. `pack` / `query` on the `pycodekg` server — find & read code
2. `pack` / `query` on the `dockg` server — find & read docs
3. `query` or `corpus_query` on the `kgrag` server — search across code + docs simultaneously
4. `Grep` / `Glob` / `Read` — last resort only

`<server> mcp --manifest` prints any server's live tool list.

## Open Work

This repo carries no `TODO.md` — kgrag-specific landed work is recorded in
`CHANGELOG.md`.
