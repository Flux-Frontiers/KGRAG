# KGRAG TODO

## Landed — no action required

- **`KGEntry.vectors_path` is a first-class registry field** (filed 2026-07-26
  from `pycode_kg`, resolved same day, **shipped in 0.11.0** — see CHANGELOG
  `[0.11.0]`). Added to `KGEntry` and the schema with an in-place `_migrate()`;
  `lancedb_path` stays readable for kinds that still ship LanceDB but is no
  longer written for code KGs; auto-detection probes `<db_dir>/vectors.sqlite`
  first; `CodeKGAdapter._load` reads `entry.vectors_path` directly instead of
  guessing a sibling of `lancedb_path`; `kgrag export`/`import` bundle the
  file-shaped store so code-KG bundles no longer ship without their vectors.
- **Doc-family adapters can pass a non-default vector-store location**
  (closed 2026-07-26, **shipped in 0.11.0**). `DocKGAdapter`/
  `GutenbergKGAdapter` previously made `vectors_path` informational only for
  doc KGs. Fixed upstream in **doc-kg 0.18.2** (`DocKG(vectors_path=...)` plus
  `--vectors-path` on the 8 vector-touching CLI commands) and wired through
  here; the kgrag floor is `doc-kg>=0.18.2`. `vectors_path` is now
  authoritative for every KG kind.

## LanceDB retirement — fleet state needs re-measuring

> **The figures below are from 2026-07-26 and are known stale** — the gutenberg
> corpora have since migrated (see Remaining coordination), which invalidates
> the largest row. **Re-run `kgrag audit-lancedb` before quoting any of it.**
> For the *code* migration — which repo ships which backend, in what order —
> the plan of record is `pycode_kg/MIGRATION-sqlite-vec.md`; see the audit
> section below.

`kgrag audit-lancedb` measured the real registry on 2026-07-26: **242 of 253
KGs still had LanceDB as their live vector index**, holding ~2.0 GB on disk.
The schema work above only stopped kgrag *recording* it for new code KGs.

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

> **The plan of record takes the opposite line on conversion**, and it is the
> one to follow: vector stores are derived artifacts, so
> `MIGRATION-sqlite-vec.md` says **delete and rebuild** rather than convert.
> Two guards it insists on first, because they are what caught `agent_kg` out:
> capture query results *before* deleting (you cannot compare against a store
> you removed), and reconcile `SELECT COUNT(*) FROM nodes` against
> `backend.count()` — every `.agentkg` index had drifted 15–100%, so parity
> looked *better* after migrating purely because the control was incomplete.

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
| `doc-kg` | 0.19.1 | **hard** | `index.py` | yes (8 files) | ✅ Phase 4 done on branch (0.20.0) — **not yet published** |
| `diary-kg` | 0.93.4 | **hard** | 0 files | 0 files | ✅ ported on branch — **not yet published**, see below |
| `memory-kg` | 0.6.2 | **hard** | `index.py` | **0 files** | 🟠 plan Phase 3 |
| `Metabo_kg` | — | — | — | — | 🟡 plan Phase 2 — **not on PyPI**, unaudited here |

**Phase 1 (`diary_kg`) is ported — 2026-07-30, `diary-kg` 0.94.0 on branch
`claude/diarykg-setup-gf80dz`, not yet released to PyPI.** The row above stays at
0.93.4 because that is still the published version; re-audit after the release.
What landed, and what did *not*:

- Vector artifact moved from the `.diarykg/lancedb/` directory to a single
  `.diarykg/vectors.sqlite` file. DocKG's backend is **pinned** to `sqlite-vec`
  at all three construction sites rather than left on `"auto"`, and
  `vectors_path` is passed explicitly so the reported path is the written path.
  A leftover `lancedb/` dir is now inert and no longer satisfies `is_built()`.
- `diary_kg.primitives.KGEntry` gained `vectors_path` (mirroring
  `kg_rag.primitives.KGEntry` field order); `lancedb_path` retained as
  deprecated. `diary-transformer build` registers `vectors_path` now.
- Direct `lancedb` dependency dropped; `doc-kg` floor lifted to `>=0.18.2` and
  installed as `doc-kg[sqlite-vec]` — that extra is **required, not optional**,
  since doc-kg ships the `sqlite_vec` runtime opt-in and the pinned backend
  fails at index-open without it.
- **The plan's Learning #2/#3 traps do not apply here, verified rather than
  assumed.** No score recalibration was needed: both backends in this stack
  already use cosine (`kg_utils` `LanceDBBackend` queries with
  `.metric("cosine")`; `SqliteVecBackend` declares `distance_metric=cosine`), so
  there is no squared-L2 → cosine factor as in `ftree_kg`. And DocKG's
  `_META_COLUMNS` carries `kind`, the only vector-store field DiaryKG reads —
  every other displayed field comes from the enriched SQLite `nodes` table — so
  the blanked-output trap cannot bite.
- **Not done, and blocking a "verified" claim:** plan step 6 (capture a same-day
  LanceDB control, rebuild, `diff`) was **not** run — the checkout has no diary
  corpus and no installed deps, so there was nothing to build or compare. Plan
  step 8 (re-register with kgrag) is likewise outstanding. The suite was not
  executed either; verification was `ruff check`/`format` clean, all files
  compiled, and the migration invariants exercised directly with the vector
  wiring stubbed. **Someone with the Pepys corpus must run the parity check and
  re-register before this is trusted as done.**

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
- ~~**doc-kg still hard-requires `lancedb>=0.29.0`**~~ — **RESOLVED on branch,
  doc-kg 0.20.0 (Phase 4), not yet published.** This was the binding constraint
  for *installs*: an unconditional dependency, so lancedb landed in every worker
  image regardless of extras, and every sibling depending on doc-kg (diary-kg,
  gutenberg-kg, corpus_pepys) inherited it no matter what it declared itself.

  0.20.0 drops it to an optional `[lancedb]` extra needed **only** to read a
  pre-0.20.0 store via `dockg convert-index` — nothing is stranded, and the
  converter still reads vectors straight out of LanceDB with no re-embedding.
  `vector_backend` now defaults to `"sqlite-vec"` instead of `"auto"`, and
  `SemanticIndex`'s implicit backend is sqlite-vec rather than LanceDB.

  Verified in the regenerated lock rather than asserted: `lancedb` is
  `optional = true` with `markers = extra == "lancedb"`, `sqlite-vec` is
  `optional = false`, and `[extras]` reads `lancedb = ["lancedb"]` /
  `sqlite-vec = []` with `all` free of lancedb.

  Two things to carry forward:

  * **The `[sqlite-vec]` extra is retained as an empty no-op alias**, because
    diary-kg >=0.94.0 pins `doc-kg[sqlite-vec]`. Deleting it would fail every
    diary-kg install on an unknown extra. Do not "clean it up".
  * **kgmodule-utils is now the only remaining source.** `[semantic]` still
    carries `lancedb>=0.19.0` (see the bullet above). doc-kg depends on bare
    `kgmodule-utils>=0.9.0` with no extras, so nothing here reintroduces it —
    but anything installing `kgmodule-utils[semantic]` still gets it. That work
    item is unchanged and is now the last one on this axis.

  corpus_pepys no longer *imports* lancedb anywhere (worker is sqlite-vec only,
  LanceDB fallback removed, merged as corpus_pepys#1); after doc-kg 0.20.0 is
  published it should stop being *installed* there too.

  **The dependency drop is an *outcome* of each repo's migration, not a
  shortcut past it** — see the audit section above. It is tempting to read this
  bullet as "two releases demote an extra and we are done"; that was the
  diary-kg mistake corrected there. Per the plan, diary-kg is a real Phase-1
  port (30 lancedb source refs, 2 `--lancedb` CLI refs, no `KGModule` seam to
  flip) and doc-kg is Phase 4. Sequence the work from
  `MIGRATION-sqlite-vec.md`; the `pyproject.toml` edit is step 6 of 8 in its
  checklist, not the whole job.

  ~~Also cosmetic: `diarykg build` still prints a "LanceDB :" path label while
  writing `vectors.sqlite`.~~ **Fixed in diary-kg 0.94.0** — `build`, `reindex`
  and `status` now print `Vectors :`, and the `diarykg-mcp` banner reports
  `vectors`.
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

  **Half of that trigger has now fired.** `diary_kg` 0.94.0 writes
  `.diarykg/vectors.sqlite`, so gutenberg_kg's `_register_diary`
  (`ingest.py:293-301`) is stale. Note what it actually does — it *registers*,
  it does not build: it probes `.diarykg/lancedb` and passes
  `lancedb_path=lancedb if lancedb.exists() else None`, with no `vectors_path`
  at all. Against a 0.94.0 diary the probe simply misses, so every
  gutenberg-orchestrated diary registers with **both** vector columns empty and
  the registry loses the vector-store pointer entirely — silently, since `None`
  is a legal value. Fix is a one-liner per the doc-family pattern: probe
  `.diarykg/vectors.sqlite` and pass `vectors_path=`.

  **Correction — the book path was broken too, and had been for longer.** An
  earlier revision of this bullet said `ingest.py:243-250` (`register_book`,
  `.dockg/lancedb`, same shape) "stays correct until `doc_kg` Phase 4." That was
  wrong, and waiting on doc_kg would have left the larger half of the bug in
  place. `build_dockg` constructs `DocKG(book_dir, embedder=...)` with **no
  `vector_backend`**, leaving it on `"auto"` — which already resolved to
  sqlite-vec for a fresh corpus. So every freshly built book was already writing
  `.dockg/vectors.sqlite` and registering nothing, entirely independent of
  diary_kg. The lesson generalises: `auto` had *silently migrated* call sites
  well before any repo declared itself migrated, so "this reference is still
  correct" cannot be inferred from a repo's stated migration status — check what
  the builder actually writes.

  **Both are fixed**, along with two more sites of the same defect in
  `serve/handler.py`'s bootstrap (the DocKG bundle entry passed its LanceDB dir
  *unconditionally*, recording a directory that need not exist). All four now
  share `gutenberg_kg.vector_store.resolve_vector_paths()`, whose precedence
  deliberately matches `handler._open_vector_source` — the defect was the read
  path and the register path disagreeing.
