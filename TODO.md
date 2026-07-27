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

## LanceDB retirement — fleet is still ~96% un-migrated

`kgrag audit-lancedb` (added alongside the above) measured the real registry on
2026-07-26: **242 of 253 KGs still have LanceDB as their live vector index**,
holding **~2.0 GB** on disk. It is not gone — the schema work above only stopped
kgrag *recording* it for new code KGs.

| Status | KGs | Note |
|---|---|---|
| `unmigrated` | 242 | 237 gutenberg, 3 doc, 2 code |
| `stale-row` | 9 | registry references a dir already deleted |
| `residue` | 1 | migrated but `lancedb/` still on disk |
| `no-index` | 1 | nothing built |

Migration path, verified end to end on a scratch copy of the Moby Dick corpus
(10,910 vectors converted, validated, still queryable through `DocKGAdapter`):

```
kgrag audit-lancedb --commands   # review, then pipe to a shell
```

- doc/gutenberg/ia KGs convert in place via `dockg convert-index` — reads vectors
  straight out of LanceDB, so there is **no re-embedding**.
- code KGs have no converter; they need a `pycodekg build`.

### Known gap — CLOSED 2026-07-26

`DocKGAdapter`/`GutenbergKGAdapter` could not pass a non-default vector-store
location, so `KGEntry.vectors_path` was informational only for doc-family KGs.
Fixed upstream in **doc-kg 0.18.2** (`DocKG(vectors_path=...)`, plus a
`--vectors-path` option on the 8 vector-touching CLI commands) and wired through
here; the kgrag floor is now `doc-kg>=0.18.2`. `vectors_path` is authoritative
for every KG kind.

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
