# Release Notes — v0.11.0

> Released: 2026-07-29

KGRAG now tracks sqlite-vec vector stores as first-class registry data. As the
fleet migrates off LanceDB, a registered KG can point at a `vectors.sqlite` file
instead of a `lancedb/` directory, and the registry, adapters, health checks and
export path all understand the difference. This release also pins `mcp` below
2.0 — without it, a clean install produced a `kgrag-mcp` that could not start.

## What changed

**`vectors_path` is a real field, not an overload of `lancedb_path`.**
`KGEntry` gains a `vectors_path` column recording the sqlite-vec store *file*,
added to existing registries by an in-place migration on next open, so nothing
needs re-registering to keep working. `kgrag register --vectors PATH` sets it
directly. `lancedb_path` remains for corpora built by pre-migration builders and
is no longer written for code KGs at all — the two coexist deliberately while
the fleet is mid-transition, and only the last repo to migrate will make the old
field removable.

**Adapters stopped ignoring the registered vector store.** The doc-family
adapters derived `vectors.sqlite` from the graph's directory and disregarded
whatever the registry said, so a corpus whose vectors lived anywhere else was
simply unreachable. They now honour `vectors_path`. `kgrag export` had a related
gap: it shipped code-KG bundles without their vectors, producing archives that
looked complete and were not.

**`kgrag audit-lancedb` reports the migration's real state.** It classifies each
KG as unmigrated, residue, stale-row, clean, or no-index, emits the exact
remediation command for each, and finds `lancedb/` directories on disk that no
registry entry references. It reports only — it never deletes or rebuilds. A
`stale_vectors` health check covers the inverse case, where a registered vector
store has gone missing.

**`mcp` is pinned below 2.0.** mcp 2.0 removed the low-level `Server` decorator
API — `@server.list_tools()` and `@server.call_tool()` — that this package is
built on. The class still *imports* under 2.0, so nothing fails until the server
is constructed, at which point no handler registers at all. That made it easy to
miss: a pinned lock file keeps every developer working, and only a fresh install
from PyPI sees it. New tests build the server for real rather than merely
importing it, because an import-only check would have passed while `kgrag-mcp`
stayed broken.

## Upgrading

`pip install --upgrade kg-rag`. Existing registries migrate themselves on first
open — no re-registration, no rebuild, and `lancedb_path` entries keep working
untouched.

If you have migrated any KG to sqlite-vec, re-register it (or pass `--vectors`)
so the registry records the new path; until then the entry still points at the
old store. `kgrag audit-lancedb` will tell you where each KG actually stands.

Note that PyPI goes straight from 0.10.0 to 0.11.0 — 0.10.1 appears in the
changelog but was never published, and its changes ship here.

---

_Full changelog: [CHANGELOG.md](CHANGELOG.md)_
