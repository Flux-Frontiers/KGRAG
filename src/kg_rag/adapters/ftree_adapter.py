"""ftree_adapter.py — KGAdapter for FileTreeKG.

Wraps the ``ftree_kg.FileTreeKG`` class. Surfaces a file-system / repository
structure graph (directories, files, modules, dependency and import edges)
through the standard KGRAG federation interface.

Author: Eric G. Suchanek, PhD
License: Elastic 2.0
"""

from __future__ import annotations

from typing import Any

from kg_rag.adapters.base import KGAdapter
from kg_rag.primitives import CrossHit, CrossSnippet, KGEntry, KGKind


class FTreeKGAdapter(KGAdapter):
    """Adapter wrapping the ``ftree_kg.FileTreeKG`` class.

    :param entry: KGEntry with ``kind=KGKind.FILETREE``.
    """

    def __init__(self, entry: KGEntry, embedder=None) -> None:
        super().__init__(entry, embedder=embedder)
        self._kg: Any = None

    def _load(self) -> None:
        if self._kg is not None:
            return
        try:
            from ftree_kg import FileTreeKG  # pylint: disable=import-outside-toplevel
        except ImportError as exc:
            raise ImportError(
                "ftree-kg is not installed. Install it with: pip install ftree-kg"
            ) from exc
        entry = self.entry
        self._kg = FileTreeKG(
            repo_root=str(entry.repo_path),
            db_path=str(entry.sqlite_path) if entry.sqlite_path else None,
            lancedb_path=str(entry.lancedb_path) if entry.lancedb_path else None,
        )

    def is_available(self) -> bool:
        """Return True if ftree_kg is importable and the DB is built.

        :return: True if this adapter can serve queries.
        """
        try:
            import ftree_kg  # noqa: F401  # pylint: disable=import-outside-toplevel

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
        """Query the FileTreeKG and return ranked hits.

        :param q: Natural-language query string.
        :param k: Number of results to return.
        :param min_score: Minimum relevance score; hits below this are dropped.
        :param semantic_floor: If the best hit's score is below this value the
            entire result set is discarded.
        :return: List of CrossHit objects ranked by score.
        """
        self._load()
        result = self._kg.query(q, k=k)
        nodes = list(result.nodes)[:k]
        if semantic_floor > 0.0 and nodes:
            if nodes[0].get("score", 0.0) < semantic_floor:
                return []
        hits = []
        for n in nodes:
            score = n.get("score", 0.0)
            if score < min_score:
                continue
            hits.append(
                CrossHit(
                    kg_name=self.entry.name,
                    kg_kind=KGKind.FILETREE,
                    node_id=n.get("node_id", ""),
                    name=n.get("name", ""),
                    kind=n.get("kind", ""),
                    score=score,
                    summary=n.get("docstring", ""),
                    source_path=n.get("source_path", ""),
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
        """Return source snippets for matching file-tree nodes.

        :param q: Natural-language query string.
        :param k: Number of snippets to return.
        :param context: Lines of context around code definitions.
        :param semantic_floor: If the best snippet's score is below this value
            the entire result set is discarded.
        :return: List of CrossSnippet objects.
        """
        self._load()
        pack = self._kg.pack(q, k=k, context=context)
        snippets = list(pack.snippets)
        if semantic_floor > 0.0 and snippets:
            if snippets[0].get("score", 0.0) < semantic_floor:
                return []
        return [
            CrossSnippet(
                kg_name=self.entry.name,
                kg_kind=KGKind.FILETREE,
                node_id=s.get("node_id", ""),
                source_path=s.get("source_path", ""),
                content=s.get("content", ""),
                score=s.get("score", 0.0),
            )
            for s in snippets
        ]

    def stats(self) -> dict[str, Any]:
        """Return live statistics about this FileTreeKG instance.

        :return: Dict with kind, node/edge counts, and metadata.
        """
        self._load()
        db_size = 0.0
        if self.entry.sqlite_path and self.entry.sqlite_path.exists():
            db_size = round(self.entry.sqlite_path.stat().st_size / 1_048_576, 2)
        try:
            s = self._kg.stats()
            return {
                "kind": "filetree",
                "kg_name": self.entry.name,
                "builder_version": self.entry.builder_version,
                "available": True,
                "db_size_mb": db_size,
                "node_count": s.get("total_nodes", s.get("node_count", 0)),
                "edge_count": s.get("total_edges", s.get("edge_count", 0)),
            }
        except Exception as exc:  # pylint: disable=broad-exception-caught
            return {
                "kind": "filetree",
                "kg_name": self.entry.name,
                "available": True,
                "db_size_mb": db_size,
                "error": str(exc),
            }

    def analyze(self) -> str:
        """Run analysis on this FileTreeKG instance.

        :return: Markdown-formatted analysis report.
        """
        self._load()
        try:
            return self._kg.analyze()
        except Exception as exc:  # pylint: disable=broad-exception-caught
            return f"# FileTreeKG Analysis\n\nAnalysis failed: {exc}\n"

    def _collect_snapshot_metrics(self) -> dict[str, Any]:
        """Return file-tree-specific metrics for the snapshot."""
        try:
            self._load()
            s = self._kg.stats()
            return {
                "total_nodes": s.get("total_nodes", s.get("node_count", 0)),
                "total_edges": s.get("total_edges", s.get("edge_count", 0)),
            }
        except Exception:  # pylint: disable=broad-exception-caught
            return {}
