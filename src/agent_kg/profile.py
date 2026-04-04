"""profile.py — UserProfile tree: globally persistent personal knowledge.

Stores Preference, Style, Interest, Expertise, Commitment, and Context
nodes for a person in user-scoped storage (~/.kgrag/profiles/<person_id>/).

This tree is NEVER pruned — it only grows and is updated in place.
One canonical profile exists regardless of which repo you're working in.

Syncs key fields back to KGRAG PersonCorpusEntry metadata at session close.
"""

from __future__ import annotations

import json
import sqlite3
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from agent_kg.schema import Edge, EdgeRelation, Node, NodeKind

_PROFILE_SCHEMA = """
CREATE TABLE IF NOT EXISTS profile_nodes (
    id          TEXT PRIMARY KEY,
    kind        TEXT NOT NULL,
    label       TEXT NOT NULL,
    text        TEXT DEFAULT '',
    confidence  REAL DEFAULT 1.0,
    category    TEXT DEFAULT '',
    created_at  TEXT NOT NULL,
    updated_at  TEXT NOT NULL,
    metadata    TEXT DEFAULT '{}'
);

CREATE INDEX IF NOT EXISTS idx_profile_kind ON profile_nodes(kind);

CREATE TABLE IF NOT EXISTS profile_edges (
    id         TEXT PRIMARY KEY,
    source_id  TEXT NOT NULL,
    target_id  TEXT NOT NULL,
    relation   TEXT NOT NULL,
    created_at TEXT NOT NULL
);
"""


class UserProfileStore:
    """SQLite-backed UserProfile tree for a single person.

    :param profile_dir: Path to ``~/.kgrag/profiles/<person_id>/``.
    """

    def __init__(self, profile_dir: Path) -> None:
        self._dir = Path(profile_dir)
        self._db_path = self._dir / "userprofile.sqlite"
        self._db: sqlite3.Connection | None = None

    def _get_db(self) -> sqlite3.Connection:
        if self._db is None:
            self._dir.mkdir(parents=True, exist_ok=True)
            self._db = sqlite3.connect(str(self._db_path), check_same_thread=False)
            self._db.row_factory = sqlite3.Row
            self._db.executescript(_PROFILE_SCHEMA)
            self._db.commit()
        return self._db

    # ------------------------------------------------------------------
    # Upsert
    # ------------------------------------------------------------------

    def upsert(self, kind: NodeKind, label: str, text: str = "",
               confidence: float = 1.0, category: str = "") -> Node:
        """Insert a new profile node or update confidence + text if label exists.

        :param kind: NodeKind (PREFERENCE, EXPERTISE, INTEREST, etc.)
        :param label: Short canonical label for this fact.
        :param text: Full original text for provenance.
        :param confidence: Confidence score 0–1.
        :param category: Optional sub-category.
        :return: The upserted Node.
        """
        import uuid  # noqa: PLC0415
        db = self._get_db()
        now = datetime.now(UTC).isoformat()

        # Check for existing node with same kind + label (case-insensitive)
        row = db.execute(
            "SELECT * FROM profile_nodes WHERE kind = ? AND LOWER(label) = LOWER(?)",
            (str(kind), label),
        ).fetchone()

        if row:
            # Update confidence and text
            new_conf = min(1.0, max(float(row["confidence"]), confidence))
            db.execute(
                "UPDATE profile_nodes SET confidence = ?, text = ?, updated_at = ? WHERE id = ?",
                (new_conf, text or row["text"], now, row["id"]),
            )
            db.commit()
            return self._row_to_node(dict(row))
        else:
            node_id = str(uuid.uuid4())
            db.execute(
                """INSERT INTO profile_nodes
                   (id, kind, label, text, confidence, category, created_at, updated_at)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                (node_id, str(kind), label, text, confidence, category, now, now),
            )
            db.commit()
            return Node(
                id=node_id, kind=kind, label=label, text=text,
                confidence=confidence, category=category,
            )

    def apply_updates(self, updates: list[dict[str, Any]]) -> list[Node]:
        """Apply a batch of NLP-extracted preference/commitment/expertise records.

        Each dict must have ``kind``, ``label``, and ``text`` keys.

        :param updates: List of ``{"kind", "label", "text"}`` dicts from
                        :func:`~agent_kg.nlp.preferences.extract_preferences`.
        :return: List of upserted nodes.
        """
        _KIND_MAP = {
            "preference": NodeKind.PREFERENCE,
            "style": NodeKind.STYLE,
            "interest": NodeKind.INTEREST,
            "expertise": NodeKind.EXPERTISE,
            "commitment": NodeKind.COMMITMENT,
            "context": NodeKind.CONTEXT,
        }
        nodes = []
        for u in updates:
            kind_key = u.get("kind", "preference")
            node_kind = _KIND_MAP.get(kind_key, NodeKind.PREFERENCE)
            node = self.upsert(
                kind=node_kind,
                label=u["label"],
                text=u.get("text", u["label"]),
            )
            nodes.append(node)
        return nodes

    # ------------------------------------------------------------------
    # Query
    # ------------------------------------------------------------------

    def get_by_kind(self, kind: NodeKind) -> list[Node]:
        """Return all profile nodes of a given kind."""
        rows = self._get_db().execute(
            "SELECT * FROM profile_nodes WHERE kind = ? ORDER BY confidence DESC",
            (str(kind),),
        ).fetchall()
        return [self._row_to_node(dict(r)) for r in rows]

    def preferences(self) -> list[Node]:
        return self.get_by_kind(NodeKind.PREFERENCE)

    def commitments(self) -> list[Node]:
        return self.get_by_kind(NodeKind.COMMITMENT)

    def expertise(self) -> list[Node]:
        return self.get_by_kind(NodeKind.EXPERTISE)

    def interests(self) -> list[Node]:
        return self.get_by_kind(NodeKind.INTEREST)

    def styles(self) -> list[Node]:
        return self.get_by_kind(NodeKind.STYLE)

    def all_nodes(self) -> list[Node]:
        """Return all profile nodes ordered by kind + confidence."""
        rows = self._get_db().execute(
            "SELECT * FROM profile_nodes ORDER BY kind, confidence DESC"
        ).fetchall()
        return [self._row_to_node(dict(r)) for r in rows]

    def summary(self) -> dict[str, Any]:
        """Return a structured summary of the profile (for PersonCorpusEntry sync)."""
        return {
            "preferences": [n.label for n in self.preferences()],
            "commitments": [n.label for n in self.commitments()],
            "expertise": [n.label for n in self.expertise()],
            "interests": [n.label for n in self.interests()],
            "styles": [n.label for n in self.styles()],
        }

    def render_markdown(self) -> str:
        """Render the full UserProfile as a Markdown report."""
        lines = ["# UserProfile\n"]
        sections = [
            ("Commitments", self.commitments()),
            ("Preferences", self.preferences()),
            ("Expertise", self.expertise()),
            ("Interests", self.interests()),
            ("Style", self.styles()),
        ]
        for title, nodes in sections:
            if nodes:
                lines.append(f"## {title}")
                for n in nodes:
                    conf_pct = int(n.confidence * 100)
                    lines.append(f"- {n.label} *(confidence: {conf_pct}%)*")
                lines.append("")
        return "\n".join(lines)

    def stats(self) -> dict[str, Any]:
        db = self._get_db()
        count = db.execute("SELECT COUNT(*) FROM profile_nodes").fetchone()[0]
        kind_counts: dict[str, int] = {}
        for row in db.execute("SELECT kind, COUNT(*) FROM profile_nodes GROUP BY kind"):
            kind_counts[row[0]] = row[1]
        return {"total": count, "by_kind": kind_counts}

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _row_to_node(self, r: dict) -> Node:
        def _dt(s):
            try:
                return datetime.fromisoformat(s)
            except Exception:  # pylint: disable=broad-exception-caught
                return datetime.now(UTC)

        return Node(
            id=r["id"],
            kind=NodeKind(r["kind"]),
            label=r.get("label", ""),
            text=r.get("text", ""),
            confidence=r.get("confidence", 1.0),
            category=r.get("category", ""),
            created_at=_dt(r.get("created_at")),
            updated_at=_dt(r.get("updated_at")),
            metadata=json.loads(r.get("metadata", "{}")),
        )

    def close(self) -> None:
        if self._db:
            self._db.close()
            self._db = None
