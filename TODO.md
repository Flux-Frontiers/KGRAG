# KGRAG TODO

## Registry schema: `KGEntry.lancedb_path` models a retired store

**Filed 2026-07-26 from `pycode_kg` (driver repo for the sqlite-vec migration).**
Not blocking — kgrag works today. This is a naming/modelling debt to pay in a
future kgrag release.

### What happened

pycode-kg 0.20.0 retired LanceDB entirely; sqlite-vec is the only vector
backend. `PyCodeKG.__init__` now takes `vectors_path` (a `.pycodekg/vectors.sqlite`
file), not `lancedb_dir` (a directory). Passing `lancedb_dir=` raises TypeError,
which is what broke `CodeKGAdapter` against 0.20.0.

### The stopgap now in the tree

[pycodekg_adaptor.py:37-43](src/kg_rag/adapters/pycodekg_adaptor.py#L37-L43) derives
the sqlite-vec store as a *sibling* of the recorded lancedb path:

```python
if entry.lancedb_path:
    vectors = str(Path(entry.lancedb_path).parent / "vectors.sqlite")
else:
    vectors = str(entry.repo_path / ".pycodekg" / "vectors.sqlite")
```

That is a path-shape guess, not a recorded fact. It holds only while every code
KG uses the default `.pycodekg/` layout.

### Why it should be fixed properly

- `KGEntry.lancedb_path` ([primitives.py:77](src/kg_rag/primitives.py#L77)) and the
  `lancedb_path TEXT` column ([registry.py:54](src/kg_rag/registry.py#L54)) name a
  store that no longer exists for code KGs. Anyone reading the registry is
  misled about what is on disk.
- Auto-detection in [cmd_registry.py:112-114](src/kg_rag/cli/cmd_registry.py#L112-L114)
  and [cmd_init.py:160](src/kg_rag/cli/cmd_init.py#L160) probes for a `lancedb`
  *directory*. On a freshly built pycode-kg ≥0.20 repo that directory is gone, so
  `lancedb_path` registers as `None` and the adapter lands on the `repo_path`
  fallback branch. Correct by luck for the default layout; wrong for any repo
  whose vectors live elsewhere (`--vectors` accepts an arbitrary path).
- `KGEntry.is_built` ([primitives.py:101](src/kg_rag/primitives.py#L101)) counts a
  LanceDB dir as evidence of a built KG. For code KGs that check is now dead;
  only the `sqlite_path` branch fires.
- Vector-store presence is invisible in the UI/API surface: `kgrag registry show`,
  the Streamlit app, and the MCP `list_kgs`/`get_kg` payloads all label the field
  "LanceDB".
- `kgrag corpus export/import` ([cmd_corpus_io.py:133-136](src/kg_rag/cli/cmd_corpus_io.py#L133-L136))
  tars a `lancedb/` *directory*. A sqlite-vec store is a single file — code-KG
  corpus bundles silently ship without their vectors today.

### Suggested shape (not prescriptive)

1. Add `vectors_path: Path | None` to `KGEntry` plus a `vectors_path TEXT`
   column. There is already a migration precedent to copy —
   [registry.py:75-82](src/kg_rag/registry.py#L75-L82) does
   `ALTER TABLE kg_entries ADD COLUMN builder_version …` in `_migrate()`.
2. Keep `lancedb_path` readable for one release (doc_kg still ships LanceDB by
   design as a fallback for un-migrated corpora, so the field is not dead
   fleet-wide) but stop writing it for code KGs, and deprecate the
   `--lancedb` option in favour of `--vectors`.
3. Teach auto-detection to probe for `<db_dir>/vectors.sqlite` first, falling
   back to `<db_dir>/lancedb` for kinds that still use it.
4. Then delete the sibling-derivation branch in `CodeKGAdapter._load` and read
   `entry.vectors_path` directly.
5. Fix the corpus export/import path so a file-shaped vector store is bundled.

### Coordination

- `kgrag_priv` carries the identical adapter stopgap; land both together.
- Adapter fix + floors (`pycode-kg>=0.20.0`, `doc-kg>=0.18.1`) are already in the
  working tree here and in `kgrag_priv`; 430 / 363 tests pass respectively.
- Related fleet follow-up: KG_utils 0.7.0 plans to split `lancedb` out of the
  `[semantic]` extra so the package stops installing transitively.
