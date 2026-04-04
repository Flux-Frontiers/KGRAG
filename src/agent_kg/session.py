"""session.py — Session lifecycle management for AgentKG."""

from __future__ import annotations

import uuid
from datetime import UTC, datetime
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from agent_kg.store import AgentKGStore


class Session:
    """Represents one active AgentKG session.

    A session groups a set of conversation turns. Sessions persist across
    process restarts — the graph accumulates by default. Use :meth:`close`
    to record the end time; use :meth:`wipe` to clear the conversation tree.

    :param session_id: UUID string for this session.
    :param store: The :class:`~agent_kg.store.AgentKGStore` backing this session.
    """

    def __init__(self, session_id: str, store: "AgentKGStore") -> None:
        self.id = session_id
        self._store = store
        self._turn_index = 0
        self._start_time = datetime.now(UTC)

    @classmethod
    def open(cls, store: "AgentKGStore", session_id: str | None = None) -> "Session":
        """Open a new session or resume an existing one.

        :param store: The backing store.
        :param session_id: If given, resumes this session; else creates a new UUID.
        :return: A :class:`Session` instance.
        """
        sid = session_id or str(uuid.uuid4())
        existing = store.get_session(sid)
        sess = cls(sid, store)
        if existing:
            # Resume: count existing turns to set turn_index
            turns = store.get_all_turns(session_id=sid)
            sess._turn_index = max((t.turn_index for t in turns), default=0) + 1
            sess._start_time = datetime.fromisoformat(existing["start_time"])
        else:
            # New session
            store.upsert_session(
                session_id=sid,
                start_time=sess._start_time.isoformat(),
            )
        return sess

    def next_turn_index(self) -> int:
        """Return and increment the current turn counter."""
        idx = self._turn_index
        self._turn_index += 1
        return idx

    def close(self) -> None:
        """Record end_time for this session."""
        existing = self._store.get_session(self.id)
        turn_count = existing["turn_count"] if existing else self._turn_index
        pruning_passes = existing["pruning_passes"] if existing else 0
        self._store.upsert_session(
            session_id=self.id,
            start_time=self._start_time.isoformat(),
            end_time=datetime.now(UTC).isoformat(),
            turn_count=turn_count,
            pruning_passes=pruning_passes,
        )

    def record_turn(self) -> None:
        """Increment the session's turn count in storage."""
        self._store.increment_session_turns(self.id)

    def record_prune(self) -> None:
        """Increment the session's pruning pass count in storage."""
        self._store.increment_session_prune_passes(self.id)

    @property
    def turn_count(self) -> int:
        """Current number of turns in this session."""
        return self._turn_index

    def __repr__(self) -> str:
        return f"Session(id={self.id[:8]}…, turns={self._turn_index})"
