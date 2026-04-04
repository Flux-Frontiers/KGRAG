"""schema.py — AgentKG node and edge type definitions."""

from __future__ import annotations

import json
import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import StrEnum
from typing import Any


class NodeKind(StrEnum):
    """Node types in the AgentKG conversation and UserProfile trees."""

    # Conversation tree
    TURN = "turn"
    TOPIC = "topic"
    INTENT = "intent"
    ENTITY = "entity"
    TASK = "task"
    SUMMARY = "summary"
    # UserProfile tree
    PREFERENCE = "preference"
    STYLE = "style"
    INTEREST = "interest"
    EXPERTISE = "expertise"
    COMMITMENT = "commitment"
    CONTEXT = "context"
    USER_PROFILE = "user_profile"
    # Project scope
    PROJECT_CONTEXT = "project_context"


class EdgeRelation(StrEnum):
    """Edge relation types for both conversation and UserProfile trees."""

    # Conversation tree
    FOLLOWS = "FOLLOWS"
    ADDRESSES = "ADDRESSES"
    EXPRESSES = "EXPRESSES"
    MENTIONS = "MENTIONS"
    CREATES = "CREATES"
    RESOLVES = "RESOLVES"
    RELATED_TO = "RELATED_TO"
    REFERENCES = "REFERENCES"
    COMPRESSED_INTO = "COMPRESSED_INTO"
    EXPANDS = "EXPANDS"
    # UserProfile tree
    PREFERS = "PREFERS"
    INTERESTED_IN = "INTERESTED_IN"
    EXPERT_IN = "EXPERT_IN"
    COMMITTED_TO = "COMMITTED_TO"
    UPDATED_BY = "UPDATED_BY"
    CONFLICTS_WITH = "CONFLICTS_WITH"
    HAS_CONTEXT = "HAS_CONTEXT"


class TaskStatus(StrEnum):
    """Task lifecycle states."""

    OPEN = "open"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    ABANDONED = "abandoned"


class IntentCategory(StrEnum):
    """Classified intent categories for Turn nodes."""

    QUESTION = "question"
    REQUEST = "request"
    CORRECTION = "correction"
    CONFIRMATION = "confirmation"
    CLARIFICATION = "clarification"
    CONTEXT = "context"
    FEEDBACK = "feedback"
    UNKNOWN = "unknown"


def _now() -> datetime:
    return datetime.now(UTC)


def _new_id() -> str:
    return str(uuid.uuid4())


@dataclass
class Node:
    """A node in the AgentKG graph.

    Used for all node kinds: Turn, Topic, Intent, Entity, Task, Summary,
    Preference, Style, Interest, Expertise, Commitment, Context.

    :param kind: Node type from NodeKind.
    :param id: UUID string (auto-generated).
    :param label: Short display label (e.g. topic name, entity name).
    :param text: Full text content (e.g. turn text, summary text).
    :param role: ``"user"`` or ``"assistant"`` for Turn nodes.
    :param turn_index: Ordinal position in conversation (Turn nodes).
    :param token_count: Approximate token count (Turn nodes).
    :param status: Task lifecycle status (Task nodes).
    :param category: Intent category string (Intent nodes).
    :param source: Entity provenance kind (Entity nodes).
    :param confidence: Confidence score 0–1 (Preference/learned nodes).
    :param covers_turns: Turn IDs compressed into this Summary.
    :param pruning_pass: Number of pruning passes this node has survived.
    :param session_id: ID of the session that created this node.
    """

    kind: NodeKind
    id: str = field(default_factory=_new_id)
    label: str = ""
    text: str = ""
    role: str = ""
    turn_index: int = 0
    token_count: int = 0
    status: str = ""
    category: str = ""
    source: str = ""
    confidence: float = 1.0
    covers_turns: list[str] = field(default_factory=list)
    pruning_pass: int = 0
    session_id: str = ""
    first_seen: datetime = field(default_factory=_now)
    last_seen: datetime = field(default_factory=_now)
    created_at: datetime = field(default_factory=_now)
    updated_at: datetime = field(default_factory=_now)
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        """Serialize to a flat dict suitable for SQLite insertion."""
        return {
            "id": self.id,
            "kind": str(self.kind),
            "label": self.label,
            "text": self.text,
            "role": self.role,
            "turn_index": self.turn_index,
            "token_count": self.token_count,
            "status": self.status,
            "category": self.category,
            "source": self.source,
            "confidence": self.confidence,
            "covers_turns": json.dumps(self.covers_turns),
            "pruning_pass": self.pruning_pass,
            "session_id": self.session_id,
            "first_seen": self.first_seen.isoformat(),
            "last_seen": self.last_seen.isoformat(),
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "metadata": json.dumps(self.metadata),
        }

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> Node:
        """Deserialize from a SQLite row dict."""
        def _dt(s: str | None) -> datetime:
            try:
                return datetime.fromisoformat(s) if s else _now()
            except Exception:
                return _now()

        return cls(
            id=d["id"],
            kind=NodeKind(d["kind"]),
            label=d.get("label", ""),
            text=d.get("text", ""),
            role=d.get("role", ""),
            turn_index=d.get("turn_index", 0),
            token_count=d.get("token_count", 0),
            status=d.get("status", ""),
            category=d.get("category", ""),
            source=d.get("source", ""),
            confidence=d.get("confidence", 1.0),
            covers_turns=json.loads(d.get("covers_turns", "[]")),
            pruning_pass=d.get("pruning_pass", 0),
            session_id=d.get("session_id", ""),
            first_seen=_dt(d.get("first_seen")),
            last_seen=_dt(d.get("last_seen")),
            created_at=_dt(d.get("created_at")),
            updated_at=_dt(d.get("updated_at")),
            metadata=json.loads(d.get("metadata", "{}")),
        )


@dataclass
class Edge:
    """A directed edge in the AgentKG graph.

    :param source_id: Source node ID.
    :param target_id: Target node ID.
    :param relation: Relationship type from EdgeRelation.
    :param id: UUID string (auto-generated).
    :param weight: Edge weight (default 1.0).
    :param metadata: Extra key-value data.
    :param created_at: Creation timestamp.
    """

    source_id: str
    target_id: str
    relation: EdgeRelation | str
    id: str = field(default_factory=_new_id)
    weight: float = 1.0
    metadata: dict[str, Any] = field(default_factory=dict)
    created_at: datetime = field(default_factory=_now)

    def to_dict(self) -> dict[str, Any]:
        """Serialize to a flat dict for SQLite insertion."""
        return {
            "id": self.id,
            "source_id": self.source_id,
            "target_id": self.target_id,
            "relation": str(self.relation),
            "weight": self.weight,
            "metadata": json.dumps(self.metadata),
            "created_at": self.created_at.isoformat(),
        }


@dataclass
class PruneReport:
    """Result of a KG Context Pruning pass.

    :param summaries_created: Number of Summary nodes created.
    :param turns_pruned: Number of Turn nodes removed.
    :param nodes_removed: Total nodes removed.
    :param pruning_pass: The pruning pass index after this run.
    :param token_savings_approx: Estimated token reduction.
    """

    summaries_created: int
    turns_pruned: int
    nodes_removed: int
    pruning_pass: int
    token_savings_approx: int = 0
