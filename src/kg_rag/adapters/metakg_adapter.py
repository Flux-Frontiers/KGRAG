"""
metakg_adapter.py

Adapter wrapping the metakg package.
"""

from __future__ import annotations

from typing import Any

from kg_rag.adapters.base import KGAdapter
from kg_rag.primitives import CrossHit, CrossSnippet, KGEntry, KGKind


class MetaKGAdapter(KGAdapter):
    """Adapter for MetaKG (metabolic pathway knowledge graphs).

    :param entry: KGEntry with kind=KGKind.META.
    """

    def __init__(self, entry: KGEntry) -> None:
        super().__init__(entry)
        self._kg: Any = None

    def _load(self):
        if self._kg is not None:
            return
        try:
            from metakg.orchestrator import (  # pylint: disable=import-outside-toplevel
                MetaKGOrchestrator,
            )
        except ImportError as e:
            raise ImportError("metakg is not installed.") from e
        entry = self.entry
        self._kg = MetaKGOrchestrator(
            repo_root=str(entry.repo_path),
            db_path=str(entry.sqlite_path) if entry.sqlite_path else None,
            lancedb_path=str(entry.lancedb_path) if entry.lancedb_path else None,
        )

    def is_available(self) -> bool:
        """Return True if metakg is installed and the DB is built.

        :return: True if this adapter can serve queries.
        """
        try:
            import metakg  # noqa: F401  # pylint: disable=import-outside-toplevel

            return self.entry.is_built
        except ImportError:
            return False

    def query(self, q: str, k: int = 8) -> list[CrossHit]:
        """Query the MetaKG and return ranked hits.

        :param q: Natural-language query string.
        :param k: Number of results to return.
        :return: List of CrossHit objects ranked by score.
        """
        self._load()
        try:
            result = self._kg.query(q, k=k)
            hits = []
            for hit in (result.ranked_hits if hasattr(result, "ranked_hits") else [])[:k]:
                node = hit.node if hasattr(hit, "node") else hit
                hits.append(
                    CrossHit(
                        kg_name=self.entry.name,
                        kg_kind=KGKind.META,
                        node_id=getattr(node, "id", str(node)),
                        name=getattr(node, "name", str(node)),
                        kind=getattr(node, "kind", "pathway"),
                        score=getattr(hit, "score", 0.0),
                        summary=getattr(node, "description", "") or "",
                        source_path=getattr(node, "source", "") or "",
                    )
                )
            return hits
        except Exception:  # pylint: disable=broad-exception-caught
            return []

    def pack(self, q: str, k: int = 8, context: int = 5) -> list[CrossSnippet]:
        """Query the MetaKG and return source snippets.

        :param q: Natural-language query string.
        :param k: Number of snippets to return.
        :param context: Lines of context (unused for meta KGs).
        :return: List of CrossSnippet objects.
        """
        self._load()
        try:
            pack = self._kg.pack(q, k=k)
            snippets = []
            for s in getattr(pack, "snippets", []):
                snippets.append(
                    CrossSnippet(
                        kg_name=self.entry.name,
                        kg_kind=KGKind.META,
                        node_id=getattr(s, "node_id", ""),
                        source_path=getattr(s, "path", ""),
                        content=getattr(s, "text", str(s)),
                        score=getattr(s, "score", 0.0),
                    )
                )
            return snippets
        except Exception:  # pylint: disable=broad-exception-caught
            return []

    def stats(self) -> dict[str, Any]:
        """Return basic statistics about this MetaKG instance.

        :return: Dict with availability status.
        """
        return {"kind": "meta", "status": "available" if self.is_available() else "unavailable"}
