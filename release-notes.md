# Release Notes - v0.21.0

> Released: 2026-11-25

kgrag 0.21.0 makes `kgrag rebuild-indices` easier to run over a whole
registry. The first full run spent a long, silent stretch on a file tree
over all of `~/repos`; now such a KG can be left out by name, and every
build says where it stands in the run.

## What changed

**Skip a KG by name.** `--exclude NAME` leaves that KG out of the run and
lists it in the summary with the reason "excluded with --exclude". Repeat
it to skip several.

**Each build is numbered.** The header above each build reads, for
example, `fleet-docs (3 of 151)`, so a long run shows how far along it is.

**Current fleet locks.** The lock now carries ftree-kg 0.19.0, whose
`ftreekg build` draws a progress bar for each pass.

## Upgrading

Nothing to migrate.

---

_Full changelog: [CHANGELOG.md](CHANGELOG.md)_
