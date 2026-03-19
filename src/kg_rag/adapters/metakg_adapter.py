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
            db_path=str(entry.sqlite_path) if entry.sqlite_path else None,
            lancedb_dir=str(entry.lancedb_path) if entry.lancedb_path else None,
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
        """Return statistics about this MetaKG instance.

        Attempts to retrieve node and edge counts from the underlying
        MetaKGOrchestrator. Falls back to availability-only status if the
        orchestrator does not expose a stats API.

        :return: Dict with kind, status, and where available node_count/edge_count.
        """
        base: dict[str, Any] = {
            "kind": "meta",
            "status": "available" if self.is_available() else "unavailable",
        }
        if not self.is_available():
            return base
        try:
            self._load()
            raw = self._kg.stats() if callable(getattr(self._kg, "stats", None)) else {}
            if isinstance(raw, dict):
                base["node_count"] = raw.get("node_count") or raw.get("total_nodes", "n/a")
                base["edge_count"] = raw.get("edge_count") or raw.get("total_edges", "n/a")
        except Exception:  # pylint: disable=broad-exception-caught
            pass
        return base

    def analyze(self) -> str:
        """Run analysis on this MetaKG instance and return a Markdown report.

        Delegates to the MetaKGOrchestrator's ``analyze()`` method when available.
        Falls back to a stats-based summary report when the underlying library
        does not expose a dedicated analyzer.

        :return: Markdown-formatted analysis report.
        """
        header = (
            "# MetaKG Analysis Report\n\n"
            f"**KG:** `{self.entry.name}`  |  **repo:** `{self.entry.repo_path}`\n"
        )
        if not self.is_available():
            return header + "\n**Status:** unavailable — metakg library not installed.\n"

        try:
            self._load()
            # Prefer a dedicated analyze() on the orchestrator if it exists
            if callable(getattr(self._kg, "analyze", None)):
                result = self._kg.analyze()
                if isinstance(result, str):
                    return header + "\n" + result
                if isinstance(result, dict):
                    import json  # pylint: disable=import-outside-toplevel

                    return header + "\n```json\n" + json.dumps(result, indent=2) + "\n```\n"

            # Fallback: stats-based summary
            s = self.stats()
            lines: list[str] = [
                header,
                "## Summary",
                "",
                f"- **Status:** {s.get('status', 'unknown')}",
                f"- **Node count:** {s.get('node_count', 'n/a')}",
                f"- **Edge count:** {s.get('edge_count', 'n/a')}",
                "",
                "> Detailed analysis requires the MetaKGOrchestrator to expose an"
                " `analyze()` method. Implement `MetaKGOrchestrator.analyze()` in"
                " the metakg package to enable full reporting.",
                "",
            ]
            return "\n".join(lines)
        except Exception as exc:  # pylint: disable=broad-exception-caught
            return header + f"\nAnalysis failed: {exc}\n"

    def _collect_snapshot_metrics(self) -> dict[str, Any]:
        """Return meta-specific metrics and availability status."""
        return {"status": "available" if self.is_available() else "unavailable"}
