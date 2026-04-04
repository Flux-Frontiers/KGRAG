"""consolidate.py — Phase 2 background consolidation for AgentKG.

Triggered when turn count exceeds a threshold (default: 20) or explicitly:
  - Re-embed any nodes with missing/stale vectors
  - Recompute RELATED_TO edges between Topic nodes
  - Update Task statuses based on RESOLVES edge analysis
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from agent_kg.schema import EdgeRelation, NodeKind, TaskStatus

if TYPE_CHECKING:
    from agent_kg.store import AgentKGStore

_CONSOLIDATE_THRESHOLD = 20  # turns before consolidation is triggered


def consolidate(
    store: "AgentKGStore",
    session_id: str | None = None,
    force: bool = False,
) -> dict[str, Any]:
    """Run a Phase 2 consolidation pass.

    :param store: The backing store.
    :param session_id: Restrict to a specific session (None = all).
    :param force: Run even if below the threshold.
    :return: Report dict with ``nodes_embedded``, ``edges_created``, ``tasks_updated``.
    """
    report: dict[str, Any] = {
        "nodes_embedded": 0,
        "edges_created": 0,
        "tasks_updated": 0,
    }

    # Check threshold
    all_turns = store.get_all_turns(session_id=session_id)
    if not force and len(all_turns) < _CONSOLIDATE_THRESHOLD:
        return report

    # ------------------------------------------------------------------
    # 1. Re-embed nodes that may lack embeddings (best-effort)
    # ------------------------------------------------------------------
    for kind in (NodeKind.TURN, NodeKind.TOPIC, NodeKind.ENTITY, NodeKind.SUMMARY):
        nodes = store.get_nodes_by_kind(kind, session_id=session_id)
        for node in nodes:
            if node.text or node.label:
                try:
                    store.embed_node(node)
                    report["nodes_embedded"] += 1
                except Exception:  # pylint: disable=broad-exception-caught
                    pass

    # ------------------------------------------------------------------
    # 2. Recompute RELATED_TO edges between Topic nodes
    # ------------------------------------------------------------------
    try:
        new_edges = store.refresh_related_to_edges(threshold=0.75)
        report["edges_created"] += new_edges
    except Exception:  # pylint: disable=broad-exception-caught
        pass

    # ------------------------------------------------------------------
    # 3. Update Task statuses: mark tasks completed if RESOLVES edge exists
    # ------------------------------------------------------------------
    tasks = store.get_nodes_by_kind(NodeKind.TASK)
    for task in tasks:
        if task.status == str(TaskStatus.OPEN):
            resolving_edges = store.get_edges(target_id=task.id, relation=str(EdgeRelation.RESOLVES))
            if resolving_edges:
                store.update_node_field(task.id, "status", str(TaskStatus.COMPLETED))
                report["tasks_updated"] += 1

    return report


def should_consolidate(store: "AgentKGStore", session_id: str | None = None) -> bool:
    """Return True if a consolidation pass is warranted.

    :param store: The backing store.
    :param session_id: Restrict to a specific session.
    :return: True if turn count exceeds the threshold.
    """
    turns = store.get_all_turns(session_id=session_id)
    return len(turns) >= _CONSOLIDATE_THRESHOLD
