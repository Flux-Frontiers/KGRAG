"""
{{name}}/adapter.py

{{AdapterName}} — KGAdapter shim wiring {{ClassName}} into the KGRAG federation layer.
"""

from __future__ import annotations

from typing import Any

from kg_rag.adapters.base import KGAdapter
from kg_rag.primitives import CrossHit, CrossSnippet, KGEntry, KGKind

from {{name}}.module import {{ClassName}}


class {{AdapterName}}(KGAdapter):
    """KGRAG adapter for {{ClassName}}.

    :param entry: KGEntry with kind=KGKind.{{kg_kind|upper}}.
    """

    def __init__(self, entry: KGEntry) -> None:
        super().__init__(entry)
        self._kg: {{ClassName}} | None = None

    def _load(self) -> None:
        if self._kg is not None:
            return
        self._kg = {{ClassName}}(
            repo_root=self.entry.repo_path,
            db_path=self.entry.sqlite_path,
            lancedb_path=self.entry.lancedb_path,
        )

    def is_available(self) -> bool:
        """Return True if {{name}} is importable and the DB is built.

        :return: True if this adapter can serve queries.
        """
        try:
            import {{name}}  # noqa: F401  # pylint: disable=import-outside-toplevel
            return self.entry.is_built
        except ImportError:
            return False

    def query(self, q: str, k: int = 8) -> list[CrossHit]:
        """Query {{ClassName}} and return ranked hits.

        :param q: Natural-language query string.
        :param k: Number of results to return.
        :return: List of CrossHit objects, or [] on error.
        """
        try:
            self._load()
            result = self._kg.query(q, k=k)
            return [
                CrossHit(
                    kg_name=self.entry.name,
                    kg_kind=KGKind.{{kg_kind|upper}},
                    node_id=n["node_id"],
                    name=n.get("name", ""),
                    kind=n.get("kind", ""),
                    score=n.get("score", 0.0),
                    summary=n.get("docstring", ""),
                    source_path=n.get("source_path", ""),
                )
                for n in result.nodes[:k]
            ]
        except Exception:  # pylint: disable=broad-exception-caught
            return []

    def pack(self, q: str, k: int = 8, context: int = 5) -> list[CrossSnippet]:
        """Query {{ClassName}} and return source snippets.

        :param q: Natural-language query string.
        :param k: Number of snippets to return.
        :param context: Lines of context (for source-code KGs).
        :return: List of CrossSnippet objects, or [] on error.
        """
        try:
            self._load()
            pack = self._kg.pack(q, k=k, context=context)
            return [
                CrossSnippet(
                    kg_name=self.entry.name,
                    kg_kind=KGKind.{{kg_kind|upper}},
                    node_id=s.node_id,
                    source_path=s.source_path,
                    content=s.content,
                    score=s.score,
                    lineno=s.lineno,
                    end_lineno=s.end_lineno,
                )
                for s in pack.snippets
            ]
        except Exception:  # pylint: disable=broad-exception-caught
            return []

    def stats(self) -> dict[str, Any]:
        """Return basic statistics about this {{ClassName}} instance.

        :return: Dict with at minimum a "kind" key.
        """
        try:
            self._load()
            s = self._kg.stats()
            return {
                "kind": "{{kg_kind}}",
                "node_count": s.node_count,
                "edge_count": s.edge_count,
            }
        except Exception:  # pylint: disable=broad-exception-caught
            return {"kind": "{{kg_kind}}", "error": "stats unavailable"}

    def analyze(self) -> str:
        """Run full analysis on this {{ClassName}} instance.

        :return: Markdown-formatted analysis report.
        """
        try:
            self._load()
            return self._kg.analyze()
        except Exception as exc:  # pylint: disable=broad-exception-caught
            return f"# {{ClassName}} Analysis\n\nAnalysis failed: {exc}\n"
