"""_code_module_adapter.py -- shared KGAdapter for the tree-sitter code KGs.

``swift_kg.SwiftKG`` and ``tscode_kg.TypeScriptKG`` are ports of PyCodeKG to
other languages. Both subclass ``kg_utils.pipeline.KGModule``, take the same
``repo_root`` / ``db_path`` / ``vectors_path`` constructor, and return nodes
of the same shape (score under ``relevance``, source span under ``snippet``).
The per-language adapters differ only in which package they import and which
``KGKind`` they report, so they are thin subclasses of this one.

Author: Eric G. Suchanek, PhD
License: Elastic 2.0
"""

from __future__ import annotations

import importlib
from typing import Any, ClassVar

from kg_rag.adapters.base import KGAdapter, node_metadata
from kg_rag.primitives import CrossHit, CrossSnippet, KGEntry, KGKind, QueryScope


def _semantic(node: dict[str, Any]) -> float:
    """Raw cosine similarity of a node, falling back to the reranked score.

    ``relevance["score"]`` is normalised so the top hit of every query reads
    1.0, whatever its real relevance. That makes it useless for a semantic
    floor and for ranking one KG's hits against another's, so the code
    adapters use ``relevance["semantic"]``, as ``CodeKGAdapter`` does.
    """
    relevance = node.get("relevance") or {}
    return float(relevance.get("semantic", relevance.get("score", 0.0)))


class CodeModuleKGAdapter(KGAdapter):
    """Adapter for a ``KGModule``-based code KG in a language other than Python.

    Subclasses set :attr:`kg_kind`, :attr:`module_name`, :attr:`class_name`,
    :attr:`dist_name` and :attr:`store_dir`.

    :param entry: KGEntry whose kind is the subclass's :attr:`kg_kind`.
    """

    kg_kind: ClassVar[KGKind]
    module_name: ClassVar[str]
    class_name: ClassVar[str]
    dist_name: ClassVar[str]
    store_dir: ClassVar[str]

    def __init__(self, entry: KGEntry, embedder=None) -> None:
        super().__init__(entry, embedder=embedder)
        self._kg: Any = None

    def _load(self) -> None:
        if self._kg is not None:
            return
        try:
            module = importlib.import_module(self.module_name)
        except ImportError as exc:
            raise ImportError(
                f"{self.dist_name} is not installed. Install it with: pip install {self.dist_name}"
            ) from exc
        entry = self.entry
        store = entry.repo_path / self.store_dir
        self._kg = getattr(module, self.class_name)(
            repo_root=str(entry.repo_path),
            db_path=str(entry.sqlite_path) if entry.sqlite_path else str(store / "graph.sqlite"),
            vectors_path=(
                str(entry.vectors_path) if entry.vectors_path else str(store / "vectors.sqlite")
            ),
        )
        if self._embedder is not None:
            # Inject before KGModule.index is first touched, as CodeKGAdapter does.
            self._kg._embedder = self._embedder

    def is_available(self) -> bool:
        """Return True if the backing package is importable and the DB is built.

        :return: True if this adapter can serve queries.
        """
        try:
            importlib.import_module(self.module_name)
        except ImportError:
            return False
        return self.entry.is_built

    def query(
        self,
        q: str,
        k: int = 8,
        min_score: float = 0.0,
        semantic_floor: float = 0.0,
        scope: QueryScope | None = None,
    ) -> list[CrossHit]:
        """Query the code graph and return ranked hits.

        :param q: Natural-language query string.
        :param k: Number of results to return.
        :param min_score: Minimum semantic score; hits below this are dropped.
        :param semantic_floor: If the best hit's semantic score is below this
            value the entire result set is discarded.
        :param scope: Unused; code nodes carry no dates.
        :return: List of CrossHit objects ranked by score.
        """
        self._load()
        nodes = list(self._kg.query(q, k=k).nodes)[:k]
        if semantic_floor > 0.0 and nodes and _semantic(nodes[0]) < semantic_floor:
            return []
        hits = []
        for n in nodes:
            score = _semantic(n)
            if score < min_score:
                continue
            hits.append(
                CrossHit(
                    kg_name=self.entry.name,
                    kg_kind=self.kg_kind,
                    node_id=n.get("id", ""),
                    name=n.get("name", ""),
                    kind=n.get("kind", ""),
                    score=score,
                    summary=n.get("docstring") or "",
                    source_path=n.get("module_path") or "",
                    metadata=node_metadata(n),
                )
            )
        return hits

    def pack(
        self,
        q: str,
        k: int = 8,
        context: int = 5,
        semantic_floor: float = 0.0,
        scope: QueryScope | None = None,
    ) -> list[CrossSnippet]:
        """Return source snippets for matching code nodes.

        :param q: Natural-language query string.
        :param k: Number of snippets to return.
        :param context: Lines of context around each definition.
        :param semantic_floor: If the best snippet's semantic score is below
            this value the entire result set is discarded.
        :param scope: Unused; code nodes carry no dates.
        :return: List of CrossSnippet objects.
        """
        self._load()
        nodes = [n for n in self._kg.pack(q, k=k, context=context).nodes if n.get("snippet")]
        if semantic_floor > 0.0 and nodes and _semantic(nodes[0]) < semantic_floor:
            return []
        return [
            CrossSnippet(
                kg_name=self.entry.name,
                kg_kind=self.kg_kind,
                node_id=n.get("id", ""),
                source_path=n["snippet"].get("path", ""),
                content=n["snippet"].get("text", ""),
                score=_semantic(n),
                lineno=n["snippet"].get("start"),
                end_lineno=n["snippet"].get("end"),
                metadata=node_metadata(n),
            )
            for n in nodes
        ]

    def stats(self) -> dict[str, Any]:
        """Return live statistics about this code graph.

        :return: Standard envelope plus node and edge counts by kind.
        """
        self._load()
        db_size = 0.0
        if self.entry.sqlite_path and self.entry.sqlite_path.exists():
            db_size = round(self.entry.sqlite_path.stat().st_size / 1_048_576, 2)
        try:
            s = self._kg.stats()
            return {
                "kind": self.kg_kind.value,
                "kg_name": self.entry.name,
                "builder_version": self.entry.builder_version,
                "available": True,
                "db_size_mb": db_size,
                "node_count": s.get("meaningful_nodes", s.get("total_nodes", 0)),
                "edge_count": s.get("total_edges", 0),
                "node_counts": s.get("node_counts", {}),
                "docstring_coverage": s.get("docstring_coverage", 0.0),
            }
        except Exception as exc:  # pylint: disable=broad-exception-caught
            return {
                "kind": self.kg_kind.value,
                "kg_name": self.entry.name,
                "available": True,
                "db_size_mb": db_size,
                "error": str(exc),
            }

    def analyze(self) -> str:
        """Run the module's own analysis.

        :return: Markdown-formatted analysis report.
        """
        self._load()
        try:
            return self._kg.analyze()
        except Exception as exc:  # pylint: disable=broad-exception-caught
            return f"# {self.class_name} Analysis\n\nAnalysis failed: {exc}\n"

    def _collect_snapshot_metrics(self) -> dict[str, Any]:
        """Return node and edge counts for the snapshot."""
        try:
            self._load()
            s = self._kg.stats()
            return {
                "total_nodes": s.get("total_nodes", 0),
                "total_edges": s.get("total_edges", 0),
                "meaningful_nodes": s.get("meaningful_nodes", 0),
                "node_counts": s.get("node_counts", {}),
            }
        except Exception:  # pylint: disable=broad-exception-caught
            return {}
