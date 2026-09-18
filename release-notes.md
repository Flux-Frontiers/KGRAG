# Release Notes — v0.15.1

> Released: 2026-09-18

`kgrag audit-lancedb` no longer tells you to delete a live index, and dependency floors catch up to the fleet.

## What changed

**`audit-lancedb` could recommend deleting real data.** It decided a KG had finished migrating to sqlite-vec by checking whether `vectors.sqlite` existed. A failed or interrupted migration leaves an empty-stub file in exactly that shape, so the audit classified it as leftover residue and its suggested remediation was `rm -rf` on the directory that, in that state, still held the only copy of the index. The check now confirms the store actually has data before calling it migrated, found on `waverider`'s doc KG.

**`kgrag timeline` stopped framing an undated module as unfinished.** Not every knowledge graph is dated by design -- code KGs already have git for that, and some domains don't occur at a time at all -- and the wording used to read that abstention as a gap.

**Dependency floors caught up.** `kgmodule-utils`, `doc-kg`, `pycode-kg`, `memory-kg` and `diary-kg` all move to the fleet's current releases; the `doc-kg`/`pycode-kg` dev-group test dependencies, which govern which real class the adapter tests actually construct, had drifted behind their own extras' floors and are corrected along with them.

## Upgrading

No action needed. `poetry update` picks up the new floors; nothing else changes behavior for existing callers.

---

_Full changelog: [CHANGELOG.md](CHANGELOG.md)_
