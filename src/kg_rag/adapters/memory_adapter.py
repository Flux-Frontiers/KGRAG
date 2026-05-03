"""memory_adapter.py — KGAdapter for MemoryKG (episodic memory knowledge graph)."""

from __future__ import annotations

from typing import Any

from kg_rag.adapters.base import KGAdapter
from kg_rag.primitives import CrossHit, CrossSnippet, KGEntry, KGKind


class MemoryKGAdapter(KGAdapter):
    """Adapter wrapping ``memory_kg.MemoryKG`` — episodic memory knowledge graph.

    ``KGEntry.repo_path`` must point to the project root that contains
    ``.memorykg/``.  Nodes are ranked by the MemoryKG hybrid query engine;
    scores are assigned positionally (highest-ranked node receives 1.0).

    :param entry: KGEntry with ``kind=KGKind.MEMORY``.
    """

    def __init__(self, entry: KGEntry, embedder=None) -> None:
        super().__init__(entry, embedder=embedder)
        self._kg: Any = None

    def _load(self) -> None:
        if self._kg is not None:
            return
        try:
            from memory_kg.kg import MemoryKG  # pylint: disable=import-outside-toplevel
        except ImportError as exc:
            raise ImportError(
                "memory-kg is not installed. "
                "Install it with: pip install memory-kg or add it to your environment."
            ) from exc
        entry = self.entry
        sqlite = str(entry.sqlite_path) if entry.sqlite_path else None
        lancedb = str(entry.lancedb_path) if entry.lancedb_path else None
        self._kg = MemoryKG(
            corpus_root=str(entry.repo_path),
            db_path=sqlite or str(entry.repo_path / ".memorykg" / "graph.sqlite"),
            lancedb_dir=lancedb or str(entry.repo_path / ".memorykg" / "lancedb"),
            embedder=self._embedder,
        )

    def is_available(self) -> bool:
        """Return True if memory_kg is installed and the DB is built.

        :return: True if this adapter can serve queries.
        """
        try:
            import memory_kg  # noqa: F401  # pylint: disable=import-outside-toplevel

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
        """Semantic + structural query over the episodic memory corpus.

        Nodes are ranked by the MemoryKG hybrid engine; scores are positional
        (1.0 for rank-0, decreasing toward 0.0 for lower ranks).

        :param q: Natural-language query string.
        :param k: Number of results to return.
        :param min_score: Minimum relevance score; hits below this are dropped.
        :param semantic_floor: If the top hit's positional score is below this
            value the entire result set is discarded.
        :return: Ranked list of CrossHit objects.
        """
        self._load()
        result = self._kg.query(q, k=k)
        nodes = result.nodes[:k]
        n_nodes = len(nodes)
        hits = []
        for i, node in enumerate(nodes):
            score = 1.0 - (i / max(n_nodes, 1))
            if semantic_floor > 0.0 and i == 0 and score < semantic_floor:
                return []
            if score < min_score:
                continue
            hits.append(
                CrossHit(
                    kg_name=self.entry.name,
                    kg_kind=KGKind.MEMORY,
                    node_id=node["id"],
                    name=node.get("title") or node.get("name") or node["id"],
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
        """Return episodic memory snippets for LLM ingestion.

        :param q: Natural-language query string.
        :param k: Number of snippets to return.
        :param context: Unused (no line-number semantics in MemoryKG).
        :param semantic_floor: If the top snippet's positional score is below
            this value the entire result set is discarded.
        :return: List of CrossSnippet objects.
        """
        self._load()
        pack = self._kg.pack(q, k=k)
        nodes = pack.nodes
        n_nodes = len(nodes)
        snippets = []
        for i, node in enumerate(nodes):
            score = 1.0 - (i / max(n_nodes, 1))
            if semantic_floor > 0.0 and i == 0 and score < semantic_floor:
                return []
            snippets.append(
                CrossSnippet(
                    kg_name=self.entry.name,
                    kg_kind=KGKind.MEMORY,
                    node_id=node["id"],
                    source_path=node.get("file_path") or "",
                    content=node.get("excerpt") or node.get("text") or "",
                    score=round(score, 4),
                )
            )
        return snippets

    def stats(self) -> dict[str, Any]:
        """Return live statistics about this MemoryKG instance.

        :return: Standard envelope plus memory-specific counts (nodes by kind).
        """
        self._load()
        db_size = 0.0
        if self.entry.sqlite_path and self.entry.sqlite_path.exists():
            db_size = round(self.entry.sqlite_path.stat().st_size / 1_048_576, 2)
        try:
            s = self._kg.stats()
            return {
                "kind": "memory",
                "kg_name": self.entry.name,
                "builder_version": self.entry.builder_version,
                "available": True,
                "db_size_mb": db_size,
                "node_count": s.get("total_nodes", "n/a"),
                "edge_count": s.get("total_edges", "n/a"),
                "node_counts": s.get("node_counts", {}),
                "edge_counts": s.get("edge_counts", {}),
            }
        except Exception as exc:  # pylint: disable=broad-exception-caught
            return {
                "kind": "memory",
                "kg_name": self.entry.name,
                "available": True,
                "db_size_mb": db_size,
                "error": str(exc),
            }

    def analyze(self) -> str:
        """Run full corpus analysis on this MemoryKG.

        :return: Markdown-formatted analysis report.
        """
        self._load()
        try:
            from memory_kg.memorykg_thorough_analysis import (  # pylint: disable=import-outside-toplevel
                MemoryKGAnalyzer,
            )
            from rich.console import Console  # pylint: disable=import-outside-toplevel

            analyzer = MemoryKGAnalyzer(self._kg, console=Console(quiet=True))
            result = analyzer.run_analysis()

            stats = result.get("stats", {})
            lines: list[str] = [
                "# MemoryKG Analysis Report",
                "",
                f"**KG:** `{self.entry.name}`  |  **corpus:** `{self.entry.repo_path}`",
                "",
                "## Baseline",
                "",
                f"- Total nodes: **{stats.get('total_nodes', 'n/a')}**",
                f"- Total edges: **{stats.get('total_edges', 'n/a')}**",
                "",
            ]
            return "\n".join(lines)
        except Exception as exc:  # pylint: disable=broad-exception-caught
            return f"# MemoryKG Analysis\n\nAnalysis failed: {exc}\n"

    def _collect_snapshot_metrics(self) -> dict[str, Any]:
        """Return memory-specific metrics for the snapshot."""
        try:
            self._load()
            s = self._kg.stats()
            return {
                "total_nodes": s.get("total_nodes", 0),
                "total_edges": s.get("total_edges", 0),
                "node_counts": s.get("node_counts", {}),
                "edge_counts": s.get("edge_counts", {}),
            }
        except Exception:  # pylint: disable=broad-exception-caught
            return {}
