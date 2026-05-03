"""
snapshots.py — Backwards-compatibility re-export shim.

The canonical implementation now lives in ``kg_utils.snapshots`` (kgmodule-utils).
All existing ``from kg_rag.snapshots import ...`` call-sites continue to work.
"""

from kg_utils.snapshots import Snapshot as Snapshot  # noqa: F401
from kg_utils.snapshots import SnapshotManager as SnapshotManager  # noqa: F401
from kg_utils.snapshots import SnapshotManifest as SnapshotManifest  # noqa: F401

__all__ = ["Snapshot", "SnapshotManifest", "SnapshotManager"]
