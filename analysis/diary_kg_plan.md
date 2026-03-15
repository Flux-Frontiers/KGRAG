# DiaryKG Module — Implementation Plan

## Goal

Build `pepys/diary_kg/` — a self-contained knowledge graph module for diaries,
analogous to `doc_kg` and `code_kg`.  `DiaryTransformer` is the **chunking engine**;
`DiaryKG` is the **KG module** that uses it.

---

## Architecture

```
pepys/
  diary_transformer/        ← semantic chunking engine (DONE)
  diary_kg/                 ← NEW — KG module
    __init__.py
    kg.py                   ← DiaryKG class (main API)
    cli.py                  ← Click CLI: build/query/pack/analyze/status

src/kg_rag/adapters/
  diary_adapter.py          ← UPDATE: delegate to DiaryKG instead of DocKG directly

pyproject.toml              ← ADD: diarykg console-script entry point
```

### Storage layout (on disk)

```
<project-root>/
  pepys_diary.txt           ← source file (provenance anchor)
  .diarykg/
    corpus/                 ← .md chunk files from DiaryTransformer
      entry_0001_chunk_0.md
      ...
    graph.sqlite            ← DocKG SQLite index
    lancedb/                ← DocKG LanceDB vector index
```

---

## File 1: `pepys/diary_kg/__init__.py`

```python
from .kg import DiaryKG
__all__ = ["DiaryKG"]
```

---

## File 2: `pepys/diary_kg/kg.py`

### Class: `DiaryKG`

```python
class DiaryKG:
    KG_DIR = ".diarykg"

    def __init__(
        self,
        root: str | Path,               # project root (where .diarykg/ will live)
        source_file: str | None = None, # relative path to diary .txt inside root
    )
```

`root` = the directory that owns the `.diarykg/` subdirectory.
`source_file` = path to the diary `.txt` relative to root (stored in `.diarykg/config.json`
on first build; auto-detected on subsequent calls if omitted).

**Derived paths** (all under `root/.diarykg/`):
- `corpus_dir = root / .diarykg / corpus`
- `db_path    = root / .diarykg / graph.sqlite`
- `lancedb_dir= root / .diarykg / lancedb`
- `config     = root / .diarykg / config.json`

**Public methods:**

```python
def build(
    self,
    batch_size: int = 0,        # 0 = all entries
    seed: int | None = None,
    max_chunks_per_entry: int = 3,
    chunking_strategy: str = "sentence_group",
    chunk_size: int = 512,
    sentences_per_chunk: int = 4,
    workers: int = 1,
    topics_file: str | None = None,
    wipe: bool = False,
) -> int:
    """Run DiaryTransformer.ingest_to_corpus() then dockg build.
    Returns number of .md files written."""
```

Steps inside `build()`:
1. If `wipe`: delete `corpus/`, `graph.sqlite`, `lancedb/`
2. `DiaryTransformer(...).ingest_to_corpus(source_path, corpus_dir, ...)`
3. `DocKG(corpus_dir, db_path, lancedb_dir).build()` — or subprocess `dockg build --repo corpus_dir`
4. Write `config.json` with `{source_file, built_at, chunk_count, ...}`

```python
def query(self, q: str, k: int = 8) -> list[CrossHit]:
    """Semantic search over the diary corpus."""

def pack(self, q: str, k: int = 8) -> list[CrossSnippet]:
    """Return source snippets for LLM ingestion."""

def stats(self) -> dict:
    """Return {chunk_count, entry_count, source_file, built_at, ...}"""

def analyze(self) -> str:
    """Markdown report: temporal span, topic distribution, context
    distribution, source files, DocKG baseline stats."""

def is_built(self) -> bool:
    """True if graph.sqlite or lancedb/ exist."""
```

**Internal:**
- `_load_dockg()` — lazy-loads `DocKG(corpus_dir, db_path, lancedb_dir)`
- `_load_config()` — reads `config.json`; raises if KG not built
- `query()` and `pack()` call `_load_dockg()` then map node metadata:
  `node['metadata']['source_file']` → `CrossHit.source_path` (original `.txt`, not chunk `.md`)

---

## File 3: `pepys/diary_kg/cli.py`

Click group `diarykg` with five commands.

### `diarykg build`

```
diarykg build [ROOT] [OPTIONS]

Arguments:
  ROOT              Project root directory (default: .)

Options:
  --source, -s      Path to diary .txt relative to ROOT (required on first build)
  --wipe            Delete existing corpus + DBs before rebuilding
  --batch-size, -b  Entries to sample (0 = all) [default: 0]
  --seed            RNG seed
  --max-chunks, -m  Max chunks per entry [default: 3]
  --chunking        sentence_group | semantic | hybrid [default: sentence_group]
  --chunk-size      Max chars per chunk [default: 512]
  --workers, -w     Parallel workers [default: 1]
  --topics-file     YAML topics override
```

Output (rich):
```
Building DiaryKG  pepys_diary.txt → .diarykg/
  Loading NLP models...
  Ingesting 3000 entries...
  ✓ Wrote 8400 chunk files to .diarykg/corpus/
  Building DocKG index...
  ✓ SQLite  : .diarykg/graph.sqlite
  ✓ LanceDB : .diarykg/lancedb/
Done! 8400 chunks indexed.
```

### `diarykg query`

```
diarykg query QUERY [ROOT] [OPTIONS]

Arguments:
  QUERY             Natural-language query string
  ROOT              Project root [default: .]

Options:
  -k                Number of results [default: 8]
  --json            Output raw JSON
```

Output (rich table):
```
┌──────┬──────────────────────────────────────┬───────────┬────────────────────┐
│ Rank │ Summary                              │ Category  │ Source             │
├──────┼──────────────────────────────────────┼───────────┼────────────────────┤
│  1   │ Went to the theatre with my wife...  │ social    │ pepys_diary.txt    │
│  2   │ Great discourse about the Navy...    │ work      │ pepys_diary.txt    │
└──────┴──────────────────────────────────────┴───────────┴────────────────────┘
```

Timestamp extracted from chunk frontmatter shown in Source column:
`pepys_diary.txt @ 1667-04-15`

### `diarykg pack`

```
diarykg pack QUERY [ROOT] [OPTIONS]

Arguments:
  QUERY             Natural-language query
  ROOT              Project root [default: .]

Options:
  -k                Number of snippets [default: 8]
  --output, -o      Write pack to file instead of stdout
```

Outputs LLM-ready fenced blocks:
```markdown
## [diary:pepys] pepys_diary.txt @ 1667-04-15
```
...chunk text...
```

### `diarykg analyze`

```
diarykg analyze [ROOT] [OPTIONS]

Arguments:
  ROOT              Project root [default: .]

Options:
  --output, -o      Write Markdown report to file
```

Calls `DiaryKG.analyze()` and prints/saves the Markdown report.
Report sections:
- Corpus Overview (chunk count, source files, temporal span)
- Topic Distribution (table)
- Context Distribution (table)
- DocKG Baseline (nodes, edges)

### `diarykg status`

```
diarykg status [ROOT]
```

Quick health check — no DB load required:
```
DiaryKG status: .
  Source file : pepys_diary.txt
  Built       : yes
  Corpus      : 8400 .md files
  SQLite      : .diarykg/graph.sqlite (2.1 MB)
  LanceDB     : .diarykg/lancedb/ (14.3 MB)
  Built at    : 2026-03-15T19:42:00
```

---

## File 4: Update `src/kg_rag/adapters/diary_adapter.py`

Replace the current DocKG-direct implementation with delegation to `DiaryKG`:

```python
from diary_kg.kg import DiaryKG   # import from pepys/diary_kg

class DiaryKGAdapter(KGAdapter):
    def _load(self):
        root = self.entry.repo_path
        source = self.entry.metadata.get("source_file")
        self._kg = DiaryKG(root, source_file=source)

    def query(self, q, k=8):   # delegates to self._kg.query()
    def pack(self, q, k=8):    # delegates to self._kg.pack()
    def stats(self):           # delegates to self._kg.stats()
    def analyze(self):         # delegates to self._kg.analyze()
```

`KGEntry.metadata["source_file"]` carries the provenance — set at registration time
via `kgrag register --metadata source_file=pepys_diary.txt` or by `diarykg build`
when it auto-registers (via `--register`).

---

## File 5: `pyproject.toml` — add entry point

```toml
diarykg = "diary_kg.cli:cli"
```

Note: since `diary_kg` lives under `pepys/`, also add the package declaration:
```toml
packages = [
  { include = "kg_rag", from = "src" },
  { include = "diary_kg", from = "pepys" },
  { include = "diary_transformer", from = "pepys" },
]
```

---

## Implementation order

1. `pepys/diary_kg/__init__.py` — trivial
2. `pepys/diary_kg/kg.py` — `DiaryKG` class with `build()`, `_load_dockg()`, `query()`, `pack()`, `stats()`, `analyze()`, `is_built()`
3. `pepys/diary_kg/cli.py` — Click group with all five commands
4. `src/kg_rag/adapters/diary_adapter.py` — simplify to delegate to `DiaryKG`
5. `pyproject.toml` — add packages + console script

---

## Key design decisions

| Decision | Choice | Reason |
|---|---|---|
| Storage backend | DocKG (via `doc_kg.kg.DocKG`) | Already a dependency; proven storage |
| Corpus location | `.diarykg/corpus/` inside root | Mirrors `.dockg/`, `.codekg/` pattern |
| Provenance in queries | `metadata.source_file` from frontmatter | Surfaces original `.txt`, not chunk path |
| `source_line` | Not used | Calendar date is the semantic anchor for diaries |
| File tree input | Deferred — ftreeKG module not yet available | Single `.txt` only for now; design allows extension |
| `batch_size=0` default for `build` | All entries | KG should be complete; sampling is for `transform` previews |
