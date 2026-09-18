# Release Notes — v0.16.0

> Released: 2026-09-18

kg-rag can now see three more kinds of knowledge graph: connectomes, Swift codebases and TypeScript codebases. Before this release, discovery walked straight past them.

## What changed

**Three new kinds.** `connectome`, `swift` and `typescript` each have a discovery marker, an adapter, a place in the MCP tools' kind filters, and a colour and icon in the app. The Swift and TypeScript adapters share one base, because SwiftKG and TypeScriptKG have the same shape as PyCodeKG. All three rank hits by raw semantic similarity, as the code adapter does, so their best hits compete fairly with every other KG's in a federated query.

**Connectomes install through a new extra.** `pip install "kg-rag[connectome]"` brings in `connectome-kg` 0.3.1, its first PyPI release, which can query a built connectome without the 34 GB source release. Each connectome is its own KG, so discovery registers the FlyWire brain and any later dataset separately. The adapter reports a connectome available only when it has both its graph and its vector index, since a query without the index would fail rather than return nothing.

**One unknown registry row no longer takes everything down.** The registry is shared by every kg-rag on a machine, so a newer kg-rag can write a kind an older one has never seen. That used to raise out of every registry read, breaking `kgrag list`, `kgrag status` and the MCP server. The row is now skipped with a warning.

## Upgrading

Upgrade every kg-rag on the machine that reads the shared registry. A kg-rag older than 0.16.0 fails on any `connectome`, `swift` or `typescript` row as soon as one is registered. Add the `connectome` extra if you register connectomes. swift-kg and tscode-kg are installed on their own.

---

_Full changelog: [CHANGELOG.md](CHANGELOG.md)_
