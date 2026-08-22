# Release Notes — v0.14.0

> Released: 2026-08-22

This release makes time a first-class axis for federated queries. `kgrag
timeline` sorts hits from every adopting KG into one chronological sequence,
and `QueryScope.time_range` lets any federated query be windowed to a date
range as well as a subtree or node kind. Several adapters and a dependency
fix round out the release.

## What changed

**`kgrag timeline` — chronological cross-KG query.** A diary entry, a book
publication, a photograph, and a conversation topic can now sort into one
sequence ordered by *when*, not by relevance, because every adopting module
writes the same three temporal keys. `--from`/`--to` accept any ISO
precision, and the precision is honored rather than padded: a book dated
`1876` renders as `1876`, not as a false midnight on January 1. A recorded-
only date is marked `~` to distinguish "when it was written down" from "when
it happened," and undated hits are counted and reported rather than silently
dropped.

**`QueryScope.time_range` — time as a federation axis.** Federated queries
can now be scoped to a date window alongside a subtree and node kinds, with
either bound left open-ended. This fills the slot `metadata_eq` had been
reserving since 0.10.0, and is what makes "what happened in April" answerable
across diary, memory, conversation, filesystem, and snapshot KGs in a single
call. Undated results are rejected when a time window is set, so a module
that hasn't adopted the temporal contract drops out of time-scoped queries
rather than silently matching everything. Requires `kgmodule-utils>=0.18.0`,
which also fixes the underlying bug that made this impossible before:
`GraphStore` was dropping node metadata on write.

**Adapters now carry node metadata into hits**, wiring the doc, gutenberg,
diary, memory, and filetree adapters up to the temporal contract above —
without it, `time_range` scoping would have been inert in practice.

**Fixes.** `KGRAG` no longer loads an embedding model just to be
constructed — resolution is deferred to the first adapter that actually
needs one, cutting a ~130 MB cold-cache download from commands like `kgrag
status` that never touch an embedder. `kgrag scan` now discovers FTreeKG and
AgentKG instances during auto-registration, and `MemoryKGAdapter` no longer
raises on load after memory-kg's move to sqlite-vec.

**Packaging.** `memory-kg` is now a declared dependency of the `kg` and
`all` extras, fixing `kgrag query --kind memory` on a stock install.
`pyproject.toml` converted to PEP 621. `diary-kg` and `ftree-kg` moved out
of the `kg` extra into their own `diary` and `filetree` extras — **breaking**
for anyone who relied on `kg-rag[kg]` to supply diary or filetree support.

## Upgrading

Run `poetry update` (or reinstall) to pick up `kgmodule-utils>=0.18.0`. If
you use diary or filetree KGs, install `kg-rag[kg,diary,filetree]` — the
plain `kg` extra no longer pulls them in.

---

_Full changelog: [CHANGELOG.md](CHANGELOG.md)_
