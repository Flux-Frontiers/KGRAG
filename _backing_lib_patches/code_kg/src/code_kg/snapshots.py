"""
snapshots.py — Temporal Snapshots of CodeKG Metrics

Thin compatibility layer over ``kg_rag.snapshots``.  The shared module provides
the canonical ``Snapshot``, ``SnapshotManifest``, and ``SnapshotManager``
implementations.  This module:

  - Re-exports ``Snapshot`` and ``SnapshotManifest`` from ``kg_rag.snapshots``
    for backwards compatibility.
  - Keeps domain-specific ``SnapshotMetrics`` and ``SnapshotDelta`` dataclasses
    (used by the CLI and tests) as local types.
  - Provides ``metrics_to_dict`` / ``metrics_from_dict`` helpers to convert
    between the dataclass representation and the dict-based shared model.
  - Subclasses ``SnapshotManager`` to set ``package_name="code-kg"``, override
    ``_compute_delta`` / ``_compute_delta_from_metrics`` with the
    code-kg-specific delta fields, and expose ``_collect_module_node_counts``.

Existing ``from code_kg.snapshots import ...`` call-sites continue to work
unchanged.

Usage
-----
>>> from code_kg.snapshots import SnapshotManager
>>> mgr = SnapshotManager(".codekg/snapshots")
>>> snapshot = mgr.capture("v0.5.1", "develop", graph_stats_dict)
>>> mgr.save_snapshot(snapshot)
>>> manifest = mgr.load_manifest()
>>> prev = mgr.get_previous(tree_hash)
"""

from __future__ import annotations

import sqlite3
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

# ---------------------------------------------------------------------------
# Re-export shared data models
# ---------------------------------------------------------------------------

from kg_rag.snapshots import Snapshot as Snapshot  # noqa: F401 — re-export
from kg_rag.snapshots import SnapshotManifest as SnapshotManifest  # noqa: F401 — re-export
from kg_rag.snapshots import SnapshotManager as _BaseSnapshotManager

# ---------------------------------------------------------------------------
# Domain-specific dataclasses  (used by cmd_snapshot.py and tests)
# ---------------------------------------------------------------------------


@dataclass
class SnapshotMetrics:
    """Core metrics captured in a code-kg snapshot."""

    total_nodes: int
    total_edges: int
    meaningful_nodes: int
    docstring_coverage: float  # 0.0 to 1.0
    node_counts: dict[str, int]
    edge_counts: dict[str, int]
    critical_issues: int  # number of critical issues found
    complexity_median: float  # median fan-in across functions
    module_node_counts: dict[str, int] = field(default_factory=dict)  # nodes per module path


@dataclass
class SnapshotDelta:
    """Deltas comparing this snapshot to a baseline or previous snapshot."""

    nodes: int = 0
    edges: int = 0
    coverage_delta: float = 0.0
    critical_issues_delta: int = 0


# ---------------------------------------------------------------------------
# Conversion helpers
# ---------------------------------------------------------------------------


def metrics_to_dict(metrics: SnapshotMetrics) -> dict[str, Any]:
    """Convert a ``SnapshotMetrics`` dataclass to a plain dict for storage."""
    return {
        "total_nodes": metrics.total_nodes,
        "total_edges": metrics.total_edges,
        "meaningful_nodes": metrics.meaningful_nodes,
        "docstring_coverage": metrics.docstring_coverage,
        "node_counts": metrics.node_counts,
        "edge_counts": metrics.edge_counts,
        "critical_issues": metrics.critical_issues,
        "complexity_median": metrics.complexity_median,
        "module_node_counts": metrics.module_node_counts,
    }


def metrics_from_dict(data: dict[str, Any]) -> SnapshotMetrics:
    """Reconstruct a ``SnapshotMetrics`` from a plain dict (e.g. loaded from JSON)."""
    return SnapshotMetrics(
        total_nodes=data.get("total_nodes", 0),
        total_edges=data.get("total_edges", 0),
        meaningful_nodes=data.get("meaningful_nodes", 0),
        docstring_coverage=data.get("docstring_coverage", 0.0),
        node_counts=data.get("node_counts", {}),
        edge_counts=data.get("edge_counts", {}),
        critical_issues=data.get("critical_issues", 0),
        complexity_median=data.get("complexity_median", 0.0),
        module_node_counts=data.get("module_node_counts", {}),
    )


def delta_to_dict(delta: SnapshotDelta) -> dict[str, Any]:
    """Convert a ``SnapshotDelta`` dataclass to a plain dict for storage."""
    return {
        "nodes": delta.nodes,
        "edges": delta.edges,
        "coverage_delta": delta.coverage_delta,
        "critical_issues_delta": delta.critical_issues_delta,
    }


def delta_from_dict(data: dict[str, Any] | None) -> SnapshotDelta | None:
    """Reconstruct a ``SnapshotDelta`` from a plain dict, or return ``None``."""
    if data is None:
        return None
    return SnapshotDelta(
        nodes=data.get("nodes", 0),
        edges=data.get("edges", 0),
        coverage_delta=data.get("coverage_delta", 0.0),
        critical_issues_delta=data.get("critical_issues_delta", 0),
    )


# ---------------------------------------------------------------------------
# Backwards-compat Snapshot wrapper
#
# The shared kg_rag.snapshots.Snapshot stores metrics as a plain dict and
# vs_previous/vs_baseline as plain dicts.  Legacy code-kg callers expect
# attribute access on these fields (snapshot.metrics.total_nodes, delta.nodes).
#
# We subclass Snapshot to override attribute access so that .metrics returns a
# SnapshotMetrics view and .vs_previous / .vs_baseline return SnapshotDelta
# views, while keeping the underlying dict storage for JSON serialization.
# ---------------------------------------------------------------------------


class Snapshot(Snapshot):  # type: ignore[no-redef]
    """code-kg Snapshot with attribute-accessible metrics and delta fields.

    Subclasses the shared ``kg_rag.snapshots.Snapshot`` so that:

    - ``snapshot.metrics`` returns a :class:`SnapshotMetrics` dataclass built
      lazily from the underlying metrics dict.
    - ``snapshot.vs_previous`` / ``snapshot.vs_baseline`` return
      :class:`SnapshotDelta` dataclasses (or ``None``) built lazily from the
      underlying delta dicts.
    - All serialization goes through the shared ``to_dict`` / ``from_dict``
      which store plain dicts, ensuring on-disk format compatibility.
    """

    # ------------------------------------------------------------------
    # Attribute-access shims
    # ------------------------------------------------------------------

    @property  # type: ignore[override]
    def metrics(self) -> SnapshotMetrics:  # type: ignore[override]
        raw = object.__getattribute__(self, "_metrics_raw")
        return metrics_from_dict(raw)

    @metrics.setter
    def metrics(self, value: SnapshotMetrics | dict[str, Any]) -> None:
        if isinstance(value, SnapshotMetrics):
            object.__setattr__(self, "_metrics_raw", metrics_to_dict(value))
        else:
            object.__setattr__(self, "_metrics_raw", value)

    @property  # type: ignore[override]
    def vs_previous(self) -> SnapshotDelta | None:  # type: ignore[override]
        raw = object.__getattribute__(self, "_vs_previous_raw")
        return delta_from_dict(raw)

    @vs_previous.setter
    def vs_previous(self, value: SnapshotDelta | dict[str, Any] | None) -> None:
        if isinstance(value, SnapshotDelta):
            object.__setattr__(self, "_vs_previous_raw", delta_to_dict(value))
        else:
            object.__setattr__(self, "_vs_previous_raw", value)

    @property  # type: ignore[override]
    def vs_baseline(self) -> SnapshotDelta | None:  # type: ignore[override]
        raw = object.__getattribute__(self, "_vs_baseline_raw")
        return delta_from_dict(raw)

    @vs_baseline.setter
    def vs_baseline(self, value: SnapshotDelta | dict[str, Any] | None) -> None:
        if isinstance(value, SnapshotDelta):
            object.__setattr__(self, "_vs_baseline_raw", delta_to_dict(value))
        else:
            object.__setattr__(self, "_vs_baseline_raw", value)

    # ------------------------------------------------------------------
    # __init__: intercept and store raw dicts
    # ------------------------------------------------------------------

    def __init__(
        self,
        branch: str,
        timestamp: str,
        metrics: SnapshotMetrics | dict[str, Any],
        version: str = "",
        hotspots: list[dict[str, Any]] | None = None,
        issues: list[str] | None = None,
        vs_previous: SnapshotDelta | dict[str, Any] | None = None,
        vs_baseline: SnapshotDelta | dict[str, Any] | None = None,
        tree_hash: str = "",
    ) -> None:
        # Store raw dicts before calling super().__init__
        if isinstance(metrics, SnapshotMetrics):
            object.__setattr__(self, "_metrics_raw", metrics_to_dict(metrics))
        else:
            object.__setattr__(self, "_metrics_raw", metrics or {})

        if isinstance(vs_previous, SnapshotDelta):
            object.__setattr__(self, "_vs_previous_raw", delta_to_dict(vs_previous))
        else:
            object.__setattr__(self, "_vs_previous_raw", vs_previous)

        if isinstance(vs_baseline, SnapshotDelta):
            object.__setattr__(self, "_vs_baseline_raw", delta_to_dict(vs_baseline))
        else:
            object.__setattr__(self, "_vs_baseline_raw", vs_baseline)

        # Call parent __init__ with dict forms so the shared class stores them
        raw_metrics = object.__getattribute__(self, "_metrics_raw")
        raw_vs_prev = object.__getattribute__(self, "_vs_previous_raw")
        raw_vs_base = object.__getattribute__(self, "_vs_baseline_raw")

        super().__init__(
            branch=branch,
            timestamp=timestamp,
            metrics=raw_metrics,
            version=version,
            hotspots=hotspots or [],
            issues=issues or [],
            vs_previous=raw_vs_prev,
            vs_baseline=raw_vs_base,
            tree_hash=tree_hash,
        )

    # ------------------------------------------------------------------
    # to_dict / from_dict — keep shared dict format on disk
    # ------------------------------------------------------------------

    def to_dict(self) -> dict[str, Any]:
        """Serialize to JSON-compatible dict (plain dicts for all nested fields)."""
        raw_metrics = object.__getattribute__(self, "_metrics_raw")
        raw_vs_prev = object.__getattribute__(self, "_vs_previous_raw")
        raw_vs_base = object.__getattribute__(self, "_vs_baseline_raw")
        return {
            "key": self.tree_hash,
            "branch": self.branch,
            "timestamp": self.timestamp,
            "version": self.version,
            "metrics": raw_metrics,
            "hotspots": self.hotspots,
            "issues": self.issues,
            "vs_previous": raw_vs_prev,
            "vs_baseline": raw_vs_base,
        }

    @staticmethod
    def from_dict(data: dict[str, Any]) -> "Snapshot":
        """Reconstruct from a dict loaded from JSON."""
        raw = dict(data)

        metrics_data = raw.pop("metrics", {})
        vs_prev_data = raw.pop("vs_previous", None)
        vs_base_data = raw.pop("vs_baseline", None)

        # Normalise legacy 'tree_hash' field → 'key'
        if "key" not in raw and "tree_hash" in raw:
            raw["key"] = raw.pop("tree_hash")
        else:
            raw.pop("tree_hash", None)

        key = raw.pop("key", "")
        raw.pop("commit", None)  # drop legacy field
        raw.setdefault("version", "")

        return Snapshot(
            tree_hash=key,
            metrics=metrics_data,
            vs_previous=vs_prev_data,
            vs_baseline=vs_base_data,
            branch=raw.pop("branch", ""),
            timestamp=raw.pop("timestamp", ""),
            version=raw.pop("version", ""),
            hotspots=raw.pop("hotspots", []),
            issues=raw.pop("issues", []),
        )


# ---------------------------------------------------------------------------
# code-kg SnapshotManager subclass
# ---------------------------------------------------------------------------


class SnapshotManager(_BaseSnapshotManager):
    """code-kg specific snapshot manager.

    Extends the shared :class:`kg_rag.snapshots.SnapshotManager` with:

    - ``package_name="code-kg"`` for automatic version detection.
    - Domain-specific delta fields: ``coverage_delta`` and
      ``critical_issues_delta`` in addition to the base ``nodes`` / ``edges``.
    - ``_collect_module_node_counts()`` — SQLite query for per-module node
      counts, stored in snapshot metrics under ``"module_node_counts"``.

    The ``capture()`` signature is extended with named keyword arguments
    (``coverage``, ``critical_issues``, ``complexity_median``) so that
    existing call-sites in the CLI do not need to be changed.
    """

    def __init__(
        self,
        snapshots_dir: Path | str,
        *,
        db_path: Path | str | None = None,
        package_name: str = "code-kg",
    ) -> None:
        super().__init__(snapshots_dir, package_name=package_name, db_path=db_path)

    # ------------------------------------------------------------------
    # capture — extended signature for backwards compat
    # ------------------------------------------------------------------

    def capture(  # type: ignore[override]
        self,
        version: str | None = None,
        branch: str | None = None,
        graph_stats_dict: dict[str, Any] | None = None,
        coverage: float = 0.0,
        critical_issues: int = 0,
        complexity_median: float = 0.0,
        hotspots: list[dict[str, Any]] | None = None,
        issues: list[str] | None = None,
        tree_hash: str = "",
    ) -> "Snapshot":
        """Capture a code-kg snapshot.

        Merges ``graph_stats_dict`` with code-kg-specific metric fields
        (``docstring_coverage``, ``critical_issues``, ``complexity_median``,
        ``module_node_counts``) into a single metrics dict, then delegates to
        the shared manager and returns a code-kg :class:`Snapshot` instance.

        :param version: Version string; auto-detected from package if None.
        :param branch: Git branch; auto-detected if None.
        :param graph_stats_dict: Output from the KG ``stats()`` method.
        :param coverage: Docstring coverage fraction (0.0–1.0).
        :param critical_issues: Number of critical issues detected.
        :param complexity_median: Median fan-in across functions.
        :param hotspots: Top hotspot entries.
        :param issues: Issue description strings.
        :param tree_hash: Git tree hash; auto-detected if not provided.
        :return: New :class:`Snapshot` instance (not yet persisted).
        """
        # Collect per-module counts from SQLite (returns {} if db unavailable)
        module_node_counts = self._collect_module_node_counts()

        # Call the base implementation passing extra fields via **extra_metrics
        base_snap = super().capture(
            version=version,
            branch=branch,
            graph_stats_dict=graph_stats_dict,
            tree_hash=tree_hash,
            hotspots=hotspots,
            issues=issues,
            # Extra domain-specific metric fields:
            docstring_coverage=coverage,
            critical_issues=critical_issues,
            complexity_median=complexity_median,
            module_node_counts=module_node_counts,
        )

        # Wrap in code-kg Snapshot so callers get dataclass-style attribute access
        snap = Snapshot(
            branch=base_snap.branch,
            timestamp=base_snap.timestamp,
            version=base_snap.version,
            metrics=base_snap.metrics,  # already a dict from base class
            hotspots=base_snap.hotspots,
            issues=base_snap.issues,
            vs_previous=base_snap.vs_previous,
            vs_baseline=base_snap.vs_baseline,
            tree_hash=base_snap.tree_hash,
        )
        return snap

    # ------------------------------------------------------------------
    # Override load_snapshot to return code-kg Snapshot instances
    # ------------------------------------------------------------------

    def load_snapshot(self, key: str) -> "Snapshot | None":
        """Load a snapshot by key, returning a code-kg Snapshot instance."""
        base_snap = super().load_snapshot(key)
        if base_snap is None:
            return None
        return Snapshot(
            branch=base_snap.branch,
            timestamp=base_snap.timestamp,
            version=base_snap.version,
            metrics=base_snap.metrics,
            hotspots=base_snap.hotspots,
            issues=base_snap.issues,
            vs_previous=base_snap.vs_previous,
            vs_baseline=base_snap.vs_baseline,
            tree_hash=base_snap.tree_hash,
        )

    # ------------------------------------------------------------------
    # Delta computation — adds coverage_delta and critical_issues_delta
    # ------------------------------------------------------------------

    def _compute_delta(self, snap_new: "Snapshot", snap_old: "Snapshot") -> dict[str, Any]:
        """Compute code-kg metrics delta including coverage and issue count."""
        new_m = snap_new.metrics if isinstance(snap_new.metrics, dict) else metrics_to_dict(snap_new.metrics)  # type: ignore[arg-type]
        old_m = snap_old.metrics if isinstance(snap_old.metrics, dict) else metrics_to_dict(snap_old.metrics)  # type: ignore[arg-type]
        return self._compute_delta_from_metrics(new_m, old_m)

    def _compute_delta_from_metrics(
        self, new_m: dict[str, Any], old_m: dict[str, Any]
    ) -> dict[str, Any]:
        """Compute delta dict from two raw metrics dicts.

        Includes the base ``nodes`` / ``edges`` plus the code-kg-specific
        ``coverage_delta`` and ``critical_issues_delta`` fields.
        """
        return {
            "nodes": new_m.get("total_nodes", 0) - old_m.get("total_nodes", 0),
            "edges": new_m.get("total_edges", 0) - old_m.get("total_edges", 0),
            "coverage_delta": new_m.get("docstring_coverage", 0.0)
            - old_m.get("docstring_coverage", 0.0),
            "critical_issues_delta": new_m.get("critical_issues", 0)
            - old_m.get("critical_issues", 0),
        }

    # ------------------------------------------------------------------
    # diff_snapshots — includes module_node_counts_delta and issues_delta
    # ------------------------------------------------------------------

    def diff_snapshots(self, key_a: str, key_b: str) -> dict[str, Any]:
        """Compare two snapshots side-by-side.

        Extends the shared diff with ``module_node_counts_delta`` and
        ``issues_delta`` (introduced / resolved issue strings).

        :param key_a: First snapshot key (tree hash).
        :param key_b: Second snapshot key (tree hash).
        :return: Dict with metrics from both, computed deltas.
        """
        snap_a = self.load_snapshot(key_a)
        snap_b = self.load_snapshot(key_b)

        if not snap_a or not snap_b:
            return {"error": "One or both snapshots not found"}

        # Resolve metrics to dicts for delta computation
        m_a = snap_a.metrics if isinstance(snap_a.metrics, dict) else metrics_to_dict(snap_a.metrics)  # type: ignore[arg-type]
        m_b = snap_b.metrics if isinstance(snap_b.metrics, dict) else metrics_to_dict(snap_b.metrics)  # type: ignore[arg-type]

        all_node_kinds = set(m_a.get("node_counts", {})) | set(m_b.get("node_counts", {}))
        all_edge_rels = set(m_a.get("edge_counts", {})) | set(m_b.get("edge_counts", {}))

        node_counts_delta = {
            k: m_b.get("node_counts", {}).get(k, 0) - m_a.get("node_counts", {}).get(k, 0)
            for k in all_node_kinds
        }
        edge_counts_delta = {
            k: m_b.get("edge_counts", {}).get(k, 0) - m_a.get("edge_counts", {}).get(k, 0)
            for k in all_edge_rels
        }

        all_modules = set(m_a.get("module_node_counts", {})) | set(
            m_b.get("module_node_counts", {})
        )
        module_node_counts_delta = {
            mod: m_b.get("module_node_counts", {}).get(mod, 0)
            - m_a.get("module_node_counts", {}).get(mod, 0)
            for mod in all_modules
            if m_b.get("module_node_counts", {}).get(mod, 0)
            != m_a.get("module_node_counts", {}).get(mod, 0)
        }

        issues_a = set(snap_a.issues)
        issues_b = set(snap_b.issues)

        return {
            "a": {"key": snap_a.key, "metrics": m_a, "issues": snap_a.issues},
            "b": {"key": snap_b.key, "metrics": m_b, "issues": snap_b.issues},
            "delta": self._compute_delta_from_metrics(m_b, m_a),
            "node_counts_delta": node_counts_delta,
            "edge_counts_delta": edge_counts_delta,
            "module_node_counts_delta": module_node_counts_delta,
            "issues_delta": {
                "introduced": list(issues_b - issues_a),
                "resolved": list(issues_a - issues_b),
            },
        }

    # ------------------------------------------------------------------
    # SQLite per-module node counts
    # ------------------------------------------------------------------

    def _collect_module_node_counts(self) -> dict[str, int]:
        """Query SQLite for per-module node counts.

        :return: Dict mapping ``module_path`` to node count, or ``{}`` if the
                 database is unavailable or the query fails.
        """
        if not self.db_path or not self.db_path.exists():
            return {}
        try:
            with sqlite3.connect(self.db_path) as conn:
                rows = conn.execute(
                    "SELECT module_path, COUNT(*) FROM nodes GROUP BY module_path"
                ).fetchall()
            return {row[0]: row[1] for row in rows if row[0]}
        except sqlite3.Error:
            return {}


# ---------------------------------------------------------------------------
# Public re-exports (so ``from code_kg.snapshots import X`` keeps working)
# ---------------------------------------------------------------------------

__all__ = [
    "Snapshot",
    "SnapshotManifest",
    "SnapshotManager",
    "SnapshotMetrics",
    "SnapshotDelta",
    "metrics_to_dict",
    "metrics_from_dict",
    "delta_to_dict",
    "delta_from_dict",
]
