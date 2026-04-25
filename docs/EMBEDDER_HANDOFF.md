# Embedder Backend Handoff

**Context:** We added a pluggable `EmbedBackend` to KGRAG to support Raspberry Pi / ARM
deployments via `llama-cpp-python` + `bge-small-en-v1.5-Q8_0.gguf`.  The KGRAG side is
done and pushed to `claude/raspberry-pi-query-design-dOWGL`.  What remains is:

1. PRs against the upstream KG libraries to surface `embedder=` as a proper constructor
   parameter (so KGRAG can stop monkey-patching `_kg._embedder`).
2. Follow-up KGRAG commits to clean up the monkey-patches once those PRs merge.

---

## Status

| Adapter | KGRAG injection | Upstream PR needed |
|---|---|---|
| `CodeKGAdapter` | ✅ monkey-patch (works) | ✅ pycode_kg — see below |
| `DocKGAdapter` | ✅ clean constructor param | ✅ done — `DocKG.__init__` accepts `embedder=` |
| `DiaryKGAdapter` | ⬜ not wired | ⬜ diary_kg — verify KGModule, then same pattern |
| `AgentKGAdapter` | ⬜ not wired | ⬜ agent_kg — verify KGModule, then same pattern |
| `MetaKGAdapter` | ⬜ not wired | ⬜ metabo_kg — verify KGModule, then same pattern |

---

## PR pattern

**Note:** Only `pycode_kg` extends `KGModule`.  `DocKG`, `DiaryKG`, `AgentKG`,
and `MetaKG` are plain classes — each has its own embedding architecture and
needs a different injection approach (see per-repo notes below).

The `KGModule` two-file pattern applies only to `pycode_kg` (and any future
repo that actually subclasses `KGModule`):

### File 1: `src/<pkg>/module/base.py` — `KGModule.__init__`

Add `embedder` parameter and pre-set `_embedder`:

```diff
     def __init__(
         self,
         repo_root: str | Path,
         ...,
         model: str = DEFAULT_MODEL,
         table: str = "kg_nodes",
+        embedder: Embedder | None = None,
     ) -> None:
         ...
-        self._embedder: Embedder | None = None
+        self._embedder: Embedder | None = embedder
```

### File 2: `src/<pkg>/kg.py` — concrete KG class `__init__`

Add import, parameter, and pass-through:

```diff
+from <pkg>.index import Embedder
 from <pkg>.module.base import KGModule
```

```diff
     def __init__(
         self,
         repo_root: str | Path,
         ...,
         model: str = DEFAULT_MODEL,
         table: str = "<pkg>_nodes",
+        embedder: Embedder | None = None,
     ) -> None:
         super().__init__(
             repo_root,
             ...,
             model=model,
             table=table,
+            embedder=embedder,
         )
```

**Commit message:**
```
feat(module): add embedder parameter to KGModule and <ConcreteKG> constructors

Allows callers to inject a custom embedding backend at construction time
rather than relying on post-construction assignment to _embedder.

When embedder= is provided, _embedder is pre-set so the lazy-init in
KGModule.embedder never fires SentenceTransformerEmbedder. SemanticIndex
already accepts an Embedder at construction — this change surfaces that
capability through the public API.

Backwards compatible: embedder defaults to None, existing call sites unchanged.
```

---

## pycode_kg PR (ready to push)

Branch: `feat/embedder-constructor-param`

Changes already written — see diff above applied to:
- `src/pycode_kg/module/base.py`
- `src/pycode_kg/kg.py`

**PR description:**
```
## Summary

- Add `embedder: Embedder | None = None` to `KGModule.__init__`
- Pass through in `PyCodeKG.__init__`
- Pre-set `self._embedder = embedder` to bypass lazy-init when provided

## Motivation

KGRAG needs to inject a pluggable embedding backend (e.g. LlamaCppEmbedder
for Raspberry Pi / ARM) into KGModule-based KGs. Without this, the only way
is assigning to `_embedder` after construction — a private attribute access
that is fragile and not part of the public API.

SemanticIndex already accepts an Embedder at construction and KGModule.index
already passes self.embedder to it. This PR surfaces that existing capability
through a proper constructor parameter.

## Backwards compatibility

Fully backwards compatible. embedder defaults to None, which preserves the
existing lazy-init behaviour. No existing call sites need to change.

## Test plan
- [ ] Existing tests pass unchanged
- [ ] `PyCodeKG(..., embedder=my_embedder)` → `kg._embedder is my_embedder`
- [ ] `kg.query(...)` calls `my_embedder.embed_query()`, not SentenceTransformerEmbedder
```

---

## KGRAG follow-up (after each upstream PR merges)

### CodeKGAdapter — clean up monkey-patch

```python
# src/kg_rag/adapters/pycodekg_adaptor.py  _load()
# BEFORE (monkey-patch):
self._kg = PyCodeKG(repo_root=..., db_path=..., lancedb_dir=...)
if self._embedder is not None:
    self._kg._embedder = self._embedder

# AFTER (clean):
self._kg = PyCodeKG(
    repo_root=..., db_path=..., lancedb_dir=...,
    embedder=self._embedder,
)
```

### DocKGAdapter — same pattern

```python
# src/kg_rag/adapters/dockg_adapter.py  _load()
# BEFORE:
self._kg = DocKG(corpus_root=..., db_path=..., lancedb_dir=...)
if self._embedder is not None:
    self._kg._embedder = self._embedder

# AFTER:
self._kg = DocKG(
    corpus_root=..., db_path=..., lancedb_dir=...,
    embedder=self._embedder,
)
```

### DiaryKGAdapter — wire up (not yet done)

First confirm `DiaryKG` extends `KGModule`, then:

```python
# src/kg_rag/adapters/diary_adapter.py  _load()
self._kg = DiaryKG(
    self.entry.repo_path,
    source_file=source_file,
    embedder=self._embedder,   # add this
)
```

### AgentKGAdapter — wire up (not yet done)

```python
# src/kg_rag/adapters/agent_adapter.py  _load()
self._kg = AgentKG(
    repo_path=self.entry.repo_path,
    person_id=person_id,
    session_id=session_id or None,
    embedder=self._embedder,   # add this
)
```

### MetaKGAdapter — wire up (not yet done)

```python
# src/kg_rag/adapters/metakg_adapter.py  _load()
self._kg = MetaKG(
    db_path=...,
    lancedb_dir=...,
    embedder=self._embedder,   # add this — verify MetaKG extends KGModule first
)
```

---

## Reference

- Full design spec: `docs/RASPBERRY_PI_QUERY_DESIGN.md`
- KGRAG implementation: `src/kg_rag/embed.py`
- Branch: `claude/raspberry-pi-query-design-dOWGL`
