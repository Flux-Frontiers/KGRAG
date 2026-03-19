# MetaboKG Snapshot Infrastructure Refactor

*Applying the centralised snapshot pattern to the metabolic pathway KG.*

---

## Background

MetaboKG (currently named MetaKG in the codebase) is the first domain-specific
KG outside software engineering — a semantic + structural knowledge graph for
metabolic pathways in biochemistry. See `.claude/METABOG_NAMING_NOTE.md` for
the full naming rationale.

This document describes how the snapshot refactor applies to MetaboKG, aligning
it with the same centralised pattern used by CodeKG and DocKG.

---

## Current State

### MetaKGAdapter.snapshot() — 36 lines of boilerplate

The current implementation in `src/kg_rag/adapters/metakg_adapter.py:181-216`
follows the same copy-paste pattern as every other adapter:

```python
def snapshot(self, version: str, label: str | None = None) -> dict[str, Any]:
    gs = self._graph_stats()
    snap: dict[str, Any] = {
        "version": version,
        "label": label,
        "timestamp": datetime.now(UTC).isoformat(),
        "kind": "meta",
        "kg_name": self.entry.name,
        "node_count": gs["node_count"],
        "edge_count": gs["edge_count"],
        "status": "available" if self.is_available() else "unavailable",
    }
    if not self.is_available():
        return snap
    try:
        self._load()
        if callable(getattr(self._kg, "snapshot", None)):
            result = self._kg.snapshot(version, label=label)
            if isinstance(result, dict):
                return result
            raw = getattr(result, "__dict__", None)
            if raw is not None:
                return {k: v for k, v in raw.items() if not k.startswith("_")}
    except Exception:
        pass
    return snap
```

Problems:

1. **Duplicated envelope construction** — version, label, timestamp, kind,
   kg_name, node_count, edge_count are built identically in every adapter.
2. **Duplicated delegation pattern** — the `getattr` / `callable` /
   `isinstance` / `__dict__` dance to delegate to the backing library is the
   same boilerplate found in CodeKGAdapter, DocKGAdapter, DiaryKGAdapter, and
   StubKGAdapter.
3. **No snapshot persistence** — unlike CodeKG and DocKG which persist to
   `.codekg/snapshots/` and `.dockg/snapshots/`, MetaKG has no snapshot
   directory or manifest.
4. **No CLI snapshot commands** — no `metakg snapshot save|list|show|diff`.

### Backing library status

The `metabo-kg` dependency is commented out in `pyproject.toml`:

```toml
# metabo-kg = {git = "https://github.com/Flux-Frontiers/metabo_kg.git"}
```

The external `metakg` package wraps `MetaKGOrchestrator`. Its snapshot
infrastructure (if any) is unknown — the adapter defensively checks for a
`.snapshot()` method and falls back gracefully.

---

## Refactored Design

### 1. Adapter: delete snapshot(), add _collect_snapshot_metrics()

Once the base class `KGAdapter.snapshot()` becomes a concrete template method
(see `docs/SNAPSHOT_REFACTOR.md`), MetaKGAdapter replaces its 36-line
`snapshot()` with a focused 10-line hook:

```python
# AFTER — metakg_adapter.py
def _collect_snapshot_metrics(self) -> dict[str, Any]:
    """Return metabolic-pathway-specific metrics for the snapshot envelope."""
    metrics: dict[str, Any] = {
        "status": "available" if self.is_available() else "unavailable",
    }
    if not self.is_available():
        return metrics
    try:
        self._load()
        raw = self._kg.stats() if callable(getattr(self._kg, "stats", None)) else {}
        if isinstance(raw, dict):
            metrics["pathway_count"] = raw.get("pathway_count", 0)
            metrics["enzyme_count"] = raw.get("enzyme_count", 0)
            metrics["metabolite_count"] = raw.get("metabolite_count", 0)
            metrics["reaction_count"] = raw.get("reaction_count", 0)
    except Exception:
        pass
    return metrics
```

**Result: -26 lines, zero envelope duplication, domain-focused.**

### 2. Backing library: metabo_kg/snapshots.py

When the `metabo_kg` package is built out, its `snapshots.py` should follow the
thin-layer pattern:

```python
# metabo_kg/snapshots.py — thin layer over kg_rag.snapshots
from kg_rag.snapshots import Snapshot, SnapshotManifest, SnapshotManager

@dataclass
class MetaboSnapshotMetrics:
    """Typed domain metrics for metabolic pathway snapshots."""
    pathway_count: int = 0
    enzyme_count: int = 0
    metabolite_count: int = 0
    reaction_count: int = 0
    total_nodes: int = 0
    total_edges: int = 0

@dataclass
class MetaboSnapshotDelta:
    """Domain-specific delta between two metabolic snapshots."""
    pathway_delta: int = 0
    enzyme_delta: int = 0
    metabolite_delta: int = 0
    reaction_delta: int = 0
    node_delta: int = 0
    edge_delta: int = 0

class MetaboSnapshotManager(SnapshotManager):
    """Metabolic pathway snapshot manager."""

    def __init__(self, db_path=None):
        super().__init__(package_name="metabo_kg", db_path=db_path)

    def _compute_delta_from_metrics(self, old, new):
        return MetaboSnapshotDelta(
            pathway_delta=new.get("pathway_count", 0) - old.get("pathway_count", 0),
            enzyme_delta=new.get("enzyme_count", 0) - old.get("enzyme_count", 0),
            metabolite_delta=new.get("metabolite_count", 0) - old.get("metabolite_count", 0),
            reaction_delta=new.get("reaction_count", 0) - old.get("reaction_count", 0),
            node_delta=new.get("total_nodes", 0) - old.get("total_nodes", 0),
            edge_delta=new.get("total_edges", 0) - old.get("total_edges", 0),
        )
```

### 3. Snapshot persistence

Snapshots should be persisted to `.metabokg/snapshots/` (not `.metakg/`),
consistent with the rename plan:

```
.metabokg/
  snapshots/
    manifest.json          # SnapshotManifest index
    <hash>.json            # Individual snapshot files
```

### 4. CLI commands (future)

```bash
metabokg snapshot save   # Capture current state
metabokg snapshot list   # List all snapshots
metabokg snapshot show   # Show a specific snapshot
metabokg snapshot diff   # Diff two snapshots
```

---

## Impact

### Adapter changes

| Metric | Before | After | Delta |
|--------|--------|-------|-------|
| `snapshot()` lines | 36 | 0 (inherited) | -36 |
| `_collect_snapshot_metrics()` lines | 0 | 10 | +10 |
| **Net** | 36 | 10 | **-26** |

### What MetaboKG gains from the shared infrastructure

| Capability | Before | After |
|-----------|--------|-------|
| Standard snapshot envelope | Manual construction | Free from base class |
| Snapshot persistence | None | `.metabokg/snapshots/` via SnapshotManager |
| Snapshot manifest | None | JSON manifest via SnapshotManifest |
| Snapshot diffing | None | Domain-aware deltas via MetaboSnapshotManager |
| CLI commands | None | `metabokg snapshot save/list/show/diff` |

### Domain-specific metrics

MetaboKG snapshots capture biochemistry-specific data that no other KG tracks:

| Metric | Description |
|--------|-------------|
| `pathway_count` | Number of metabolic pathways indexed |
| `enzyme_count` | Number of enzyme nodes (catalysts) |
| `metabolite_count` | Number of metabolite nodes (substrates/products) |
| `reaction_count` | Number of reaction edges |

These flow into the snapshot envelope as `_collect_snapshot_metrics()` return
values, alongside the standard `node_count` and `edge_count` provided by the
base class.

---

## Migration checklist

### Phase 1: Adapter refactor (KGRAG)

- [ ] Replace `MetaKGAdapter.snapshot()` with `_collect_snapshot_metrics()`
- [ ] Update tests to verify snapshot envelope + domain metrics
- [ ] Verify `KGAdapter.snapshot()` template method works for MetaKG kind

### Phase 2: Backing library (metabo_kg)

- [ ] Create `metabo_kg/snapshots.py` with thin-layer pattern
- [ ] Implement `MetaboSnapshotManager` with domain-specific deltas
- [ ] Add snapshot persistence to `.metabokg/snapshots/`
- [ ] Wire `MetaKGOrchestrator.snapshot()` to the new manager
- [ ] Add CLI snapshot subcommands

### Phase 3: Naming rename (MetaKG -> MetaboKG)

- [ ] Rename `MetaKGAdapter` -> `MetaboKGAdapter`
- [ ] Rename `KGKind.META` -> `KGKind.METABO`
- [ ] Update imports, tests, docs
- [ ] Rename `.metakg/` -> `.metabokg/` directory convention
- [ ] Release with changelog entry

---

## Architecture

```
kg_rag.snapshots  (canonical source — shared with CodeKG, DocKG)
├── Snapshot
├── SnapshotManifest
└── SnapshotManager
        ↑
        │  subclass
        │
metabo_kg.snapshots  (thin domain layer)
├── MetaboSnapshotMetrics   — pathway_count, enzyme_count, metabolite_count, reaction_count
├── MetaboSnapshotDelta     — pathway_delta, enzyme_delta, etc.
└── MetaboSnapshotManager   — domain-specific _compute_delta_from_metrics()
```

```
KGAdapter.snapshot()  (concrete template method — base class)
    │
    ├── builds standard envelope (version, timestamp, kind, node_count, edge_count)
    └── calls _collect_snapshot_metrics()
              │
              └── MetaKGAdapter: returns {status, pathway_count, enzyme_count,
                                          metabolite_count, reaction_count}
```

---

## Why this matters

MetaboKG is the proof that KGRAG's architecture generalises beyond software
engineering. The snapshot refactor ensures that this first non-software KG gets
the same infrastructure quality as CodeKG and DocKG — persistence, diffing, CLI
commands — without re-implementing any of it.

The shared `kg_rag.snapshots` module means that future domain KGs (genomics,
proteomics, legal, etc.) get all of this for free by subclassing
`SnapshotManager` and overriding one method.
