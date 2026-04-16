# DocKG — Stack Reference
**Domain:** Unstructured documents (Markdown, plain text)
**Package:** `doc-kg` | `Flux-Frontiers/doc_kg`
**CLI binary:** `dockg`
**MCP server:** `dockg mcp --repo <path>`
**Index location:** `<repo>/.dockg/`

## What It Does
Builds a hybrid semantic + structural knowledge graph from any corpus of `.md`
and `.txt` files. Chunks text, extracts topics, entities, and keywords, builds
SIMILAR_TO, HAS_TOPIC, MENTIONS_ENTITY, CONTAINS, and NEXT edges. This is NOT
a documentation indexer — it handles any unstructured document corpus.

## Node Types
| Kind | Description |
|---|---|
| `document` | Source file |
| `section` | Heading-delimited section |
| `chunk` | Text chunk (semantic or heading boundary) |
| `topic` | Extracted topic tag |
| `entity` | Named entity |
| `keyword` | Extracted keyword |

## Edge Types
`CONTAINS`, `NEXT`, `REFERENCES`, `SIMILAR_TO`, `HAS_TOPIC`,
`MENTIONS_ENTITY`, `HAS_KEYWORD`, `CO_OCCURS_WITH`

## MCP Tools (4)
| Tool | Use When |
|---|---|
| `graph_stats()` | Corpus size + health check |
| `query_docs(q, k, hop)` | Hybrid semantic + graph search |
| `pack_docs(q, k, hop)` | Markdown text pack for LLM context |
| `get_node(node_id)` | Fetch one node by ID |

## Key Build Commands
```bash
dockg build --repo .                           # full build
dockg build --repo . --exclude-dir bundles     # exclude dirs
dockg build --repo . --update                  # incremental
dockg analyze --repo . -o analysis/dockg.md
dockg snapshot save --repo .
```

## Usage Rules
- `pack_docs(q)` before `Read`/`Grep` for document understanding
- `query_docs(q)` for finding relevant sections/chunks
- Reads `[tool.dockg].exclude` from `pyproject.toml`
- Default model: `all-mpnet-base-v2` (higher semantic quality than codekg)
- No `--wipe` flag — build always wipes unless `--update`
