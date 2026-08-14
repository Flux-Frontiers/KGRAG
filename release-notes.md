# Release Notes — v0.12.0

> Released: 2026-08-14

This release makes `kg-rag` dramatically lighter to install and the repository
cleaner to read. A no-extras install now pulls 56 fewer packages, and the
public repo sheds its deployment scaffolding and stale planning documents —
what ships is the orchestration library, and what you see is what ships.

## What changed

**A much smaller install.** Two dependency declarations that never belonged in
the runtime set are gone: the Jupyter notebook stack (`jupyter-server`,
`mistune`, and the entire tree that arrived with them — nothing in `src/`
imports any of it) and `pip` itself, which was pinned as a runtime dependency
despite only being needed by dev tooling. The lock shrinks from 262 packages
to 206, core runtime dependencies drop from 12 to 10, and all seven extras
are unchanged. Verified against the built wheel: no jupyter or pip
requirement in its metadata, and all 14 console scripts load from a clean
no-extras install.

**A leaner, truthful repository.** The RunPod deployment infrastructure
(`runpod/`, `.runpod/`) has moved out of the public repo — it is operational
material, downstream of the package. The long-stale `TODO.md` is retired:
the LanceDB-retirement work it tracked is complete (every published fleet
package now ships sqlite-vec), and fleet coordination lives with the rest of
the fleet's operational docs. `FLEET_VERSIONS.md` now lives under `docs/`
and is linked from the README, and the README's feature list credits
sqlite-vec — the actual semantic backend — rather than LanceDB.

**CI lint no longer lies to you.** The dev floor for ruff is capped below
0.16, whose formatter rewrites Python inside Markdown code blocks and had
put `main` itself into a state where `ruff format --check` failed for every
PR. CI and pre-commit now agree on a formatter version.

## Upgrading

Nothing to do. `pip install --upgrade kg-rag` — the API, CLI, and all extras
are unchanged. If your environment relied on Jupyter arriving transitively
through kg-rag, install it directly; kg-rag no longer brings it.

---

_Full changelog: [CHANGELOG.md](CHANGELOG.md)_
