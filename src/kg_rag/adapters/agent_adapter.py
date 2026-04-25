"""agent_adapter.py — KGAdapter wrapping the agent_kg package.

AgentKG is unique among adapters: it is mutated during a session (ingest/prune)
in addition to being queried (query/pack/assemble_context). The adapter exposes
both read and write operations through the standard KGAdapter contract plus
AgentKG-specific extension methods.

Storage layout (auto-created on first use)::

    <repo>/.agentkg/
        graph.sqlite       # conversation tree (Turn, Topic, Task, Summary nodes)
        lancedb/           # semantic embeddings
        snapshots/         # temporal snapshots

    ~/.kgrag/profiles/<person_id>/
        userprofile.sqlite # global UserProfile (Preference, Expertise, etc.)

Author: Eric G. Suchanek, PhD
Last Revision: 2026-04-22 19:27:45
License: Elastic 2.0
"""

# pylint: disable=import-outside-toplevel

from __future__ import annotations

from typing import Any

from kg_rag.adapters.base import KGAdapter
from kg_rag.primitives import CrossHit, CrossSnippet, KGEntry, KGKind


class AgentKGAdapter(KGAdapter):
    """Adapter wrapping ``agent_kg.AgentKG`` — live conversational memory graph.

    Unlike static KGs (CodeKG, DocKG), AgentKG is written during a session.
    The adapter exposes both the standard KGAdapter read contract and three
    write/assembly methods unique to AgentKG:

    - :meth:`ingest` — add a conversation turn (Phase 1)
    - :meth:`prune` — run KG Context Pruning (Phase 3)
    - :meth:`assemble_context` — assemble token-budgeted context (Phase 2)

    :param entry: KGEntry with ``kind=KGKind.AGENT``.
                  ``entry.metadata["person_id"]`` sets the UserProfile identity.
    """

    def __init__(self, entry: KGEntry, embedder=None) -> None:
        super().__init__(entry, embedder=embedder)
        self._kg: Any = None

    # ------------------------------------------------------------------
    # Lazy init
    # ------------------------------------------------------------------

    def _load(self) -> None:
        if self._kg is not None:
            return
        try:
            from agent_kg.graph import AgentKG  # noqa: PLC0415
        except ImportError as exc:
            raise ImportError(
                "agent-kg is not installed. "
                "It lives in src/agent_kg/ — run `poetry install` to include it."
            ) from exc
        person_id = self.entry.metadata.get("person_id", "default")
        session_id = self.entry.metadata.get("session_id", None)
        self._kg = AgentKG(
            repo_path=self.entry.repo_path,
            person_id=person_id,
            session_id=session_id or None,
        )

    # ------------------------------------------------------------------
    # KGAdapter contract (read)
    # ------------------------------------------------------------------

    def is_available(self) -> bool:
        """Return True if agent_kg is importable and the graph DB exists.

        Checks the canonical ``.agentkg/graph.sqlite`` path when
        ``entry.sqlite_path`` is not explicitly set.

        :return: True if this adapter can serve queries.
        """
        try:
            import agent_kg  # noqa: F401, PLC0415
        except ImportError:
            return False
        if self.entry.is_built:
            return True
        # Also check the default .agentkg/ location
        default_db = self.entry.repo_path / ".agentkg" / "graph.sqlite"
        return default_db.exists()

    def query(
        self,
        q: str,
        k: int = 8,
        min_score: float = 0.0,
        semantic_floor: float = 0.0,
    ) -> list[CrossHit]:
        """Semantic search over the conversation graph.

        :param q: Natural-language query string.
        :param k: Number of results to return.
        :param min_score: Minimum relevance score; hits below this are dropped.
        :param semantic_floor: If the best hit's score is below this value the
            entire result set is discarded.
        :return: Ranked list of :class:`~kg_rag.primitives.CrossHit` objects.
        """
        self._load()
        raw = list(self._kg.index.search(q, k=k))
        if semantic_floor > 0.0 and raw:
            if raw[0].get("score", 0.0) < semantic_floor:
                return []
        hits = []
        for h in raw:
            score = h.get("score", 0.0)
            if score < min_score:
                continue
            hits.append(
                CrossHit(
                    kg_name=self.entry.name,
                    kg_kind=KGKind.AGENT,
                    node_id=h.get("node_id", ""),
                    name=h.get("label", h.get("text", ""))[:80],
                    kind=h.get("kind", "turn"),
                    score=score,
                    summary=h.get("text", "")[:200],
                    source_path=str(self.entry.repo_path / ".agentkg" / "graph.sqlite"),
                )
            )
        return hits

    def pack(
        self,
        q: str,
        k: int = 8,
        context: int = 5,
        semantic_floor: float = 0.0,
    ) -> list[CrossSnippet]:
        """Return conversation snippets for LLM context injection.

        :param q: Natural-language query string.
        :param k: Number of snippets to return.
        :param context: Unused (no line-number semantics in AgentKG).
        :param semantic_floor: If the best snippet's score is below this value
            the entire result set is discarded.
        :return: List of :class:`~kg_rag.primitives.CrossSnippet` objects.
        """
        self._load()
        raw = list(self._kg.pack(q, k=k))
        if semantic_floor > 0.0 and raw:
            if raw[0].get("score", 0.0) < semantic_floor:
                return []
        snippets = []
        for s in raw:
            snippets.append(
                CrossSnippet(
                    kg_name=self.entry.name,
                    kg_kind=KGKind.AGENT,
                    node_id=s.get("node_id", ""),
                    source_path=str(self.entry.repo_path / ".agentkg" / "graph.sqlite"),
                    content=s.get("content", ""),
                    score=s.get("score", 0.0),
                )
            )
        return snippets

    def stats(self) -> dict[str, Any]:
        """Return node + edge counts and session info.

        :return: Dict with ``node_count``, ``edge_count``, ``kind``, ``session_id``.
        """
        self._load()
        try:
            s = self._kg.stats()
            return {
                "node_count": s.get("node_count", 0),
                "edge_count": s.get("edge_count", 0),
                "kind": "agent",
                "session_id": s.get("session_id", ""),
                "turn_count": s.get("turn_count", 0),
            }
        except Exception:  # pylint: disable=broad-exception-caught
            return {"node_count": 0, "edge_count": 0, "kind": "agent"}

    def analyze(self) -> str:
        """Return a Markdown analysis report for this AgentKG instance.

        :return: Markdown-formatted report string.
        """
        self._load()
        try:
            return self._kg.analyze()
        except Exception as exc:  # pylint: disable=broad-exception-caught
            return f"# AgentKG Analysis\n\nAnalysis failed: {exc}"

    # ------------------------------------------------------------------
    # AgentKG-specific write/assembly interface
    # ------------------------------------------------------------------

    def ingest(self, text: str, role: str = "user") -> Any:
        """Add a conversation turn to the AgentKG graph (Phase 1).

        :param text: Raw turn text.
        :param role: ``"user"`` or ``"assistant"``.
        :return: :class:`~agent_kg.ingest.IngestResult` with created nodes.
        """
        self._load()
        return self._kg.ingest(text=text, role=role)

    def prune(self, token_budget: int | None = None, window: int = 20) -> Any:
        """Execute KG Context Pruning (Phase 3).

        Compresses old Turn subgraphs into dense Summary nodes.

        :param token_budget: Optional token budget trigger.
        :param window: Number of most-recent turns to keep verbatim.
        :return: :class:`~agent_kg.schema.PruneReport`.
        """
        self._load()
        return self._kg.prune(token_budget=token_budget, window=window)

    def assemble_context(self, query: str, budget: int = 4000) -> str:
        """Assemble a token-budgeted context block from the conversation graph.

        Defeats context rot by combining:
        - Semantically relevant summaries (compressed old context)
        - Open tasks (commitment preservation)
        - Semantically relevant past turns
        - Verbatim recent turns

        :param query: Current query for semantic retrieval.
        :param budget: Approximate token budget.
        :return: Markdown-formatted context string.
        """
        self._load()
        return self._kg.assemble_context(query, budget=budget)

    def should_prune(self, token_budget: int | None = None) -> bool:
        """Return True if the graph is ready for a pruning pass.

        :param token_budget: Optional token budget for trigger calculation.
        :return: True if cold subgraph is large enough to prune.
        """
        self._load()
        return self._kg.should_prune(token_budget=token_budget)

    def close_session(self) -> None:
        """Record end_time for the current session."""
        if self._kg is not None:
            self._kg.close_session()

    # ------------------------------------------------------------------
    # Snapshot support
    # ------------------------------------------------------------------

    def _collect_snapshot_metrics(self) -> dict[str, Any]:
        """Return AgentKG-specific metrics for the snapshot."""
        try:
            self._load()
            s = self._kg.stats()
            return {
                "total_nodes": s.get("node_count", 0),
                "total_edges": s.get("edge_count", 0),
                "turn_count": s.get("turn_count", 0),
                "session_id": s.get("session_id", ""),
            }
        except Exception:  # pylint: disable=broad-exception-caught
            return {}
