# Release Notes -- v0.18.2

> Released: 2026-11-09

A dependency release. kg-rag's floors for the fleet's KG packages move to
their current releases, so a fresh install resolves the versions kg-rag is
tested against. Federation, the registry and every command are unchanged.

## What changed

**Floors at the current fleet releases.** kgmodule-utils 0.30.0, for the
core and for `[ingest]`. In the extras, in `all` and in the dev group:
doc-kg 0.30.0, pycode-kg 0.29.3, vault-kg 0.6.1 and connectome-kg 0.10.1. In
the dev group only: genealogy-kg 0.6.0, swift-kg 0.5.1 and tscode-kg 0.8.1.
memory-kg, diary-kg, ftree-kg and agent-kg were already at their latest
releases.

**doc-kg is still optional.** It backs the doc and gutenberg adapters through
the `kg` and `all` extras. Each adapter imports it only when it runs, and
without doc-kg the orchestrator runs but cannot query doc KGs.

## Upgrading

`pip install -U "kg-rag[all]"` (or the extras you use). No registry or index
changes.

---

_Full changelog: [CHANGELOG.md](CHANGELOG.md)_
