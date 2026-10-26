# Release Notes - v0.18.0

> Released: 2026-10-26

### Changed

- **The KGRAG MCP server is built on `kg_utils.mcp`, and its tools drop the
  `kgrag_` prefix.** `kg_rag.mcp_server` no longer hand-rolls the low-level
  `Server` API: `build_server()` serves a new `kg_rag.federation.Federation`
  through `make_server()`, so `kgrag mcp` takes the fleet's standard flags
  (`--db`, `--repo`, `--transport stdio|streamable-http`, `--host`, `--port`,
  `--manifest`) and answers the five canonical tools -- `stats`, `query`,
  `pack`, `get_node`, `neighbors` -- like every other fleet server, plus 19
  extras (`list_kgs`, `kg_info`, `corpus_*`, `person_*`): 24 tools. Renamed
  with no aliases, per the centralization plan: `kgrag_query` is `query`,
  `kgrag_corpus_query` is `corpus_query`, and so on. Federated node ids are
  `<kg>::<node id>`, and `get_node` / `neighbors` take them unchanged.
  `query` and `pack` take `hop`, `max_nodes` and `rels`; `hop=0`, the
  default, returns what the old tools returned, and `hop>0` appends each
  seed's neighbourhood ranked after the seeds. `--db` is the registry;
  `--registry`, its old spelling, is accepted with a warning until 0.19.
  `--vectors` and `--model` are refused: each registered KG uses its own.
  The direct `mcp` pin is replaced by `kgmodule-utils[mcp]>=0.29.0`, whose
  extra brings `mcp>=1.23.0,<2`.
- **Floors onto the 0.29.0 fleet releases**, whose `stats()` the adapters
  read in the fleet shape: doc-kg 0.29.0, memory-kg 0.13.0, pycode-kg 0.29.0,
  diary-kg 0.101.0, ftree-kg 0.18.0, connectome-kg 0.9.0 and vault-kg 0.6.0
  (the extras and the dev group), plus agent-kg 0.14.0, genealogy-kg 0.4.0,
  swift-kg 0.5.0, tscode-kg 0.8.0 and metabo-kg v0.18.0 (dev group).
- **Every adapter reports stats in the fleet shape.** `KGAdapter.stats()`
  is concrete and returns `{"kind", "nodes": {"total", "by_kind"},
  "edges": {"total", "by_rel"}, ...}` (FLEET_STANDARDS, "KG stats shape"),
  with `kind` set to the registry kind and the envelope (`kg_name`,
  `available`, `builder_version`, `db_size_mb`) as extras. Eleven adapter
  overrides and the stub adapters' flat `stats()` are gone; the vault
  adapter builds on `super().stats()`.
  Modules not yet on the shape are read through `fleet_stats()`, which maps
  the old flat keys and files any uncounted remainder under
  `"(unreported)"`, so the pycodekg adapter no longer reports
  `meaningful_nodes` as its node count. `kgrag status` and `kgrag analyze`
  read totals through the new `stat_totals()`, and the per-domain status
  line lists each KG's top node kinds rather than a hand-written field per
  kind.
  Snapshot metrics read the same shape (flattened back to `total_nodes` /
  `node_counts`), so the code, agent, diary, connectome and stub adapters
  keep recording real counts against modules whose `stats()` has moved to
  the shape, rather than zeros.
- **`docs/MCP.md`'s tool reference is generated.** `scripts/gen_mcp_reference.py`
  renders it from `kgrag mcp --manifest`; `--check` fails when the file has
  drifted, and a test runs it. `Claude.mcp.json`, `CLAUDE.md`, `AGENTS.md`,
  the skills and the docs use the canonical tool names.

### Removed

- **LanceDB is retired.** `kgrag audit-lancedb` is deleted, `kgrag register
  --lancedb` is gone, `KGEntry` loses `lancedb_path`, and the doc and
  gutenberg adapters pass `vectors_path`. The registry keeps its
  `lancedb_path` column, unused, because a released kgrag still writes it;
  corpus import skips the field with a warning, and `kgrag health` reports
  a KG with only a LanceDB store as `lancedb_only`.

- **`agent-kg` dev floor raised to `>=0.13.0`, and the lock moved to it.**
  agent-kg 0.13.0 removed the private `agent_kg.graph._PROFILE_BASE`
  constant the real-class agent adapter test patched, and added the
  `AGENTKG_PROFILE_ROOT` variable that replaces it. The test now sets the
  variable, so it still keeps the profile out of `~/.kgrag/profiles`; older
  agent-kg releases ignore the variable, hence the floor.

---

_Full changelog: [CHANGELOG.md](CHANGELOG.md)_
