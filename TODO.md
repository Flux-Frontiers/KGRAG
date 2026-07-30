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

> **Stale as of 2026-07-30** — the gutenberg corpora have since been migrated
> (see Remaining coordination). Re-run the audit for real numbers.

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
- **kgmodule-utils has *not* split `lancedb` out of `[semantic]` yet** — corrected
  2026-07-30. The old note here said "KG_utils 0.7.0 plans to…"; 0.7.0 shipped
  long ago and **0.9.0 is the current release**, where `lancedb>=0.19.0` is still
  an `[semantic]` requirement (alongside `sqlite-vec==0.1.9`, which 0.9.0 added
  to both `[semantic]` and a standalone `[sqlite-vec]` extra). So `[semantic]`
  still drags lancedb in; only installs that *avoid* `[semantic]` escape it.
  kgrag itself is safe on this axis — it depends on bare `kgmodule-utils>=0.8.0`
  with no extras — as is corpus_pepys, which installs
  `[synthesis,sqlite-vec]`. The work item is unchanged, just not done: drop
  `lancedb` from `[semantic]` in a future kgmodule-utils release.
- **doc-kg / diary-kg still hard-require `lancedb>=0.29.0`** (checked 2026-07-30
  at doc-kg 0.19.1 / diary-kg 0.93.4, filed from `corpus_pepys`). This is the
  binding constraint: unlike the kgmodule-utils case above, it is an
  unconditional dependency, so lancedb lands in every worker image no matter
  which extras are selected. corpus_pepys no longer *imports* lancedb anywhere
  (worker is sqlite-vec only, LanceDB fallback removed, merged as
  corpus_pepys#1), but the package is still installed. Full retirement needs
  doc-kg/diary-kg releases that demote lancedb to an optional extra; also
  cosmetic: `diarykg build` still prints a "LanceDB :" path label while writing
  `vectors.sqlite`.
- **`gutenberg_kg` is migrated** — reported by the maintainer 2026-07-30 (done
  outside this repo, so unverified here). Its pins are already
  `kgmodule-utils[synthesis,sqlite-vec]>=0.8.0` / `doc-kg>=0.18.1` on `main`.
  This invalidates the largest row of the audit table above (237 gutenberg
  corpora counted as `unmigrated` on 2026-07-26) — **re-run `kgrag
  audit-lancedb` for current numbers before treating that table as fleet
  state.**
