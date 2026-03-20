"""agent_adapter.py — KGAdapter for AgentKG."""

from __future__ import annotations

from typing import Any

from kg_rag.adapters.base import KGAdapter
from kg_rag.primitives import CrossHit, CrossSnippet, KGEntry, KGKind


class AgentKGAdapter(KGAdapter):
    """Adapter wrapping agent_kg.AgentKG.

    :param entry: KGEntry with kind=KGKind.AGENT.
    """

    def __init__(self, entry: KGEntry) -> None:
        super().__init__(entry)
        self._kg: Any = None

    def _load(self) -> None:
        if self._kg is not None:
            return
        try:
            from agent_kg.kg import (
                AgentKG,  # noqa: PLC0415  # pylint: disable=import-outside-toplevel
            )
        except ImportError as exc:
            raise ImportError("agent-kg not installed") from exc
        person_id = self.entry.metadata.get("person_id", "default")
        self._kg = AgentKG(self.entry.repo_path, person_id=person_id)

    def is_available(self) -> bool:
        try:
            import agent_kg  # noqa: F401, PLC0415  # pylint: disable=import-outside-toplevel

            return self.entry.is_built
        except ImportError:
            return False

    def query(self, q: str, k: int = 8) -> list[CrossHit]:
        self._load()
        hits = []
        for h in self._kg.index.search(q, k=k):
            hits.append(
                CrossHit(
                    kg_name=self.entry.name,
                    kg_kind=KGKind.AGENT,
                    node_id=h.get("node_id", ""),
                    name=h.get("text", "")[:80],
                    kind=h.get("kind", "turn"),
                    score=h.get("score", 0.0),
                    summary=h.get("text", "")[:200],
                    source_path=".agentkg/graph.sqlite",
                )
            )
        return hits

    def pack(self, q: str, k: int = 8, context: int = 5) -> list[CrossSnippet]:
        self._load()
        snippets = []
        for h in self._kg.index.search(q, k=k):
            snippets.append(
                CrossSnippet(
                    kg_name=self.entry.name,
                    kg_kind=KGKind.AGENT,
                    node_id=h.get("node_id", ""),
                    source_path=".agentkg/graph.sqlite",
                    content=h.get("text", ""),
                    score=h.get("score", 0.0),
                )
            )
        return snippets

    def stats(self) -> dict[str, Any]:
        self._load()
        return self._kg.stats()

    def _collect_snapshot_metrics(self) -> dict[str, Any]:
        try:
            self._load()
            s = self._kg.stats()
            return {"total_nodes": s.get("nodes", 0), "total_edges": s.get("edges", 0)}
        except Exception:  # pylint: disable=broad-exception-caught
            return {}
