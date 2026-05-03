"""
test_snapshots.py

Tests for the snapshot subsystem. kg_rag.snapshots is a re-export shim —
the real implementation lives in kg_utils.snapshots. Tests cover:

  * Re-export shim: the three public names are importable from kg_rag.snapshots
  * Snapshot model: to_dict / from_dict round-trip, key property, legacy fields
  * SnapshotManifest model: to_dict / from_dict round-trip
  * PruneResult: total_cleaned property
  * SnapshotManager.capture(): builds correct Snapshot with explicit params
  * SnapshotManager.save_snapshot(): persists JSON + manifest, rejects 0 nodes,
      dedup refresh, force=True, updates existing key
  * SnapshotManager.load_snapshot(): round-trip and 'latest' alias
  * SnapshotManager.get_previous() / get_baseline(): chronological ordering
  * SnapshotManager.list_snapshots(): reverse-chron, limit, branch filter
  * SnapshotManager.diff_snapshots(): delta computation
  * SnapshotManager.prune_snapshots(): dry_run, metric-duplicates, orphans
  * KGAdapter.snapshot() template method: envelope shape + subclass merging
"""

from __future__ import annotations

import json

import pytest

# ---------------------------------------------------------------------------
# Shim re-export
# ---------------------------------------------------------------------------


def test_shim_exports_snapshot():
    from kg_rag.snapshots import Snapshot

    assert callable(Snapshot)


def test_shim_exports_snapshot_manager():
    from kg_rag.snapshots import SnapshotManager

    assert callable(SnapshotManager)


def test_shim_exports_snapshot_manifest():
    from kg_rag.snapshots import SnapshotManifest

    assert callable(SnapshotManifest)


def test_shim_same_class_as_kg_utils():
    """kg_rag.snapshots must re-export the exact same objects as kg_utils.snapshots."""
    from kg_utils.snapshots import Snapshot as UtilsSnapshot

    from kg_rag.snapshots import Snapshot as KragSnapshot

    assert KragSnapshot is UtilsSnapshot


# ---------------------------------------------------------------------------
# Snapshot model
# ---------------------------------------------------------------------------


class TestSnapshot:
    def _make(self, **kw):
        from kg_rag.snapshots import Snapshot

        defaults = dict(
            branch="main",
            timestamp="2024-01-01T00:00:00+00:00",
            metrics={"total_nodes": 100, "total_edges": 200},
            version="1.2.3",
            tree_hash="abc123",
        )
        defaults.update(kw)
        return Snapshot(**defaults)

    def test_key_equals_tree_hash(self):
        s = self._make(tree_hash="deadbeef")
        assert s.key == "deadbeef"

    def test_to_dict_contains_required_keys(self):
        s = self._make()
        d = s.to_dict()
        for k in ("key", "branch", "timestamp", "version", "metrics"):
            assert k in d, f"missing key: {k!r}"

    def test_to_dict_key_is_tree_hash(self):
        s = self._make(tree_hash="abc123")
        assert s.to_dict()["key"] == "abc123"

    def test_from_dict_round_trip(self):
        from kg_rag.snapshots import Snapshot

        s = self._make(
            hotspots=[{"id": "x", "score": 0.9}],
            issues=["coverage low"],
            vs_previous={"nodes": 5, "edges": 10},
            vs_baseline={"nodes": -2, "edges": 4},
        )
        s2 = Snapshot.from_dict(s.to_dict())
        assert s2.branch == s.branch
        assert s2.timestamp == s.timestamp
        assert s2.version == s.version
        assert s2.metrics == s.metrics
        assert s2.tree_hash == s.tree_hash
        assert s2.hotspots == s.hotspots
        assert s2.issues == s.issues
        assert s2.vs_previous == s.vs_previous
        assert s2.vs_baseline == s.vs_baseline

    def test_from_dict_legacy_tree_hash_field(self):
        """Legacy JSON files stored 'tree_hash' at top level instead of 'key'."""
        from kg_rag.snapshots import Snapshot

        data = {
            "tree_hash": "legacy_hash",
            "branch": "main",
            "timestamp": "2024-01-01T00:00:00+00:00",
            "version": "1.0",
            "metrics": {"total_nodes": 50, "total_edges": 80},
        }
        s = Snapshot.from_dict(data)
        assert s.tree_hash == "legacy_hash"

    def test_from_dict_legacy_commit_field_ignored(self):
        """'commit' key in old snapshots must not cause errors."""
        from kg_rag.snapshots import Snapshot

        data = {
            "key": "new_hash",
            "commit": "old_sha",
            "branch": "main",
            "timestamp": "2024-01-01T00:00:00+00:00",
            "version": "1.0",
            "metrics": {"total_nodes": 10, "total_edges": 20},
        }
        s = Snapshot.from_dict(data)
        assert s.tree_hash == "new_hash"

    def test_default_hotspots_and_issues_are_empty(self):
        s = self._make()
        assert s.hotspots == []
        assert s.issues == []

    def test_default_vs_fields_are_none(self):
        s = self._make()
        assert s.vs_previous is None
        assert s.vs_baseline is None


# ---------------------------------------------------------------------------
# SnapshotManifest model
# ---------------------------------------------------------------------------


class TestSnapshotManifest:
    def test_to_dict_round_trip(self):
        from kg_rag.snapshots import SnapshotManifest

        m = SnapshotManifest(
            format_version="1.0",
            last_update="2024-06-01T12:00:00+00:00",
            snapshots=[{"key": "abc", "branch": "main"}],
        )
        d = m.to_dict()
        m2 = SnapshotManifest.from_dict(d)
        assert m2.format_version == m.format_version
        assert m2.last_update == m.last_update
        assert m2.snapshots == m.snapshots

    def test_empty_manifest(self):
        from kg_rag.snapshots import SnapshotManifest

        m = SnapshotManifest.from_dict({})
        assert m.snapshots == []
        assert m.format_version == "1.0"


# ---------------------------------------------------------------------------
# PruneResult
# ---------------------------------------------------------------------------


def test_prune_result_total_cleaned():
    from kg_utils.snapshots import PruneResult

    r = PruneResult(
        removed=["a", "b"],
        orphaned_files=["x.json"],
        broken_entries=["z"],
        dry_run=False,
    )
    assert r.total_cleaned == 4


def test_prune_result_dry_run_flag():
    from kg_utils.snapshots import PruneResult

    r = PruneResult(removed=[], orphaned_files=[], broken_entries=[], dry_run=True)
    assert r.dry_run is True
    assert r.total_cleaned == 0


# ---------------------------------------------------------------------------
# SnapshotManager fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def mgr(tmp_path):
    from kg_rag.snapshots import SnapshotManager

    return SnapshotManager(tmp_path / "snapshots", package_name="kg-rag")


def _snap(mgr, *, nodes=100, edges=200, branch="main", tree_hash="abc", version="1.0", **kw):
    """Convenience: capture a snapshot with explicit git params (no subprocess)."""
    return mgr.capture(
        version=version,
        branch=branch,
        tree_hash=tree_hash,
        graph_stats_dict={"total_nodes": nodes, "total_edges": edges},
        **kw,
    )


# ---------------------------------------------------------------------------
# SnapshotManager.capture
# ---------------------------------------------------------------------------


class TestSnapshotManagerCapture:
    def test_capture_sets_branch_and_version(self, mgr):
        s = _snap(mgr, branch="feature", version="2.0.0", tree_hash="h1")
        assert s.branch == "feature"
        assert s.version == "2.0.0"
        assert s.tree_hash == "h1"

    def test_capture_merges_extra_metrics(self, mgr):
        s = _snap(mgr, tree_hash="h1", coverage=0.87, critical_issues=2)
        assert s.metrics["coverage"] == 0.87
        assert s.metrics["critical_issues"] == 2
        assert s.metrics["total_nodes"] == 100

    def test_capture_with_hotspots_and_issues(self, mgr):
        s = _snap(
            mgr,
            tree_hash="h1",
            hotspots=[{"id": "fn:x", "score": 0.9}],
            issues=["orphan modules detected"],
        )
        assert s.hotspots[0]["id"] == "fn:x"
        assert "orphan modules detected" in s.issues

    def test_capture_no_vs_previous_on_first_snapshot(self, mgr):
        s = _snap(mgr, tree_hash="h1")
        assert s.vs_previous is None

    def test_load_has_vs_previous_after_two_saves(self, mgr):
        """vs_previous is backfilled by load_snapshot(), not set during capture().
        A freshly-captured snapshot has no timestamp in the manifest yet, so
        get_previous() returns None; loading after saving backfills it."""
        s1 = _snap(mgr, nodes=100, edges=200, tree_hash="h1")
        mgr.save_snapshot(s1, force=True)
        s2 = _snap(mgr, nodes=120, edges=230, tree_hash="h2")
        mgr.save_snapshot(s2, force=True)
        loaded = mgr.load_snapshot("h2")
        assert loaded is not None
        assert loaded.vs_previous is not None
        assert loaded.vs_previous["nodes"] == 20
        assert loaded.vs_previous["edges"] == 30

    def test_capture_vs_baseline_equals_delta_from_first(self, mgr):
        s1 = _snap(mgr, nodes=100, edges=200, tree_hash="h1")
        mgr.save_snapshot(s1)
        s2 = _snap(mgr, nodes=150, edges=250, tree_hash="h2")
        mgr.save_snapshot(s2)
        s3 = _snap(mgr, nodes=160, edges=260, tree_hash="h3")
        assert s3.vs_baseline is not None
        assert s3.vs_baseline["nodes"] == 60  # 160 - 100
        assert s3.vs_baseline["edges"] == 60  # 260 - 200


# ---------------------------------------------------------------------------
# SnapshotManager.save_snapshot
# ---------------------------------------------------------------------------


class TestSnapshotManagerSave:
    def test_save_creates_json_file(self, mgr):
        s = _snap(mgr, tree_hash="abc")
        path = mgr.save_snapshot(s)
        assert path is not None
        assert path.exists()
        data = json.loads(path.read_text())
        assert data["metrics"]["total_nodes"] == 100

    def test_save_updates_manifest(self, mgr):
        s = _snap(mgr, tree_hash="abc")
        mgr.save_snapshot(s)
        manifest = mgr.load_manifest()
        assert len(manifest.snapshots) == 1
        assert manifest.snapshots[0]["key"] == "abc"

    def test_save_rejects_zero_nodes(self, mgr):
        s = _snap(mgr, nodes=0, tree_hash="empty")
        with pytest.raises(ValueError, match="0 nodes"):
            mgr.save_snapshot(s)

    def test_save_dedup_refresh_same_metrics(self, mgr):
        """Saving the same metrics under a new hash refreshes the entry in-place."""
        s1 = _snap(mgr, nodes=100, edges=200, tree_hash="h1", version="1.0")
        mgr.save_snapshot(s1)
        s2 = _snap(mgr, nodes=100, edges=200, tree_hash="h2", version="1.0")
        mgr.save_snapshot(s2)
        manifest = mgr.load_manifest()
        assert len(manifest.snapshots) == 1, "dedup must keep only one entry"
        assert manifest.snapshots[0]["key"] == "h2"

    def test_save_force_skips_dedup(self, mgr):
        """force=True always creates a new manifest entry."""
        s1 = _snap(mgr, nodes=100, edges=200, tree_hash="h1", version="1.0")
        mgr.save_snapshot(s1)
        s2 = _snap(mgr, nodes=100, edges=200, tree_hash="h2", version="1.0")
        mgr.save_snapshot(s2, force=True)
        manifest = mgr.load_manifest()
        assert len(manifest.snapshots) == 2

    def test_save_new_metrics_creates_new_entry(self, mgr):
        s1 = _snap(mgr, nodes=100, edges=200, tree_hash="h1", version="1.0")
        mgr.save_snapshot(s1)
        s2 = _snap(mgr, nodes=150, edges=300, tree_hash="h2", version="1.0")
        mgr.save_snapshot(s2)
        manifest = mgr.load_manifest()
        assert len(manifest.snapshots) == 2

    def test_save_updates_existing_key(self, mgr):
        """Saving a snapshot with the same tree_hash replaces it."""
        s1 = _snap(mgr, nodes=100, edges=200, tree_hash="same", version="1.0")
        mgr.save_snapshot(s1)
        s2 = _snap(mgr, nodes=110, edges=210, tree_hash="same", version="1.1")
        mgr.save_snapshot(s2, force=True)
        manifest = mgr.load_manifest()
        matching = [e for e in manifest.snapshots if e["key"] == "same"]
        assert len(matching) == 1


# ---------------------------------------------------------------------------
# SnapshotManager.load_snapshot
# ---------------------------------------------------------------------------


class TestSnapshotManagerLoad:
    def test_load_by_key(self, mgr):
        s = _snap(mgr, tree_hash="xyz", nodes=42, edges=84)
        mgr.save_snapshot(s)
        loaded = mgr.load_snapshot("xyz")
        assert loaded is not None
        assert loaded.metrics["total_nodes"] == 42
        assert loaded.tree_hash == "xyz"

    def test_load_missing_key_returns_none(self, mgr):
        assert mgr.load_snapshot("no_such_key") is None

    def test_load_latest_alias(self, mgr):
        s1 = _snap(mgr, nodes=10, edges=20, tree_hash="old")
        mgr.save_snapshot(s1)
        s2 = _snap(mgr, nodes=50, edges=100, tree_hash="new")
        mgr.save_snapshot(s2, force=True)
        latest = mgr.load_snapshot("latest")
        assert latest is not None
        assert latest.metrics["total_nodes"] == 50

    def test_load_latest_empty_returns_none(self, mgr):
        assert mgr.load_snapshot("latest") is None

    def test_load_round_trip_preserves_all_fields(self, mgr):
        s = _snap(
            mgr,
            tree_hash="full",
            nodes=77,
            edges=88,
            version="3.1.4",
            branch="dev",
            hotspots=[{"id": "fn:x", "score": 0.95}],
            issues=["high coupling"],
        )
        mgr.save_snapshot(s)
        loaded = mgr.load_snapshot("full")
        assert loaded.version == "3.1.4"
        assert loaded.branch == "dev"
        assert loaded.hotspots[0]["score"] == 0.95
        assert "high coupling" in loaded.issues


# ---------------------------------------------------------------------------
# SnapshotManager.get_previous / get_baseline
# ---------------------------------------------------------------------------


class TestSnapshotManagerHistory:
    def _save_sequence(self, mgr, count: int = 3) -> list:
        snaps = []
        for i in range(count):
            s = _snap(mgr, nodes=100 + i * 10, edges=200 + i * 20, tree_hash=f"h{i}")
            mgr.save_snapshot(s, force=True)
            snaps.append(s)
        return snaps

    def test_get_baseline_is_oldest(self, mgr):
        snaps = self._save_sequence(mgr, 3)
        baseline = mgr.get_baseline()
        assert baseline is not None
        assert baseline.tree_hash == snaps[0].tree_hash

    def test_get_previous_is_chronologically_prior(self, mgr):
        snaps = self._save_sequence(mgr, 3)
        prev = mgr.get_previous(snaps[2].tree_hash)
        assert prev is not None
        assert prev.tree_hash == snaps[1].tree_hash

    def test_get_previous_for_first_snapshot_is_none(self, mgr):
        snaps = self._save_sequence(mgr, 2)
        prev = mgr.get_previous(snaps[0].tree_hash)
        assert prev is None

    def test_get_baseline_empty_is_none(self, mgr):
        assert mgr.get_baseline() is None


# ---------------------------------------------------------------------------
# SnapshotManager.list_snapshots
# ---------------------------------------------------------------------------


class TestSnapshotManagerList:
    def test_list_reverse_chronological(self, mgr):
        for i, h in enumerate(["h0", "h1", "h2"]):
            mgr.save_snapshot(_snap(mgr, nodes=100 + i, tree_hash=h), force=True)
        listed = mgr.list_snapshots()
        keys = [s["key"] for s in listed]
        assert keys == ["h2", "h1", "h0"]

    def test_list_limit(self, mgr):
        for i, h in enumerate(["h0", "h1", "h2"]):
            mgr.save_snapshot(_snap(mgr, nodes=100 + i, tree_hash=h), force=True)
        assert len(mgr.list_snapshots(limit=2)) == 2

    def test_list_branch_filter(self, mgr):
        mgr.save_snapshot(_snap(mgr, tree_hash="m1", branch="main"), force=True)
        mgr.save_snapshot(_snap(mgr, nodes=150, tree_hash="f1", branch="feature"), force=True)
        main_only = mgr.list_snapshots(branch="main")
        assert all(s["branch"] == "main" for s in main_only)
        assert len(main_only) == 1

    def test_list_empty_returns_empty(self, mgr):
        assert mgr.list_snapshots() == []


# ---------------------------------------------------------------------------
# SnapshotManager.diff_snapshots
# ---------------------------------------------------------------------------


class TestSnapshotManagerDiff:
    def test_diff_computes_node_and_edge_deltas(self, mgr):
        s1 = _snap(mgr, nodes=100, edges=200, tree_hash="before")
        s2 = _snap(mgr, nodes=120, edges=230, tree_hash="after")
        mgr.save_snapshot(s1, force=True)
        mgr.save_snapshot(s2, force=True)
        diff = mgr.diff_snapshots("before", "after")
        assert diff["delta"]["nodes"] == 20
        assert diff["delta"]["edges"] == 30

    def test_diff_negative_delta(self, mgr):
        s1 = _snap(mgr, nodes=120, edges=300, tree_hash="big")
        s2 = _snap(mgr, nodes=100, edges=200, tree_hash="small")
        mgr.save_snapshot(s1, force=True)
        mgr.save_snapshot(s2, force=True)
        diff = mgr.diff_snapshots("big", "small")
        assert diff["delta"]["nodes"] == -20

    def test_diff_missing_key_returns_error(self, mgr):
        s = _snap(mgr, tree_hash="only")
        mgr.save_snapshot(s)
        diff = mgr.diff_snapshots("only", "missing")
        assert "error" in diff

    def test_diff_includes_node_counts_delta(self, mgr):
        s1 = _snap(
            mgr,
            nodes=50,
            edges=80,
            tree_hash="k1",
            node_counts={"function": 30, "class": 20},
        )
        s2 = _snap(
            mgr,
            nodes=60,
            edges=90,
            tree_hash="k2",
            node_counts={"function": 35, "class": 25},
        )
        mgr.save_snapshot(s1, force=True)
        mgr.save_snapshot(s2, force=True)
        diff = mgr.diff_snapshots("k1", "k2")
        nc_delta = diff.get("node_counts_delta", {})
        assert nc_delta.get("function") == 5
        assert nc_delta.get("class") == 5


# ---------------------------------------------------------------------------
# SnapshotManager.prune_snapshots
# ---------------------------------------------------------------------------


class TestSnapshotManagerPrune:
    def _populate(self, mgr):
        """Save three snapshots: first (baseline), middle (duplicate), last (changed)."""
        s0 = _snap(mgr, nodes=100, tree_hash="h0", version="1.0")
        s1 = _snap(mgr, nodes=100, tree_hash="h1", version="1.0")  # metric duplicate of s0
        s2 = _snap(mgr, nodes=200, tree_hash="h2", version="1.0")  # genuinely changed
        for s in (s0, s1, s2):
            mgr.save_snapshot(s, force=True)

    def test_prune_dry_run_removes_nothing(self, mgr):
        self._populate(mgr)
        result = mgr.prune_snapshots(dry_run=True)
        assert result.dry_run is True
        assert len(mgr.load_manifest().snapshots) == 3

    def test_prune_removes_metric_duplicate(self, mgr):
        self._populate(mgr)
        result = mgr.prune_snapshots()
        assert "h1" in result.removed
        manifest = mgr.load_manifest()
        keys = {e["key"] for e in manifest.snapshots}
        assert "h1" not in keys
        assert "h0" in keys
        assert "h2" in keys

    def test_prune_removes_orphaned_files(self, mgr):
        self._populate(mgr)
        orphan = mgr.snapshots_dir / "orphan_abc123.json"
        orphan.write_text('{"key": "orphan"}')
        result = mgr.prune_snapshots()
        assert "orphan_abc123.json" in result.orphaned_files
        assert not orphan.exists()

    def test_prune_cleans_broken_entries(self, mgr):
        self._populate(mgr)
        manifest = mgr.load_manifest()
        # Manually add a broken entry (manifest points to non-existent file)
        manifest.snapshots.append(
            {
                "key": "broken",
                "branch": "main",
                "timestamp": "2020-01-01T00:00:00+00:00",
                "file": "broken.json",
                "version": "0.1",
                "metrics": {},
            }
        )
        mgr._save_manifest(manifest)
        result = mgr.prune_snapshots()
        assert "broken" in result.broken_entries

    def test_prune_preserves_first_and_last(self, mgr):
        """Baseline and latest must never be pruned, even if metrics match."""
        s0 = _snap(mgr, nodes=100, tree_hash="base", version="1.0")
        s1 = _snap(mgr, nodes=100, tree_hash="latest", version="1.0")
        mgr.save_snapshot(s0, force=True)
        mgr.save_snapshot(s1, force=True)
        result = mgr.prune_snapshots()
        assert "base" not in result.removed
        assert "latest" not in result.removed


# ---------------------------------------------------------------------------
# KGAdapter.snapshot() template method
# ---------------------------------------------------------------------------


class TestKGAdapterSnapshotMethod:
    """Tests for the base.py snapshot() template method via a minimal stub adapter."""

    def _make_entry(self):
        from kg_rag.primitives import KGEntry, KGKind

        return KGEntry(
            name="test-kg",
            kind=KGKind.DOC,
            repo_path="/tmp/test",
            venv_path="/tmp/test/.venv",
        )

    def _make_adapter(self, stats_dict, extra_metrics=None):
        """Build a minimal concrete KGAdapter with controlled stats and extra metrics."""
        from kg_rag.adapters.base import KGAdapter

        _stats = stats_dict
        _extra = extra_metrics or {}

        class _Adapter(KGAdapter):
            def is_available(self):
                return True

            def query(self, q, **kw):
                return []

            def pack(self, q, **kw):
                return []

            def stats(self):
                return _stats

            def analyze(self):
                return ""

            def _collect_snapshot_metrics(self):
                return _extra

        return _Adapter(self._make_entry())

    def test_snapshot_envelope_keys(self):
        adapter = self._make_adapter({"node_count": 42, "edge_count": 84})
        snap = adapter.snapshot(version="0.9.0")
        for key in ("version", "timestamp", "kind", "kg_name", "node_count", "edge_count"):
            assert key in snap, f"missing key: {key!r}"
        assert snap["version"] == "0.9.0"
        assert snap["node_count"] == 42
        assert snap["kg_name"] == "test-kg"

    def test_snapshot_merges_extra_metrics(self):
        adapter = self._make_adapter(
            {"node_count": 10, "edge_count": 20},
            extra_metrics={"chunk_count": 5, "topic_count": 3},
        )
        snap = adapter.snapshot(version="1.0.0")
        assert snap["chunk_count"] == 5
        assert snap["topic_count"] == 3

    def test_snapshot_label_is_included(self):
        adapter = self._make_adapter({"node_count": 1, "edge_count": 1})
        snap = adapter.snapshot(version="1.0", label="pre-release")
        assert snap["label"] == "pre-release"
