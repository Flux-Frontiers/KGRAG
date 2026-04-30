# Embedder Centralization & SIGBUS Root-Cause Fix

**Date:** 2026-04-28
**Versions:** `kg_utils` 0.2.2 · `doc_kg` 0.12.3 · `diary_kg` 0.92.2

---

## Background

`diarykg reindex` was crashing with **Bus Error 10 (SIGBUS)** on Apple Silicon
during the DocKG re-embedding step.  The crash appeared MPS-related but the
true cause was a LanceDB Rust worker stack overflow triggered by an OR-predicate
recursion.  Fixing the crash revealed that embedding model loading was duplicated
across four separate files, each with its own variant of the `local_files_only`
guard.  Both problems were fixed in this session.

---

## Root Cause: Three Stacked Bugs

### Bug 1 — `local_files_only` missing in `doc_kg/index.py`

`SentenceTransformerEmbedder.__init__` called `SentenceTransformer(model)` with
no `local_files_only=True`.  When `kg_utils.embed.resolve_model_path()` returns
a path that *exists* on disk, HuggingFace still issues a HEAD request to check
for updates.  This left stale network/thread state that interacted badly with
`multiprocessing.get_context("spawn")`.

**Fix:** Added `local_files_only=True` to all ST construction calls when the
local path exists.

### Bug 2 — `rebuild_index()` calling `SentenceTransformer` directly

`DiaryKG.rebuild_index()` called `SentenceTransformer(self._model)` directly,
bypassing the `local_files_only` fix in `doc_kg/index.py`.  The embedder was
double-loaded on MPS and the HF network guard was skipped again.

**Fix:** Removed the direct ST call; let DocKG use its own internal embedder via
`dockg.build()` — which already calls the fixed `SentenceTransformerEmbedder`.

### Bug 3 — `wipe=False` → 1024-clause OR predicate → 666-deep LanceDB recursion → SIGBUS

When `dockg.build(wipe=False)` runs on an existing LanceDB table it issues a
batch `DELETE WHERE id = 'a' OR id = 'b' OR … (×1024)`.  LanceDB's predicate
evaluator is *recursive*, not iterative.  With 1024 clauses the Rust worker
thread stack recurses 666 levels, hits the guard page, and the kernel raises
`KERN_PROTECTION_FAILURE` → **SIGBUS**.

The crash dump showed:

```
Thread 21 Crashed:
  _lancedb.abi3.so  lance::dataset::scanner::...  (×666 frames)
KERN_PROTECTION_FAILURE at 0x…  (stack guard page)
```

**Fix:** Always pass `wipe=True` to `dockg.build()` in `rebuild_index()`.

### Bonus: `discover_similar=True` (default) takes ~4 hours on 41 k nodes

DocKG's SIMILAR_TO scan is O(n²).  With 41 k diary nodes and 18 embedding
passes each pass was ~14 minutes.

**Fix:** Pass `discover_similar=False` in `rebuild_index()`.

---

## Centralization: `kg_utils.embedder`

All model-loading logic was moved to a single canonical module so the
`local_files_only` guard and `KNOWN_MODELS` alias resolution live in exactly
one place.

### New module: `kg_utils/src/kg_utils/embedder.py`

```python
# Public API
load_sentence_transformer(model_name: str = DEFAULT_MODEL) -> Any
get_embedder(model_name: str = DEFAULT_MODEL) -> SentenceTransformerEmbedder
wrap_embedder(st_model: Any, model_name: str) -> SentenceTransformerEmbedder
```

**`load_sentence_transformer`** — safe load sequence:

```python
def load_sentence_transformer(model_name: str = DEFAULT_MODEL) -> Any:
    from sentence_transformers import SentenceTransformer
    resolved = KNOWN_MODELS.get(model_name, model_name)
    trust_remote = "nomic-ai/" in resolved
    local_path = resolve_model_path(resolved)
    if local_path.exists():
        return SentenceTransformer(str(local_path),
                                   local_files_only=True,
                                   trust_remote_code=trust_remote)
    try:
        return SentenceTransformer(resolved,
                                   local_files_only=True,
                                   trust_remote_code=trust_remote)
    except OSError:
        return SentenceTransformer(resolved, trust_remote_code=trust_remote)
```

Key properties:
- `local_files_only=True` always attempted first — prevents HF HEAD requests
- Falls back to network *only* if the model is genuinely absent
- `sentence_transformers` imported lazily — no ST dep at import time
- Alias resolution (`bge-small` → `BAAI/bge-small-en-v1.5`) via `KNOWN_MODELS`

**`wrap_embedder`** — wraps a live `SentenceTransformer` instance already in
memory as an `Embedder`.  Used by `DiaryKG.build()` to share the model that
`DiaryTransformer` already loaded, avoiding a second MPS allocation:

```python
shared_embedder = wrap_embedder(dt.sentence_model, self._model)
dockg.build(wipe=True, embedder=shared_embedder, discover_similar=False)
```

### `Embedder` abstract base

```python
class Embedder(ABC):
    dim: int
    def embed_texts(self, texts: list[str]) -> list[list[float]]: ...
    def embed_query(self, text: str) -> list[float]: ...   # delegates to embed_texts
```

---

## Files Changed

### `kg_utils` (0.2.1 → 0.2.2)

| File | Change |
|---|---|
| `src/kg_utils/embedder.py` | **New.** `Embedder`, `SentenceTransformerEmbedder`, `load_sentence_transformer`, `get_embedder`, `wrap_embedder` |
| `src/kg_utils/__init__.py` | Bumped `__version__` to `"0.2.2"`; added `embedder` to docstring |

### `doc_kg` (0.12.2 → 0.12.3)

| File | Change |
|---|---|
| `src/doc_kg/index.py` | Removed 70+ lines: `_local_model_path`, `Embedder`, `SentenceTransformerEmbedder`. Now imports + re-exports from `kg_utils.embedder` |
| `src/doc_kg/embedder_worker.py` | Removed `_local_model_path`. `_embed_shard` now calls `load_sentence_transformer(model_name)` (1 line). Fixed `PIPELINE_MODEL = "BAAI/bge-small-en-v1.5"` |
| `src/doc_kg/cli/cmd_model.py` | Replaced dead import with `from kg_utils.embed import resolve_model_path` |

### `diary_kg` (0.92.1 → 0.92.2)

| File | Change |
|---|---|
| `src/diary_transformer/diary_embedder.py` | Removed `_local_model_path`. `_embed_shard` calls `load_sentence_transformer(model_id)` |
| `src/diary_kg/kg.py` | Removed `_wrap_sentence_transformer` (35 lines). `rebuild_index()`: `dockg.build(wipe=True, discover_similar=False)`. `build()`: uses `wrap_embedder()` |

---

## Invariants to Never Break

> **Always pass `wipe=True` to `dockg.build()` inside `rebuild_index()`.**
> `wipe=False` generates a batch DELETE with 1024 OR-clauses → LanceDB
> recursive predicate evaluator → stack overflow → SIGBUS on macOS/Linux.

> **Always pass `discover_similar=False` in `rebuild_index()`.**
> SIMILAR_TO is O(n²).  On 41 k nodes it takes ~4 hours.  Only enable it
> during a deliberate full corpus analysis.

> **Use `load_sentence_transformer()` for all ST loads.**
> Never call `SentenceTransformer(model)` directly in KG module code.
> Direct calls skip the `local_files_only` guard and the alias resolver.

---

## Backward Compatibility

`doc_kg.index` re-exports `Embedder` and `SentenceTransformerEmbedder` from
`kg_utils.embedder` so existing callers (`doc_kg/kg.py`, `chunker.py`,
`pipeline.py`, KGRAG adapters) need no changes:

```python
# doc_kg/index.py
from kg_utils.embedder import Embedder, SentenceTransformerEmbedder
# re-exported here for backward compatibility
```

The identity check passes: `doc_kg.index.Embedder is kg_utils.embedder.Embedder`.

---

## Test Coverage Added

### `kg_utils/tests/test_embedder.py` (26 tests)

| Test group | What it verifies |
|---|---|
| `Embedder` abstract base | `embed_texts` raises `NotImplementedError`; `embed_query` delegates |
| `KNOWN_MODELS` resolution | Alias → full id; full id passthrough |
| `load_sentence_transformer` (mocked) | `local_files_only=True` when path exists; OSError falls back to network (2 ST calls) |
| `load_sentence_transformer` (real MPS) | Returns model; device is `mps:0` or `cpu`; dim=384 |
| `SentenceTransformerEmbedder` | dim, model_name, `__repr__`, embed_query length+norm, embed_texts batch+norm, semantic separation, query/texts consistency |
| `get_embedder` factory | Returns `SentenceTransformerEmbedder`; alias resolves |
| `wrap_embedder` | Is `Embedder`; dim; model_name; query+texts; matches direct encode |
| Backward compat | `doc_kg.index.Embedder is kg_utils.embedder.Embedder` |

All 26 pass in ~2.4 s (session-scoped model fixture — loaded once).

### `diary_kg/tests/test_diary_kg_cli.py` — `TestReindex` (6 tests added)

- `reindex --help` exits 0 and mentions corpus/index
- `reindex` appears in root `--help`
- Success path calls `kg.rebuild_index()` once
- Output mentions `graph.sqlite` and `lancedb`
- `FileNotFoundError` → exit nonzero + error message
- Unexpected `RuntimeError` → exit nonzero

### `doc_kg/tests/test_cli.py` — download-model (5 tests added)

- `download-model` in root `--help`
- `download-model --help` shows `--model` and `--force`
- Already-cached path → exit 0, mentions "cached" and `--force`
- `--force` redownloads and calls `st_model.save()` once
- Save target matches resolved local path

---

## Version Table

| Package | Before | After |
|---|---|---|
| `kg_utils` | 0.2.1 | **0.2.2** |
| `doc_kg` | 0.12.2 | **0.12.3** |
| `diary_kg` | 0.92.1 | **0.92.2** |
