"""
snapshots.py — Temporal Snapshots of DiaryKG Metrics

Mirrors the code_kg SnapshotManager pattern exactly:
- Key is the git tree hash (HEAD^{tree}), stable across rebases
- Snapshots stored in .diarykg/snapshots/{tree_hash}.json
- manifest.json indexes all snapshots with fast lookup
- Deltas computed vs previous (chronological) and vs baseline (oldest)

Usage
-----
>>> from diary_kg.snapshots import DiarySnapshotManager
>>> mgr = DiarySnapshotManager(".diarykg/snapshots")
>>> snap = mgr.capture(version="0.1.0", info=kg.info(), db_stats=kg.stats())
>>> mgr.save_snapshot(snap)
>>> mgr.list_snapshots()
"""

from __future__ import annotations

import json
import subprocess
from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from pathlib import Path


# ---------------------------------------------------------------------------
# Dataclasses
# ---------------------------------------------------------------------------

@dataclass
class DiarySnapshotMetrics:
    """Diary-specific metrics captured in a snapshot."""

    chunk_count: int
    entry_count: int
    node_count: int          # DocKG total nodes
    edge_count: int          # DocKG total edges
    topic_counts: dict[str, int] = field(default_factory=dict)
    context_counts: dict[str, int] = field(default_factory=dict)
    temporal_span: dict[str, str] = field(default_factory=dict)  # {start, end}
    chunking_strategy: str = ""
    chunk_size: int = 512


@dataclass
class DiarySnapshotDelta:
    """Deltas comparing this snapshot to a baseline or previous snapshot."""

    chunks: int = 0
    entries: int = 0
    nodes: int = 0
    edges: int = 0


@dataclass
class DiarySnapshot:
    """A temporal snapshot of DiaryKG metrics."""

    branch: str
    timestamp: str       # ISO 8601 UTC
    version: str
    metrics: DiarySnapshotMetrics
    vs_previous: DiarySnapshotDelta | None = None
    vs_baseline: DiarySnapshotDelta | None = None
    tree_hash: str = ""
    label: str | None = None
    source_file: str | None = None

    @property
    def key(self) -> str:
        """Stable file key: git tree hash."""
        return self.tree_hash

    def to_dict(self) -> dict:
        return {
            "key": self.tree_hash,
            "branch": self.branch,
            "timestamp": self.timestamp,
            "version": self.version,
            "label": self.label,
            "source_file": self.source_file,
            "metrics": asdict(self.metrics),
            "vs_previous": asdict(self.vs_previous) if self.vs_previous else None,
            "vs_baseline": asdict(self.vs_baseline) if self.vs_baseline else None,
        }

    @staticmethod
    def from_dict(data: dict) -> DiarySnapshot:
        d = dict(data)
        metrics = DiarySnapshotMetrics(**d.pop("metrics"))
        vp = d.pop("vs_previous", None)
        vb = d.pop("vs_baseline", None)
        key = d.pop("key", "")
        return DiarySnapshot(
            tree_hash=key,
            metrics=metrics,
            vs_previous=DiarySnapshotDelta(**vp) if vp else None,
            vs_baseline=DiarySnapshotDelta(**vb) if vb else None,
            **d,
        )


@dataclass
class DiarySnapshotManifest:
    """Index of all DiaryKG snapshots."""

    format_version: str = "1.0"
    last_update: str = ""
    snapshots: list[dict] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "format": self.format_version,
            "last_update": self.last_update,
            "snapshots": self.snapshots,
        }

    @staticmethod
    def from_dict(data: dict) -> DiarySnapshotManifest:
        return DiarySnapshotManifest(
            format_version=data.get("format", "1.0"),
            last_update=data.get("last_update", ""),
            snapshots=data.get("snapshots", []),
        )


# ---------------------------------------------------------------------------
# Manager
# ---------------------------------------------------------------------------

class DiarySnapshotManager:
    """Manages DiaryKG snapshot storage, retrieval, and comparison."""

    def __init__(self, snapshots_dir: Path | str) -> None:
        self.snapshots_dir = Path(snapshots_dir)
        self.snapshots_dir.mkdir(parents=True, exist_ok=True)
        self.manifest_path = self.snapshots_dir / "manifest.json"

    # ------------------------------------------------------------------
    # Capture
    # ------------------------------------------------------------------

    def capture(
        self,
        version: str,
        info: dict,
        db_stats: dict,
        branch: str | None = None,
        tree_hash: str = "",
        label: str | None = None,
        source_file: str | None = None,
    ) -> DiarySnapshot:
        """Capture a snapshot from current DiaryKG state.

        :param version: Version string (e.g. ``"0.1.0"``).
        :param info: Output of ``DiaryKG.info()``.
        :param db_stats: Output of ``DiaryKG.stats()`` (node/edge counts).
        :param branch: Git branch; auto-detected if ``None``.
        :param tree_hash: Git tree hash; auto-detected if empty.
        :param label: Optional human-readable label.
        :param source_file: Source diary file label.
        :return: New ``DiarySnapshot`` instance (not yet saved).
        """
        if branch is None:
            branch = self._get_current_branch()
        if not tree_hash:
            tree_hash = self._get_current_tree_hash()

        node_count = db_stats.get("node_count", 0)
        edge_count = db_stats.get("edge_count", 0)
        if not isinstance(node_count, int):
            node_count = 0
        if not isinstance(edge_count, int):
            edge_count = 0

        metrics = DiarySnapshotMetrics(
            chunk_count=info.get("chunk_count", 0),
            entry_count=info.get("entry_count", 0),
            node_count=node_count,
            edge_count=edge_count,
            topic_counts=info.get("topic_counts") or {},
            context_counts=info.get("context_counts") or {},
            temporal_span=info.get("temporal_span") or {},
            chunking_strategy=info.get("chunking_strategy", ""),
            chunk_size=info.get("chunk_size", 512),
        )

        snapshot = DiarySnapshot(
            branch=branch,
            timestamp=datetime.now(UTC).isoformat(),
            version=version,
            metrics=metrics,
            tree_hash=tree_hash,
            label=label,
            source_file=source_file or info.get("source_file"),
        )

        prev = self.get_previous(tree_hash)
        if prev:
            snapshot.vs_previous = self._compute_delta(snapshot, prev)

        baseline = self.get_baseline()
        if baseline:
            snapshot.vs_baseline = self._compute_delta(snapshot, baseline)

        return snapshot

    # ------------------------------------------------------------------
    # Save / Load
    # ------------------------------------------------------------------

    def save_snapshot(self, snapshot: DiarySnapshot) -> Path:
        """Save snapshot JSON and update manifest.

        :param snapshot: Snapshot to persist.
        :return: Path to the saved JSON file.
        :raises ValueError: If chunk_count is 0 (degenerate / unbuilt KG).
        """
        if snapshot.metrics.chunk_count == 0:
            raise ValueError(
                "Refusing to save degenerate snapshot with 0 chunks. "
                "Run 'diarykg build' before capturing a snapshot."
            )

        snap_file = self.snapshots_dir / f"{snapshot.key}.json"
        snap_file.write_text(json.dumps(snapshot.to_dict(), indent=2), encoding="utf-8")

        manifest = self.load_manifest()
        existing_idx = next(
            (i for i, s in enumerate(manifest.snapshots) if s.get("key") == snapshot.key),
            None,
        )
        entry = {
            "key": snapshot.key,
            "branch": snapshot.branch,
            "timestamp": snapshot.timestamp,
            "version": snapshot.version,
            "label": snapshot.label,
            "file": snap_file.name,
            "metrics": asdict(snapshot.metrics),
            "deltas": {
                "vs_previous": asdict(snapshot.vs_previous) if snapshot.vs_previous else None,
                "vs_baseline": asdict(snapshot.vs_baseline) if snapshot.vs_baseline else None,
            },
        }

        if existing_idx is not None:
            manifest.snapshots[existing_idx] = entry
        else:
            manifest.snapshots.append(entry)

        manifest.last_update = datetime.now(UTC).isoformat()
        self._save_manifest(manifest)
        return snap_file

    def load_manifest(self) -> DiarySnapshotManifest:
        """Load manifest.json; return empty manifest if absent."""
        if not self.manifest_path.exists():
            return DiarySnapshotManifest()
        return DiarySnapshotManifest.from_dict(
            json.loads(self.manifest_path.read_text(encoding="utf-8"))
        )

    def _save_manifest(self, manifest: DiarySnapshotManifest) -> None:
        self.manifest_path.write_text(
            json.dumps(manifest.to_dict(), indent=2), encoding="utf-8"
        )

    def load_snapshot(self, key: str) -> DiarySnapshot | None:
        """Load a full snapshot by tree-hash key."""
        snap_file = self.snapshots_dir / f"{key}.json"
        if not snap_file.exists():
            return None
        return DiarySnapshot.from_dict(json.loads(snap_file.read_text(encoding="utf-8")))

    # ------------------------------------------------------------------
    # Queries
    # ------------------------------------------------------------------

    def get_previous(self, key: str) -> DiarySnapshot | None:
        """Return the snapshot immediately before this one (by timestamp)."""
        manifest = self.load_manifest()
        current_ts = next(
            (s["timestamp"] for s in manifest.snapshots if s.get("key") == key), None
        )
        if not current_ts:
            return None
        prev_entry = None
        for s in sorted(manifest.snapshots, key=lambda x: x["timestamp"], reverse=True):
            if s["timestamp"] < current_ts:
                prev_entry = s
                break
        return self.load_snapshot(prev_entry["key"]) if prev_entry else None

    def get_baseline(self) -> DiarySnapshot | None:
        """Return the oldest snapshot (baseline for comparison)."""
        manifest = self.load_manifest()
        if not manifest.snapshots:
            return None
        entry = min(manifest.snapshots, key=lambda x: x["timestamp"])
        return self.load_snapshot(entry["key"])

    def list_snapshots(
        self,
        limit: int | None = None,
        branch: str | None = None,
    ) -> list[dict]:
        """List snapshots in reverse-chronological order.

        Missing ``vs_previous`` deltas are filled in on-the-fly from adjacent
        manifest entries so every entry (except the oldest) has a delta.

        :param limit: Max results; ``None`` = all.
        :param branch: Filter by branch name.
        :return: List of manifest entry dicts.
        """
        manifest = self.load_manifest()
        all_snaps = sorted(manifest.snapshots, key=lambda x: x["timestamp"], reverse=True)
        if branch is not None:
            all_snaps = [s for s in all_snaps if s.get("branch") == branch]

        for i, snap in enumerate(all_snaps):
            if snap.get("deltas", {}).get("vs_previous") is None and i + 1 < len(all_snaps):
                prev = all_snaps[i + 1]
                snap.setdefault("deltas", {})["vs_previous"] = {
                    "chunks": snap["metrics"]["chunk_count"] - prev["metrics"]["chunk_count"],
                    "entries": snap["metrics"]["entry_count"] - prev["metrics"]["entry_count"],
                    "nodes": snap["metrics"]["node_count"] - prev["metrics"]["node_count"],
                    "edges": snap["metrics"]["edge_count"] - prev["metrics"]["edge_count"],
                }

        return all_snaps[:limit] if limit else all_snaps

    def diff_snapshots(self, key_a: str, key_b: str) -> dict:
        """Compare two snapshots side-by-side.

        :param key_a: Earlier snapshot key.
        :param key_b: Later snapshot key.
        :return: Dict with ``a``, ``b``, ``delta`` keys.
        """
        snap_a = self.load_snapshot(key_a)
        snap_b = self.load_snapshot(key_b)
        if not snap_a or not snap_b:
            return {"error": "One or both snapshots not found"}

        delta = self._compute_delta(snap_b, snap_a)

        all_topics = set(snap_a.metrics.topic_counts) | set(snap_b.metrics.topic_counts)
        topic_delta = {
            t: snap_b.metrics.topic_counts.get(t, 0) - snap_a.metrics.topic_counts.get(t, 0)
            for t in all_topics
            if snap_b.metrics.topic_counts.get(t, 0) != snap_a.metrics.topic_counts.get(t, 0)
        }

        return {
            "a": {"key": snap_a.key, "metrics": asdict(snap_a.metrics)},
            "b": {"key": snap_b.key, "metrics": asdict(snap_b.metrics)},
            "delta": asdict(delta),
            "topic_counts_delta": topic_delta,
        }

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _compute_delta(snap_new: DiarySnapshot, snap_old: DiarySnapshot) -> DiarySnapshotDelta:
        return DiarySnapshotDelta(
            chunks=snap_new.metrics.chunk_count - snap_old.metrics.chunk_count,
            entries=snap_new.metrics.entry_count - snap_old.metrics.entry_count,
            nodes=snap_new.metrics.node_count - snap_old.metrics.node_count,
            edges=snap_new.metrics.edge_count - snap_old.metrics.edge_count,
        )

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
