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
        self._kg: Any = None

    def _load(self):
        if self._kg is not None:
            return
        try:
            from code_kg.kg import CodeKG  # pylint: disable=import-outside-toplevel
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
            lancedb_dir=lancedb or str(entry.repo_path / ".codekg" / "lancedb"),
        )

    def is_available(self) -> bool:
        """Return True if code_kg is installed and the DB is built.

        :return: True if this adapter can serve queries.
        """
        try:
            import code_kg  # noqa: F401  # pylint: disable=import-outside-toplevel

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
        for node in result.nodes[:k]:
            relevance = node.get("relevance") or {}
            hits.append(
                CrossHit(
                    kg_name=self.entry.name,
                    kg_kind=KGKind.CODE,
                    node_id=node["id"],
                    name=node.get("name", ""),
                    kind=node.get("kind", ""),
                    score=relevance.get("score", 0.0),
                    summary=node.get("docstring") or "",
                    source_path=node.get("module_path") or "",
                )
            )
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
        for node in pack.nodes:
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
        """Return basic statistics about this CodeKG instance.

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
        """Run full architectural analysis on this CodeKG.

        :return: Markdown-formatted analysis report.
        """
        self._load()
        try:
            return self._kg.analyze()
        except Exception as exc:  # pylint: disable=broad-exception-caught
            return f"Analysis failed: {exc}"
