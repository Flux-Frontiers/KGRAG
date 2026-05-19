# Release Notes - v0.7.5

> Released: 2026-05-18

## Changed

- **`poetry.lock`** — `doc-kg` bumped from `0.15.0` to `0.15.2`; adds
  `transformers >=4.40.0,<4.57` constraint and tightens `rich <15.0.0`.
  Fixes the broken `poetry.lock` that caused the v0.7.4 release to fail.
- **`runpod/docker-compose.yml`** — `HANDLER_SECRET` env var added to the
  service definition so local Docker tests honour the same secret as the
  RunPod endpoint.
- **`src/kg_rag/mcp_server.py`** — MCP tool schemas updated: `agent`,
  `filetree`, `gutenberg`, and `ia` KG kinds added to the `kind` enum in
  `kgrag_query`, `kgrag_corpus_query`, and `kgrag_person_query` tool
  definitions.

---

_Full changelog: [CHANGELOG.md](CHANGELOG.md)_
