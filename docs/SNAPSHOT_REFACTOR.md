# Snapshot Infrastructure Refactor

*Centralising snapshot logic across KGRAG and all KG modules.*

---

## Problem

Every KG adapter copy-pasted the same ~30-line `snapshot()` method:

```python
def snapshot(self, version, label=None):
    self._load()
    try:
        if callable(getattr(self._kg, "snapshot", None)):
            result = self._kg.snapshot(version, label=label)
            if isinstance(result, dict):
                return result
            raw = getattr(result, "__dict__", None)
            if raw is not None:
                return {k: v for k, v in raw.items() if not k.startswith("_")}
    except Exception:
        pass
    gs = self._graph_stats()
    return { ... }  # fallback dict
```

This pattern was duplicated across **11 adapters**. Meanwhile, three backing
libraries (code\_kg, doc\_kg, ftree\_kg) each maintained their own 400–550 line
`snapshots.py` with nearly identical `SnapshotManager`, `Snapshot`,
`SnapshotManifest`, and `SnapshotDelta` implementations.

Any change to the snapshot contract required touching 11 adapter files and 3
library repos — a guaranteed source of drift and bugs.

---

## Solution

### 1. Shared snapshot module: `kg_rag.snapshots`

A single canonical module providing:

| Type | Purpose |
|------|---------|
| `Snapshot` | Dict-based metrics dataclass (domain-flexible) |
| `SnapshotManifest` | JSON manifest index |
| `SnapshotManager` | Parameterised manager with overridable delta computation |

`Snapshot.metrics` is a `dict[str, Any]` — not a typed dataclass — so that
domains can store whatever fields they need (docstring\_coverage, total\_files,
coverage\_score, etc.) without requiring changes to the shared model.

`SnapshotManager` is parameterised by `package_name` for version detection and
accepts an optional `db_path` for SQLite-based metric collection.  Subclasses
override `_compute_delta()` and `_compute_delta_from_metrics()` to add
domain-specific delta fields.

### 2. Template method on `KGAdapter`

`KGAdapter.snapshot()` is now a **concrete template method** — no longer
abstract.  It builds a standard envelope and delegates to a single hook:

```python
# base.py — the only snapshot code adapters need to know about
def snapshot(self, version, label=None):
    gs = self._graph_stats()
    snap = {
        "version": version,
        "label": label,
        "timestamp": datetime.now(UTC).isoformat(),
        "kind": self.entry.kind.value,
        "kg_name": self.entry.name,
        "node_count": gs["node_count"],
        "edge_count": gs["edge_count"],
    }
    extra = self._collect_snapshot_metrics()
    if extra:
        snap.update(extra)
    return snap

def _collect_snapshot_metrics(self) -> dict[str, Any]:
    """Override to add domain-specific metrics."""
    return {}
```

Adapters override `_collect_snapshot_metrics()` — typically 5–15 lines of
focused domain logic instead of 30 lines of boilerplate.

### 3. Backing libraries as thin layers

Each library's `snapshots.py` becomes a compatibility layer:

- **Imports** `Snapshot`, `SnapshotManifest`, `SnapshotManager` from
  `kg_rag.snapshots` (re-exported for backwards compat).
- **Keeps** domain-specific `SnapshotMetrics` and `SnapshotDelta` dataclasses
  for typed CLI and test access.
- **Subclasses** `SnapshotManager` for domain-specific deltas and metric
  collection (e.g. `coverage_delta`, `files_delta`, `_collect_module_node_counts`).
- **Provides** `metrics_to_dict` / `metrics_from_dict` helpers for converting
  between the typed dataclass and the underlying dict.

---

## Impact

### Lines changed (KGRAG adapters)

| Adapter | Before | After | Delta |
|---------|--------|-------|-------|
| CodeKGAdapter | 31 lines | 14 lines | -17 |
| DocKGAdapter | 21 lines | 12 lines | -9 |
| MetaKGAdapter | 36 lines | 2 lines | -34 |
| DiaryKGAdapter | 31 lines | 12 lines | -19 |
| StubKGAdapter | 37 lines | 16 lines | -21 |
| **6 stub subclasses** | 0 each | 0 each | 0 |

**Net: -100 lines of boilerplate removed from adapters.**

### Backing libraries

| Library | Before | After | Reduction |
|---------|--------|-------|-----------|
| code\_kg/snapshots.py | 558 lines (standalone) | ~400 lines (thin layer) | Logic delegated to kg\_rag |
| doc\_kg/snapshots.py | 454 lines (standalone) | ~350 lines (thin layer) | Logic delegated to kg\_rag |
| ftree\_kg/snapshots.py | 493 lines (standalone) | ~290 lines (thin layer) | Logic delegated to kg\_rag |

### Test results

| Repo | Tests | Result |
|------|-------|--------|
| KGRAG | 162 | All pass |
| code\_kg | 259 | All pass |
| doc\_kg | 117 | All pass |
| ftree\_kg | (no test suite) | Imports verified |

---

## Migration guide

### For existing adapters

Replace your `snapshot()` override with `_collect_snapshot_metrics()`:

```python
# BEFORE (every adapter)
def snapshot(self, version, label=None):
    self._load()
    try:
        if callable(getattr(self._kg, "snapshot", None)):
            result = self._kg.snapshot(version, label=label)
            ...
    except Exception:
        pass
    gs = self._graph_stats()
    return {"version": version, "label": label, ...}

# AFTER
def _collect_snapshot_metrics(self) -> dict[str, Any]:
    try:
        self._load()
        s = self._kg.store.stats()
        return {"total_nodes": s.get("total_nodes", 0), ...}
    except Exception:
        return {}
```

### For new KG modules

1. Your adapter gets `snapshot()` for free — no override needed for basic
   snapshots.
2. Override `_collect_snapshot_metrics()` to add domain-specific data.
3. Subclass `kg_rag.snapshots.SnapshotManager` for your CLI snapshot commands,
   setting `package_name` and overriding `_compute_delta_from_metrics()` for
   domain-specific deltas.

### For backing library maintainers

Replace your standalone `snapshots.py` with the thin layer from
`_backing_lib_patches/<repo>/`.  Existing `from <pkg>.snapshots import ...`
call-sites continue to work unchanged.

---

## Architecture

```
kg_rag.snapshots  (canonical source)
├── Snapshot           — dict-based metrics, flexible
├── SnapshotManifest   — JSON manifest index
└── SnapshotManager    — capture / save / load / list / diff
        ↑
        │  subclass with domain-specific deltas
        │
    ┌───┴───────────────┬──────────────────┐
    │                   │                  │
code_kg.snapshots  doc_kg.snapshots  ftree_kg.snapshots
    │                   │                  │
    ├── SnapshotMetrics ├── SnapshotMetrics├── SnapshotMetrics
    ├── SnapshotDelta   ├── SnapshotDelta  ├── SnapshotDelta
    └── SnapshotManager └── SnapshotManager└── SnapshotManager
        (coverage_delta)    (issues_delta)     (files_delta)
```

```
KGAdapter.snapshot()  (concrete template method)
    │
    ├── builds standard envelope (version, timestamp, kind, counts)
    └── calls _collect_snapshot_metrics()
            │
            ├── CodeKGAdapter: returns store.stats() dict
            ├── DocKGAdapter:  returns store.stats() dict
            ├── StubKGAdapter: returns {status, total_nodes, total_edges}
            └── (new adapter):  return {} for basic, or override for richer data
```
