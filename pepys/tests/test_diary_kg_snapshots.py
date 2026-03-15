"""
test_diary_kg_snapshots.py

Unit tests for diary_kg.snapshots — DiarySnapshotMetrics, DiarySnapshotDelta,
DiarySnapshot, DiarySnapshotManifest, and DiarySnapshotManager.
"""

from __future__ import annotations

import json
from dataclasses import asdict
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest

from diary_kg.snapshots import (
    DiarySnapshot,
    DiarySnapshotDelta,
    DiarySnapshotManifest,
    DiarySnapshotManager,
    DiarySnapshotMetrics,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _metrics(
    chunk_count: int = 10,
    entry_count: int = 5,
    node_count: int = 20,
    edge_count: int = 15,
    topic_counts: dict | None = None,
    context_counts: dict | None = None,
) -> DiarySnapshotMetrics:
    return DiarySnapshotMetrics(
        chunk_count=chunk_count,
        entry_count=entry_count,
        node_count=node_count,
        edge_count=edge_count,
        topic_counts=topic_counts or {"work": 4, "domestic": 3},
        context_counts=context_counts or {"Home": 3, "Office": 2},
        temporal_span={"start": "1660-01-01T00:00", "end": "1667-04-15T22:30"},
        chunking_strategy="sentence_group",
        chunk_size=512,
    )


def _snapshot(
    tree_hash: str = "abc123",
    branch: str = "main",
    timestamp: str | None = None,
    chunk_count: int = 10,
    label: str | None = None,
) -> DiarySnapshot:
    return DiarySnapshot(
        branch=branch,
        timestamp=timestamp or datetime.now(UTC).isoformat(),
        version="0.1.0",
        metrics=_metrics(chunk_count=chunk_count),
        tree_hash=tree_hash,
        label=label,
        source_file="pepys_diary.txt",
    )


def _make_mgr(tmp_path: Path) -> DiarySnapshotManager:
    return DiarySnapshotManager(tmp_path / "snapshots")


# ---------------------------------------------------------------------------
# Dataclasses
# ---------------------------------------------------------------------------

class TestDiarySnapshotMetrics:
    def test_required_fields(self):
        m = _metrics()
        assert m.chunk_count == 10
        assert m.entry_count == 5
        assert m.node_count == 20
        assert m.edge_count == 15

    def test_defaults(self):
        m = DiarySnapshotMetrics(chunk_count=0, entry_count=0, node_count=0, edge_count=0)
        assert m.topic_counts == {}
        assert m.context_counts == {}
        assert m.temporal_span == {}
        assert m.chunking_strategy == ""
        assert m.chunk_size == 512


class TestDiarySnapshotDelta:
    def test_defaults_are_zero(self):
        d = DiarySnapshotDelta()
        assert d.chunks == 0
        assert d.entries == 0
        assert d.nodes == 0
        assert d.edges == 0

    def test_set_values(self):
        d = DiarySnapshotDelta(chunks=5, entries=2, nodes=10, edges=8)
        assert d.chunks == 5


class TestDiarySnapshot:
    def test_key_returns_tree_hash(self):
        s = _snapshot(tree_hash="deadbeef")
        assert s.key == "deadbeef"

    def test_to_dict_roundtrip(self):
        s = _snapshot()
        d = s.to_dict()
        assert d["key"] == s.tree_hash
        assert d["branch"] == s.branch
        assert d["version"] == s.version
        assert "metrics" in d

    def test_from_dict_roundtrip(self):
        s = _snapshot(label="test label")
        restored = DiarySnapshot.from_dict(s.to_dict())
        assert restored.key == s.key
        assert restored.branch == s.branch
        assert restored.label == s.label
        assert restored.metrics.chunk_count == s.metrics.chunk_count

    def test_vs_previous_serialized(self):
        s = _snapshot()
        s.vs_previous = DiarySnapshotDelta(chunks=2, entries=1, nodes=4, edges=3)
        d = s.to_dict()
        assert d["vs_previous"]["chunks"] == 2

    def test_vs_previous_none_in_dict(self):
        s = _snapshot()
        d = s.to_dict()
        assert d["vs_previous"] is None


class TestDiarySnapshotManifest:
    def test_empty_manifest(self):
        m = DiarySnapshotManifest()
        assert m.snapshots == []
        assert m.format_version == "1.0"

    def test_to_dict_from_dict_roundtrip(self):
        m = DiarySnapshotManifest(
            last_update="2024-01-01T00:00:00",
            snapshots=[{"key": "abc", "timestamp": "2024-01-01T00:00:00"}],
        )
        restored = DiarySnapshotManifest.from_dict(m.to_dict())
        assert len(restored.snapshots) == 1
        assert restored.last_update == m.last_update


# ---------------------------------------------------------------------------
# DiarySnapshotManager — save / load
# ---------------------------------------------------------------------------

class TestSaveLoadSnapshot:
    def test_save_creates_json_file(self, tmp_path):
        mgr = _make_mgr(tmp_path)
        s = _snapshot(tree_hash="aaa111")
        mgr.save_snapshot(s)
        assert (mgr.snapshots_dir / "aaa111.json").exists()

    def test_save_updates_manifest(self, tmp_path):
        mgr = _make_mgr(tmp_path)
        mgr.save_snapshot(_snapshot(tree_hash="aaa111"))
        manifest = mgr.load_manifest()
        keys = [e["key"] for e in manifest.snapshots]
        assert "aaa111" in keys

    def test_save_rejects_zero_chunk_count(self, tmp_path):
        mgr = _make_mgr(tmp_path)
        s = _snapshot(chunk_count=0)
        with pytest.raises(ValueError, match="0 chunks"):
            mgr.save_snapshot(s)

    def test_load_snapshot_returns_snapshot(self, tmp_path):
        mgr = _make_mgr(tmp_path)
        s = _snapshot(tree_hash="bbb222")
        mgr.save_snapshot(s)
        loaded = mgr.load_snapshot("bbb222")
        assert loaded is not None
        assert loaded.key == "bbb222"

    def test_load_snapshot_missing_returns_none(self, tmp_path):
        mgr = _make_mgr(tmp_path)
        assert mgr.load_snapshot("nonexistent") is None

    def test_upsert_same_key(self, tmp_path):
        mgr = _make_mgr(tmp_path)
        s = _snapshot(tree_hash="ccc333", label="first")
        mgr.save_snapshot(s)
        s2 = _snapshot(tree_hash="ccc333", label="updated")
        mgr.save_snapshot(s2)
        manifest = mgr.load_manifest()
        entries = [e for e in manifest.snapshots if e["key"] == "ccc333"]
        assert len(entries) == 1  # upserted, not duplicated

    def test_empty_manifest_when_no_file(self, tmp_path):
        mgr = _make_mgr(tmp_path)
        manifest = mgr.load_manifest()
        assert manifest.snapshots == []


# ---------------------------------------------------------------------------
# DiarySnapshotManager — list / diff / baseline / previous
# ---------------------------------------------------------------------------

class TestListSnapshots:
    def _populate(self, mgr: DiarySnapshotManager) -> list[str]:
        """Save 3 snapshots at staggered timestamps; return keys."""
        keys = []
        base_ts = datetime(2024, 1, 1, 0, 0, 0, tzinfo=UTC)
        for i, (key, chunk_count) in enumerate([("k1", 5), ("k2", 10), ("k3", 15)]):
            ts = (base_ts + timedelta(hours=i)).isoformat()
            s = _snapshot(tree_hash=key, timestamp=ts, chunk_count=chunk_count)
            mgr.save_snapshot(s)
            keys.append(key)
        return keys

    def test_returns_reverse_chronological(self, tmp_path):
        mgr = _make_mgr(tmp_path)
        self._populate(mgr)
        snaps = mgr.list_snapshots()
        timestamps = [s["timestamp"] for s in snaps]
        assert timestamps == sorted(timestamps, reverse=True)

    def test_limit_respected(self, tmp_path):
        mgr = _make_mgr(tmp_path)
        self._populate(mgr)
        snaps = mgr.list_snapshots(limit=2)
        assert len(snaps) == 2

    def test_branch_filter(self, tmp_path):
        mgr = _make_mgr(tmp_path)
        s1 = _snapshot(tree_hash="main1", branch="main")
        s2 = _snapshot(tree_hash="feat1", branch="feature")
        s1.timestamp = datetime(2024, 1, 1, tzinfo=UTC).isoformat()
        s2.timestamp = datetime(2024, 1, 2, tzinfo=UTC).isoformat()
        mgr.save_snapshot(s1)
        mgr.save_snapshot(s2)
        main_snaps = mgr.list_snapshots(branch="main")
        assert all(s.get("branch") == "main" for s in main_snaps)
        assert len(main_snaps) == 1

    def test_fills_vs_previous_delta(self, tmp_path):
        mgr = _make_mgr(tmp_path)
        self._populate(mgr)
        snaps = mgr.list_snapshots()
        # All but the last (oldest) should have vs_previous delta
        for snap in snaps[:-1]:
            assert snap.get("deltas", {}).get("vs_previous") is not None

    def test_empty_list_when_no_snapshots(self, tmp_path):
        mgr = _make_mgr(tmp_path)
        assert mgr.list_snapshots() == []


class TestGetBaselineAndPrevious:
    def test_get_baseline_returns_oldest(self, tmp_path):
        mgr = _make_mgr(tmp_path)
        old = _snapshot(tree_hash="old1", timestamp=datetime(2023, 1, 1, tzinfo=UTC).isoformat())
        new = _snapshot(tree_hash="new1", timestamp=datetime(2024, 1, 1, tzinfo=UTC).isoformat())
        mgr.save_snapshot(old)
        mgr.save_snapshot(new)
        baseline = mgr.get_baseline()
        assert baseline is not None
        assert baseline.key == "old1"

    def test_get_baseline_empty_returns_none(self, tmp_path):
        mgr = _make_mgr(tmp_path)
        assert mgr.get_baseline() is None

    def test_get_previous_returns_immediately_before(self, tmp_path):
        mgr = _make_mgr(tmp_path)
        s1 = _snapshot(tree_hash="s1", timestamp=datetime(2024, 1, 1, tzinfo=UTC).isoformat())
        s2 = _snapshot(tree_hash="s2", timestamp=datetime(2024, 1, 2, tzinfo=UTC).isoformat())
        s3 = _snapshot(tree_hash="s3", timestamp=datetime(2024, 1, 3, tzinfo=UTC).isoformat())
        for s in [s1, s2, s3]:
            mgr.save_snapshot(s)
        prev = mgr.get_previous("s3")
        assert prev is not None
        assert prev.key == "s2"

    def test_get_previous_for_oldest_returns_none(self, tmp_path):
        mgr = _make_mgr(tmp_path)
        s = _snapshot(tree_hash="only")
        mgr.save_snapshot(s)
        assert mgr.get_previous("only") is None

    def test_get_previous_unknown_key_returns_none(self, tmp_path):
        mgr = _make_mgr(tmp_path)
        assert mgr.get_previous("doesnotexist") is None


class TestDiffSnapshots:
    def test_diff_returns_a_b_delta(self, tmp_path):
        mgr = _make_mgr(tmp_path)
        a = _snapshot(tree_hash="sa", chunk_count=10)
        b = _snapshot(tree_hash="sb", chunk_count=20)
        mgr.save_snapshot(a)
        mgr.save_snapshot(b)
        result = mgr.diff_snapshots("sa", "sb")
        assert "a" in result
        assert "b" in result
        assert "delta" in result
        assert result["delta"]["chunks"] == 10

    def test_diff_topic_counts_delta(self, tmp_path):
        mgr = _make_mgr(tmp_path)
        a = _snapshot(tree_hash="sa")
        a.metrics.topic_counts = {"work": 2, "domestic": 3}
        b = _snapshot(tree_hash="sb")
        b.metrics.topic_counts = {"work": 5, "domestic": 3, "social": 1}
        mgr.save_snapshot(a)
        mgr.save_snapshot(b)
        result = mgr.diff_snapshots("sa", "sb")
        assert "topic_counts_delta" in result
        assert result["topic_counts_delta"].get("work") == 3
        assert result["topic_counts_delta"].get("social") == 1
        # domestic unchanged — should NOT appear
        assert "domestic" not in result["topic_counts_delta"]

    def test_diff_missing_key_returns_error(self, tmp_path):
        mgr = _make_mgr(tmp_path)
        result = mgr.diff_snapshots("missing_a", "missing_b")
        assert "error" in result


# ---------------------------------------------------------------------------
# DiarySnapshotManager — capture
# ---------------------------------------------------------------------------

class TestCapture:
    def test_capture_returns_snapshot(self, tmp_path):
        mgr = _make_mgr(tmp_path)
        info = {
            "chunk_count": 10,
            "entry_count": 5,
            "topic_counts": {"work": 3},
            "context_counts": {"Office": 2},
            "temporal_span": {"start": "1660-01-01", "end": "1667-04-15"},
            "chunking_strategy": "sentence_group",
            "chunk_size": 512,
        }
        db_stats = {"node_count": 20, "edge_count": 15}
        snap = mgr.capture(
            version="0.1.0",
            info=info,
            db_stats=db_stats,
            branch="main",
            tree_hash="testhash",
            label="test capture",
            source_file="pepys.txt",
        )
        assert isinstance(snap, DiarySnapshot)
        assert snap.metrics.chunk_count == 10
        assert snap.metrics.node_count == 20
        assert snap.label == "test capture"
        assert snap.source_file == "pepys.txt"
        assert snap.key == "testhash"

    def test_capture_sets_vs_previous_when_prior_exists(self, tmp_path):
        mgr = _make_mgr(tmp_path)
        first = _snapshot(tree_hash="first", chunk_count=5,
                          timestamp=datetime(2024, 1, 1, tzinfo=UTC).isoformat())
        mgr.save_snapshot(first)

        info = {
            "chunk_count": 10,
            "entry_count": 5,
            "topic_counts": {},
            "context_counts": {},
            "temporal_span": None,
            "chunking_strategy": "",
            "chunk_size": 512,
        }
        db_stats = {"node_count": 0, "edge_count": 0}
        snap = mgr.capture(
            version="0.2.0",
            info=info,
            db_stats=db_stats,
            branch="main",
            tree_hash="second",
        )
        assert snap.vs_previous is not None
        assert snap.vs_previous.chunks == 5  # 10 - 5

    def test_capture_non_int_node_count_treated_as_zero(self, tmp_path):
        mgr = _make_mgr(tmp_path)
        snap = mgr.capture(
            version="0.1.0",
            info={"chunk_count": 5, "entry_count": 2},
            db_stats={"node_count": "n/a", "edge_count": "n/a"},
            branch="main",
            tree_hash="xyz",
        )
        assert snap.metrics.node_count == 0
        assert snap.metrics.edge_count == 0
