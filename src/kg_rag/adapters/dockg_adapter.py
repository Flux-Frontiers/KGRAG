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

    def __init__(self, entry: KGEntry, embedder=None) -> None:
        super().__init__(entry, embedder=embedder)
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
            corpus_root=str(entry.repo_path),
            db_path=sqlite or str(entry.repo_path / ".dockg" / "graph.sqlite"),
            lancedb_dir=lancedb or str(entry.repo_path / ".dockg" / "lancedb"),
            embedder=self._embedder,
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

    def query(
        self,
        q: str,
        k: int = 8,
        min_score: float = 0.0,
        semantic_floor: float = 0.0,
    ) -> list[CrossHit]:
        """Query the DocKG and return ranked hits.

        :param q: Natural-language query string.
        :param k: Number of results to return.
        :param min_score: Minimum relevance score; hits below this are dropped.
        :param semantic_floor: If the best hit's score is below this value the
            entire result set is discarded — returns [] rather than k noisy
            near-neighbor hits from an irrelevant KG.
        :return: List of CrossHit objects ranked by score.
        """
        self._load()
        result = self._kg.query(q, k=k)
        nodes = result.nodes[:k]
        if semantic_floor > 0.0 and nodes:
            if nodes[0].get("relevance", {}).get("score", 0.0) < semantic_floor:
                return []
        hits = []
        for node in nodes:
            score = node.get("relevance", {}).get("score", 0.0)
            if score < min_score:
                continue
            hits.append(
                CrossHit(
                    kg_name=self.entry.name,
                    kg_kind=KGKind.DOC,
                    node_id=node["id"],
                    name=node.get("name") or node.get("title", ""),
                    kind=node.get("kind", "chunk"),
                    score=round(score, 4),
                    summary=node.get("text") or node.get("title", ""),
                    source_path=node.get("file_path") or "",
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
        """Query the DocKG and return source snippets.

        :param q: Natural-language query string.
        :param k: Number of snippets to return.
        :param context: Lines of context (unused for doc KGs).
        :param semantic_floor: If the best snippet's score is below this value
            the entire result set is discarded.
        :return: List of CrossSnippet objects.
        """
        self._load()
        pack = self._kg.pack(q, k=k)
        nodes = pack.nodes
        if semantic_floor > 0.0 and nodes:
            if (nodes[0].get("relevance") or {}).get("score", 0.0) < semantic_floor:
                return []
        snippets = []
        for node in nodes:
            relevance = node.get("relevance") or {}
            snippets.append(
                CrossSnippet(
                    kg_name=self.entry.name,
                    kg_kind=KGKind.DOC,
                    node_id=node["id"],
                    source_path=node.get("file_path") or "",
                    content=node.get("text") or "",
                    score=relevance.get("score", 0.0),
                )
            )
        return snippets

    def stats(self) -> dict[str, Any]:
        """Return basic statistics about this DocKG instance.

        :return: Dict with node_count, edge_count.
        """
        self._load()
        try:
            s = self._kg.store.stats()
            return {
                "node_count": s.get("total_nodes", "n/a"),
                "edge_count": s.get("total_edges", "n/a"),
                "kind": "doc",
            }
        except Exception:  # pylint: disable=broad-exception-caught
            return {"kind": "doc", "error": "stats unavailable"}

    def analyze(self) -> str:
        """Run full corpus analysis on this DocKG.

        Uses DocKGAnalyzer to compute baseline metrics, per-document structure,
        semantic coverage (topic/entity/keyword), hot chunks, and issues/strengths.

        :return: Markdown-formatted analysis report.
        """
        self._load()
        try:
            from doc_kg.dockg_thorough_analysis import (  # pylint: disable=import-outside-toplevel
                DocKGAnalyzer,
            )
            from rich.console import Console  # pylint: disable=import-outside-toplevel

            analyzer = DocKGAnalyzer(self._kg, console=Console(quiet=True))
            result = analyzer.run_analysis()

            stats = result.get("stats", {})
            cov = result.get("semantic_coverage", {})
            lines: list[str] = [
                "# DocKG Analysis Report",
                "",
                f"**KG:** `{self.entry.name}`  |  **corpus:** `{self.entry.repo_path}`",
                "",
                "## Baseline",
                "",
                f"- Total nodes: **{stats.get('total_nodes', 'n/a')}**",
                f"- Total edges: **{stats.get('total_edges', 'n/a')}**",
                "",
                "## Semantic Coverage",
                "",
                f"- Topic coverage:   **{cov.get('topic_coverage', 0.0):.1%}**",
                f"- Entity coverage:  **{cov.get('entity_coverage', 0.0):.1%}**",
                f"- Keyword coverage: **{cov.get('keyword_coverage', 0.0):.1%}**",
                "",
                "## Top Documents by Chunk Count",
                "",
                "| File | Chunks | Sections | References | Semantic Links |",
                "|---|---:|---:|---:|---:|",
            ]
            for m in result.get("document_metrics", [])[:15]:
                lines.append(
                    f"| `{m['file_path']}` | {m['chunks']} | {m['sections']}"
                    f" | {m['refs_out']} | {m['semantic_links']} |"
                )
            lines.append("")

            hot = result.get("hot_chunks", [])
            if hot:
                lines += [
                    "## Hot Chunks",
                    "",
                    "| Chunk ID | File | Semantic Links | References |",
                    "|---|---|---:|---:|",
                ]
                for c in hot:
                    lines.append(
                        f"| `{c['id']}` | `{c['file_path']}`"
                        f" | {c['semantic_links']} | {c['references']} |"
                    )
                lines.append("")

            if result.get("issues"):
                lines += ["## ⚠️ Issues", ""]
                for item in result["issues"]:
                    lines.append(f"- {item}")
                lines.append("")

            if result.get("strengths"):
                lines += ["## ✅ Strengths", ""]
                for item in result["strengths"]:
                    lines.append(f"- {item}")
                lines.append("")

            return "\n".join(lines)
        except Exception as exc:  # pylint: disable=broad-exception-caught
            return f"# DocKG Analysis\n\nAnalysis failed: {exc}\n"

    def _collect_snapshot_metrics(self) -> dict[str, Any]:
        """Return doc-specific metrics for the snapshot."""
        try:
            self._load()
            s = self._kg.store.stats()
            return {
                "total_nodes": s.get("total_nodes", 0),
                "total_edges": s.get("total_edges", 0),
                "node_counts": s.get("node_counts", {}),
                "edge_counts": s.get("edge_counts", {}),
            }
        except Exception:  # pylint: disable=broad-exception-caught
            return {}
