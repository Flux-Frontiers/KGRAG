# Release Notes - v0.20.0

> Released: 2026-11-24

kgrag 0.20.0 adds `kgrag rebuild-indices`, one command that rebuilds every
knowledge graph in the registry. Before it, rebuilding meant a hand-kept
list of repositories that missed corpora and drifted from what the registry
actually held.

## What changed

**One rebuild for the whole registry.** The command walks the registry, or
one corpus, kind or KG, and runs each KG's own builder (pycodekg, dockg,
ftreekg, tscodekg, swiftkg, memorykg, genkg, vaultkg or diarykg) in the
folder that holds its store. Builders come from `PATH` first, then from the
nearest `.venv` above the KG. Agent KGs, whose store is their own source,
and static corpora that are costly to rebuild (Gutenberg, Internet Archive,
connectome) are skipped with the reason shown. `--dry-run` prints the whole
plan without building anything, and a failed build does not stop the rest.

**Current fleet locks.** The lock now carries kgmodule-utils 0.32.0,
pycode-kg 0.30.0 and genealogy-kg 0.7.0. kgmodule-utils 0.32.0 records a
hash for every source file and leaves out text from a file edited since the
build; kgrag's adapters already drop nodes with no text, so a federated
answer never quotes shifted lines.

## Upgrading

Nothing to migrate. Run `kgrag rebuild-indices --dry-run` to see what a
rebuild would do, then run it without the flag after upgrading a builder.

---

_Full changelog: [CHANGELOG.md](CHANGELOG.md)_
