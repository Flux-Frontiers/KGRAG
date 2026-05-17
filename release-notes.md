# Release Notes — v0.7.1

> Released: 2026-05-17

## Highlights

### RunPod Hub publishing support

A new `.runpod/` directory makes the KGRAG serverless worker publishable to the
RunPod Hub with one click. `hub.json` defines the listing (GPU pool, env var UI
for `KG_VOLUME` and synthesis settings), `tests.json` provides three smoke tests
that run against an empty volume, and a Hub-compatible `Dockerfile` installs all
three non-PyPI packages (`kg-rag`, `gutenberg-kg`, `metabo-kg`) directly from
GitHub — no local wheel build required.

### build_kg.py hardening

The pod volume builder gains four improvements:

- **`--cpu` flag** — sets `CUDA_VISIBLE_DEVICES=-1` for pods with GPU drivers
  too old for the installed PyTorch CUDA build.
- **13-genre default list** — expands from 3 to the full corpus
  (american-literature through world-literature).
- **Skip already-downloaded genres** — detects a non-empty `corpus/<genre>/`
  dir and skips re-download, so interrupted builds resume cleanly.
- **Explicit torch install** — installs `torch` from the `cu124` wheel index
  before project packages; override via `TORCH_CUDA_INDEX`.

### Reliability fixes

- **httpx timeouts** in both `kgrag synthesize` and the RunPod worker's synthesis
  path replaced scalar timeouts with `httpx.Timeout(connect=10, read=600, ...)` —
  the scalar form was firing on read inactivity, killing responses from large local
  models before they finished streaming.
- **Per-book Gutenberg registry** — the worker now walks
  `corpus/<genre>/<book>/.dockg/` at cold start and registers each book as its own
  KG entry (203 books in a typical corpus), replacing the old single consolidated
  entry that returned project documentation mixed into literary results.

---

_Full changelog: [CHANGELOG.md](CHANGELOG.md)_
