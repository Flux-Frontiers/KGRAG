"""
codekg_adapter.py

Adapter wrapping the code_kg.CodeKG class.
"""
from __future__ import annotations

from typing import Any

from kg_rag.adapters.base import KGAdapter
from kg_rag.primitives import CrossHit, CrossSnippet, KGEntry, KGKind


class CodeKGAdapter(KGAdapter):
    """Adapter for CodeKG (Python code knowledge graphs).

    :param entry: KGEntry with kind=KGKind.CODE.
    """

    def __init__(self, entry: KGEntry) -> None:
        super().__init__(entry)
        self._kg = None

    def _load(self):
        if self._kg is not None:
            return
        try:
            from code_kg.kg import CodeKG
        except ImportError as e:
            raise ImportError(
                "code-kg is not installed. Install it with: pip install code-kg"
            ) from e
        entry = self.entry
        sqlite = str(entry.sqlite_path) if entry.sqlite_path else None
        lancedb = str(entry.lancedb_path) if entry.lancedb_path else None
        self._kg = CodeKG(
            repo_root=str(entry.repo_path),
            db_path=sqlite or str(entry.repo_path / ".codekg" / "graph.sqlite"),
            lancedb_path=lancedb or str(entry.repo_path / ".codekg" / "lancedb"),
        )

    def is_available(self) -> bool:
        """Return True if code_kg is installed and the DB is built.

        :return: True if this adapter can serve queries.
        """
        try:
            import code_kg  # noqa: F401
            return self.entry.is_built
        except ImportError:
            return False

    def query(self, q: str, k: int = 8) -> list[CrossHit]:
        """Query the CodeKG and return ranked hits.

        :param q: Natural-language query string.
        :param k: Number of results to return.
        :return: List of CrossHit objects ranked by score.
        """
        self._load()
        result = self._kg.query(q, k=k)
        hits = []
        for hit in result.ranked_hits[:k]:
            node = hit.node
            hits.append(CrossHit(
                kg_name=self.entry.name,
                kg_kind=KGKind.CODE,
                node_id=node.id,
                name=node.name,
                kind=node.kind,
                score=hit.score,
                summary=node.docstring or "",
                source_path=node.module_path or "",
            ))
        return hits

    def pack(self, q: str, k: int = 8, context: int = 5) -> list[CrossSnippet]:
        """Query the CodeKG and return source snippets.

        :param q: Natural-language query string.
        :param k: Number of snippets to return.
        :param context: Lines of context around code.
        :return: List of CrossSnippet objects.
        """
        self._load()
        pack = self._kg.pack(q, k=k, context=context)
        snippets = []
        for s in pack.snippets:
            snippets.append(CrossSnippet(
                kg_name=self.entry.name,
                kg_kind=KGKind.CODE,
                node_id=s.node_id,
                source_path=s.path,
                content=s.text,
                score=s.score,
                lineno=s.lineno,
                end_lineno=s.end_lineno,
            ))
        return snippets

    def stats(self) -> dict[str, Any]:
        """Return basic statistics about this CodeKG instance.

        :return: Dict with node_count, edge_count.
        """
        self._load()
        try:
            s = self._kg.store
            return {
                "node_count": s.node_count(),
                "edge_count": s.edge_count(),
                "kind": "code",
            }
        except Exception:
            return {"kind": "code", "error": "stats unavailable"}
