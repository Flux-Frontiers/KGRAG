# DiaryKG — Stack Reference
**Domain:** Diary and journal narrative
**Package:** `diary-kg` | `Flux-Frontiers/diary_kg`
**CLI binary:** `diarykg`
**MCP server:** `diarykg-mcp --repo <path>` (via `poetry run` from diary_kg repo)
**Index location:** `<repo>/.diarykg/`

## What It Does
Builds a semantic knowledge graph from diary and journal corpora (`.txt`).
Segments entries by date, extracts topics and context tags, enables temporal
and thematic search across large personal narrative corpora.

## Node Types
`entry`, `chunk`, `topic`, `context`, `entity`

## Active Corpus: Pepys Diary
- **Repo:** `/Users/egs/repos/diary_kg`
- **Source:** `pepys/pepys_enriched_full.txt`
- **Span:** 1660-01-01 → 1669-08-02 (Samuel Pepys complete diary)
- **7,282 entries**, 7,285 chunks
- **41,544 nodes**, **581,630 edges**
- Top topics: `pepys_domestic`, `pepys_court`, `work`

## MCP Tools (3)
| Tool | Use When |
|---|---|
| `diary_stats()` | Corpus metadata, temporal span, topic distribution |
| `query_diary(q, k)` | Semantic search over diary entries |
| `pack_diary(q, k)` | Text excerpts for LLM context |

## MCP Launch (must use poetry run)
```json
{
  "command": "/Users/egs/.local/bin/poetry",
  "args": ["run", "diarykg-mcp", "--repo", "/Users/egs/repos/diary_kg"],
  "cwd": "/Users/egs/repos/diary_kg",
  "env": { "POETRY_VIRTUALENVS_IN_PROJECT": "true" }
}
```

## Key Build Commands
```bash
cd /Users/egs/repos/diary_kg
diarykg build --repo . --source pepys/pepys_enriched_full.txt
diarykg analyze --repo .
diarykg status --repo .
diarykg snapshot save --repo .
```

## Usage Rules
- `query_diary(q)` for temporal/narrative search across Pepys
- `pack_diary(q)` to get passage text for LLM context
- `diary_stats()` for corpus health and topic overview
