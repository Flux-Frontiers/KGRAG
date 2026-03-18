"""
viz.py

Viewport abstraction for the KGRAG visualizer.

A Viewport is a rectangular region of the KGRAG visualizer canvas that has been
allocated to a single KG adapter.  Adapters receive a Viewport via their
``KGAdapter.display(viewport)`` call and must confine all rendering to it.

Two display modes are defined:

* ``DisplayMode.SEMANTIC``    — render the KG as a tree in the TreeOfKnowledge
  forest.  Visual encoding follows the VISION spec: node count → height, edge/
  node ratio → branch density, KG kind → species/shape, semantic coverage →
  colour saturation, recent snapshot delta → fresh-tip colour.

* ``DisplayMode.ONTOLOGICAL`` — render the KG's graph topology as a 2-D (or 3-D)
  node-link diagram.  Nodes are coloured by their kind (function, class, chunk,
  section, …); edges are coloured by relation type; layout is force-directed by
  default, or hierarchical/radial where the KG kind implies a natural ordering.

The rendering context (``Viewport.container``) is typed as ``Any`` so the same
interface works across Streamlit (the current host), future web-canvas frontends,
PyGame/OpenGL viewports, or terminal renderers.  Adapters must call Streamlit
methods on ``viewport.container``, never on the ``st`` module directly, ensuring
their output is confined to the allocated region.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any


class RenderBackend(StrEnum):
    """UI host that owns the Viewport.

    Adapters inspect this to decide which rendering API to use when
    ``display()`` is called.  They must never import a backend's library at
    module level — all UI imports must be deferred inside the ``display()``
    implementation so that the adapter module remains importable regardless of
    which extras are installed.
    """

    STREAMLIT = "streamlit"
    """Streamlit web app.  ``Viewport.container`` is a ``DeltaGenerator``
    (Streamlit container / column).  Render by calling Streamlit methods on
    ``viewport.container``."""

    QT2D = "qt2d"
    """PyQt5 2-D canvas.  ``Viewport.container`` is a ``QGraphicsScene``.
    Render by adding ``QGraphicsItem`` objects to the scene."""

    QT3D = "qt3d"
    """PyQt5/PyVista 3-D canvas.  ``Viewport.container`` is a
    ``pyvistaqt.QtInteractor``.  Render by adding PyVista meshes to the
    interactor's plotter."""


class DisplayMode(StrEnum):
    """Rendering mode requested by the KGRAG visualizer for a KG adapter.

    Pass this inside a :class:`Viewport` to tell the adapter which kind of
    visualization to produce.
    """

    SEMANTIC = "semantic"
    """Semantic / forest-tree view.

    Render the KG as a single tree in the TreeOfKnowledge forest.  The tree is
    a *direct visual encoding* of the KG's structural properties:

    * **Overall size / height** — proportional to ``node_count``
    * **Branch density / complexity** — proportional to ``edge_count / node_count``
    * **Species (trunk shape, branching style)** — determined by ``KGKind``:
      - ``code`` → dense symmetrical conifer (deep call graphs, many short branches)
      - ``doc`` → mid-density broadleaf (section hierarchy, cross-references)
      - ``diary`` → gnarled deciduous (irregular temporal branches)
      - ``meta`` → intricate lattice (metabolic cycles visible as loops)
      - ``legal`` → strict columnar cypress (statutory hierarchy)
      - ``verse`` → layered canopy (book → chapter → verse strata)
      - ``memory`` → sprawling oak (associative, high branching factor)
      - ``pdbfile`` / ``disulfide`` → crystalline / fractal coral
      - ``person`` → grove anchor — draws nearby trees closer
    * **Colour saturation** — encodes semantic coverage score
    * **Fresh green tips** — encodes recent activity (positive snapshot delta)
    * **Bark patina / texture** — encodes age (``KGEntry.created_at``)

    Person corpora render as a *grove*: a cluster of close-standing trees whose
    canopies touch, one tree per member KG.
    """

    ONTOLOGICAL = "ontological"
    """Ontological / structural node-link view.

    Render the KG's internal graph topology as a 2-D diagram.  Intended as an
    *analytical instrument* — not decorative — for inspecting the structural
    shape of a compiled knowledge graph:

    * **Nodes** — circles sized by degree, coloured by node kind:
      - ``module`` → steel blue    (#4A90D9)
      - ``class`` → amber          (#E67E22)
      - ``function`` → forest green (#27AE60)
      - ``method`` → violet         (#8E44AD)
      - ``chunk`` → gold            (#F39C12)
      - ``section`` → teal          (#1ABC9C)
      - ``entity`` → crimson        (#E74C3C)
    * **Edges** — lines coloured by relation type (``calls``, ``imports``,
      ``references``, ``contains``, ``linked_to``, …)
    * **Layout** — force-directed (Fruchterman–Reingold) by default; radial or
      hierarchical for KG kinds with a natural ordering (``legal``, ``verse``,
      ``diary``)
    * **Interaction** — zoom, pan, hover-to-inspect node summary, click-to-
      resolve ``kgrag://`` URL (when the host UI supports it)
    """


@dataclass
class Viewport:
    """A rectangular display region allocated to one KG adapter in the visualizer.

    The KGRAG visualizer divides its canvas into Viewports — one per KG (or one
    per corpus member, for corpus-scoped views).  Each Viewport carries:

    * a **rendering context** (``container``) — the UI object the adapter writes
      into.  In Streamlit this is a ``DeltaGenerator`` (a column or container);
      in other frontends it will be the equivalent region handle.  Adapters must
      call drawing methods on this object, not on the global ``st`` module, so
      that all output is confined to the allocated area.
    * a **display mode** (``mode``) — whether to produce a SEMANTIC tree or an
      ONTOLOGICAL node-link graph.
    * **geometry hints** (``width``, ``height``) — pixel dimensions of the region.
      ``0`` means "fill available" (Streamlit default).
    * an optional **title** override and an opaque **metadata** dict for passing
      per-render hints (highlighted node IDs, active query string, etc.).

    :param container: UI rendering context.  In Streamlit, a ``DeltaGenerator``
        (e.g. the return value of ``st.container()`` or one element of
        ``st.columns()``).  Adapters call ``st``-style methods on this object.
    :param mode: Which visualization type to produce.
        Defaults to :attr:`DisplayMode.SEMANTIC`.
    :param width: Pixel width of the viewport.  ``0`` → fill available width.
    :param height: Pixel height of the viewport.  ``0`` → adapter chooses.
    :param title: Title shown at the top of the viewport.  If empty the adapter
        uses its ``KGEntry.name``.
    :param metadata: Opaque key-value bag.  Recognised keys (by convention):
        - ``"highlighted_nodes"`` — ``list[str]`` of node IDs to highlight
        - ``"active_query"`` — ``str`` query string that triggered this render
        - ``"snapshot_hash"`` — ``str`` snapshot hash for differential rendering
        - ``"depth"`` — ``int`` max traversal depth for ontological layout
    """

    container: Any
    mode: DisplayMode = DisplayMode.SEMANTIC
    backend: RenderBackend = RenderBackend.STREAMLIT
    width: int = 0
    height: int = 0
    title: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)

    # ------------------------------------------------------------------
    # Factory helpers — convenience constructors for common layouts
    # ------------------------------------------------------------------

    @classmethod
    def streamlit_semantic(
        cls, container: Any, *, width: int = 0, height: int = 0, title: str = "", **meta: Any
    ) -> Viewport:
        """Streamlit container configured for SEMANTIC display."""
        return cls(
            container=container,
            mode=DisplayMode.SEMANTIC,
            backend=RenderBackend.STREAMLIT,
            width=width,
            height=height,
            title=title,
            metadata=dict(meta),
        )

    @classmethod
    def streamlit_ontological(
        cls, container: Any, *, width: int = 0, height: int = 0, title: str = "", **meta: Any
    ) -> Viewport:
        """Streamlit container configured for ONTOLOGICAL display."""
        return cls(
            container=container,
            mode=DisplayMode.ONTOLOGICAL,
            backend=RenderBackend.STREAMLIT,
            width=width,
            height=height,
            title=title,
            metadata=dict(meta),
        )

    @classmethod
    def qt2d_semantic(
        cls, scene: Any, *, width: int = 0, height: int = 0, title: str = "", **meta: Any
    ) -> Viewport:
        """Qt2D QGraphicsScene configured for SEMANTIC display."""
        return cls(
            container=scene,
            mode=DisplayMode.SEMANTIC,
            backend=RenderBackend.QT2D,
            width=width,
            height=height,
            title=title,
            metadata=dict(meta),
        )

    @classmethod
    def qt2d_ontological(
        cls, scene: Any, *, width: int = 0, height: int = 0, title: str = "", **meta: Any
    ) -> Viewport:
        """Qt2D QGraphicsScene configured for ONTOLOGICAL display."""
        return cls(
            container=scene,
            mode=DisplayMode.ONTOLOGICAL,
            backend=RenderBackend.QT2D,
            width=width,
            height=height,
            title=title,
            metadata=dict(meta),
        )
