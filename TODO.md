# KGRAG TODO

## Registry schema: `KGEntry.lancedb_path` models a retired store — RESOLVED

**Filed 2026-07-26 from `pycode_kg`. Resolved 2026-07-26 (see CHANGELOG
`[Unreleased]`).**

`KGEntry` now carries a first-class `vectors_path` (plus a `vectors_path TEXT`
column and an in-place `_migrate()` step). All five suggested steps landed:

1. `vectors_path` added to `KGEntry` and the registry schema, migrated in place.
2. `lancedb_path` stays readable for kinds that still ship LanceDB, but is no
   longer written for code KGs; `--lancedb` deprecated in favour of `--vectors`.
3. Auto-detection probes `<db_dir>/vectors.sqlite`, falling back to
   `<db_dir>/lancedb` only for kinds that still use it.
4. The sibling-derivation guess is gone from `CodeKGAdapter._load` — it reads
   `entry.vectors_path` directly (defaulting to the standard `.pycodekg/` layout
   when the registry has no recorded path, so pre-existing entries keep working).
5. `kgrag export`/`import` bundle the file-shaped vector store; code-KG corpus
   bundles no longer ship without their vectors.

### Remaining coordination

- **`kgrag_priv` still carries the 0.10.1 adapter stopgap** — port this change
  there so both repos read `vectors_path` rather than deriving it.
- **Backfilling the existing fleet**: entries registered before this release have
  `vectors_path = NULL` and fall back to the default layout, so nothing breaks.
  Re-run `kgrag register <name> code <repo>` (or `kgrag scan --auto-register`) to
  record the real path — required for any repo whose vectors live outside
  `.pycodekg/`.
- **KG_utils 0.7.0** plans to split `lancedb` out of the `[semantic]` extra so the
  package stops installing transitively.
