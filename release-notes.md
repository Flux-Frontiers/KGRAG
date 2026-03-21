# Release Notes — v0.3.5

> Released: 2026-03-20

### Added
- `kgrag init --corpus NAME` — after building and registering KG layers, automatically
  add every successfully registered KG to an existing corpus in one step. Eliminates the
  need for separate `kgrag corpus add` calls when initialising a repo into an existing
  corpus. Fails gracefully with a clear error if the corpus is not found.

### Changed
- **Dependency update**: `sentence-transformers` unpinned to `^5.2.0` (was `==4.1.0`);
  `transformers` updated to `^4.57.6`; `safetensors` pinned to `^0.5.0`. `poetry.lock`
  updated accordingly (`sentence-transformers` 4.1.0 → 5.3.0, `safetensors` 0.7.0 → 0.5.3).
- **docs/USAGE.md**: Updated `kgrag init` reference and Workflow 3 example to show
  `--corpus` usage; corpus-scoped query replaces the flat `kgrag query` call.
- **docs/FEATURES.md**: Added `--corpus NAME` to the `kgrag init` options line.

### Fixed
- `SnapshotManager._compute_delta` now converts `SnapshotMetrics` dataclass objects to
  plain dicts before calling `_compute_delta_from_metrics`, fixing an `AttributeError`
  raised when subclasses (e.g. FTreeKG) hydrate `snap.metrics` as a dataclass rather
  than a dict.

---

_Full changelog: [CHANGELOG.md](CHANGELOG.md)_
