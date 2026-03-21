# KGRAG Project — Claude Code Instructions

## KG-First Code & Docs Search (MANDATORY)

Always use KG tools **before** Grep/Glob/Read:

- **Code understanding** → `mcp__codekg__*` first (pack_snippets, query_codebase, get_node, callers, explain)
- **Docs understanding** → `mcp__dockg__*` first (pack_docs, query_docs, get_node)
- **Cross-KG search** → `mcp__kgrag__*` (kgrag_corpus_query, kgrag_query)
- **Grep/Glob/Read** → only when KG tools lack coverage or for precise line-level edits

### Tool Priority

1. `mcp__codekg__pack_snippets` / `mcp__codekg__query_codebase` — find & read code
2. `mcp__dockg__pack_docs` / `mcp__dockg__query_docs` — find & read docs
3. `mcp__kgrag__kgrag_corpus_query` — search across code + docs simultaneously
4. `Grep` / `Glob` / `Read` — last resort only
