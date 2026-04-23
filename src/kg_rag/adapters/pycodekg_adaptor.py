"""
pycodekg_adaptor.py

Adapter wrapping the pycode_kg.PyCodeKG class.
"""

from __future__ import annotations

from typing import Any

from kg_rag.adapters.base import KGAdapter
from kg_rag.primitives import CrossHit, CrossSnippet, KGEntry, KGKind


class CodeKGAdapter(KGAdapter):
    """Adapter for PyCodeKG (Python code knowledge graphs).

    :param entry: KGEntry with kind=KGKind.CODE.
    """

    def __init__(self, entry: KGEntry) -> None:
        super().__init__(entry)
        self._kg: Any = None

    def _load(self):
        if self._kg is not None:
            return
        try:
            from pycode_kg.kg import PyCodeKG  # pylint: disable=import-outside-toplevel
        except ImportError as e:
            raise ImportError(
                "pycode-kg is not installed. Install it with: pip install pycode-kg"
            ) from e
        entry = self.entry
        sqlite = str(entry.sqlite_path) if entry.sqlite_path else None
        lancedb = str(entry.lancedb_path) if entry.lancedb_path else None
        self._kg = PyCodeKG(
            repo_root=str(entry.repo_path),
            db_path=sqlite or str(entry.repo_path / ".pycodekg" / "graph.sqlite"),
            lancedb_dir=lancedb or str(entry.repo_path / ".pycodekg" / "lancedb"),
        )

    def is_available(self) -> bool:
        """Return True if pycode-kg is installed and the DB is built.

        :return: True if this adapter can serve queries.
        """
        try:
            import pycode_kg  # noqa: F401  # pylint: disable=import-outside-toplevel

            return self.entry.is_built
        except ImportError:
            return False

    def query(
        self,
        q: str,
        k: int = 8,
        min_score: float = 0.0,
        semantic_floor: float = 0.0,
    ) -> list[CrossHit]:
        """Query the PyCodeKG and return ranked hits.

        :param q: Natural-language query string.
        :param k: Number of results to return.
        :param min_score: Minimum relevance score; hits below this are dropped.
        :param semantic_floor: If the best hit's score is below this value the
            entire result set is discarded — returns [] rather than k noisy
            near-neighbor hits from an irrelevant KG.
        :return: List of CrossHit objects ranked by score.
        """
        self._load()
        result = self._kg.query(q, k=k, min_score=min_score)
        nodes = result.nodes[:k]
        if semantic_floor > 0.0 and nodes:
            best = nodes[0].get("relevance") or {}
            # Use the raw LanceDB cosine similarity ("semantic") rather than
            # the reranked "score", which is normalized so the top result in
            # each query always reaches 1.0 regardless of actual relevance.
            # "semantic" is 1-dist, directly comparable to DocKG's score.
            best_score = best.get("semantic", best.get("score", 0.0))
            if best_score < semantic_floor:
                return []
        hits = []
        for node in nodes:
            relevance = node.get("relevance") or {}
            score = relevance.get("semantic", relevance.get("score", 0.0))
            if score < min_score:
                continue
            hits.append(
                CrossHit(
                    kg_name=self.entry.name,
                    kg_kind=KGKind.CODE,
                    node_id=node["id"],
                    name=node.get("name", ""),
                    kind=node.get("kind", ""),
                    score=score,
                    summary=node.get("docstring") or "",
                    source_path=node.get("module_path") or "",
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
        """Query the PyCodeKG and return source snippets.

        :param q: Natural-language query string.
        :param k: Number of snippets to return.
        :param context: Lines of context around code.
        :param semantic_floor: If the best snippet's score is below this value
            the entire result set is discarded.
        :return: List of CrossSnippet objects.
        """
        self._load()
        pack = self._kg.pack(q, k=k, context=context)
        nodes = pack.nodes
        if semantic_floor > 0.0 and nodes:
            best = nodes[0].get("relevance") or {}
            best_score = best.get("semantic", best.get("score", 0.0))
            if best_score < semantic_floor:
                return []
        snippets = []
        for node in nodes:
            snippet = node.get("snippet") or {}
            relevance = node.get("relevance") or {}
            snippets.append(
                CrossSnippet(
                    kg_name=self.entry.name,
                    kg_kind=KGKind.CODE,
                    node_id=node["id"],
                    source_path=snippet.get("path", ""),
                    content=snippet.get("text", ""),
                    score=relevance.get("score", 0.0),
                    lineno=snippet.get("start"),
                    end_lineno=snippet.get("end"),
                )
            )
        return snippets

    def stats(self) -> dict[str, Any]:
        """Return basic statistics about this PyCodeKG instance.

        :return: Dict with node_count, edge_count.
        """
        self._load()
        try:
            s = self._kg.store.stats()
            return {
                "node_count": s.get("meaningful_nodes", s.get("total_nodes", "n/a")),
                "edge_count": s.get("total_edges", "n/a"),
                "kind": "code",
            }
        except Exception:  # pylint: disable=broad-exception-caught
            return {"kind": "code", "error": "stats unavailable"}

    def analyze(self) -> str:
        """Run full architectural analysis on this PyCodeKG.

        :return: Markdown-formatted analysis report.
        """
        self._load()
        try:
            return self._kg.analyze()
        except Exception as exc:  # pylint: disable=broad-exception-caught
            return f"Analysis failed: {exc}"

    def _collect_snapshot_metrics(self) -> dict[str, Any]:
        """Return code-specific metrics (coverage, complexity) for the snapshot."""
        try:
            self._load()
            s = self._kg.store.stats()
            return {
                "total_nodes": s.get("total_nodes", 0),
                "total_edges": s.get("total_edges", 0),
                "meaningful_nodes": s.get("meaningful_nodes", 0),
                "node_counts": s.get("node_counts", {}),
                "edge_counts": s.get("edge_counts", {}),
            }
        except Exception:  # pylint: disable=broad-exception-caught
            return {}
