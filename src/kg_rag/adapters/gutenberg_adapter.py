"""
gutenberg_adapter.py

KGAdapter for GutenbergKG — Project Gutenberg book corpus.

Wraps a DocKG-backed knowledge graph built by the ``gutenberg_kg`` ingest
pipeline and exposes the standard KGRAG adapter interface (query, pack, stats,
analyze, snapshot).  Also provides corpus-level status and snapshot methods
that delegate to ``gutenberg_kg.corpus``, covering the full genre collection
rather than a single registered KG entry.

Author: Eric G. Suchanek, PhD
Last Revision: 2026-05-06
License: Elastic 2.0
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from kg_rag.adapters.base import KGAdapter
from kg_rag.primitives import CrossHit, CrossSnippet, KGEntry, KGKind


class GutenbergKGAdapter(KGAdapter):
    """Adapter for GutenbergKG — Project Gutenberg book and literature corpus.

    Backed by DocKG indices built per genre/book by the ``gutenberg_kg`` ingest
    pipeline.  Each registered KG entry points to one DocKG-compatible
    ``graph.sqlite`` (typically at ``<corpus-dir>/.dockg/graph.sqlite``).
    When auto-detecting, falls back to ``<repo>/.gutenbergkg/graph.sqlite``.

    :param entry: A KGEntry instance with ``kind=KGKind.GUTENBERG``.
    """

    def __init__(self, entry: KGEntry, embedder=None) -> None:
        super().__init__(entry, embedder=embedder)
        self._kg: Any = None

    def _load(self) -> None:
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
            db_path=sqlite or str(entry.repo_path / ".gutenbergkg" / "graph.sqlite"),
            lancedb_dir=lancedb or str(entry.repo_path / ".gutenbergkg" / "lancedb"),
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
        """Query the Gutenberg corpus and return ranked hits.

        :param q: Natural-language query string.
        :param k: Number of results to return.
        :param min_score: Minimum relevance score; hits below this are dropped.
        :param semantic_floor: If the best hit's score is below this value the
            entire result set is discarded.
        :return: List of CrossHit objects ranked by score.
        """
        if not self.is_available():
            return []
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
                    kg_kind=KGKind.GUTENBERG,
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
        """Return Gutenberg text snippets for LLM ingestion.

        :param q: Natural-language query string.
        :param k: Number of snippets to return.
        :param context: Lines of context (unused for doc-backed KGs).
        :param semantic_floor: If the best snippet's score is below this value
            the entire result set is discarded.
        :return: List of CrossSnippet objects.
        """
        if not self.is_available():
            return []
        self._load()
        pack = self._kg.pack(q, k=k)
        nodes = pack.nodes
        if semantic_floor > 0.0 and nodes:
            if (nodes[0].get("relevance") or {}).get("score", 0.0) < semantic_floor:
                return []
        snippets = []
        for node in nodes:
            text = (node.get("excerpt") or node.get("text") or "").strip()
            if not text:
                continue
            relevance = node.get("relevance") or {}
            snippets.append(
                CrossSnippet(
                    kg_name=self.entry.name,
                    kg_kind=KGKind.GUTENBERG,
                    node_id=node["id"],
                    source_path=node.get("file_path") or "",
                    content=text,
                    score=relevance.get("score", 0.0),
                )
            )
        return snippets

    def stats(self) -> dict[str, Any]:
        """Return live statistics about this Gutenberg corpus instance.

        :return: Standard envelope plus doc-style counts.
        """
        if not self.is_available():
            return {"kind": "gutenberg", "status": "unavailable", "available": False}
        self._load()
        db_size = 0.0
        if self.entry.sqlite_path and self.entry.sqlite_path.exists():
            db_size = round(self.entry.sqlite_path.stat().st_size / 1_048_576, 2)
        try:
            s = self._kg.stats()
            return {
                "kind": "gutenberg",
                "kg_name": self.entry.name,
                "builder_version": self.entry.builder_version,
                "available": True,
                "db_size_mb": db_size,
                "node_count": s.get("node_count", "n/a"),
                "edge_count": s.get("edge_count", "n/a"),
                "document_count": s.get("document_count", 0),
                "chunk_count": s.get("chunk_count", 0),
                "section_count": s.get("section_count", 0),
                "topic_count": s.get("topic_count", 0),
                "entity_count": s.get("entity_count", 0),
                "keyword_count": s.get("keyword_count", 0),
            }
        except Exception as exc:  # pylint: disable=broad-exception-caught
            return {
                "kind": "gutenberg",
                "kg_name": self.entry.name,
                "available": True,
                "db_size_mb": db_size,
                "error": str(exc),
            }

    def analyze(self) -> str:
        """Run full corpus analysis on this Gutenberg index.

        :return: Markdown-formatted analysis report.
        """
        if not self.is_available():
            return (
                "# GutenbergKG Analysis Report\n\n"
                f"**KG:** `{self.entry.name}`  |  **repo:** `{self.entry.repo_path}`\n\n"
                "**Status:** unavailable — DB not built.\n"
            )
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
                "# GutenbergKG Analysis Report",
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
                lines += ["## Issues", ""]
                for item in result["issues"]:
                    lines.append(f"- {item}")
                lines.append("")

            if result.get("strengths"):
                lines += ["## Strengths", ""]
                for item in result["strengths"]:
                    lines.append(f"- {item}")
                lines.append("")

            return "\n".join(lines)
        except Exception as exc:  # pylint: disable=broad-exception-caught
            return f"# GutenbergKG Analysis\n\nAnalysis failed: {exc}\n"

    def _collect_snapshot_metrics(self) -> dict[str, Any]:
        """Return Gutenberg corpus metrics for the snapshot."""
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

    # ------------------------------------------------------------------
    # Corpus-level status & snapshot methods (delegate to gutenberg_kg.corpus)
    # ------------------------------------------------------------------

    def _corpus_lib(self):
        """Lazy import of gutenberg_kg.corpus; raises ImportError if absent."""
        try:
            import gutenberg_kg.corpus as _c  # pylint: disable=import-outside-toplevel

            return _c
        except ImportError as exc:
            raise ImportError("gutenberg-kg is not installed") from exc

    def _registry(self, registry_path: str | None) -> Path:
        return Path(registry_path) if registry_path else Path.home() / ".kgrag" / "registry.sqlite"

    def _snapshots_dir(self) -> Path:
        return self.entry.repo_path / "corpus" / ".snapshots"

    def corpus_status(self, registry_path: str | None = None) -> dict[str, Any]:
        """Return live corpus-wide statistics from the KGRAG registry.

        Reads per-book SQLite databases directly — no rebuild required.

        :param registry_path: Override KGRAG registry path
            (default: ``~/.kgrag/registry.sqlite``).
        :return: Status dict with ``kind``, ``timestamp``, ``version``,
            ``totals``, and ``genres``.
        """
        try:
            lib = self._corpus_lib()
        except ImportError:
            return {
                "kind": "corpus_status",
                "available": False,
                "error": "gutenberg-kg is not installed",
            }
        reg = self._registry(registry_path)
        if not reg.exists():
            return {
                "kind": "corpus_status",
                "available": False,
                "error": f"Registry not found: {reg}",
            }
        try:
            return lib.corpus_status(reg, self.entry.repo_path, self.entry.repo_path / "corpus")
        except Exception as exc:  # pylint: disable=broad-exception-caught
            return {"kind": "corpus_status", "available": False, "error": str(exc)}

    def snapshot_save(
        self,
        output: str | None = None,
        registry_path: str | None = None,
    ) -> dict[str, Any]:
        """Capture current corpus metrics and save a timestamped snapshot.

        :param output: Override output file path
            (default: ``<repo>/corpus/.snapshots/snapshot-<ts>.json``).
        :param registry_path: Override KGRAG registry path.
        :return: The saved snapshot dict.
        :raises FileNotFoundError: If the registry is not found.
        :raises ImportError: If gutenberg-kg is not installed.
        """
        lib = self._corpus_lib()
        reg = self._registry(registry_path)
        if not reg.exists():
            raise FileNotFoundError(f"Registry not found: {reg}")
        _, snap = lib.snapshot_save(
            reg,
            self.entry.repo_path,
            self.entry.repo_path / "corpus",
            Path(output) if output else None,
        )
        return snap

    def snapshot_list(self) -> list[dict[str, Any]]:
        """List saved corpus snapshots, oldest first.

        :return: List of snapshot dicts; empty if none found or gutenberg-kg absent.
        """
        try:
            return self._corpus_lib().snapshot_list(self._snapshots_dir())
        except ImportError:
            return []

    def snapshot_show(self, snapshot: str | None = None) -> dict[str, Any]:
        """Return the full dict for a snapshot.

        :param snapshot: Filename or timestamp prefix to match
            (default: most recent).
        :return: Snapshot dict, or ``{}`` if not found or gutenberg-kg absent.
        """
        try:
            return self._corpus_lib().snapshot_show(self._snapshots_dir(), snapshot)
        except ImportError:
            return {}

    def snapshot_diff(
        self,
        a: str | None = None,
        b: str | None = None,
    ) -> dict[str, Any]:
        """Return a structured diff between two snapshots.

        :param a: First snapshot filename or prefix (default: second-to-last).
        :param b: Second snapshot filename or prefix (default: most recent).
        :return: Diff dict with ``a``, ``b``, ``totals``, and ``changed_genres``;
            or ``{"error": ...}`` if insufficient snapshots or gutenberg-kg absent.
        """
        try:
            return self._corpus_lib().snapshot_diff(self._snapshots_dir(), a, b)
        except ImportError:
            return {"error": "gutenberg-kg is not installed"}
