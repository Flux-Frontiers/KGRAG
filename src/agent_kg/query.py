"""query.py — Semantic query and snippet pack for AgentKG.

Delegates to the LanceDB semantic index in AgentKGStore.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from agent_kg.schema import NodeKind

if TYPE_CHECKING:
    from agent_kg.store import AgentKGStore


def query(
    store: "AgentKGStore",
    q: str,
    k: int = 8,
    kind_filter: str | None = None,
) -> list[dict[str, Any]]:
    """Semantic query over the conversation graph.

    :param store: The backing store.
    :param q: Natural-language query string.
    :param k: Number of results.
    :param kind_filter: Optional NodeKind string to restrict results.
    :return: List of ``{node_id, kind, text, session_id, score}`` dicts,
             enriched with full node data from SQLite.
    """
    hits = store.search(q, k=k, kind_filter=kind_filter)
    enriched = []
    for h in hits:
        node = store.get_node(h["node_id"])
        if node:
            enriched.append({
                "node_id": h["node_id"],
                "kind": h["kind"],
                "text": node.text or node.label,
                "label": node.label,
                "role": node.role,
                "turn_index": node.turn_index,
                "session_id": h["session_id"],
                "score": h["score"],
                "status": node.status,
                "created_at": node.created_at.isoformat(),
            })
        else:
            enriched.append(h)
    return enriched


def pack(
    store: "AgentKGStore",
    q: str,
    k: int = 8,
) -> list[dict[str, Any]]:
    """Retrieve conversation snippets for LLM context packing.

    Returns formatted text blocks ready for injection into a prompt,
    prioritising Summaries and Turns over structural nodes.

    :param store: The backing store.
    :param q: Natural-language query string.
    :param k: Number of snippets to return.
    :return: List of ``{node_id, kind, content, score}`` dicts.
    """
    results = []
    # Prefer summaries first (they represent compressed history)
    summaries = store.search(q, k=k // 2 + 1, kind_filter=str(NodeKind.SUMMARY))
    turns = store.search(q, k=k, kind_filter=str(NodeKind.TURN))

    seen: set[str] = set()

    def _add(hits: list[dict], prefix: str = "") -> None:
        for h in hits:
            if h["node_id"] in seen or len(results) >= k:
                return
            seen.add(h["node_id"])
            node = store.get_node(h["node_id"])
            content = node.text if node else h.get("text", "")
            if prefix and node and node.role:
                content = f"[{node.role.upper()}] {content}"
            results.append({
                "node_id": h["node_id"],
                "kind": h["kind"],
                "content": content,
                "score": h["score"],
            })

    _add(summaries, prefix="summary")
    _add(turns, prefix="turn")

    # Fill remaining slots with any other relevant nodes
    if len(results) < k:
        others = store.search(q, k=k - len(results))
        _add(others)

    return results
