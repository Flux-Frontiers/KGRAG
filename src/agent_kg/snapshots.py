"""snapshots.py — Temporal snapshot support for AgentKG.

Captures point-in-time metrics for the conversation tree:
  - node/edge counts by kind
  - turn count, summary count, open tasks
  - pruning_pass level
  - session count

Mirrors the snapshot format used by code_kg and doc_kg.
Stored in ``<repo>/.agentkg/snapshots/<timestamp>.json``.
"""

from __future__ import annotations

import json
from datetime import UTC, datetime
from pathlib import Path
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from agent_kg.store import AgentKGStore

from agent_kg.schema import NodeKind


def capture(
    store: "AgentKGStore",
    snapshots_dir: Path,
    label: str | None = None,
    version: str = "0.1.0",
) -> dict[str, Any]:
    """Capture and persist a snapshot of the current AgentKG state.

    :param store: The backing store.
    :param snapshots_dir: Directory to write the snapshot JSON file.
    :param label: Optional human-readable label.
    :param version: Version string.
    :return: The snapshot dict (also written to disk).
    """
    s = store.stats()
    turns = store.get_all_turns()
    open_tasks = store.get_open_tasks()
    summaries = store.get_nodes_by_kind(NodeKind.SUMMARY)
    sessions = store.list_sessions()

    pruning_pass = 0
    if turns:
        pruning_pass = max(t.pruning_pass for t in turns)
    elif summaries:
        pruning_pass = max(s_.pruning_pass for s_ in summaries)

    snap: dict[str, Any] = {
        "version": version,
        "label": label,
        "timestamp": datetime.now(UTC).isoformat(),
        "kind": "agent",
        "node_count": s["node_count"],
        "edge_count": s["edge_count"],
        "kind_counts": s.get("kind_counts", {}),
        "turn_count": len(turns),
        "summary_count": len(summaries),
        "open_task_count": len(open_tasks),
        "session_count": len(sessions),
        "pruning_pass": pruning_pass,
    }

    snapshots_dir = Path(snapshots_dir)
    snapshots_dir.mkdir(parents=True, exist_ok=True)
    ts = datetime.now(UTC).strftime("%Y%m%dT%H%M%S")
    path = snapshots_dir / f"{ts}.json"
    path.write_text(json.dumps(snap, indent=2))

    return snap


def list_snapshots(snapshots_dir: Path) -> list[dict[str, Any]]:
    """Return all snapshots in ``snapshots_dir``, newest first.

    :param snapshots_dir: Directory containing snapshot JSON files.
    :return: List of snapshot dicts with an added ``path`` key.
    """
    p = Path(snapshots_dir)
    if not p.exists():
        return []
    snaps = []
    for f in sorted(p.glob("*.json"), reverse=True):
        try:
            data = json.loads(f.read_text())
            data["path"] = str(f)
            snaps.append(data)
        except Exception:  # pylint: disable=broad-exception-caught
            pass
    return snaps


def diff_snapshots(
    snap_a: dict[str, Any], snap_b: dict[str, Any]
) -> dict[str, Any]:
    """Compute deltas between two snapshots.

    :param snap_a: Earlier snapshot.
    :param snap_b: Later snapshot.
    :return: Dict of ``{field: (a_value, b_value, delta)}`` for numeric fields.
    """
    numeric_keys = ["node_count", "edge_count", "turn_count", "summary_count",
                    "open_task_count", "session_count", "pruning_pass"]
    deltas: dict[str, Any] = {}
    for key in numeric_keys:
        a = snap_a.get(key, 0)
        b = snap_b.get(key, 0)
        try:
            deltas[key] = {"before": a, "after": b, "delta": b - a}
        except TypeError:
            deltas[key] = {"before": a, "after": b, "delta": None}
    return deltas
