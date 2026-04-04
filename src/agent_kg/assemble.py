"""assemble.py — Context assembly for AgentKG.

Implements the KG-based context assembly strategy that defeats context rot:
  1. Semantic retrieval — find nodes relevant to the current query
  2. Temporal spine — include the most recent N turns verbatim
  3. Open tasks — always include open Task nodes
  4. Token budget — pack in priority order until budget is reached

The result is a Markdown string ready for injection into a model's context,
structured to preserve decisions and open commitments while staying token-bounded.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from agent_kg.schema import NodeKind

if TYPE_CHECKING:
    from agent_kg.store import AgentKGStore

_RECENT_WINDOW = 6   # verbatim recent turns always included
_CHARS_PER_TOKEN = 4  # rough approximation


def _approx_tokens(text: str) -> int:
    return max(1, len(text) // _CHARS_PER_TOKEN)


def assemble_context(
    store: "AgentKGStore",
    query: str,
    budget: int = 4000,
    recent_window: int = _RECENT_WINDOW,
    session_id: str | None = None,
) -> str:
    """Assemble a token-budgeted context block from the conversation graph.

    :param store: The backing :class:`~agent_kg.store.AgentKGStore`.
    :param query: The current user query (used for semantic retrieval).
    :param budget: Approximate token budget for the assembled context.
    :param recent_window: Number of most-recent turns to always include verbatim.
    :param session_id: Restrict recent turns to this session (None = all).
    :return: Markdown-formatted context string.
    """
    parts: list[str] = []
    tokens_used = 0

    def _add(text: str) -> bool:
        nonlocal tokens_used
        cost = _approx_tokens(text)
        if tokens_used + cost > budget:
            return False
        parts.append(text)
        tokens_used += cost
        return True

    # ------------------------------------------------------------------
    # 1. Open tasks — always include (commitment preservation)
    # ------------------------------------------------------------------
    open_tasks = store.get_open_tasks()
    if open_tasks:
        task_lines = [f"- {t.label or t.text}" for t in open_tasks[:10]]
        _add("## Open Tasks\n" + "\n".join(task_lines))

    # ------------------------------------------------------------------
    # 2. Semantically relevant summaries (compressed old context)
    # ------------------------------------------------------------------
    summaries = store.search(query, k=4, kind_filter=str(NodeKind.SUMMARY))
    if summaries:
        summary_texts = []
        for s in summaries:
            node = store.get_node(s["node_id"])
            if node and node.text:
                summary_texts.append(f"**Summary**: {node.text}")
        if summary_texts:
            _add("## Relevant Context (Compressed)\n" + "\n\n".join(summary_texts))

    # ------------------------------------------------------------------
    # 3. Semantically relevant turns (not recent)
    # ------------------------------------------------------------------
    recent_turns = store.get_all_turns(session_id=session_id)[-recent_window:]
    recent_ids = {t.id for t in recent_turns}

    sem_hits = store.search(query, k=6, kind_filter=str(NodeKind.TURN))
    sem_turns = []
    for h in sem_hits:
        if h["node_id"] not in recent_ids:
            node = store.get_node(h["node_id"])
            if node:
                sem_turns.append(node)

    if sem_turns:
        sem_lines = []
        for t in sem_turns[:4]:
            role_label = t.role.upper() if t.role else "UNKNOWN"
            sem_lines.append(f"**[{role_label}]** {t.text[:300]}")
        _add("## Relevant Past Turns\n" + "\n\n".join(sem_lines))

    # ------------------------------------------------------------------
    # 4. Active topics
    # ------------------------------------------------------------------
    topic_hits = store.search(query, k=5, kind_filter=str(NodeKind.TOPIC))
    if topic_hits:
        topic_labels = []
        for h in topic_hits:
            node = store.get_node(h["node_id"])
            if node:
                topic_labels.append(node.label or node.text)
        if topic_labels:
            _add("## Active Topics\n" + ", ".join(topic_labels[:8]))

    # ------------------------------------------------------------------
    # 5. Verbatim recent turns — search ALL sessions (CLI calls each create
    #    a new session; we want the most recent turns regardless of session)
    # ------------------------------------------------------------------
    recent_turns = store.get_all_turns(session_id=None)[-recent_window:]
    if recent_turns:
        recent_lines = []
        for t in recent_turns:
            role_label = t.role.upper() if t.role else "UNKNOWN"
            recent_lines.append(f"**[{role_label}]** {t.text}")
        _add("## Recent Conversation\n" + "\n\n".join(recent_lines))

    if not parts:
        return "_No conversation context available yet._"

    header = f"# AgentKG Context (~{tokens_used} tokens)\n"
    return header + "\n\n".join(parts)
