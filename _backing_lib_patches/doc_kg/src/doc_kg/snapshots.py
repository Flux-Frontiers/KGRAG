"""
snapshots.py — Temporal Snapshots of DocKG Metrics

Thin compatibility layer over the shared ``kg_rag.snapshots`` module.

The shared module provides canonical ``Snapshot``, ``SnapshotManifest``, and
``SnapshotManager`` backed by free-form dicts.  This module re-exports those
types and adds:

  - ``SnapshotMetrics`` — domain-specific dataclass (used by CLI and tests)
  - ``SnapshotDelta``   — domain-specific dataclass (used by CLI and tests)
  - ``SnapshotManager`` subclass that:
      * sets ``package_name="doc-kg"`` by default
      * overrides ``capture()`` to accept the legacy per-field kwargs
        (``coverage_score``, ``issues_count``, ``complexity_median``) and
        build the structured ``metrics`` dict
      * overrides ``_compute_delta_from_metrics`` to include
        ``coverage_delta`` and ``issues_delta``
  - ``metrics_to_dict`` / ``metrics_from_dict`` — helpers for converting
    between ``SnapshotMetrics`` dataclass and the underlying dict

``Snapshot`` is re-exported from ``kg_rag.snapshots``.  For backwards
compatibility ``snapshot.metrics`` returns a ``SnapshotMetrics``-shaped
view object when the snapshot was constructed via this module's helpers.

Usage
-----
>>> from doc_kg.snapshots import SnapshotManager
>>> mgr = SnapshotManager(".dockg/snapshots")
>>> snapshot = mgr.capture("v0.3.0", "main", graph_stats_dict)
>>> mgr.save_snapshot(snapshot)
>>> manifest = mgr.load_manifest()
>>> prev = mgr.get_previous(tree_hash)
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

# ---------------------------------------------------------------------------
# Re-export shared base types (backwards-compat public API)
# ---------------------------------------------------------------------------

from kg_rag.snapshots import Snapshot as _BaseSnapshot
from kg_rag.snapshots import SnapshotManifest  # noqa: F401  re-exported
from kg_rag.snapshots import SnapshotManager as _BaseSnapshotManager

__all__ = [
    "SnapshotMetrics",
    "SnapshotDelta",
    "Snapshot",
    "SnapshotManifest",
    "SnapshotManager",
    "metrics_to_dict",
    "metrics_from_dict",
]


# ---------------------------------------------------------------------------
# Domain-specific dataclasses (used by CLI and tests)
# ---------------------------------------------------------------------------


@dataclass
class SnapshotMetrics:
    """Core metrics captured in a DocKG snapshot."""

    total_nodes: int
    total_edges: int
    meaningful_nodes: int
    coverage_score: float  # 0.0 to 1.0 — semantic coverage
    node_counts: dict[str, int]
    edge_counts: dict[str, int]
    issues_count: int
    complexity_median: float  # median semantic_links across hot chunks


@dataclass
class SnapshotDelta:
    """Deltas comparing this snapshot to a baseline or previous snapshot."""

    nodes: int = 0
    edges: int = 0
    coverage_delta: float = 0.0
    issues_delta: int = 0


# ---------------------------------------------------------------------------
# Conversion helpers
# ---------------------------------------------------------------------------


def metrics_to_dict(m: SnapshotMetrics) -> dict[str, Any]:
    """Convert a ``SnapshotMetrics`` dataclass to a plain dict."""
    return {
        "total_nodes": m.total_nodes,
        "total_edges": m.total_edges,
        "meaningful_nodes": m.meaningful_nodes,
        "coverage_score": m.coverage_score,
        "node_counts": m.node_counts,
        "edge_counts": m.edge_counts,
        "issues_count": m.issues_count,
        "complexity_median": m.complexity_median,
    }


def metrics_from_dict(d: dict[str, Any]) -> SnapshotMetrics:
    """Reconstruct a ``SnapshotMetrics`` dataclass from a plain dict."""
    return SnapshotMetrics(
        total_nodes=int(d.get("total_nodes", 0)),
        total_edges=int(d.get("total_edges", 0)),
        meaningful_nodes=int(d.get("meaningful_nodes", 0)),
        coverage_score=float(d.get("coverage_score", 0.0)),
        node_counts=d.get("node_counts", {}),
        edge_counts=d.get("edge_counts", {}),
        issues_count=int(d.get("issues_count", 0)),
        complexity_median=float(d.get("complexity_median", 0.0)),
    )


def _delta_to_dict(delta: SnapshotDelta | None) -> dict[str, Any] | None:
    """Convert a ``SnapshotDelta`` to a plain dict, or return None."""
    if delta is None:
        return None
    return {
        "nodes": delta.nodes,
        "edges": delta.edges,
        "coverage_delta": delta.coverage_delta,
        "issues_delta": delta.issues_delta,
    }


def _delta_from_dict(d: dict[str, Any] | None) -> SnapshotDelta | None:
    """Reconstruct a ``SnapshotDelta`` from a plain dict, or return None."""
    if d is None:
        return None
    return SnapshotDelta(
        nodes=int(d.get("nodes", 0)),
        edges=int(d.get("edges", 0)),
        coverage_delta=float(d.get("coverage_delta", 0.0)),
        issues_delta=int(d.get("issues_delta", 0)),
    )


# ---------------------------------------------------------------------------
# Snapshot — thin compatibility wrapper around the shared dict-based model
# ---------------------------------------------------------------------------


class Snapshot(_BaseSnapshot):
    """DocKG-flavoured snapshot with attribute-style access to metrics and deltas.

    Extends the shared ``kg_rag.snapshots.Snapshot`` (which stores metrics
    as a free-form dict) with ``@property`` accessors that return the typed
    ``SnapshotMetrics`` and ``SnapshotDelta`` objects that the CLI and tests
    expect.

    The underlying ``metrics``, ``vs_previous``, and ``vs_baseline`` fields
    remain plain dicts on disk; the properties are view-only adapters.

    Implementation note
    -------------------
    Python dataclass fields are stored in ``__dict__`` under their field name.
    The properties below always read and write the raw dict stored in
    ``self.__dict__`` directly so that the shared base-class infrastructure
    (which expects plain dicts) continues to work without modification.
    """

    @property  # type: ignore[override]
    def metrics(self) -> SnapshotMetrics:  # type: ignore[override]
        """Return metrics as a ``SnapshotMetrics`` dataclass view."""
        return metrics_from_dict(self.__dict__["metrics"])

    @metrics.setter
    def metrics(self, value: SnapshotMetrics | dict[str, Any]) -> None:
        if isinstance(value, SnapshotMetrics):
            self.__dict__["metrics"] = metrics_to_dict(value)
        else:
            self.__dict__["metrics"] = value

    @property  # type: ignore[override]
    def vs_previous(self) -> SnapshotDelta | None:  # type: ignore[override]
        """Return vs_previous as a ``SnapshotDelta`` dataclass view."""
        raw = self.__dict__["vs_previous"]
        return _delta_from_dict(raw)

    @vs_previous.setter
    def vs_previous(self, value: SnapshotDelta | dict[str, Any] | None) -> None:
        if isinstance(value, SnapshotDelta):
            self.__dict__["vs_previous"] = _delta_to_dict(value)
        else:
            self.__dict__["vs_previous"] = value

    @property  # type: ignore[override]
    def vs_baseline(self) -> SnapshotDelta | None:  # type: ignore[override]
        """Return vs_baseline as a ``SnapshotDelta`` dataclass view."""
        raw = self.__dict__["vs_baseline"]
        return _delta_from_dict(raw)

    @vs_baseline.setter
    def vs_baseline(self, value: SnapshotDelta | dict[str, Any] | None) -> None:
        if isinstance(value, SnapshotDelta):
            self.__dict__["vs_baseline"] = _delta_to_dict(value)
        else:
            self.__dict__["vs_baseline"] = value

    def to_dict(self) -> dict[str, Any]:
        """Convert snapshot to a JSON-serializable dictionary."""
        return {
            "key": self.tree_hash,
            "branch": self.branch,
            "timestamp": self.timestamp,
            "version": self.version,
            # Use raw dict stored in __dict__ to avoid dataclass wrapping
            "metrics": self.__dict__["metrics"],
            "hotspots": self.hotspots,
            "issues": self.issues,
            "vs_previous": self.__dict__["vs_previous"],
            "vs_baseline": self.__dict__["vs_baseline"],
        }

    @staticmethod
    def from_dict(data: dict[str, Any]) -> "Snapshot":  # type: ignore[override]
        """Reconstruct a DocKG ``Snapshot`` from a dictionary."""
        # Use the base deserialization, then re-wrap as a DocKG Snapshot.
        base = _BaseSnapshot.from_dict(data)
        return _rewrap(base)


# ---------------------------------------------------------------------------
# SnapshotManager — doc-kg specialisation of the shared manager
# ---------------------------------------------------------------------------


class SnapshotManager(_BaseSnapshotManager):
    """DocKG snapshot manager.

    Subclasses the shared ``kg_rag.snapshots.SnapshotManager`` and adds:

    * ``package_name="doc-kg"`` default for version detection.
    * Legacy ``capture()`` kwargs: ``coverage_score``, ``issues_count``,
      ``complexity_median`` — merged into the metrics dict.
    * ``_compute_delta_from_metrics`` extended with ``coverage_delta`` and
      ``issues_delta``.
    * Returns ``doc_kg.snapshots.Snapshot`` instances (with typed-accessor
      properties) from all load/capture methods.

    Base-class compatibility
    ------------------------
    The shared base class stores ``metrics``, ``vs_previous``, and
    ``vs_baseline`` as plain dicts and passes them directly to
    ``_compute_delta_from_metrics``.  All overrides here that load or
    capture snapshots re-wrap the returned ``_BaseSnapshot`` instances as
    ``doc_kg.snapshots.Snapshot`` objects via :func:`_rewrap`.  The
    overridden ``_compute_delta`` extracts raw dicts from ``__dict__``
    before delegating, so the base infrastructure and our typed properties
    co-exist without conflict.
    """

    def __init__(
        self,
        snapshots_dir: Any,
        *,
        package_name: str = "doc-kg",
        db_path: Any = None,
    ) -> None:
        super().__init__(snapshots_dir, package_name=package_name, db_path=db_path)

    # ------------------------------------------------------------------
    # capture — backwards-compat wrapper
    # ------------------------------------------------------------------

    def capture(
        self,
        version: str | None = None,
        branch: str | None = None,
        graph_stats_dict: dict[str, Any] | None = None,
        coverage_score: float = 0.0,
        issues_count: int = 0,
        complexity_median: float = 0.0,
        hotspots: list[dict[str, Any]] | None = None,
        issues: list[str] | None = None,
        tree_hash: str = "",
    ) -> "Snapshot":
        """Capture a DocKG snapshot.

        Accepts the legacy per-field kwargs (``coverage_score``,
        ``issues_count``, ``complexity_median``) in addition to the dict-based
        ``graph_stats_dict`` from the base class, and builds the full metrics
        dict expected by the shared infrastructure.

        :param version: Version string (e.g., "0.3.0").
        :param branch: Git branch name; auto-detected if None.
        :param graph_stats_dict: Output from ``graph_stats()`` / ``store.stats()``.
        :param coverage_score: Semantic coverage score (0.0 to 1.0).
        :param issues_count: Number of issues found.
        :param complexity_median: Median semantic_links across hot chunks.
        :param hotspots: Top hot chunks with metadata.
        :param issues: List of issue description strings.
        :param tree_hash: Git tree hash; auto-detected if not provided.
        :return: New :class:`Snapshot` instance (not yet persisted).
        """
        stats = graph_stats_dict or {}
        node_counts = stats.get("node_counts", {})
        meaningful_nodes = max(
            0,
            int(stats.get("total_nodes", 0)) - int(node_counts.get("document", 0)),
        )

        extra: dict[str, Any] = {
            "meaningful_nodes": meaningful_nodes,
            "coverage_score": float(coverage_score),
            "issues_count": int(issues_count),
            "complexity_median": float(complexity_median),
        }

        base_snap = super().capture(
            version=version,
            branch=branch,
            graph_stats_dict=stats,
            tree_hash=tree_hash,
            hotspots=hotspots,
            issues=issues,
            **extra,
        )

        # Re-wrap as doc_kg Snapshot with typed-accessor properties
        return _rewrap(base_snap)

    # ------------------------------------------------------------------
    # diff_snapshots — pass raw dicts into the base implementation
    # ------------------------------------------------------------------

    def diff_snapshots(self, key_a: str, key_b: str) -> dict[str, Any]:
        """Compare two snapshots side-by-side, including doc-kg delta fields.

        Delegates to the base implementation after ensuring both snapshots
        present their ``metrics`` as plain dicts (the base uses ``.get()`` on
        metrics and embeds them directly in the return value).
        """
        # Load via base to get plain _BaseSnapshot objects (raw dicts).
        snap_a = _BaseSnapshotManager.load_snapshot(self, key_a)
        snap_b = _BaseSnapshotManager.load_snapshot(self, key_b)

        if not snap_a or not snap_b:
            return {"error": "One or both snapshots not found"}

        all_node_kinds = set(snap_a.metrics.get("node_counts", {})) | set(
            snap_b.metrics.get("node_counts", {})
        )
        all_edge_rels = set(snap_a.metrics.get("edge_counts", {})) | set(
            snap_b.metrics.get("edge_counts", {})
        )

        node_counts_delta = {
            k: snap_b.metrics.get("node_counts", {}).get(k, 0)
            - snap_a.metrics.get("node_counts", {}).get(k, 0)
            for k in all_node_kinds
        }
        edge_counts_delta = {
            k: snap_b.metrics.get("edge_counts", {}).get(k, 0)
            - snap_a.metrics.get("edge_counts", {}).get(k, 0)
            for k in all_edge_rels
        }

        return {
            "a": {
                "key": snap_a.key,
                "metrics": snap_a.metrics,
                "issues": snap_a.issues,
                "timestamp": snap_a.timestamp,
            },
            "b": {
                "key": snap_b.key,
                "metrics": snap_b.metrics,
                "issues": snap_b.issues,
                "timestamp": snap_b.timestamp,
            },
            "delta": self._compute_delta_from_metrics(snap_b.metrics, snap_a.metrics),
            "node_counts_delta": node_counts_delta,
            "edge_counts_delta": edge_counts_delta,
        }

    # ------------------------------------------------------------------
    # Delta computation — adds coverage_delta and issues_delta
    # ------------------------------------------------------------------

    def _compute_delta(
        self, snap_new: _BaseSnapshot, snap_old: _BaseSnapshot
    ) -> dict[str, Any]:
        """Compute delta, extracting raw metric dicts from __dict__ to avoid
        hitting the typed-property layer on doc_kg Snapshot instances."""
        new_m = snap_new.__dict__.get("metrics", snap_new.metrics)
        old_m = snap_old.__dict__.get("metrics", snap_old.metrics)
        # If the raw value is still a dataclass (e.g. constructed directly),
        # fall back to converting it.
        if isinstance(new_m, SnapshotMetrics):
            new_m = metrics_to_dict(new_m)
        if isinstance(old_m, SnapshotMetrics):
            old_m = metrics_to_dict(old_m)
        return self._compute_delta_from_metrics(new_m, old_m)

    def _compute_delta_from_metrics(
        self, new_m: dict[str, Any], old_m: dict[str, Any]
    ) -> dict[str, Any]:
        """Compute delta dict including doc-kg specific fields."""
        return {
            "nodes": new_m.get("total_nodes", 0) - old_m.get("total_nodes", 0),
            "edges": new_m.get("total_edges", 0) - old_m.get("total_edges", 0),
            "coverage_delta": (
                new_m.get("coverage_score", 0.0) - old_m.get("coverage_score", 0.0)
            ),
            "issues_delta": new_m.get("issues_count", 0) - old_m.get("issues_count", 0),
        }

    # ------------------------------------------------------------------
    # save_snapshot — normalise typed properties back to raw dicts first
    # ------------------------------------------------------------------

    def save_snapshot(self, snapshot: _BaseSnapshot) -> Any:  # type: ignore[override]
        """Persist snapshot, normalising any typed-property values to raw dicts.

        The base ``save_snapshot`` inspects ``snapshot.metrics`` (expects a
        dict) and ``snapshot.vs_previous`` / ``snapshot.vs_baseline`` (expects
        dicts or None) directly.  If ``snapshot`` is a doc_kg ``Snapshot``
        the properties return typed dataclasses instead; we substitute a plain
        ``_BaseSnapshot`` carrying the raw dicts so the base implementation
        can serialise without modification.
        """
        if isinstance(snapshot, Snapshot):
            # Build a plain base-Snapshot with raw dicts (no property layer).
            raw = _BaseSnapshot(
                branch=snapshot.branch,
                timestamp=snapshot.timestamp,
                version=snapshot.version,
                metrics=snapshot.__dict__["metrics"],
                hotspots=snapshot.hotspots,
                issues=snapshot.issues,
                vs_previous=snapshot.__dict__["vs_previous"],
                vs_baseline=snapshot.__dict__["vs_baseline"],
                tree_hash=snapshot.tree_hash,
            )
            return super().save_snapshot(raw)
        return super().save_snapshot(snapshot)

    # ------------------------------------------------------------------
    # Load helpers — re-wrap base Snapshot instances as doc_kg Snapshots
    # ------------------------------------------------------------------

    def load_snapshot(self, key: str) -> "Snapshot | None":  # type: ignore[override]
        snap = super().load_snapshot(key)
        return _rewrap(snap) if snap is not None else None

    def get_previous(self, key: str) -> "Snapshot | None":  # type: ignore[override]
        snap = super().get_previous(key)
        return _rewrap(snap) if snap is not None else None

    def get_baseline(self) -> "Snapshot | None":  # type: ignore[override]
        snap = super().get_baseline()
        return _rewrap(snap) if snap is not None else None


# ---------------------------------------------------------------------------
# Internal helper
# ---------------------------------------------------------------------------


def _rewrap(base: _BaseSnapshot) -> Snapshot:
    """Re-wrap a base Snapshot as a doc_kg Snapshot (no data copying)."""
    if isinstance(base, Snapshot):
        return base
    snap = Snapshot.__new__(Snapshot)
    snap.__dict__.update(base.__dict__)
    return snap
