"""
base.py

Abstract adapter protocol for all KG backends.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import UTC, datetime
from typing import Any

from kg_utils.stats import kg_stats, stats_problems
from kg_utils.temporal import TEMPORAL_KEYS

from kg_rag.primitives import CrossHit, CrossSnippet, KGEntry, QueryScope
from kg_rag.viz import DisplayMode, Viewport


class KGAdapter(ABC):
    """Abstract base for KG adapters (CodeKG, DocKG, MetaKG).

    Each adapter wraps the specific KG library and exposes a uniform
    interface for querying, packing, and introspecting a single KG instance.

    :param entry: The KGEntry this adapter serves.
    :param embedder: Optional shared embedding backend.  When provided,
        adapters that wrap a ``KGModule``-based backend inject this object
        into the underlying KG's ``_embedder`` slot before the first query,
        replacing the default ``SentenceTransformerEmbedder`` with whatever
        backend the caller has configured (e.g.
        :class:`~kg_rag.embed.LlamaCppEmbedder`).  ``None`` means each KG
        library uses its own built-in default.
    """

    #: Whether this adapter can push a :class:`~kg_rag.primitives.QueryScope`
    #: down into its backend retrieval.  When False, the orchestrator applies
    #: the scope as a best-effort post-filter on returned hits/snippets instead.
    #: Subclasses that accept a ``scope`` argument on :meth:`query`/:meth:`pack`
    #: and forward it to their backend should override this to True.
    supports_scope: bool = False

    def __init__(self, entry: KGEntry, embedder=None) -> None:
        self.entry = entry
        self._embedder = embedder

    @abstractmethod
    def is_available(self) -> bool:
        """Return True if the underlying KG library is installed and the DB exists.

        :return: True if this adapter can serve queries.
        """

    @abstractmethod
    def query(
        self,
        q: str,
        k: int = 8,
        min_score: float = 0.0,
        semantic_floor: float = 0.0,
        scope: QueryScope | None = None,
    ) -> list[CrossHit]:
        """Query the KG and return ranked hits.

        :param q: Natural-language query string.
        :param k: Number of results to return.
        :param min_score: Minimum relevance score; hits below this are dropped.
        :param semantic_floor: Minimum score the best hit must reach.  If the
            top result is below this value the entire result set is discarded
            rather than returning k noisy near-neighbor hits.  Set to e.g.
            ``0.5`` to silence KGs that have no domain-relevant content for
            the query.
        :param scope: Optional :class:`~kg_rag.primitives.QueryScope`
            restricting retrieval to a source-path subtree and/or node kinds.
            Adapters with :attr:`supports_scope` push it into their backend;
            others may ignore it (the orchestrator post-filters on the result).
        :return: List of CrossHit objects ranked by score.
        """

    @abstractmethod
    def pack(
        self,
        q: str,
        k: int = 8,
        context: int = 5,
        semantic_floor: float = 0.0,
        scope: QueryScope | None = None,
    ) -> list[CrossSnippet]:
        """Query the KG and return source snippets.

        :param q: Natural-language query string.
        :param k: Number of snippets to return.
        :param context: Lines of context around code (code KGs only).
        :param semantic_floor: Minimum score the best result must reach.  If
            the top result is below this value the entire result set is
            discarded.  Mirrors the behaviour of the same parameter on
            :meth:`query`.
        :param scope: Optional :class:`~kg_rag.primitives.QueryScope`
            restricting retrieval; see :meth:`query`.
        :return: List of CrossSnippet objects.
        """

    @staticmethod
    def _doc_scope_kwargs(scope: QueryScope | None) -> dict[str, Any]:
        """Translate a :class:`QueryScope` into doc_kg pushdown keyword args.

        Returns the ``source_path_prefixes`` / ``node_kinds`` keywords accepted
        by ``DocKG.query``/``DocKG.pack`` (doc-backed adapters), omitting any
        constraint that is unset.  Returns an empty dict for a ``None`` or empty
        scope so callers can ``**``-splat it unconditionally.

        :param scope: The scope to translate, or None.
        :return: Keyword arguments suitable for the underlying DocKG call.
        """
        if not scope:
            return {}
        kwargs: dict[str, Any] = {}
        if scope.source_path_prefixes:
            kwargs["source_path_prefixes"] = scope.source_path_prefixes
        if scope.node_kinds:
            kwargs["node_kinds"] = scope.node_kinds
        return kwargs

    def stats(self) -> dict[str, Any]:
        """Return this KG's statistics: the fleet shape plus the adapter's envelope.

        ``{"kind", "nodes": {"total", "by_kind"}, "edges": {"total", "by_rel"}}``
        and the backend's own measures, from :meth:`fleet_stats`, with
        ``kg_name``, ``available``, ``builder_version`` and ``db_size_mb``
        added. ``kind`` is the registry kind. On failure the counts are empty
        and ``error`` says why. Adapters for backends without a ``stats()`` of
        their own override this.

        :return: The statistics dict.
        """
        kind = self.entry.kind.value
        if getattr(self, "_kg", None) is None and not self.is_available():
            return {**kg_stats(kind, {}, {}), **self._envelope(), "available": False}
        try:
            out = self.fleet_stats()
        except Exception as exc:  # pylint: disable=broad-exception-caught  # noqa: BLE001
            out = kg_stats(kind, {}, {}, error=str(exc))
        return {**out, **self._envelope(), "kind": kind}

    def _envelope(self) -> dict[str, Any]:
        """The registry-side facts every adapter's :meth:`stats` reports."""
        path = self.entry.sqlite_path
        size = round(path.stat().st_size / 1_048_576, 2) if path and path.exists() else 0.0
        return {
            "kg_name": self.entry.name,
            "available": True,
            "builder_version": self.entry.builder_version,
            "db_size_mb": size,
        }

    @abstractmethod
    def analyze(self) -> str:
        """Run full analysis on this KG and return a Markdown-formatted report.

        Every adapter must implement this method. The report format is
        adapter-specific but must be valid Markdown so callers can render,
        save, or forward it uniformly.

        :return: Markdown-formatted analysis report string.
        """
        return ""

    # ------------------------------------------------------------------
    # Snapshot — concrete template method
    # ------------------------------------------------------------------

    def snapshot(self, version: str, label: str | None = None) -> dict[str, Any]:
        """Capture a point-in-time snapshot of this KG's state.

        **Template method** — builds a standard envelope from
        :meth:`_graph_stats` and merges in any domain-specific data returned
        by :meth:`_collect_snapshot_metrics`.  Subclasses should **not**
        override this method; override ``_collect_snapshot_metrics()`` instead.

        The returned dict always contains:

        * ``version`` — the caller-supplied version string
        * ``label`` — optional human-readable label
        * ``timestamp`` — ISO 8601 UTC timestamp
        * ``kind`` — KG kind value (e.g. ``"code"``, ``"doc"``)
        * ``kg_name`` — registered KG name
        * ``node_count`` / ``edge_count`` — topology counts

        :param version: Semantic-version string for this snapshot (e.g. "1.2.0").
        :param label: Optional human-readable label for the snapshot.
        :return: Serialisable snapshot dict.
        """
        gs = self._graph_stats()
        snap: dict[str, Any] = {
            "version": version,
            "label": label,
            "timestamp": datetime.now(UTC).isoformat(),
            "kind": self.entry.kind.value,
            "kg_name": self.entry.name,
            "node_count": gs["node_count"],
            "edge_count": gs["edge_count"],
        }
        extra = self._collect_snapshot_metrics()
        if extra:
            snap.update(extra)
        return snap

    def _collect_snapshot_metrics(self) -> dict[str, Any]:
        """Return additional domain-specific metrics for the snapshot.

        Override in subclasses to add data beyond the standard envelope.
        For example, a code adapter might add ``docstring_coverage``,
        ``critical_issues``, or ``module_node_counts``.

        The default implementation returns an empty dict — adapters that
        have no domain-specific metrics need not override this.

        :return: Dict of extra key-value pairs to merge into the snapshot.
        """
        return {}

    # ------------------------------------------------------------------
    # Viewport display
    # ------------------------------------------------------------------

    def display(self, viewport: Viewport) -> None:
        """Render this KG's visualization into the provided viewport.

        Subclasses must override this method to produce one or both display modes:

        * ``DisplayMode.SEMANTIC`` — render the KG as a tree in the
          TreeOfKnowledge forest.  Tree shape, size, branch density, colour
          saturation, and fresh-tip colour encode structural and temporal
          properties per the VISION specification.

        * ``DisplayMode.ONTOLOGICAL`` — render the KG's internal graph topology
          as a 2-D node-link diagram.  Nodes coloured by kind; edges by relation
          type; layout force-directed or hierarchical based on KG kind.

        **Rendering contract:**

        * All Streamlit (or other UI framework) calls must target
          ``viewport.container``, never the global ``st`` module, so that output
          is confined to the allocated region.
        * Do not raise exceptions — catch internal errors and render a fallback
          error card inside the viewport instead.
        * Respect ``viewport.width`` and ``viewport.height`` when sizing charts
          or canvas elements (``0`` means fill available).

        The base implementation renders a placeholder card so that stub adapters
        participate in the visualizer without crashing it.  Override to provide
        the real visualization.

        :param viewport: The rectangular display region to render into.
        """
        self._display_stub(viewport)

    def _display_stub(self, viewport: Viewport) -> None:
        """Render a placeholder card for adapters that have not yet implemented display().

        Dispatches to the correct backend stub based on ``viewport.backend``:

        * :attr:`~kg_rag.viz.RenderBackend.QT2D` — draws a synthetic tree or
          node-link diagram into the ``QGraphicsScene`` via
          :mod:`kg_rag.viz_qt`.
        * :attr:`~kg_rag.viz.RenderBackend.STREAMLIT` — renders an HTML info
          card into the Streamlit container.

        :param viewport: The viewport to render into.
        """
        from kg_rag.viz import RenderBackend  # pylint: disable=import-outside-toplevel

        if viewport.backend == RenderBackend.QT2D:
            self._display_stub_qt(viewport)
        else:
            self._display_stub_streamlit(viewport)

    def _display_stub_qt(self, viewport: Viewport) -> None:
        """Draw a synthetic placeholder into a QGraphicsScene (Qt2D backend)."""
        try:
            from kg_rag.viz_qt import (  # pylint: disable=import-outside-toplevel
                draw_stub_ontological,
                draw_stub_semantic,
            )
        except ImportError:
            return  # PyQt5 not installed

        scene = viewport.container
        if viewport.mode == DisplayMode.SEMANTIC:
            draw_stub_semantic(scene, self)
        else:
            draw_stub_ontological(scene, self)

    def _display_stub_streamlit(self, viewport: Viewport) -> None:
        """Render an HTML info card into a Streamlit container."""
        try:
            import streamlit as st  # pylint: disable=import-outside-toplevel
        except ImportError:
            return

        ct = viewport.container
        available = self.is_available()
        kind = self.entry.kind.value
        name = viewport.title or self.entry.name
        mode_label = (
            "Semantic (forest)" if viewport.mode == DisplayMode.SEMANTIC else "Ontological (graph)"
        )

        _COLOR = {
            "code": "#4A90D9",
            "doc": "#27AE60",
            "meta": "#8E44AD",
            "diary": "#E67E22",
            "verse": "#1ABC9C",
            "memory": "#F39C12",
            "disulfide": "#E74C3C",
            "pdbfile": "#95A5A6",
            "legal": "#8B4513",
            "person": "#FF69B4",
        }
        color = _COLOR.get(kind, "#95A5A6")

        with ct:
            st.markdown(
                f"<div style='border-left:4px solid {color};"
                f"border-radius:6px;padding:10px 14px;background:#1e1e2e;'>"
                f"<span style='background:{color};color:#fff;border-radius:4px;"
                f"padding:2px 8px;font-size:11px;font-weight:bold;font-family:monospace;'>"
                f"{kind}</span>&nbsp;&nbsp;"
                f"<b style='color:#f0f0f0;font-size:14px;'>{name}</b><br>"
                f"<span style='color:#888;font-size:11px;'>mode: {mode_label}</span>"
                f"</div>",
                unsafe_allow_html=True,
            )
            if available:
                gs = self._graph_stats()
                c1, c2 = ct.columns(2)
                c1.metric("Nodes", gs["node_count"])
                c2.metric("Edges", gs["edge_count"])
                ct.caption(f"_display() not yet implemented for `{self.__class__.__name__}`_")
            else:
                ct.warning(f"KG `{name}` is not built or its library is not installed.")

    def __repr__(self) -> str:
        return (
            f"{self.__class__.__name__}("
            f"name={self.entry.name!r}, "
            f"kind={self.entry.kind.value!r}, "
            f"available={self.is_available()!r})"
        )

    # ------------------------------------------------------------------
    # The canonical graph surface: the backend's own stats, node, neighbors
    # ------------------------------------------------------------------

    def _backend(self) -> Any:
        """Return the loaded backend KG, or ``None`` if this adapter has none.

        Every module-backed adapter follows one convention: ``_load()`` builds
        the backend and stores it as ``self._kg``.

        :return: The backend object, or ``None``.
        """
        load = getattr(self, "_load", None)
        if load is not None:
            load()
        return getattr(self, "_kg", None)

    def fleet_stats(self) -> dict[str, Any]:
        """Return the backend's statistics in the fleet shape (``kg_utils.stats``).

        ``{"kind", "nodes": {"total", "by_kind"}, "edges": {"total", "by_rel"}}``
        plus the backend's own keys. A backend already in the shape is passed
        through; one released before the shape (settled 2026-10-25) is read
        here, once, for every adapter, so no adapter translates on its own:

        * ``node_counts`` / ``edge_counts`` become ``by_kind`` / ``by_rel``;
        * the total is ``total_nodes``, ``node_count`` or an integer ``nodes``
          (likewise for edges), and whatever part of it the breakdown does not
          cover is filed under ``"(unreported)"``, so the two always agree.

        A domain measure such as ``meaningful_nodes`` is never taken for the
        total.

        :return: The statistics in the fleet shape.
        """
        kind = self.entry.kind.value
        backend = self._backend()
        if backend is not None and hasattr(backend, "stats"):
            raw = backend.stats()
        elif type(self).stats is not KGAdapter.stats:
            raw = self.stats()  # an adapter with its own stats() and no backend
        else:
            return kg_stats(kind, {}, {})
        if not stats_problems(raw):
            return {**raw, "kind": kind}
        if not isinstance(raw, dict):
            raise TypeError(f"{kind} backend stats() returned {type(raw).__name__}, not a dict")

        def breakdown(counts_key: str, *total_keys: str) -> dict[str, int]:
            counts = raw.get(counts_key)
            by = (
                {str(k): v for k, v in counts.items() if isinstance(v, int)}
                if isinstance(counts, dict)
                else {}
            )
            total = next(
                (
                    raw[k]
                    for k in total_keys
                    if isinstance(raw.get(k), int) and not isinstance(raw.get(k), bool)
                ),
                sum(by.values()),
            )
            if total > sum(by.values()):
                by["(unreported)"] = total - sum(by.values())
            return by

        legacy = {
            "kind", "nodes", "edges", "node_count", "edge_count",
            "total_nodes", "total_edges", "node_counts", "edge_counts",
        }  # fmt: skip
        return kg_stats(
            kind,
            breakdown("node_counts", "total_nodes", "node_count", "nodes"),
            breakdown("edge_counts", "total_edges", "edge_count", "edges"),
            **{k: v for k, v in raw.items() if k not in legacy},
        )

    def node(self, node_id: str) -> dict[str, Any] | None:
        """Fetch one node from the backend by its own (unqualified) ID.

        :param node_id: The node's ID inside this KG.
        :return: The node dict, or ``None`` if the KG has no such node.
        :raises NotImplementedError: If the backend has no ``node()``.
        """
        backend = self._backend()
        if backend is None or not hasattr(backend, "node"):
            raise NotImplementedError(f"{self.entry.kind.value} KGs cannot fetch a node by id")
        return backend.node(node_id)

    def neighbors(
        self,
        node_id: str,
        *,
        rels: list[str] | None = None,
        direction: str = "both",
        limit: int = 50,
    ) -> dict[str, Any] | None:
        """Return a node's one-hop neighbourhood from the backend.

        :param node_id: The node's ID inside this KG.
        :param rels: Relation types to follow, or ``None`` for all.
        :param direction: ``"out"``, ``"in"`` or ``"both"``.
        :param limit: Maximum number of edges.
        :return: ``{"node", "edges", "nodes"}``, or ``None`` for an unknown node.
        :raises NotImplementedError: If the backend has no ``neighbors()``.
        """
        backend = self._backend()
        if backend is None or not hasattr(backend, "neighbors"):
            raise NotImplementedError(f"{self.entry.kind.value} KGs cannot walk neighbours yet")
        return backend.neighbors(node_id, rels=rels, direction=direction, limit=limit)

    # ------------------------------------------------------------------
    # Internal helpers — used by the orchestrator, not part of the public API
    # ------------------------------------------------------------------

    def _graph_stats(self) -> dict[str, int]:
        """Return this KG's total node and edge counts, from :meth:`fleet_stats`.

        Every row counts: a backend's narrower measure (``meaningful_nodes``)
        no longer stands in for the total, so totals compare across KGs.
        Failures normalise to ``0``.

        :return: Dict with integer ``node_count`` and ``edge_count``.
        """
        try:
            fs = self.fleet_stats()
            return {"node_count": fs["nodes"]["total"], "edge_count": fs["edges"]["total"]}
        except Exception:  # pylint: disable=broad-exception-caught  # noqa: BLE001
            return {"node_count": 0, "edge_count": 0}


def stat_totals(stats: dict[str, Any]) -> tuple[int | None, int | None]:
    """Return ``(nodes, edges)`` totals from a stats dict in the fleet shape.

    :param stats: An adapter's :meth:`KGAdapter.stats`.
    :return: The totals, or ``None`` for each one the dict does not report
        (an unavailable KG, or a backend with no graph counts).
    """
    out: list[int | None] = []
    for section in ("nodes", "edges"):
        part = stats.get(section)
        total = part.get("total") if isinstance(part, dict) else None
        out.append(total if isinstance(total, int) else None)
    return out[0], out[1]


def node_metadata(node: dict[str, Any]) -> dict[str, Any]:
    """Extract a node's metadata mapping from a backend query result.

    Backends differ in how they surface it: ``kg_utils.store`` returns a
    decoded ``metadata`` dict, while some modules flatten the temporal contract
    keys onto the node itself.  This reads both, preferring the nested mapping
    and falling back to any contract keys found at the top level, so an adapter
    populates :attr:`~kg_rag.primitives.CrossHit.metadata` with one call
    regardless of which shape its backend uses.

    Returning ``{}`` for a node with no metadata is meaningful rather than
    merely empty: a ``time_range`` scope treats an undated result as out of
    scope, so a backend that carries no dates drops out of time-scoped queries
    instead of matching everything.

    :param node: A node dict from a backend query result.
    :return: The node's metadata mapping, possibly empty.
    """
    raw = node.get("metadata")
    if isinstance(raw, dict) and raw:
        return dict(raw)
    flat = {k: node[k] for k in TEMPORAL_KEYS if node.get(k)}
    return flat
