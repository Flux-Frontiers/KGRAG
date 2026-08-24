"""genealogy_adapter.py -- KGAdapter for GenealogyKG.

Wraps the ``genealogy_kg.GenealogyKG`` class. Surfaces a genealogical
knowledge graph -- people, families, events, places and sources built from a
GEDCOM file -- through the standard KGRAG federation interface.

Author: Eric G. Suchanek, PhD
License: Elastic 2.0
"""

from __future__ import annotations

from typing import Any

from kg_rag.adapters.base import KGAdapter, node_metadata
from kg_rag.primitives import CrossHit, CrossSnippet, KGEntry, KGKind, QueryScope


class GenealogyKGAdapter(KGAdapter):
    """Adapter wrapping the ``genealogy_kg.GenealogyKG`` class.

    :param entry: KGEntry with ``kind=KGKind.GENEALOGY``.
    """

    def __init__(self, entry: KGEntry, embedder=None) -> None:
        super().__init__(entry, embedder=embedder)
        self._kg: Any = None

    def _load(self) -> None:
        if self._kg is not None:
            return
        try:
            from genealogy_kg import GenealogyKG  # pylint: disable=import-outside-toplevel
        except ImportError as exc:
            raise ImportError(
                "genealogy-kg is not installed. Install it with: pip install genealogy-kg"
            ) from exc
        entry = self.entry
        self._kg = GenealogyKG(
            repo_root=str(entry.repo_path),
            db_path=str(entry.sqlite_path) if entry.sqlite_path else None,
            vectors_path=str(entry.vectors_path) if entry.vectors_path else None,
        )

    def is_available(self) -> bool:
        """Return True if genealogy_kg is importable and the DB is built.

        :return: True if this adapter can serve queries.
        """
        try:
            import genealogy_kg  # noqa: F401  # pylint: disable=import-outside-toplevel

            return self.entry.is_built
        except ImportError:
            return False

    @staticmethod
    def _score(node: dict[str, Any]) -> float:
        # kg_utils.pipeline nests the rank score under "relevance", not at
        # the node's top level -- see ftree_adapter.py's node_id/score/
        # snippets fields, which assume the pre-refactor flat shape and are
        # confirmed stale against the current kg_utils.pipeline.KGModule API.
        return float(node.get("relevance", {}).get("score", 0.0))

    def query(
        self,
        q: str,
        k: int = 8,
        min_score: float = 0.0,
        semantic_floor: float = 0.0,
        scope: QueryScope | None = None,
    ) -> list[CrossHit]:
        """Query the genealogy graph and return ranked hits.

        :param q: Natural-language query string.
        :param k: Number of results to return.
        :param min_score: Minimum relevance score; hits below this are dropped.
        :param semantic_floor: If the best hit's score is below this value the
            entire result set is discarded.
        :return: List of CrossHit objects ranked by score.
        """
        self._load()
        nodes = list(self._kg.query(q, k=k).nodes)[:k]
        if semantic_floor > 0.0 and nodes and self._score(nodes[0]) < semantic_floor:
            return []
        hits = []
        for n in nodes:
            score = self._score(n)
            if score < min_score:
                continue
            hits.append(
                CrossHit(
                    kg_name=self.entry.name,
                    kg_kind=KGKind.GENEALOGY,
                    node_id=n.get("id", ""),
                    name=n.get("name", ""),
                    kind=n.get("kind", ""),
                    score=score,
                    summary=n.get("docstring", ""),
                    source_path=n.get("module_path", ""),
                    metadata=node_metadata(n),
                )
            )
        return hits

    def pack(
        self,
        q: str,
        k: int = 8,
        context: int = 5,
        semantic_floor: float = 0.0,
        scope: QueryScope | None = None,
    ) -> list[CrossSnippet]:
        """Return GEDCOM record snippets for matching genealogy nodes.

        :param q: Natural-language query string.
        :param k: Number of snippets to return.
        :param context: Lines of context around the matched record.
        :param semantic_floor: If the best snippet's score is below this value
            the entire result set is discarded.
        :return: List of CrossSnippet objects.
        """
        self._load()
        # The per-node snippet lives at node["snippet"] (path/start/end/text);
        # SnippetPack.snippets is always [] on kg_utils.pipeline's current
        # KGModule.pack() -- see the note in _score() above.
        nodes = [n for n in self._kg.pack(q, k=k, context=context).nodes if n.get("snippet")]
        if semantic_floor > 0.0 and nodes and self._score(nodes[0]) < semantic_floor:
            return []
        snippets = []
        for n in nodes:
            snippet = n["snippet"]
            snippets.append(
                CrossSnippet(
                    kg_name=self.entry.name,
                    kg_kind=KGKind.GENEALOGY,
                    node_id=n.get("id", ""),
                    source_path=n.get("module_path", ""),
                    lineno=snippet.get("start"),
                    end_lineno=snippet.get("end"),
                    content=snippet.get("text", ""),
                    score=self._score(n),
                    metadata=node_metadata(n),
                )
            )
        return snippets

    def stats(self) -> dict[str, Any]:
        """Return live statistics about this GenealogyKG instance.

        :return: Dict with kind, node/edge counts, and metadata.
        """
        self._load()
        db_size = 0.0
        if self.entry.sqlite_path and self.entry.sqlite_path.exists():
            db_size = round(self.entry.sqlite_path.stat().st_size / 1_048_576, 2)
        try:
            s = self._kg.stats()
            return {
                "kind": "genealogy",
                "kg_name": self.entry.name,
                "builder_version": self.entry.builder_version,
                "available": True,
                "db_size_mb": db_size,
                "node_count": s.get("total_nodes", 0),
                "edge_count": s.get("total_edges", 0),
                "person_count": s.get("node_counts", {}).get("person", 0),
                "family_count": s.get("node_counts", {}).get("family", 0),
            }
        except Exception as exc:  # pylint: disable=broad-exception-caught
            return {
                "kind": "genealogy",
                "kg_name": self.entry.name,
                "available": True,
                "db_size_mb": db_size,
                "error": str(exc),
            }

    def analyze(self) -> str:
        """Run analysis on this GenealogyKG instance.

        :return: Markdown-formatted analysis report.
        """
        self._load()
        try:
            return self._kg.analyze()
        except Exception as exc:  # pylint: disable=broad-exception-caught
            return f"# GenealogyKG Analysis\n\nAnalysis failed: {exc}\n"

    def _collect_snapshot_metrics(self) -> dict[str, Any]:
        """Return genealogy-specific metrics for the snapshot."""
        try:
            self._load()
            s = self._kg.stats()
            counts = s.get("node_counts", {})
            return {
                "total_nodes": s.get("total_nodes", 0),
                "total_edges": s.get("total_edges", 0),
                "person_count": counts.get("person", 0),
                "family_count": counts.get("family", 0),
            }
        except Exception:  # pylint: disable=broad-exception-caught
            return {}
