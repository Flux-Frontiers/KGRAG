"""connectome_adapter.py -- KGAdapter for ConnectomeKG.

Wraps the ``connectomekg.ConnectomeKG`` class (PyPI/repo ``connectome_kg``).
Surfaces a synapse-resolution connectome -- neurons, cell types, neuropils,
hemilineages, labels and ontology terms, built from a FlyWire Codex release --
through the standard KGRAG federation interface.

A connectome has no source files, so unlike the code and document kinds its
nodes carry no source span and ``KGModule.pack()`` returns no ``snippet`` for
them. Each node's ``docstring`` is instead a full English description ("Cell
type DNp01: 2 neurons (1 left, 1 right); descending, ..."), and that is what
this adapter packs.

Author: Eric G. Suchanek, PhD
License: Elastic 2.0
"""

from __future__ import annotations

from typing import Any

from kg_rag.adapters.base import KGAdapter, node_metadata
from kg_rag.primitives import CrossHit, CrossSnippet, KGEntry, KGKind, QueryScope


class ConnectomeKGAdapter(KGAdapter):
    """Adapter wrapping the ``connectomekg.ConnectomeKG`` class.

    :param entry: KGEntry with ``kind=KGKind.CONNECTOME``.
    """

    def __init__(self, entry: KGEntry, embedder=None) -> None:
        super().__init__(entry, embedder=embedder)
        self._kg: Any = None

    def _load(self) -> None:
        if self._kg is not None:
            return
        try:
            from connectomekg import ConnectomeKG  # pylint: disable=import-outside-toplevel
        except ImportError as exc:
            raise ImportError(
                "connectome-kg is not installed. Install it from "
                "https://github.com/Flux-Frontiers/connectome_kg"
            ) from exc
        entry = self.entry
        kwargs: dict[str, Any] = {}
        if entry.sqlite_path:
            kwargs["db_path"] = str(entry.sqlite_path)
        if entry.vectors_path:
            kwargs["vectors_path"] = str(entry.vectors_path)
        self._kg = ConnectomeKG(str(entry.repo_path), **kwargs)

    def is_available(self) -> bool:
        """Return True if connectomekg is importable and both stores exist.

        Stricter than the other kinds' ``entry.is_built``, which accepts either
        store. ``ConnectomeKG.query()`` raises ``FileNotFoundError`` when there
        is no vector index, and a connectome can legitimately be built without
        one (``connkg build --no-index``). Reporting such a KG as available
        would make every federated query against it fail rather than skip it.

        :return: True if this adapter can serve queries.
        """
        try:
            import connectomekg  # noqa: F401  # pylint: disable=import-outside-toplevel
        except ImportError:
            return False
        entry = self.entry
        return bool(
            entry.sqlite_path
            and entry.sqlite_path.exists()
            and entry.vectors_path
            and entry.vectors_path.exists()
        )

    @staticmethod
    def _score(node: dict[str, Any]) -> float:
        # Raw cosine similarity. kg_utils.pipeline also reports a reranked
        # "score", but it is normalised so every query's top hit reads 1.0,
        # which would make semantic_floor a no-op and rank this KG's best hit
        # level with every other KG's in a federated query.
        relevance = node.get("relevance") or {}
        return float(relevance.get("semantic", relevance.get("score", 0.0)))

    def query(
        self,
        q: str,
        k: int = 8,
        min_score: float = 0.0,
        semantic_floor: float = 0.0,
        scope: QueryScope | None = None,
    ) -> list[CrossHit]:
        """Query the connectome and return ranked hits.

        :param q: Natural-language query string.
        :param k: Number of results to return.
        :param min_score: Minimum relevance score; hits below this are dropped.
        :param semantic_floor: If the best hit's score is below this value the
            entire result set is discarded.
        :param scope: Unused; connectome nodes carry no dates.
        :return: List of CrossHit objects ranked by score.
        """
        self._load()
        nodes = list(self._kg.query(q, k=k).nodes)[:k]
        if semantic_floor > 0.0 and nodes and self._score(nodes[0]) < semantic_floor:
            return []
        hits = []
        for n in nodes:
            score = self._score(n)
            if score < min_score:
                continue
            hits.append(
                CrossHit(
                    kg_name=self.entry.name,
                    kg_kind=KGKind.CONNECTOME,
                    node_id=n.get("id", ""),
                    name=n.get("name", ""),
                    kind=n.get("kind", ""),
                    score=score,
                    summary=n.get("docstring", ""),
                    source_path=n.get("module_path", ""),
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
        """Return a description snippet for each matching connectome node.

        :param q: Natural-language query string.
        :param k: Number of snippets to return.
        :param context: Unused; connectome nodes have no source span.
        :param semantic_floor: If the best snippet's score is below this value
            the entire result set is discarded.
        :param scope: Unused; connectome nodes carry no dates.
        :return: List of CrossSnippet objects.
        """
        self._load()
        nodes = [n for n in self._kg.pack(q, k=k).nodes if n.get("docstring")][:k]
        if semantic_floor > 0.0 and nodes and self._score(nodes[0]) < semantic_floor:
            return []
        return [
            CrossSnippet(
                kg_name=self.entry.name,
                kg_kind=KGKind.CONNECTOME,
                node_id=n.get("id", ""),
                source_path=n.get("module_path", ""),
                content=f"{n.get('name', '')} ({n.get('kind', '')})\n\n{n['docstring']}",
                score=self._score(n),
                metadata=node_metadata(n),
            )
            for n in nodes
        ]

    def stats(self) -> dict[str, Any]:
        """Return live statistics about this ConnectomeKG instance.

        :return: Dict with kind, node/edge counts, and connectome counts.
        """
        self._load()
        db_size = 0.0
        if self.entry.sqlite_path and self.entry.sqlite_path.exists():
            db_size = round(self.entry.sqlite_path.stat().st_size / 1_048_576, 2)
        try:
            s = self._kg.stats()
            nodes = s.get("node_counts", {})
            return {
                "kind": "connectome",
                "kg_name": self.entry.name,
                "builder_version": self.entry.builder_version,
                "available": True,
                "db_size_mb": db_size,
                "node_count": s.get("total_nodes", 0),
                "edge_count": s.get("total_edges", 0),
                "neuron_count": nodes.get("neuron", 0),
                "cell_type_count": nodes.get("cell_type", 0),
                "neuropil_count": nodes.get("neuropil", 0),
                "synapse_pair_count": s.get("edge_counts", {}).get("SYNAPSES_TO", 0),
            }
        except Exception as exc:  # pylint: disable=broad-exception-caught
            return {
                "kind": "connectome",
                "kg_name": self.entry.name,
                "available": True,
                "db_size_mb": db_size,
                "error": str(exc),
            }

    def analyze(self) -> str:
        """Run analysis on this ConnectomeKG instance.

        :return: Markdown-formatted analysis report.
        """
        self._load()
        try:
            return self._kg.analyze()
        except Exception as exc:  # pylint: disable=broad-exception-caught
            return f"# ConnectomeKG Analysis\n\nAnalysis failed: {exc}\n"

    def _collect_snapshot_metrics(self) -> dict[str, Any]:
        """Return connectome-specific metrics for the snapshot."""
        try:
            self._load()
            s = self._kg.stats()
            nodes = s.get("node_counts", {})
            return {
                "total_nodes": s.get("total_nodes", 0),
                "total_edges": s.get("total_edges", 0),
                "neuron_count": nodes.get("neuron", 0),
                "cell_type_count": nodes.get("cell_type", 0),
            }
        except Exception:  # pylint: disable=broad-exception-caught
            return {}
