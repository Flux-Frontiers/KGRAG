"""
snapshots.py — Shared Snapshot Infrastructure for all KG Modules

Provides the canonical data models and manager for capturing, storing, and
comparing temporal metric snapshots.  Individual KG backends (code_kg, doc_kg,
ftree_kg, etc.) import from here instead of maintaining their own copies.

Every snapshot is keyed by git tree hash and contains:
  - Timestamp and branch metadata
  - Metrics dict (domain-flexible: total_nodes, total_edges, node_counts, …)
  - Hotspots list and issues list
  - Deltas vs. previous and baseline snapshots

Snapshots are stored as JSON files alongside a ``manifest.json`` index inside
a configurable directory (e.g. ``.codekg/snapshots/``).

Usage
-----
>>> from kg_rag.snapshots import SnapshotManager
>>> mgr = SnapshotManager(".codekg/snapshots", package_name="code-kg")
>>> snapshot = mgr.capture(graph_stats_dict=kg.store.stats())
>>> mgr.save_snapshot(snapshot)
"""

from __future__ import annotations

import dataclasses
import importlib.metadata
import json
import subprocess
from dataclasses import dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

# ---------------------------------------------------------------------------
# Data models
# ---------------------------------------------------------------------------


@dataclass
class Snapshot:
    """A temporal snapshot of KG metrics.

    ``metrics`` is a free-form dict so that each domain can store whatever
    fields it needs (docstring_coverage, total_files, etc.) without requiring
    changes to this shared data model.  The only required keys are
    ``total_nodes`` and ``total_edges`` — the manager uses these for delta
    computation.

    ``vs_previous`` and ``vs_baseline`` are also free-form dicts so that
    domain-specific delta fields (coverage_delta, files_delta, …) can be
    stored alongside the universal ``nodes`` and ``edges`` deltas.
    """

    branch: str
    timestamp: str  # ISO 8601 UTC
    metrics: dict[str, Any]
    version: str = ""
    hotspots: list[dict[str, Any]] = field(default_factory=list)
    issues: list[str] = field(default_factory=list)
    vs_previous: dict[str, Any] | None = None
    vs_baseline: dict[str, Any] | None = None
    tree_hash: str = ""

    @property
    def key(self) -> str:
        """Stable file key: git tree hash."""
        return self.tree_hash

    def to_dict(self) -> dict[str, Any]:
        """Convert to a JSON-serializable dictionary."""
        return {
            "key": self.tree_hash,
            "branch": self.branch,
            "timestamp": self.timestamp,
            "version": self.version,
            "metrics": self.metrics,
            "hotspots": self.hotspots,
            "issues": self.issues,
            "vs_previous": self.vs_previous,
            "vs_baseline": self.vs_baseline,
        }

    @staticmethod
    def from_dict(data: dict[str, Any]) -> Snapshot:
        """Reconstruct a Snapshot from a dictionary loaded from JSON."""
        raw = dict(data)  # shallow copy to avoid mutating caller's data

        metrics = raw.pop("metrics", {})
        vs_prev = raw.pop("vs_previous", None)
        vs_base = raw.pop("vs_baseline", None)

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
            metrics=metrics,
            vs_previous=vs_prev,
            vs_baseline=vs_base,
            branch=raw.pop("branch", ""),
            timestamp=raw.pop("timestamp", ""),
            version=raw.pop("version", ""),
            hotspots=raw.pop("hotspots", []),
            issues=raw.pop("issues", []),
        )


@dataclass
class SnapshotManifest:
    """Index of all snapshots, with fast lookup by tree hash."""

    format_version: str = "1.0"
    last_update: str = ""
    snapshots: list[dict[str, Any]] = field(default_factory=list)

    def to_dict(self) -> dict[str, Any]:
        """Serialize to dict."""
        return {
            "format": self.format_version,
            "last_update": self.last_update,
            "snapshots": self.snapshots,
        }

    @staticmethod
    def from_dict(data: dict[str, Any]) -> SnapshotManifest:
        """Reconstruct from dict."""
        return SnapshotManifest(
            format_version=data.get("format", "1.0"),
            last_update=data.get("last_update", ""),
            snapshots=data.get("snapshots", []),
        )


# ---------------------------------------------------------------------------
# SnapshotManager
# ---------------------------------------------------------------------------


class SnapshotManager:
    """Manages snapshot capture, persistence, retrieval, and comparison.

    This is the single shared implementation.  Domain-specific KG libraries
    subclass this to override :meth:`_compute_delta` or
    :meth:`_collect_extra_metrics` when they need domain-specific delta fields
    or automatic metric collection from SQLite.

    :param snapshots_dir: Directory for snapshot JSON files and manifest.
    :param package_name: Package name for auto-detecting version
        (e.g. ``"code-kg"``, ``"doc-kg"``).  Defaults to ``"kg-rag"``.
    :param db_path: Optional SQLite database path for collecting per-module or
        per-directory node counts via :meth:`_collect_breakdown_counts`.
    """

    def __init__(
        self,
        snapshots_dir: Path | str,
        *,
        package_name: str = "kg-rag",
        db_path: Path | str | None = None,
    ) -> None:
        self.snapshots_dir = Path(snapshots_dir)
        self.snapshots_dir.mkdir(parents=True, exist_ok=True)
        self.manifest_path = self.snapshots_dir / "manifest.json"
        self.package_name = package_name
        self.db_path = Path(db_path) if db_path else None

    # ------------------------------------------------------------------
    # Package version detection
    # ------------------------------------------------------------------

    def _package_version(self) -> str:
        """Return the installed package version, or ``'unknown'``."""
        try:
            return importlib.metadata.version(self.package_name)
        except importlib.metadata.PackageNotFoundError:
            return "unknown"

    # ------------------------------------------------------------------
    # Capture & save
    # ------------------------------------------------------------------

    def capture(
        self,
        version: str | None = None,
        branch: str | None = None,
        graph_stats_dict: dict[str, Any] | None = None,
        tree_hash: str = "",
        hotspots: list[dict[str, Any]] | None = None,
        issues: list[str] | None = None,
        **extra_metrics: Any,
    ) -> Snapshot:
        """Capture a snapshot from current state.

        ``graph_stats_dict`` is merged with ``extra_metrics`` to form the
        snapshot's ``metrics`` dict.  Pass domain-specific fields as keyword
        arguments (e.g. ``coverage=0.85``, ``critical_issues=2``).

        :param version: Version string; auto-detected from package if None.
        :param branch: Git branch; auto-detected if None.
        :param graph_stats_dict: Output from the KG's ``stats()`` method.
        :param tree_hash: Git tree hash; auto-detected if not provided.
        :param hotspots: Top hotspot entries.
        :param issues: Issue description strings.
        :param extra_metrics: Additional domain-specific metric fields.
        :return: New :class:`Snapshot` instance (not yet persisted).
        """
        if not version:
            version = self._package_version()
        if branch is None:
            branch = self._get_current_branch()
        if not tree_hash:
            tree_hash = self._get_current_tree_hash()

        metrics: dict[str, Any] = dict(graph_stats_dict or {})
        metrics.update(extra_metrics)

        snapshot = Snapshot(
            branch=branch,
            timestamp=datetime.now(UTC).isoformat(),
            version=version,
            metrics=metrics,
            hotspots=hotspots or [],
            issues=issues or [],
            tree_hash=tree_hash,
        )

        prev = self.get_previous(tree_hash)
        if prev:
            snapshot.vs_previous = self._compute_delta(snapshot, prev)

        baseline = self.get_baseline()
        if baseline:
            snapshot.vs_baseline = self._compute_delta(snapshot, baseline)

        return snapshot

    def save_snapshot(self, snapshot: Snapshot) -> Path:
        """Persist a snapshot to disk and update the manifest.

        Rejects snapshots with zero ``total_nodes`` to protect against
        saving degenerate (unbuilt) state.

        :param snapshot: Snapshot to save.
        :return: Path to the saved JSON file.
        :raises ValueError: If ``total_nodes`` is 0.
        """
        m = snapshot.metrics
        total_nodes = (
            m.get("total_nodes", 0) if isinstance(m, dict) else getattr(m, "total_nodes", 0)
        )
        if total_nodes == 0:
            raise ValueError(
                "Refusing to save degenerate snapshot with 0 nodes. "
                "Build the KG before capturing a snapshot."
            )

        snapshot_file = self.snapshots_dir / f"{snapshot.key}.json"
        snapshot_file.write_text(json.dumps(snapshot.to_dict(), indent=2) + "\n", encoding="utf-8")

        manifest = self.load_manifest()
        existing_idx = next(
            (i for i, s in enumerate(manifest.snapshots) if s.get("key") == snapshot.key),
            None,
        )

        manifest_entry: dict[str, Any] = {
            "key": snapshot.key,
            "branch": snapshot.branch,
            "timestamp": snapshot.timestamp,
            "version": snapshot.version,
            "file": snapshot_file.name,
            "metrics": snapshot.metrics,
            "deltas": {
                "vs_previous": snapshot.vs_previous,
                "vs_baseline": snapshot.vs_baseline,
            },
        }

        if existing_idx is not None:
            manifest.snapshots[existing_idx] = manifest_entry
        else:
            manifest.snapshots.append(manifest_entry)

        manifest.last_update = datetime.now(UTC).isoformat()
        self._save_manifest(manifest)
        return snapshot_file

    # ------------------------------------------------------------------
    # Loading & listing
    # ------------------------------------------------------------------

    def load_manifest(self) -> SnapshotManifest:
        """Load ``manifest.json``; return empty manifest if absent."""
        if not self.manifest_path.exists():
            return SnapshotManifest()
        manifest = SnapshotManifest.from_dict(
            json.loads(self.manifest_path.read_text(encoding="utf-8"))
        )
        # Normalise legacy 'tree_hash' → 'key'
        for entry in manifest.snapshots:
            if "key" not in entry and "tree_hash" in entry:
                entry["key"] = entry.pop("tree_hash")
        return manifest

    def _save_manifest(self, manifest: SnapshotManifest) -> None:
        self.manifest_path.write_text(
            json.dumps(manifest.to_dict(), indent=2) + "\n", encoding="utf-8"
        )

    def load_snapshot(self, key: str) -> Snapshot | None:
        """Load a snapshot by key (tree hash) or ``'latest'``.

        Missing ``vs_previous`` / ``vs_baseline`` deltas are backfilled
        on-the-fly from manifest metadata.
        """
        if key == "latest":
            manifest = self.load_manifest()
            if not manifest.snapshots:
                return None
            entry = max(manifest.snapshots, key=lambda x: x.get("timestamp", ""))
            key = entry["key"]

        snapshot_file = self.snapshots_dir / f"{key}.json"
        if not snapshot_file.exists():
            return None
        snap = Snapshot.from_dict(json.loads(snapshot_file.read_text(encoding="utf-8")))

        # Backfill missing deltas from manifest
        if snap.vs_previous is None or snap.vs_baseline is None:
            manifest = self.load_manifest()
            entries = sorted(manifest.snapshots, key=lambda x: x.get("timestamp", ""), reverse=True)
            idx = next((i for i, s in enumerate(entries) if s.get("key") == key), None)

            if idx is not None:
                if snap.vs_previous is None and idx + 1 < len(entries):
                    prev_m = entries[idx + 1].get("metrics", {})
                    snap.vs_previous = {
                        "nodes": snap.metrics.get("total_nodes", 0) - prev_m.get("total_nodes", 0),
                        "edges": snap.metrics.get("total_edges", 0) - prev_m.get("total_edges", 0),
                    }
                if snap.vs_baseline is None and entries:
                    base_m = entries[-1].get("metrics", {})
                    if entries[-1].get("key") != key:
                        snap.vs_baseline = {
                            "nodes": snap.metrics.get("total_nodes", 0)
                            - base_m.get("total_nodes", 0),
                            "edges": snap.metrics.get("total_edges", 0)
                            - base_m.get("total_edges", 0),
                        }
        return snap

    def get_previous(self, key: str) -> Snapshot | None:
        """Get the snapshot immediately before *key* (by timestamp)."""
        manifest = self.load_manifest()
        current_ts = next(
            (s["timestamp"] for s in manifest.snapshots if s.get("key") == key),
            None,
        )
        if not current_ts:
            return None
        prev_entry = None
        for s in sorted(manifest.snapshots, key=lambda x: x["timestamp"], reverse=True):
            if s["timestamp"] < current_ts:
                prev_entry = s
                break
        return self.load_snapshot(prev_entry["key"]) if prev_entry else None

    def get_baseline(self) -> Snapshot | None:
        """Get the oldest snapshot (baseline for comparison)."""
        manifest = self.load_manifest()
        if not manifest.snapshots:
            return None
        baseline_entry = min(manifest.snapshots, key=lambda x: x["timestamp"])
        return self.load_snapshot(baseline_entry["key"])

    def list_snapshots(
        self,
        limit: int | None = None,
        branch: str | None = None,
    ) -> list[dict[str, Any]]:
        """List snapshots in reverse chronological order.

        Missing ``vs_previous`` deltas are computed on-the-fly from adjacent
        manifest entries.

        :param limit: Max number to return; ``None`` = all.
        :param branch: If provided, filter by branch name.
        :return: List of snapshot metadata dicts.
        """
        manifest = self.load_manifest()
        all_snaps = sorted(manifest.snapshots, key=lambda x: x["timestamp"], reverse=True)

        if branch is not None:
            all_snaps = [s for s in all_snaps if s.get("branch") == branch]

        for i, snap in enumerate(all_snaps):
            if snap.get("deltas", {}).get("vs_previous") is None and i + 1 < len(all_snaps):
                prev = all_snaps[i + 1]
                snap.setdefault("deltas", {})["vs_previous"] = self._compute_delta_from_metrics(
                    snap["metrics"], prev["metrics"]
                )

        return all_snaps[:limit] if limit else all_snaps

    def diff_snapshots(self, key_a: str, key_b: str) -> dict[str, Any]:
        """Compare two snapshots side-by-side.

        :param key_a: First snapshot key (tree hash).
        :param key_b: Second snapshot key (tree hash).
        :return: Dict with metrics from both and computed deltas.
        """
        snap_a = self.load_snapshot(key_a)
        snap_b = self.load_snapshot(key_b)

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
            "a": {"key": snap_a.key, "metrics": snap_a.metrics, "issues": snap_a.issues},
            "b": {"key": snap_b.key, "metrics": snap_b.metrics, "issues": snap_b.issues},
            "delta": self._compute_delta(snap_b, snap_a),
            "node_counts_delta": node_counts_delta,
            "edge_counts_delta": edge_counts_delta,
        }

    # ------------------------------------------------------------------
    # Delta computation — override for domain-specific delta fields
    # ------------------------------------------------------------------

    def _compute_delta(self, snap_new: Snapshot, snap_old: Snapshot) -> dict[str, Any]:
        """Compute metrics delta (new - old).

        Override in subclasses to add domain-specific delta fields
        (e.g. ``coverage_delta``, ``files_delta``).
        """

        def _to_dict(m: Any) -> dict[str, Any]:
            if isinstance(m, dict):
                return m
            if dataclasses.is_dataclass(m) and not isinstance(m, type):
                return dataclasses.asdict(m)
            return {}

        return self._compute_delta_from_metrics(
            _to_dict(snap_new.metrics), _to_dict(snap_old.metrics)
        )

    def _compute_delta_from_metrics(
        self, new_m: dict[str, Any], old_m: dict[str, Any]
    ) -> dict[str, Any]:
        """Compute delta from two raw metrics dicts.

        Override in subclasses to add domain-specific delta fields.
        """
        return {
            "nodes": new_m.get("total_nodes", 0) - old_m.get("total_nodes", 0),
            "edges": new_m.get("total_edges", 0) - old_m.get("total_edges", 0),
        }

    # ------------------------------------------------------------------
    # Git helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _get_current_tree_hash() -> str:
        """Get current git tree hash (HEAD^{tree})."""
        try:
            return subprocess.check_output(
                ["git", "rev-parse", "HEAD^{tree}"],
                text=True,
                stderr=subprocess.DEVNULL,
            ).strip()
        except (subprocess.CalledProcessError, FileNotFoundError):
            return ""

    @staticmethod
    def _get_current_branch() -> str:
        """Get current git branch name."""
        try:
            return subprocess.check_output(
                ["git", "rev-parse", "--abbrev-ref", "HEAD"],
                text=True,
                stderr=subprocess.DEVNULL,
            ).strip()
        except (subprocess.CalledProcessError, FileNotFoundError):
            return "unknown"
