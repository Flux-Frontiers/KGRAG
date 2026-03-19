"""snapshots.py — FileTreeKG Temporal Snapshots (thin layer over kg_rag.snapshots)

Imports the shared Snapshot, SnapshotManifest, and base SnapshotManager from
kg_rag.snapshots and adds FileTreeKG-specific behaviour:

  - SnapshotMetrics / SnapshotDelta dataclasses (domain types used by the CLI
    and tests for attribute-style access).
  - FtreeSnapshotManager subclass that:
      * Defaults package_name to "ftree-kg" (fallback "filetreekg").
      * Accepts the legacy ``stats_dict`` keyword in ``capture()``.
      * Returns snapshots with ``metrics`` hydrated as a SnapshotMetrics
        instance and ``vs_previous`` / ``vs_baseline`` as SnapshotDelta
        instances so existing callers continue to use attribute access.
      * Overrides ``_compute_delta_from_metrics`` to include ``files_delta``
        and ``dirs_delta``.
      * Provides ``_collect_dir_node_counts()`` (per-directory SQLite query).

The name ``SnapshotManager`` is re-exported as an alias for
``FtreeSnapshotManager`` so that ``from src.snapshots import SnapshotManager``
continues to work unchanged.

Usage
-----
>>> from src.snapshots import SnapshotManager
>>> mgr = SnapshotManager(".filetreekg/snapshots", db_path=".filetreekg/graph.sqlite")
>>> snapshot = mgr.capture(version="v0.1.0", branch="main", stats_dict=kg.stats())
>>> mgr.save_snapshot(snapshot)
>>> prev = mgr.get_previous(tree_hash)
"""

from __future__ import annotations

import sqlite3
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

# ---------------------------------------------------------------------------
# Re-export shared models for backwards compatibility
# ---------------------------------------------------------------------------
from kg_rag.snapshots import Snapshot, SnapshotManifest
from kg_rag.snapshots import SnapshotManager as _BaseSnapshotManager

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


# ---------------------------------------------------------------------------
# Domain-specific dataclasses (used by cmd_snapshot.py and tests)
# ---------------------------------------------------------------------------


@dataclass
class SnapshotMetrics:
    """Core metrics captured in a FileTreeKG snapshot."""

    total_nodes: int
    total_edges: int
    node_counts: dict[str, int]  # by kind: file, directory, symlink
    edge_counts: dict[str, int]  # by relation: CONTAINS, CHILD_OF, PARENT_OF
    total_files: int  # node_counts.get("file", 0)
    total_dirs: int  # node_counts.get("directory", 0)
    dir_node_counts: dict[str, int] = field(default_factory=dict)  # nodes per top-level dir


@dataclass
class SnapshotDelta:
    """Deltas comparing this snapshot to a baseline or previous snapshot."""

    nodes: int = 0
    edges: int = 0
    files_delta: int = 0
    dirs_delta: int = 0


# ---------------------------------------------------------------------------
# Conversion helpers
# ---------------------------------------------------------------------------


def metrics_to_dict(m: SnapshotMetrics) -> dict[str, Any]:
    """Convert a SnapshotMetrics dataclass to a plain dict (for storage)."""
    return {
        "total_nodes": m.total_nodes,
        "total_edges": m.total_edges,
        "node_counts": m.node_counts,
        "edge_counts": m.edge_counts,
        "total_files": m.total_files,
        "total_dirs": m.total_dirs,
        "dir_node_counts": m.dir_node_counts,
    }


def metrics_from_dict(d: dict[str, Any]) -> SnapshotMetrics:
    """Reconstruct a SnapshotMetrics dataclass from a plain dict.

    Back-fills fields that were added in later versions so that legacy
    snapshot JSON continues to load correctly.
    """
    node_counts: dict[str, int] = d.get("node_counts", {})
    d = dict(d)  # don't mutate caller's dict
    d.setdefault("total_files", node_counts.get("file", 0))
    d.setdefault("total_dirs", node_counts.get("directory", 0))
    d.setdefault("dir_node_counts", {})
    return SnapshotMetrics(
        total_nodes=d.get("total_nodes", 0),
        total_edges=d.get("total_edges", 0),
        node_counts=node_counts,
        edge_counts=d.get("edge_counts", {}),
        total_files=d["total_files"],
        total_dirs=d["total_dirs"],
        dir_node_counts=d["dir_node_counts"],
    )


def delta_to_dict(delta: SnapshotDelta) -> dict[str, Any]:
    """Convert a SnapshotDelta dataclass to a plain dict."""
    return {
        "nodes": delta.nodes,
        "edges": delta.edges,
        "files_delta": delta.files_delta,
        "dirs_delta": delta.dirs_delta,
    }


def delta_from_dict(d: dict[str, Any] | None) -> SnapshotDelta | None:
    """Reconstruct a SnapshotDelta from a plain dict, or return None."""
    if d is None:
        return None
    return SnapshotDelta(
        nodes=d.get("nodes", 0),
        edges=d.get("edges", 0),
        files_delta=d.get("files_delta", 0),
        dirs_delta=d.get("dirs_delta", 0),
    )


def _hydrate_snapshot(snap: Snapshot) -> Snapshot:
    """Replace dict-typed metrics / deltas with domain dataclasses in-place.

    The shared Snapshot stores ``metrics``, ``vs_previous``, and
    ``vs_baseline`` as plain dicts.  FileTreeKG callers (CLI, tests) rely on
    attribute access (``snap.metrics.total_nodes``, ``snap.vs_previous.nodes``
    etc.), so we overwrite those fields with the domain dataclass instances
    after loading.

    Returns the same Snapshot object for convenience.
    """
    if isinstance(snap.metrics, dict):
        snap.metrics = metrics_from_dict(snap.metrics)  # type: ignore[assignment]
    if isinstance(snap.vs_previous, dict):
        snap.vs_previous = delta_from_dict(snap.vs_previous)  # type: ignore[assignment]
    if isinstance(snap.vs_baseline, dict):
        snap.vs_baseline = delta_from_dict(snap.vs_baseline)  # type: ignore[assignment]
    return snap


# ---------------------------------------------------------------------------
# FileTreeKG-specific SnapshotManager
# ---------------------------------------------------------------------------


class FtreeSnapshotManager(_BaseSnapshotManager):
    """FileTreeKG snapshot manager.

    Extends the shared SnapshotManager with:
    - Default package name "ftree-kg" (fallback "filetreekg").
    - Legacy ``stats_dict`` parameter in ``capture()`` (mapped to
      ``graph_stats_dict`` of the base class).
    - ``files_delta`` and ``dirs_delta`` fields in delta computation.
    - Per-directory node counts via ``_collect_dir_node_counts()``.
    - Automatic hydration of returned Snapshot objects so that
      ``snap.metrics`` is a SnapshotMetrics instance and
      ``snap.vs_*`` are SnapshotDelta instances.
    """

    def __init__(
        self,
        snapshots_dir: Path | str,
        db_path: Path | str | None = None,
        *,
        package_name: str = "ftree-kg",
    ) -> None:
        """Initialise.

        :param snapshots_dir: Directory for snapshot JSON files and manifest.
        :param db_path: Optional path to the SQLite graph database.
        :param package_name: Package name for version detection; falls back to
            "filetreekg" if "ftree-kg" is not installed.
        """
        # Resolve the best available package name at construction time.
        import importlib.metadata

        resolved_name = package_name
        try:
            importlib.metadata.version(package_name)
        except importlib.metadata.PackageNotFoundError:
            try:
                importlib.metadata.version("filetreekg")
                resolved_name = "filetreekg"
            except importlib.metadata.PackageNotFoundError:
                pass  # keep the requested name; _package_version returns 'unknown'

        super().__init__(snapshots_dir, package_name=resolved_name, db_path=db_path)

    # ------------------------------------------------------------------
    # capture — accept legacy stats_dict kwarg
    # ------------------------------------------------------------------

    def capture(  # type: ignore[override]
        self,
        version: str | None = None,
        branch: str | None = None,
        stats_dict: dict[str, Any] | None = None,
        tree_hash: str = "",
        *,
        graph_stats_dict: dict[str, Any] | None = None,
        **kwargs: Any,
    ) -> Snapshot:
        """Capture a snapshot.

        Accepts the legacy ``stats_dict`` keyword (mapped to the base class's
        ``graph_stats_dict``) and extends the metrics dict with
        ``total_files``, ``total_dirs``, and ``dir_node_counts`` before
        delegating to the base implementation.

        All other keyword arguments are forwarded to the base class.

        :param stats_dict: Legacy alias for ``graph_stats_dict``.
        """
        # Prefer explicit graph_stats_dict over legacy stats_dict.
        effective_stats = graph_stats_dict if graph_stats_dict is not None else stats_dict or {}

        node_counts: dict[str, int] = effective_stats.get("node_counts", {})
        dir_node_counts = self._collect_dir_node_counts()

        snap = super().capture(
            version=version,
            branch=branch,
            graph_stats_dict={
                **effective_stats,
                "total_files": node_counts.get("file", 0),
                "total_dirs": node_counts.get("directory", 0),
                "dir_node_counts": dir_node_counts,
            },
            tree_hash=tree_hash,
            **kwargs,
        )
        return _hydrate_snapshot(snap)

    # ------------------------------------------------------------------
    # load_snapshot — hydrate domain types on read-back
    # ------------------------------------------------------------------

    def load_snapshot(self, key: str) -> Snapshot | None:
        snap = super().load_snapshot(key)
        if snap is None:
            return None
        return _hydrate_snapshot(snap)

    # ------------------------------------------------------------------
    # Delta computation — add files_delta and dirs_delta
    # ------------------------------------------------------------------

    def _compute_delta_from_metrics(
        self, new_m: dict[str, Any], old_m: dict[str, Any]
    ) -> dict[str, Any]:
        """Extend base delta with filesystem-specific delta fields."""
        base = super()._compute_delta_from_metrics(new_m, old_m)
        base["files_delta"] = new_m.get("total_files", 0) - old_m.get("total_files", 0)
        base["dirs_delta"] = new_m.get("total_dirs", 0) - old_m.get("total_dirs", 0)
        return base

    # ------------------------------------------------------------------
    # Per-directory node counts (SQLite query)
    # ------------------------------------------------------------------

    def _collect_dir_node_counts(self) -> dict[str, int]:
        """Query SQLite for node counts grouped by top-level directory.

        :return: Dict mapping top-level dir name to node count, or empty dict
                 if the DB is unavailable or the query fails.
        """
        if not self.db_path or not self.db_path.exists():
            return {}
        try:
            with sqlite3.connect(self.db_path) as conn:
                rows = conn.execute(
                    "SELECT source_path, COUNT(*) FROM nodes GROUP BY source_path"
                ).fetchall()
            counts: dict[str, int] = {}
            for source_path, count in rows:
                if not source_path:
                    continue
                top = source_path.split("/")[0] if "/" in source_path else source_path
                counts[top] = counts.get(top, 0) + count
            return counts
        except sqlite3.Error:
            return {}

    # ------------------------------------------------------------------
    # diff_snapshots — restore dir_node_counts_delta for CLI display
    # ------------------------------------------------------------------

    def diff_snapshots(self, key_a: str, key_b: str) -> dict[str, Any]:
        """Compare two snapshots; extends base result with dir_node_counts_delta.

        Overrides the base implementation to:
        - Ensure ``result["a"]["metrics"]`` and ``result["b"]["metrics"]`` are
          plain dicts (the base class uses the hydrated dataclass directly, but
          ``cmd_snapshot.py`` calls ``.get()`` on those values).
        - Add ``dir_node_counts_delta`` for the CLI diff display.
        """
        snap_a = self.load_snapshot(key_a)
        snap_b = self.load_snapshot(key_b)

        if not snap_a or not snap_b:
            return {"error": "One or both snapshots not found"}

        # snap.metrics is a SnapshotMetrics dataclass after _hydrate_snapshot.
        m_a = metrics_to_dict(snap_a.metrics)  # type: ignore[arg-type]
        m_b = metrics_to_dict(snap_b.metrics)  # type: ignore[arg-type]

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

        dnc_a: dict[str, int] = m_a.get("dir_node_counts", {})
        dnc_b: dict[str, int] = m_b.get("dir_node_counts", {})
        all_dirs = set(dnc_a) | set(dnc_b)
        dir_node_counts_delta = {
            d: dnc_b.get(d, 0) - dnc_a.get(d, 0)
            for d in all_dirs
            if dnc_b.get(d, 0) != dnc_a.get(d, 0)
        }

        return {
            "a": {"key": snap_a.key, "metrics": m_a},
            "b": {"key": snap_b.key, "metrics": m_b},
            "delta": self._compute_delta_from_metrics(m_b, m_a),
            "node_counts_delta": node_counts_delta,
            "edge_counts_delta": edge_counts_delta,
            "dir_node_counts_delta": dir_node_counts_delta,
        }

    # ------------------------------------------------------------------
    # save_snapshot — serialize domain dataclasses back to dicts
    # ------------------------------------------------------------------

    def save_snapshot(self, snapshot: Snapshot) -> Path:
        """Save snapshot; converts domain dataclass fields to dicts first."""
        # The base class expects metrics and vs_* to be dicts.  If they have
        # been hydrated to domain dataclasses, convert them back before saving.
        if isinstance(snapshot.metrics, SnapshotMetrics):
            snapshot.metrics = metrics_to_dict(snapshot.metrics)  # type: ignore[assignment]
        if isinstance(snapshot.vs_previous, SnapshotDelta):
            snapshot.vs_previous = delta_to_dict(snapshot.vs_previous)
        if isinstance(snapshot.vs_baseline, SnapshotDelta):
            snapshot.vs_baseline = delta_to_dict(snapshot.vs_baseline)

        path = super().save_snapshot(snapshot)

        # Re-hydrate after saving so the caller still has attribute access.
        _hydrate_snapshot(snapshot)
        return path


# ---------------------------------------------------------------------------
# Public alias — keeps ``from src.snapshots import SnapshotManager`` working
# ---------------------------------------------------------------------------

SnapshotManager = FtreeSnapshotManager
