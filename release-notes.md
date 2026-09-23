# Release Notes -- v0.17.0

> Released: 2026-09-22

KGRAG can now federate Obsidian-style Markdown vaults. A vault registered as
kind `vault` is searched alongside code, documents, diaries and every other
registered knowledge graph, and its hits carry the note's path, line span
and frontmatter dates like any other.

## What changed

**A new kind: `vault`.** VaultKG builds a graph from the links a vault's
author wrote -- wikilinks, embeds, tags and typed links such as
`supports:: [[X]]` -- with no model extraction. KGRAG reaches it through a
`VaultKGAdapter`, finds `.vaultkg/` stores with `kgrag scan`, and lists the
kind in the app and the MCP tools' kind filters. Notes with a frontmatter
`date` or `created` carry the fleet's time keys, so time-scoped queries
filter them with everything else.

**A `vault` extra.** `pip install "kg-rag[vault]"` installs VaultKG with
KGRAG; it is also part of `all`. Without it the kind reports unavailable
rather than failing.

**Current fleet dependencies.** The lock moves to connectome-kg 0.7.1,
diary-kg 0.100.0, ftree-kg 0.17.0 and memory-kg 0.12.0. The `pi` extra is
gone: it pulled `llama-cpp-python`, which nothing configured, and made
`--all-extras` need a compiler on some platforms. The `llama` embedding
backend still works if you install that package yourself.

**Docs that match the fleet.** The adapter table and sister-project list now
include GenealogyKG, SwiftKG, TypeScriptKG and VaultKG, the usage guide
counts 19 KG types, and the install instructions list every per-kind extra.

## Upgrading

```bash
uv tool install --force 'kg-rag[all]'
kgrag register my-brain vault ~/brain     # after: vaultkg build --vault ~/brain
```

Nothing else changes for existing registries. If you installed the `pi`
extra, install `llama-cpp-python` directly instead.

---

_Full changelog: [CHANGELOG.md](CHANGELOG.md)_
