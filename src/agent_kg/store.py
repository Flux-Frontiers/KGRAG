"""store.py — SQLite + LanceDB storage for the AgentKG conversation tree."""

from __future__ import annotations

import sqlite3
from pathlib import Path
from typing import Any

from agent_kg.schema import Edge, EdgeRelation, Node, NodeKind

_SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS nodes (
    id            TEXT PRIMARY KEY,
    kind          TEXT NOT NULL,
    label         TEXT DEFAULT '',
    text          TEXT DEFAULT '',
    role          TEXT DEFAULT '',
    turn_index    INTEGER DEFAULT 0,
    token_count   INTEGER DEFAULT 0,
    status        TEXT DEFAULT '',
    category      TEXT DEFAULT '',
    source        TEXT DEFAULT '',
    confidence    REAL DEFAULT 1.0,
    covers_turns  TEXT DEFAULT '[]',
    pruning_pass  INTEGER DEFAULT 0,
    session_id    TEXT DEFAULT '',
    first_seen    TEXT NOT NULL,
    last_seen     TEXT NOT NULL,
    created_at    TEXT NOT NULL,
    updated_at    TEXT NOT NULL,
    metadata      TEXT DEFAULT '{}'
);

CREATE TABLE IF NOT EXISTS edges (
    id         TEXT PRIMARY KEY,
    source_id  TEXT NOT NULL REFERENCES nodes(id) ON DELETE CASCADE,
    target_id  TEXT NOT NULL REFERENCES nodes(id) ON DELETE CASCADE,
    relation   TEXT NOT NULL,
    weight     REAL DEFAULT 1.0,
    metadata   TEXT DEFAULT '{}',
    created_at TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_nodes_kind      ON nodes(kind);
CREATE INDEX IF NOT EXISTS idx_nodes_session   ON nodes(session_id);
CREATE INDEX IF NOT EXISTS idx_nodes_turn_idx  ON nodes(turn_index);
CREATE INDEX IF NOT EXISTS idx_edges_source    ON edges(source_id);
CREATE INDEX IF NOT EXISTS idx_edges_target    ON edges(target_id);
CREATE INDEX IF NOT EXISTS idx_edges_relation  ON edges(relation);

CREATE TABLE IF NOT EXISTS sessions (
    id              TEXT PRIMARY KEY,
    start_time      TEXT NOT NULL,
    end_time        TEXT,
    turn_count      INTEGER DEFAULT 0,
    pruning_passes  INTEGER DEFAULT 0,
    metadata        TEXT DEFAULT '{}'
);
"""

_EMBED_DIM = 384
_EMBED_MODEL = "all-MiniLM-L6-v2"


class AgentKGStore:
    """Two-layer storage: SQLite for graph topology + LanceDB for embeddings.

    :param db_path: Path to the SQLite ``.db`` file.
    :param lancedb_dir: Directory for the LanceDB vector store.
    :param embed_model: sentence-transformers model name for embeddings.
    """

    def __init__(
        self,
        db_path: Path,
        lancedb_dir: Path,
        embed_model: str = _EMBED_MODEL,
    ) -> None:
        self._db_path = Path(db_path)
        self._lancedb_dir = Path(lancedb_dir)
        self._embed_model_name = embed_model
        self._db: sqlite3.Connection | None = None
        self._ldb = None
        self._tbl = None
        self._embedder = None

    # ------------------------------------------------------------------
    # Lazy init
    # ------------------------------------------------------------------

    def _get_db(self) -> sqlite3.Connection:
        if self._db is None:
            self._db_path.parent.mkdir(parents=True, exist_ok=True)
            self._db = sqlite3.connect(str(self._db_path), check_same_thread=False)
            self._db.row_factory = sqlite3.Row
            self._db.executescript(_SCHEMA_SQL)
            self._db.commit()
        return self._db

    def _get_table(self):
        if self._tbl is not None:
            return self._tbl
        try:
            import lancedb  # noqa: PLC0415
            import pyarrow as pa  # noqa: PLC0415
        except ImportError as exc:
            raise ImportError("lancedb and pyarrow are required for AgentKG embeddings") from exc

        self._lancedb_dir.mkdir(parents=True, exist_ok=True)
        self._ldb = lancedb.connect(str(self._lancedb_dir))
        schema = pa.schema([
            pa.field("node_id", pa.utf8()),
            pa.field("kind", pa.utf8()),
            pa.field("text", pa.utf8()),
            pa.field("session_id", pa.utf8()),
            pa.field("vector", pa.list_(pa.float32(), _EMBED_DIM)),
        ])
        if "nodes" in self._ldb.table_names():
            self._tbl = self._ldb.open_table("nodes")
        else:
            self._tbl = self._ldb.create_table("nodes", schema=schema)
        return self._tbl

    def _get_embedder(self):
        if self._embedder is None:
            from sentence_transformers import SentenceTransformer  # noqa: PLC0415
            self._embedder = SentenceTransformer(self._embed_model_name)
        return self._embedder

    def embed(self, text: str) -> list[float]:
        """Return a normalized sentence embedding for ``text``."""
        vec = self._get_embedder().encode(text, normalize_embeddings=True)
        return vec.tolist()

    # ------------------------------------------------------------------
    # Node CRUD
    # ------------------------------------------------------------------

    def upsert_node(self, node: Node) -> None:
        """Insert or replace a node (SQLite only — call embed_node separately)."""
        db = self._get_db()
        d = node.to_dict()
        cols = ", ".join(d.keys())
        placeholders = ", ".join(["?"] * len(d))
        db.execute(f"INSERT OR REPLACE INTO nodes ({cols}) VALUES ({placeholders})", list(d.values()))
        db.commit()

    def embed_node(self, node: Node) -> None:
        """Compute and upsert the embedding for ``node`` into LanceDB.

        Silently skips if the embedding model or LanceDB is unavailable.
        """
        text = (node.text or node.label).strip()
        if not text:
            return
        try:
            vector = self.embed(text)
        except (ImportError, Exception):  # pylint: disable=broad-exception-caught
            return  # embedding is best-effort; SQLite always written
        tbl = self._get_table()
        try:
            tbl.delete(f"node_id = '{node.id}'")
        except Exception:  # pylint: disable=broad-exception-caught
            pass
        tbl.add([{
            "node_id": node.id,
            "kind": str(node.kind),
            "text": text[:500],
            "session_id": node.session_id,
            "vector": vector,
        }])

    def upsert_node_with_embedding(self, node: Node) -> None:
        """Write to SQLite and LanceDB in one call."""
        self.upsert_node(node)
        self.embed_node(node)

    def get_node(self, node_id: str) -> Node | None:
        """Retrieve a single node by ID."""
        row = self._get_db().execute("SELECT * FROM nodes WHERE id = ?", (node_id,)).fetchone()
        return Node.from_dict(dict(row)) if row else None

    def get_nodes_by_kind(self, kind: NodeKind, session_id: str | None = None) -> list[Node]:
        """Return all nodes of ``kind``, optionally filtered to one session."""
        db = self._get_db()
        if session_id:
            rows = db.execute(
                "SELECT * FROM nodes WHERE kind = ? AND session_id = ? ORDER BY turn_index, created_at",
                (str(kind), session_id),
            ).fetchall()
        else:
            rows = db.execute(
                "SELECT * FROM nodes WHERE kind = ? ORDER BY turn_index, created_at",
                (str(kind),),
            ).fetchall()
        return [Node.from_dict(dict(r)) for r in rows]

    def get_all_turns(self, session_id: str | None = None) -> list[Node]:
        """Return Turn nodes ordered by turn_index."""
        return self.get_nodes_by_kind(NodeKind.TURN, session_id=session_id)

    def get_open_tasks(self) -> list[Node]:
        """Return all Task nodes with status = 'open'."""
        rows = self._get_db().execute(
            "SELECT * FROM nodes WHERE kind = ? AND status = 'open' ORDER BY created_at",
            (str(NodeKind.TASK),),
        ).fetchall()
        return [Node.from_dict(dict(r)) for r in rows]

    def update_node_field(self, node_id: str, field: str, value: Any) -> None:
        """Update a single field on an existing node."""
        from datetime import UTC, datetime  # noqa: PLC0415
        db = self._get_db()
        db.execute(
            f"UPDATE nodes SET {field} = ?, updated_at = ? WHERE id = ?",
            (value, datetime.now(UTC).isoformat(), node_id),
        )
        db.commit()

    def delete_nodes(self, node_ids: list[str]) -> None:
        """Delete nodes (CASCADE removes their edges) from SQLite + LanceDB."""
        if not node_ids:
            return
        db = self._get_db()
        placeholders = ",".join(["?"] * len(node_ids))
        db.execute(f"DELETE FROM nodes WHERE id IN ({placeholders})", node_ids)
        db.commit()
        try:
            tbl = self._get_table()
            for nid in node_ids:
                tbl.delete(f"node_id = '{nid}'")
        except Exception:  # pylint: disable=broad-exception-caught
            pass

    def find_similar_node(
        self, text: str, kind: NodeKind, threshold: float = 0.88
    ) -> Node | None:
        """Return an existing node of ``kind`` whose embedding is within
        ``threshold`` cosine similarity of ``text``, or None.

        Used for entity/topic deduplication during ingest.
        """
        try:
            tbl = self._get_table()
            vector = self.embed(text)
            results = tbl.search(vector).where(f"kind = '{kind}'").limit(1).to_list()
            if not results:
                return None
            distance = results[0].get("_distance", 1.0)
            similarity = 1.0 - distance
            if similarity >= threshold:
                return self.get_node(results[0]["node_id"])
        except Exception:  # pylint: disable=broad-exception-caught
            pass
        return None

    # ------------------------------------------------------------------
    # Edge CRUD
    # ------------------------------------------------------------------

    def add_edge(self, edge: Edge) -> None:
        """Insert an edge; silently ignored if it already exists."""
        db = self._get_db()
        d = edge.to_dict()
        cols = ", ".join(d.keys())
        placeholders = ", ".join(["?"] * len(d))
        db.execute(f"INSERT OR IGNORE INTO edges ({cols}) VALUES ({placeholders})", list(d.values()))
        db.commit()

    def get_edges(
        self,
        source_id: str | None = None,
        target_id: str | None = None,
        relation: str | None = None,
    ) -> list[Edge]:
        """Query edges; all parameters are optional AND-combined filters."""
        db = self._get_db()
        conditions, params = [], []
        if source_id:
            conditions.append("source_id = ?")
            params.append(source_id)
        if target_id:
            conditions.append("target_id = ?")
            params.append(target_id)
        if relation:
            conditions.append("relation = ?")
            params.append(relation)
        where = f"WHERE {' AND '.join(conditions)}" if conditions else ""
        rows = db.execute(f"SELECT * FROM edges {where}", params).fetchall()
        return [_row_to_edge(dict(r)) for r in rows]

    # ------------------------------------------------------------------
    # Semantic search (the `index` interface)
    # ------------------------------------------------------------------

    def search(
        self, query: str, k: int = 8, kind_filter: str | None = None
    ) -> list[dict[str, Any]]:
        """Semantic search over embedded nodes.

        :param query: Natural-language query string.
        :param k: Maximum results to return.
        :param kind_filter: Restrict to a specific node kind string.
        :return: List of ``{node_id, kind, text, session_id, score}`` dicts.
        """
        try:
            tbl = self._get_table()
            vector = self.embed(query)
            searcher = tbl.search(vector).limit(k * 3)
            if kind_filter:
                searcher = searcher.where(f"kind = '{kind_filter}'")
            results = searcher.to_list()
            hits = []
            for r in results:
                hits.append({
                    "node_id": r["node_id"],
                    "kind": r["kind"],
                    "text": r["text"],
                    "session_id": r.get("session_id", ""),
                    "score": float(max(0.0, 1.0 - r.get("_distance", 1.0))),
                })
                if len(hits) >= k:
                    break
            return hits
        except Exception:  # pylint: disable=broad-exception-caught
            return []

    # ------------------------------------------------------------------
    # Stats
    # ------------------------------------------------------------------

    def stats(self) -> dict[str, Any]:
        """Return node count, edge count, and per-kind breakdown."""
        db = self._get_db()
        node_count = db.execute("SELECT COUNT(*) FROM nodes").fetchone()[0]
        edge_count = db.execute("SELECT COUNT(*) FROM edges").fetchone()[0]
        kind_counts: dict[str, int] = {}
        for row in db.execute("SELECT kind, COUNT(*) FROM nodes GROUP BY kind"):
            kind_counts[row[0]] = row[1]
        return {
            "node_count": node_count,
            "nodes": node_count,
            "edge_count": edge_count,
            "edges": edge_count,
            "kind_counts": kind_counts,
            "kind": "agent",
        }

    # ------------------------------------------------------------------
    # Session management
    # ------------------------------------------------------------------

    def upsert_session(
        self,
        session_id: str,
        start_time: str,
        end_time: str | None = None,
        turn_count: int = 0,
        pruning_passes: int = 0,
    ) -> None:
        """Insert or update a session record."""
        db = self._get_db()
        db.execute(
            """INSERT OR REPLACE INTO sessions
               (id, start_time, end_time, turn_count, pruning_passes)
               VALUES (?, ?, ?, ?, ?)""",
            (session_id, start_time, end_time, turn_count, pruning_passes),
        )
        db.commit()

    def get_session(self, session_id: str) -> dict | None:
        """Return a session record dict or None."""
        row = self._get_db().execute(
            "SELECT * FROM sessions WHERE id = ?", (session_id,)
        ).fetchone()
        return dict(row) if row else None

    def list_sessions(self) -> list[dict]:
        """Return all sessions ordered by start_time."""
        rows = self._get_db().execute(
            "SELECT * FROM sessions ORDER BY start_time"
        ).fetchall()
        return [dict(r) for r in rows]

    def increment_session_turns(self, session_id: str) -> None:
        """Atomically increment turn_count for a session."""
        self._get_db().execute(
            "UPDATE sessions SET turn_count = turn_count + 1 WHERE id = ?", (session_id,)
        )
        self._get_db().commit()

    def increment_session_prune_passes(self, session_id: str) -> None:
        """Atomically increment pruning_passes for a session."""
        self._get_db().execute(
            "UPDATE sessions SET pruning_passes = pruning_passes + 1 WHERE id = ?", (session_id,)
        )
        self._get_db().commit()

    # ------------------------------------------------------------------
    # Maintenance
    # ------------------------------------------------------------------

    def refresh_related_to_edges(self, threshold: float = 0.75) -> int:
        """Re-compute RELATED_TO edges between Topic nodes.

        Returns the number of new edges created.
        """
        topics = self.get_nodes_by_kind(NodeKind.TOPIC)
        if len(topics) < 2:
            return 0
        try:
            tbl = self._get_table()
        except Exception:  # pylint: disable=broad-exception-caught
            return 0
        created = 0
        for i, t1 in enumerate(topics):
            for t2 in topics[i + 1:]:
                v1 = self.embed(t1.label or t1.text)
                v2 = self.embed(t2.label or t2.text)
                sim = float(sum(a * b for a, b in zip(v1, v2)))
                if sim >= threshold:
                    edge = Edge(source_id=t1.id, target_id=t2.id, relation=EdgeRelation.RELATED_TO, weight=sim)
                    self.add_edge(edge)
                    created += 1
        return created

    def close(self) -> None:
        """Close all open database connections."""
        if self._db:
            self._db.close()
            self._db = None


# ------------------------------------------------------------------
# Helpers
# ------------------------------------------------------------------

def _row_to_edge(r: dict) -> Edge:
    from datetime import UTC, datetime  # noqa: PLC0415
    try:
        relation = EdgeRelation(r["relation"])
    except ValueError:
        relation = r["relation"]
    return Edge(
        id=r["id"],
        source_id=r["source_id"],
        target_id=r["target_id"],
        relation=relation,
        weight=r.get("weight", 1.0),
        metadata=__import__("json").loads(r.get("metadata", "{}")),
        created_at=datetime.fromisoformat(r.get("created_at", datetime.now(UTC).isoformat())),
    )
