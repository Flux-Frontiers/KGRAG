"""
dockg_adapter.py

Adapter wrapping the doc_kg.DocKG class.
"""

from __future__ import annotations

from typing import Any

from kg_rag.adapters.base import KGAdapter
from kg_rag.primitives import CrossHit, CrossSnippet, KGEntry, KGKind


class DocKGAdapter(KGAdapter):
    """Adapter for DocKG (document/markdown knowledge graphs).

    :param entry: KGEntry with kind=KGKind.DOC.
    """

    def __init__(self, entry: KGEntry) -> None:
        super().__init__(entry)
        self._kg: Any = None

    def _load(self):
        if self._kg is not None:
            return
        try:
            from doc_kg.kg import DocKG  # pylint: disable=import-outside-toplevel
        except ImportError as e:
            raise ImportError("doc-kg is not installed. Install it with: pip install doc-kg") from e
        entry = self.entry
        sqlite = str(entry.sqlite_path) if entry.sqlite_path else None
        lancedb = str(entry.lancedb_path) if entry.lancedb_path else None
        self._kg = DocKG(
            repo_root=str(entry.repo_path),
            db_path=sqlite or str(entry.repo_path / ".dockg" / "graph.sqlite"),
            lancedb_path=lancedb or str(entry.repo_path / ".dockg" / "lancedb"),
        )

    def is_available(self) -> bool:
        """Return True if doc_kg is installed and the DB is built.

        :return: True if this adapter can serve queries.
        """
        try:
            import doc_kg  # noqa: F401  # pylint: disable=import-outside-toplevel

            return self.entry.is_built
        except ImportError:
            return False

    def query(self, q: str, k: int = 8) -> list[CrossHit]:
        """Query the DocKG and return ranked hits.

        :param q: Natural-language query string.
        :param k: Number of results to return.
        :return: List of CrossHit objects ranked by score.
        """
        self._load()
        result = self._kg.query(q, k=k)
        hits = []
        for hit in result.ranked_hits[:k]:
            node = hit.node
            hits.append(
                CrossHit(
                    kg_name=self.entry.name,
                    kg_kind=KGKind.DOC,
                    node_id=node.id,
                    name=node.name,
                    kind=getattr(node, "kind", "chunk"),
                    score=hit.score,
                    summary=getattr(node, "summary", "") or "",
                    source_path=getattr(node, "path", "") or "",
                )
            )
        return hits

    def pack(self, q: str, k: int = 8, context: int = 5) -> list[CrossSnippet]:
        """Query the DocKG and return source snippets.

        :param q: Natural-language query string.
        :param k: Number of snippets to return.
        :param context: Lines of context (unused for doc KGs).
        :return: List of CrossSnippet objects.
        """
        self._load()
        pack = self._kg.pack(q, k=k)
        snippets = []
        for s in pack.snippets:
            snippets.append(
                CrossSnippet(
                    kg_name=self.entry.name,
                    kg_kind=KGKind.DOC,
                    node_id=getattr(s, "node_id", ""),
                    source_path=getattr(s, "path", ""),
                    content=getattr(s, "text", str(s)),
                    score=getattr(s, "score", 0.0),
                )
            )
        return snippets

    def stats(self) -> dict[str, Any]:
        """Return basic statistics about this DocKG instance.

        :return: Dict with node_count, edge_count.
        """
        self._load()
        try:
            s = self._kg.store
            return {
                "node_count": s.node_count() if hasattr(s, "node_count") else "n/a",
                "edge_count": s.edge_count() if hasattr(s, "edge_count") else "n/a",
                "kind": "doc",
            }
        except Exception:  # pylint: disable=broad-exception-caught
            return {"kind": "doc", "error": "stats unavailable"}
