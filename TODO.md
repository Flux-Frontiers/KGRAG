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

### Fleet code-migration audit — 2026-07-30

> **The plan of record is `pycode_kg/MIGRATION-sqlite-vec.md`** (dated
> 2026-07-28) — phases, per-repo effort sizing, the reference implementation
> checklist, and eleven hard-won learnings. **Read it before migrating anything;
> this section only records what a package-level audit adds on top of it.**
> Its recommended order: `diary_kg` → `Metabo_kg` → `memory_kg` → `doc_kg`,
> with **`kgrag` last** (`agent_kg` since completed in PR #9).

The table below measures the **published packages** (installed from PyPI,
grepped for real code paths). That is a *narrower* lens than the plan's
`grep -rn -i lancedb src/` over repo checkouts, and the difference matters —
see the diary-kg correction below.

| Package | Version | `lancedb` dep | imports `lancedb` | sqlite-vec aware | Verdict |
|---|---|---|---|---|---|
| `pycode-kg` | 0.21.2 | none | 0 files | yes | ✅ migrated (reference impl) |
| `ftree-kg` | 0.9.0 | none | 0 files | yes | ✅ migrated — v0.9.0 |
| `agent-kg` | 0.8.2 | none | 0 files | yes | ✅ migrated — PR #9 |
| `tscode-kg` | 0.2.0 | none | 0 files | yes | ✅ migrated |
| `kgmodule-utils` | 0.9.0 | `[semantic]` extra | backend seam | yes | ✅ both backends |
| `doc-kg` | 0.19.1 | **hard** | `index.py` | yes (8 files) | 🔴 plan Phase 4 — both backends wired |
| `diary-kg` | 0.93.4 | **hard** | 0 files | 0 files | 🟢 plan Phase 1 — see correction |
| `memory-kg` | 0.6.2 | **hard** | `index.py` | **0 files** | 🟠 plan Phase 3 |
| `Metabo_kg` | — | — | — | — | 🟡 plan Phase 2 — **not on PyPI**, unaudited here |

**Correction — `diary-kg` is not just a dead dependency.** An earlier revision of
this section claimed dropping `lancedb` from diary-kg was "a one-line release
with no code change", on the basis that the published wheel contains zero
`import lancedb`. That is true but misleading: diary-kg never imports lancedb
because it *delegates* vector work to `dockg build` — while still passing
`--lancedb` paths to that subprocess (`diary_kg/kg.py:291`, `:367`) and
plumbing `self._lancedb_dir` throughout. The plan counts 30 lancedb source refs
and 2 `--lancedb` CLI refs, and sizes it as a real Phase-1 port (rename flags,
swap the artifact path, port the read/write paths by hand — `DiaryKGAdapter`
only *mirrors* the `KGModule` pattern without subclassing it, so there is no
seam to flip). **A wheel-level grep cannot see CLI strings, prose, tests or
docs — prefer the plan's repo-level counts.**

What the package audit does add, being 2 days newer than the plan:

1. **`memory-kg` 0.6.2's CLI has no sqlite-vec surface at all** — no
   `--vectors-path`, no `--vector-backend`, and it hard-requires
   `lancedb>=0.29.0`. So until plan Phase 3 lands, **do not convert a memory
   KG's vectors**: memory-kg cannot read the result. (The plan adds a caveat
   worth heeding first — memory_kg resolves `kgmodule-utils` via a **path
   dependency**, so confirm which checkout it uses before assuming it even has
   the 0.8.0 backend seam.)
2. **`doc-kg` 0.19.1 already ships `--vectors-path` and `--vector-backend auto`**
   on its vector-touching CLI commands. The plan (Phase 4) notes doc_kg is the
   one repo where *keeping* LanceDB is defensible, since `index.py` needs it to
   read LanceDB during `dockg convert-index`.
3. **`gutenberg_kg` needs a re-audit after diary_kg and doc_kg land.** Its own
   store is already sqlite-vec, but per the plan its 41 lancedb refs are it
   *orchestrating* other KGs (`ingest.py` builds `.dockg/lancedb` and
   `.diarykg/lancedb`) — correct today, stale only once those two migrate.

`kgrag` itself is clean: no `import lancedb` anywhere in `src/`. The plan agrees
it is **not a migration target** — the registry deliberately spans both backends
(`lancedb_path` + `vectors_path` columns), and dropping `lancedb_path` is the
*final* step of the whole fleet migration, valid only once every registered KG
reports a `vectors_path`. Until then the column is load-bearing. Re-register KGs
after each repo migrates.

**The `cmd_health.py` probe bug the plan flagged is fixed** (see
`[Unreleased]`). `MIGRATION-sqlite-vec.md` found it independently while
auditing — *"`codekg` is the retired predecessor of `pycode_kg` and is not on
PATH … every code-KG liveness probe silently fails"* — and prescribed
`pycodekg query --sqlite {sqlite} --vectors {vectors}`, which is what landed.
Two notes where the fix goes beyond the plan's prescription:

- The plan says the `doc` and `memory` entries need the same
  `--lancedb` → `--vectors` treatment *"once those repos migrate"*. **`doc` was
  done now, not deferred**, because doc-kg 0.19.1 already accepts
  `--vectors-path` — the flag is chosen from whichever path the registry
  records, so it is correct both before and after doc_kg's Phase 4. **`memory`
  deliberately still passes `--lancedb`**, per plan Phase 3 being outstanding.
- Two further defects in those templates were unrelated to backends and hit
  every kind regardless of migration state: `-k` is not a valid option on any of
  these Click CLIs (only `--k`), and interpolating an empty `--lancedb` value
  made the flag swallow the following token under `shlex.split`.

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
- **`gutenberg_kg`'s own store is migrated** — maintainer-reported 2026-07-30 and
  corroborated by `MIGRATION-sqlite-vec.md` ("✅ own store done",
  `vector_backend="sqlite-vec"`). Its pins on `main` are
  `kgmodule-utils[synthesis,sqlite-vec]>=0.8.0` / `doc-kg>=0.18.1`, and its
  worker already reads sqlite-vec (`_open_vector_source` prefers
  `SqliteVecBackend`). This invalidates the largest row of the 2026-07-26 audit
  table above (237 gutenberg corpora as `unmigrated`) — **re-run `kgrag
  audit-lancedb` for current numbers before treating that table as fleet
  state.** Note the plan's ordering dependency: gutenberg_kg's remaining lancedb
  references are it *orchestrating* other KGs' stores, so **re-audit it once
  `diary_kg` and `doc_kg` land**.
