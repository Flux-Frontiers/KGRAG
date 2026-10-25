"""
federation.py

The registry's knowledge graphs, served as one graph.

:class:`Federation` is what ``kgrag mcp`` serves: the fleet's canonical tools
(``stats``, ``query``, ``pack``, ``get_node``, ``neighbors``) answered across
every registered KG, with the same meanings they have on a single KG's server.

**Federated node ids.** A node id is unique inside its KG, not across KGs, so
the federation qualifies it with the KG's registry name: ``<kg>::<node id>``.
Every hit ``query`` returns carries this ``id``; ``get_node`` and ``neighbors``
take it; ``neighbors`` returns ids in the same form. ``::`` is chosen because no
fleet module puts it in a node id (theirs use single ``:``).

**Graph expansion.** A federated ``query`` with ``hop`` > 0 walks each hit's
neighbourhood inside its own KG, through that KG's ``neighbors()``, and ranks
what it reaches after every semantic hit. KGs whose backend cannot walk
neighbours contribute their hits alone.

Author: Eric G. Suchanek, PhD
"""

from __future__ import annotations

from collections.abc import Sequence
from pathlib import Path
from typing import Any

from kg_utils.stats import kg_stats
from kg_utils.validation import MAX_HOP, MAX_MAX_NODES, bounded_int

from kg_rag.orchestrator import KGRAG
from kg_rag.primitives import CrossHit, KGKind

__all__ = ["SEP", "Federation", "join_id", "split_id"]

#: Separates a KG's registry name from a node id inside it.
SEP = "::"


def join_id(kg_name: str, node_id: str) -> str:
    """Qualify *node_id* with its KG: ``<kg>::<node id>``."""
    return f"{kg_name}{SEP}{node_id}"


def split_id(federated_id: str) -> tuple[str, str]:
    """Split ``<kg>::<node id>`` into its KG name and node id.

    :raises ValueError: If *federated_id* has no ``::`` or an empty part.
    """
    kg_name, sep, node_id = federated_id.partition(SEP)
    if not sep or not kg_name or not node_id:
        raise ValueError(
            f"node_id must be '<kg>{SEP}<node id>', as query returns it; got {federated_id!r}"
        )
    return kg_name, node_id


class Federation:
    """Every KG in a registry, behind the canonical KG surface.

    :param registry_path: Registry file; ``None`` for ``KGRAG_REGISTRY`` or
        ``~/.kgrag/registry.sqlite``.
    :param project_root: Where ``[tool.kgrag]`` (embedder) config is looked up.
    """

    def __init__(self, registry_path: Path | None = None, project_root: Path | None = None) -> None:
        self.kgrag = KGRAG(registry_path=registry_path, project_root=project_root)
        self.project_root = project_root

    # What kg_utils.mcp's session banner reports.
    @property
    def repo_root(self) -> Path | None:
        """Where ``[tool.kgrag]`` config is read from."""
        return self.project_root

    @property
    def db_path(self) -> Path:
        """The registry file."""
        return self.kgrag.registry.db_path

    # ------------------------------------------------------------------
    # Canonical surface
    # ------------------------------------------------------------------

    def stats(self) -> dict[str, Any]:
        """Statistics for the whole federation, in the fleet shape.

        ``nodes`` and ``edges`` sum every available KG's own counts, by node
        kind and by relation. ``registry`` counts registered KGs by kind, and
        ``kgs`` gives each KG's totals, or why it is unavailable.

        :return: The fleet stats shape, ``kind`` ``"kgrag"``.
        """
        by_kind: dict[str, int] = {}
        by_rel: dict[str, int] = {}
        kgs: dict[str, dict[str, Any]] = {}
        entries = self.kgrag.registry.list()
        for entry in entries:
            adapter = self.kgrag._get_adapter(entry)  # pylint: disable=protected-access
            if adapter is None:
                kgs[entry.name] = {"kind": entry.kind.value, "available": False}
                continue
            try:
                fs = adapter.fleet_stats()
            except Exception as exc:  # pylint: disable=broad-exception-caught  # noqa: BLE001
                kgs[entry.name] = {"kind": entry.kind.value, "available": False, "error": str(exc)}
                continue
            for k, v in fs["nodes"]["by_kind"].items():
                by_kind[k] = by_kind.get(k, 0) + v
            for k, v in fs["edges"]["by_rel"].items():
                by_rel[k] = by_rel.get(k, 0) + v
            kgs[entry.name] = {
                "kind": entry.kind.value,
                "available": True,
                "nodes": fs["nodes"]["total"],
                "edges": fs["edges"]["total"],
            }
        reg = self.kgrag.registry.stats()
        return kg_stats(
            "kgrag",
            by_kind,
            by_rel,
            registry={
                "total": reg.total,
                "by_kind": reg.by_kind,
                "built": reg.built,
                "registry_path": str(reg.registry_path),
            },
            kgs=kgs,
        )

    def query(
        self,
        q: str,
        k: int = 8,
        *,
        hop: int = 0,
        max_nodes: int | None = None,
        rels: Sequence[str] | None = None,
        kinds: Sequence[str] | None = None,
        min_score: float = 0.0,
    ) -> dict[str, Any]:
        """Federated semantic query, optionally expanded through each KG's graph.

        :param q: Natural-language query.
        :param k: Hits per KG.
        :param hop: Hops to walk from each hit inside its own KG (0-5, default 0).
        :param max_nodes: Most results, hits first; ``None`` for no cap.
        :param rels: Relations to walk when *hop* > 0; ``None`` for all.
        :param kinds: Restrict to these KG kinds.
        :param min_score: Drop hits scoring below this.
        :return: ``{"query", "total_hits", "kgs_queried", "hits"}``; each hit
            has a federated ``id``, ``hop`` (0 for a semantic hit) and ``via_seed``.
        :raises ValueError: On an out-of-range *hop* or *max_nodes*, or an unknown kind.
        """
        bounded_int("hop", hop, 0, MAX_HOP)
        if max_nodes is not None:
            bounded_int("max_nodes", max_nodes, 1, MAX_MAX_NODES)
        result = self.kgrag.query(q, k=k, kinds=_kinds(kinds), min_score=min_score)
        hits = [_hit(h) for h in result.hits]
        if hop:
            hits += self._expand(hits, hop=hop, rels=rels)
        if max_nodes is not None:
            hits = hits[:max_nodes]
        return {
            "query": result.query,
            "total_hits": result.total_hits,
            "kgs_queried": result.kgs_queried,
            "hits": hits,
        }

    def pack(
        self,
        q: str,
        k: int = 8,
        *,
        hop: int = 0,
        max_nodes: int | None = None,
        rels: Sequence[str] | None = None,
        kinds: Sequence[str] | None = None,
        context: int = 5,
    ) -> str:
        """Federated snippet pack as Markdown, optionally with each snippet's neighbourhood.

        :param q: Natural-language query.
        :param k: Snippets per KG.
        :param hop: Hops to walk from each snippet's node (0-5, default 0);
            what is reached is listed after the snippets.
        :param max_nodes: Most snippets; ``None`` for no cap.
        :param rels: Relations to walk when *hop* > 0; ``None`` for all.
        :param kinds: Restrict to these KG kinds.
        :param context: Lines of context around code snippets.
        :return: The pack, rendered as Markdown.
        :raises ValueError: On an out-of-range *hop* or *max_nodes*, or an unknown kind.
        """
        bounded_int("hop", hop, 0, MAX_HOP)
        if max_nodes is not None:
            bounded_int("max_nodes", max_nodes, 1, MAX_MAX_NODES)
        result = self.kgrag.pack(q, k=k, context=context, kinds=_kinds(kinds))
        if max_nodes is not None:
            result.snippets = result.snippets[:max_nodes]
        text = result.render()
        if hop:
            seeds = [
                {"id": join_id(s.kg_name, s.node_id), "score": s.score} for s in result.snippets
            ]
            reached = self._expand(seeds, hop=hop, rels=rels)
            if reached:
                lines = [
                    f"- `{h['id']}` ({h['node_kind']}, {h['hop']} hop{'s' * (h['hop'] > 1)} "
                    f"from `{h['via_seed']}`) {h['name']}"
                    for h in reached
                ]
                text += "\n\n## Graph neighbourhood\n\n" + "\n".join(lines) + "\n"
        return text

    def node(self, node_id: str) -> dict[str, Any] | None:
        """Fetch one node by its federated id.

        :param node_id: ``<kg>::<node id>``.
        :return: The node, its ``id`` federated and its ``kg`` named; ``None``
            if the KG or the node does not exist.
        :raises ValueError: If *node_id* is not federated.
        """
        kg_name, inner = split_id(node_id)
        adapter = self._adapter(kg_name)
        if adapter is None:
            return None
        found = adapter.node(inner)
        return None if found is None else _federate_node(kg_name, found)

    def neighbors(
        self,
        node_id: str,
        *,
        rels: list[str] | None = None,
        direction: str = "both",
        limit: int = 50,
    ) -> dict[str, Any] | None:
        """A node's one-hop neighbourhood inside its own KG, with federated ids.

        :param node_id: ``<kg>::<node id>``.
        :param rels: Relation types to follow, or ``None`` for all.
        :param direction: ``"out"``, ``"in"`` or ``"both"``.
        :param limit: Maximum number of edges (1-500).
        :return: ``{"node", "edges", "nodes"}``; ``None`` for an unknown node or KG.
        :raises ValueError: If *node_id* is not federated, or on a bad argument.
        """
        kg_name, inner = split_id(node_id)
        adapter = self._adapter(kg_name)
        if adapter is None:
            return None
        near = adapter.neighbors(inner, rels=rels, direction=direction, limit=limit)
        if near is None:
            return None
        return {
            "node": _federate_node(kg_name, near["node"]),
            "edges": [
                {**e, "src": join_id(kg_name, e["src"]), "dst": join_id(kg_name, e["dst"])}
                for e in near["edges"]
            ],
            "nodes": [_federate_node(kg_name, n) for n in near["nodes"]],
        }

    def close(self) -> None:
        """Release the registries and every KG the federation opened."""
        for adapter in self.kgrag._adapters.values():  # pylint: disable=protected-access
            backend = getattr(adapter, "_kg", None)
            if backend is not None and hasattr(backend, "close"):
                backend.close()
        self.kgrag.close()

    # ------------------------------------------------------------------
    # Internals
    # ------------------------------------------------------------------

    def _adapter(self, kg_name: str):
        entry = self.kgrag.registry.get(kg_name)
        if entry is None:
            return None
        return self.kgrag._get_adapter(entry)  # pylint: disable=protected-access

    def _expand(
        self, seeds: list[dict[str, Any]], *, hop: int, rels: Sequence[str] | None
    ) -> list[dict[str, Any]]:
        """Walk *hop* hops from each seed inside its own KG; rank by hop, then seed score."""
        seen = {s["id"] for s in seeds}
        score = {s["id"]: float(s.get("score") or 0.0) for s in seeds}
        via = {s["id"]: s["id"] for s in seeds}
        frontier = [s["id"] for s in seeds]
        reached: list[dict[str, Any]] = []
        for h in range(1, hop + 1):
            found: list[dict[str, Any]] = []
            for fid in frontier:
                try:
                    near = self.neighbors(fid, rels=list(rels) if rels else None)
                except NotImplementedError:
                    continue
                if near is None:
                    continue
                for n in near["nodes"]:
                    if n["id"] in seen:
                        continue
                    seen.add(n["id"])
                    via[n["id"]] = via[fid]
                    found.append(
                        {
                            "id": n["id"],
                            "kg": n["kg"],
                            "name": n.get("name") or n.get("title") or "",
                            "node_kind": n.get("kind", ""),
                            "score": score[via[fid]] / (1 + h),
                            "hop": h,
                            "via_seed": via[fid],
                        }
                    )
            found.sort(key=lambda r: (-r["score"], r["id"]))
            reached += found
            frontier = [r["id"] for r in found]
        return reached


def _kinds(kinds: Sequence[str] | None) -> list[KGKind] | None:
    return [KGKind.from_str(k) for k in kinds] if kinds else None


def _hit(h: CrossHit) -> dict[str, Any]:
    return {
        "id": join_id(h.kg_name, h.node_id),
        "kg": h.kg_name,
        "kind": h.kg_kind.value,
        "node_id": h.node_id,
        "name": h.name,
        "node_kind": h.kind,
        "score": round(h.score, 4),
        "summary": h.summary,
        "source_path": h.source_path,
        "hop": 0,
        "via_seed": join_id(h.kg_name, h.node_id),
    }


def _federate_node(kg_name: str, node: dict[str, Any]) -> dict[str, Any]:
    return {**node, "id": join_id(kg_name, node["id"]), "kg": kg_name}
