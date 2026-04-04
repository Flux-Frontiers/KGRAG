"""graph.py — AgentKG: the main entry point for agent conversational memory.

``AgentKG`` is the high-level façade that wires together all AgentKG components:

  - :class:`~agent_kg.store.AgentKGStore` — SQLite + LanceDB storage
  - :class:`~agent_kg.profile.UserProfileStore` — global UserProfile tree
  - :class:`~agent_kg.session.Session` — session lifecycle
  - :func:`~agent_kg.ingest.ingest_turn` — Phase 1 incremental ingest
  - :func:`~agent_kg.query.query` / :func:`~agent_kg.query.pack` — semantic query
  - :func:`~agent_kg.assemble.assemble_context` — context assembly
  - :func:`~agent_kg.prune.prune` — KG Context Pruning
  - :class:`~agent_kg.summarize.Summarizer` — LLM summarization backend

Satisfies the AgentKGAdapter contract:
  - ``AgentKG(repo_path, person_id="default")``
  - ``ag.index.search(q, k=k)`` → list of hit dicts
  - ``ag.stats()`` → {nodes, edges, node_count, edge_count}
  - ``ag.ingest(text, role)`` → IngestResult
  - ``ag.prune(token_budget)`` → PruneReport
  - ``ag.assemble_context(query, budget)`` → Markdown str
  - ``ag.query(q, k)`` → list of hit dicts
  - ``ag.pack(q, k)`` → list of snippet dicts
  - ``ag.analyze()`` → Markdown report str
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from agent_kg import assemble, consolidate, prune, query, snapshots
from agent_kg.ingest import IngestResult, ingest_turn
from agent_kg.onboard import apply_implicit_update
from agent_kg.profile import UserProfileStore
from agent_kg.schema import NodeKind, PruneReport
from agent_kg.session import Session
from agent_kg.store import AgentKGStore
from agent_kg.summarize import Summarizer, SummarizerConfig

# Default storage layout (mirrors .codekg / .dockg convention)
_AGENTKG_DIR = ".agentkg"
_DB_NAME = "graph.sqlite"
_LANCEDB_DIR = "lancedb"
_SNAPSHOTS_DIR = "snapshots"

# Global UserProfile path
_PROFILE_BASE = Path.home() / ".kgrag" / "profiles"


class AgentKG:
    """Conversational memory as a live, queryable knowledge graph.

    Exposes both a **read** interface (query/pack/assemble_context) for
    context retrieval and a **write** interface (ingest/prune) for
    incremental updates — making it unique among KGAdapters.

    Storage layout::

        <repo>/.agentkg/
            graph.sqlite     # conversation tree
            lancedb/         # semantic embeddings
            snapshots/       # temporal snapshots

        ~/.kgrag/profiles/<person_id>/
            userprofile.sqlite   # global UserProfile tree

    :param repo_path: Repository root (conversation tree stored here).
    :param person_id: Identifier for the user's global profile (default: ``"default"``).
    :param session_id: Resume a specific session UUID; else creates new.
    :param embed_model: Sentence-transformer model for embeddings.
    :param summarizer_config: Backend config for KG Context Pruning.
    """

    def __init__(
        self,
        repo_path: str | Path,
        person_id: str = "default",
        session_id: str | None = None,
        embed_model: str | None = None,
        summarizer_config: SummarizerConfig | None = None,
    ) -> None:
        self._repo_path = Path(repo_path).resolve()
        self._person_id = person_id

        # Storage paths
        agentkg_dir = self._repo_path / _AGENTKG_DIR
        agentkg_dir.mkdir(parents=True, exist_ok=True)

        self._db_path = agentkg_dir / _DB_NAME
        self._lancedb_dir = agentkg_dir / _LANCEDB_DIR
        self._snapshots_dir = agentkg_dir / _SNAPSHOTS_DIR
        self._profile_dir = _PROFILE_BASE / person_id

        # Components (lazy where possible)
        self._store = AgentKGStore(
            db_path=self._db_path,
            lancedb_dir=self._lancedb_dir,
            embed_model=embed_model or "all-MiniLM-L6-v2",
        )
        self._profile = UserProfileStore(self._profile_dir)
        self._session = Session.open(self._store, session_id=session_id)
        self._summarizer = Summarizer(summarizer_config or SummarizerConfig.from_env())

    # ------------------------------------------------------------------
    # The index property — satisfies the AgentKGAdapter stub
    # ------------------------------------------------------------------

    @property
    def index(self) -> "AgentKGStore":
        """Expose the store as the semantic index (has .search() method)."""
        return self._store

    # ------------------------------------------------------------------
    # Write interface
    # ------------------------------------------------------------------

    def ingest(self, text: str, role: str = "user", embed: bool = True) -> IngestResult:
        """Ingest a conversation turn into the graph (Phase 1).

        :param text: Raw turn text.
        :param role: ``"user"`` or ``"assistant"``.
        :param embed: Write embeddings immediately (default True).
        :return: :class:`~agent_kg.ingest.IngestResult` with created nodes.
        """
        result = ingest_turn(
            text=text,
            role=role,
            session=self._session,
            store=self._store,
            embed=embed,
        )
        # Apply profile updates from user turns
        if role == "user" and result.profile_updates:
            apply_implicit_update(self._profile, result.profile_updates)
        return result

    def prune(
        self,
        token_budget: int | None = None,
        window: int = 20,
    ) -> PruneReport:
        """Execute one KG Context Pruning pass (Phase 3).

        :param token_budget: Optional token budget trigger.
        :param window: Hot window — most-recent N turns are never pruned.
        :return: :class:`~agent_kg.schema.PruneReport` with pass statistics.
        """
        return prune.prune(
            store=self._store,
            summarizer=self._summarizer,
            session=self._session,
            window=window,
            token_budget=token_budget,
        )

    def consolidate(self, force: bool = False) -> dict[str, Any]:
        """Run Phase 2 background consolidation.

        :param force: Run even if below the threshold.
        :return: Report dict with ``nodes_embedded``, ``edges_created``, ``tasks_updated``.
        """
        return consolidate.consolidate(
            store=self._store,
            session_id=self._session.id,
            force=force,
        )

    # ------------------------------------------------------------------
    # Read interface (KGAdapter contract + extended)
    # ------------------------------------------------------------------

    def query(self, q: str, k: int = 8) -> list[dict[str, Any]]:
        """Semantic search over the conversation graph.

        :param q: Natural-language query string.
        :param k: Number of results.
        :return: List of enriched hit dicts.
        """
        return query.query(self._store, q, k=k)

    def pack(self, q: str, k: int = 8) -> list[dict[str, Any]]:
        """Return conversation snippets for LLM context packing.

        :param q: Natural-language query string.
        :param k: Number of snippets.
        :return: List of ``{node_id, kind, content, score}`` dicts.
        """
        return query.pack(self._store, q, k=k)

    def assemble_context(self, query_text: str, budget: int = 4000) -> str:
        """Assemble a token-budgeted context block from the graph.

        :param query_text: Current query (used for semantic retrieval).
        :param budget: Approximate token budget.
        :return: Markdown-formatted context string.
        """
        return assemble.assemble_context(
            store=self._store,
            query=query_text,
            budget=budget,
            session_id=self._session.id,
        )

    def stats(self) -> dict[str, Any]:
        """Return node + edge counts and session info.

        :return: Dict with ``nodes``, ``edges``, ``node_count``, ``edge_count``,
                 ``session_id``, ``turn_count``.
        """
        s = self._store.stats()
        all_turns = self._store.get_all_turns()
        return {
            **s,
            "session_id": self._session.id,
            "turn_count": len(all_turns),
            "person_id": self._person_id,
        }

    def analyze(self) -> str:
        """Return a Markdown analysis report for this AgentKG instance.

        :return: Markdown-formatted report string.
        """
        try:
            s = self._store.stats()
            turns = self._store.get_all_turns()
            open_tasks = self._store.get_open_tasks()
            sessions = self._store.list_sessions()
            summaries = self._store.get_nodes_by_kind(NodeKind.SUMMARY)
            topics = self._store.get_nodes_by_kind(NodeKind.TOPIC)
            profile_summary = self._profile.summary()
            pruning_pass = max((t.pruning_pass for t in summaries), default=0)

            lines = [
                "# AgentKG Analysis\n",
                "## Overview",
                f"- **Repo**: `{self._repo_path}`",
                f"- **Person**: `{self._person_id}`",
                f"- **Session**: `{self._session.id[:8]}…`",
                f"- **Total nodes**: {s['node_count']}",
                f"- **Total edges**: {s['edge_count']}",
                f"- **Turns**: {len(turns)}",
                f"- **Summaries**: {len(summaries)}",
                f"- **Open tasks**: {len(open_tasks)}",
                f"- **Topics tracked**: {len(topics)}",
                f"- **Sessions**: {len(sessions)}",
                f"- **Pruning passes**: {pruning_pass}",
                "",
            ]

            if open_tasks:
                lines.append("## Open Tasks")
                for t in open_tasks[:10]:
                    lines.append(f"- {t.label or t.text}")
                lines.append("")

            if topics:
                lines.append("## Active Topics")
                topic_labels = [t.label or t.text for t in topics if t.label or t.text]
                lines.append(", ".join(topic_labels[:20]))
                lines.append("")

            if summaries:
                lines.append("## Compressed History (Summaries)")
                for sm in summaries[:5]:
                    lines.append(f"**Pass {sm.pruning_pass}**: {sm.text[:200]}…")
                lines.append("")

            # UserProfile summary
            if any(profile_summary.values()):
                lines.append("## UserProfile")
                for section, items in profile_summary.items():
                    if items:
                        lines.append(f"**{section.title()}**: {', '.join(items[:5])}")
                lines.append("")

            if sessions:
                lines.append("## Sessions")
                for sess in sessions[-5:]:
                    tc = sess.get("turn_count", 0)
                    pp = sess.get("pruning_passes", 0)
                    st = sess.get("start_time", "")[:10]
                    lines.append(f"- `{sess['id'][:8]}…` — {st}, {tc} turns, {pp} pruning passes")
                lines.append("")

            return "\n".join(lines)

        except Exception as exc:  # pylint: disable=broad-exception-caught
            return f"# AgentKG Analysis\n\nAnalysis failed: {exc}"

    # ------------------------------------------------------------------
    # Session control
    # ------------------------------------------------------------------

    def close_session(self) -> None:
        """Record end_time for the current session."""
        self._session.close()

    def snapshot(self, label: str | None = None, version: str = "0.1.0") -> dict[str, Any]:
        """Capture a point-in-time snapshot of this AgentKG's state.

        :param label: Optional human-readable label.
        :param version: Version string.
        :return: Snapshot dict (also written to disk).
        """
        return snapshots.capture(
            store=self._store,
            snapshots_dir=self._snapshots_dir,
            label=label,
            version=version,
        )

    @property
    def profile(self) -> UserProfileStore:
        """The UserProfile tree for direct inspection."""
        return self._profile

    @property
    def session(self) -> Session:
        """The current active session."""
        return self._session

    def should_prune(self, token_budget: int | None = None) -> bool:
        """Return True if the graph is ready for a pruning pass."""
        return prune.should_prune(self._store, token_budget=token_budget)

    def should_consolidate(self) -> bool:
        """Return True if a consolidation pass is warranted."""
        return consolidate.should_consolidate(self._store, session_id=self._session.id)

    def close(self) -> None:
        """Close all database connections and record session end."""
        self.close_session()
        self._store.close()
        self._profile.close()

    def __repr__(self) -> str:
        s = self._store.stats()
        return (
            f"AgentKG(repo={self._repo_path.name!r}, "
            f"person={self._person_id!r}, "
            f"nodes={s['node_count']}, edges={s['edge_count']})"
        )
