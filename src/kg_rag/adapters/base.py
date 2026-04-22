"""
base.py

Abstract adapter protocol for all KG backends.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import UTC, datetime
from typing import Any

from kg_rag.primitives import CrossHit, CrossSnippet, KGEntry
from kg_rag.viz import DisplayMode, Viewport


class KGAdapter(ABC):
    """Abstract base for KG adapters (CodeKG, DocKG, MetaKG).

    Each adapter wraps the specific KG library and exposes a uniform
    interface for querying, packing, and introspecting a single KG instance.

    :param entry: The KGEntry this adapter serves.
    """

    def __init__(self, entry: KGEntry) -> None:
        self.entry = entry

    @abstractmethod
    def is_available(self) -> bool:
        """Return True if the underlying KG library is installed and the DB exists.

        :return: True if this adapter can serve queries.
        """

    @abstractmethod
    def query(self, q: str, k: int = 8, min_score: float = 0.0) -> list[CrossHit]:
        """Query the KG and return ranked hits.

        :param q: Natural-language query string.
        :param k: Number of results to return.
        :param min_score: Minimum relevance score; hits below this are dropped.
        :return: List of CrossHit objects ranked by score.
        """

    @abstractmethod
    def pack(self, q: str, k: int = 8, context: int = 5) -> list[CrossSnippet]:
        """Query the KG and return source snippets.

        :param q: Natural-language query string.
        :param k: Number of snippets to return.
        :param context: Lines of context around code (code KGs only).
        :return: List of CrossSnippet objects.
        """

    @abstractmethod
    def stats(self) -> dict[str, Any]:
        """Return basic statistics about this KG instance.

        :return: Dict with node_count, edge_count, or equivalent metrics.
        """

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
    # Internal helpers — used by the orchestrator, not part of the public API
    # ------------------------------------------------------------------

    def _graph_stats(self) -> dict[str, int]:
        """Return raw graph topology counts for this KG instance.

        Unlike :meth:`stats`, this method strips all KG-kind-specific or
        semantic fields and always returns a plain ``{node_count, edge_count}``
        mapping with integer values.  Unavailable or non-integer counts are
        normalised to ``0``.

        This is an internal helper called by the orchestrator when it needs to
        aggregate graph-size metrics uniformly across heterogeneous KG kinds
        without being confused by domain-specific keys.

        :return: Dict with integer ``node_count`` and ``edge_count``.
        """
        raw = self.stats()

        def _to_int(val: Any) -> int:
            try:
                return int(val)
            except (TypeError, ValueError):
                return 0

        return {
            "node_count": _to_int(raw.get("node_count")),
            "edge_count": _to_int(raw.get("edge_count")),
        }
