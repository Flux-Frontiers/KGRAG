# Release Notes — v0.15.0

> Released: 2026-08-24

This release adds a sixth KG kind to the federation and closes a gap left by
last release's temporal contract, where one adapter's `pack()` was silently
dropping the metadata its own `query()` already carried correctly.

## What changed

**`KGKind.GENEALOGY` — federation support for GenealogyKG.** A new adapter
(`genealogy_adapter.py`), a registry directory marker (`.genealogykg`), and a
colour/icon in the visualizer, following the same four touches every KG kind
has needed so far. genealogy-kg itself is not yet published to PyPI, so the
adapter lazily imports it and reports itself unavailable until it is —
registering the kind now means no second wave of adapter/registry/visualizer
plumbing is needed once the package lands.

**`ftree_adapter.py.pack()` no longer drops snippet metadata.** FileTreeKG's
`pack()` populates each snippet's `metadata` dict, including the temporal
contract keys from 0.14.0's `time_range` scoping — but the adapter's own
`pack()` never forwarded it, even though the same adapter's `query()` already
did. A `time_range`-scoped `pack()` call over a FTreeKG instance therefore
saw every result as undated, silently excluding it from any date-windowed
federated query. One line pinned by new regression tests.

## Upgrading

No action needed — this is a drop-in upgrade. GenealogyKG support is inert
until `genealogy-kg` is installed and registered; the `ftree_adapter.py` fix
takes effect automatically for anyone already using `time_range`-scoped
`pack()` calls against a FileTreeKG instance.

---

_Full changelog: [CHANGELOG.md](CHANGELOG.md)_
