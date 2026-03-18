"""
viz_qt.py — PyQt5 2-D visualizer for KGRAG.

Adapted from *code_kg/viz3d.py* (Eric G. Suchanek, PhD) which was itself
adapted from *repo_vis/pkg_visualizer/pkg_visualizer.py*.

Provides a split-viewport canvas where every registered KG gets its own
rectangular region.  Each region is rendered by calling the KG adapter's
``display(viewport)`` method with a :class:`~kg_rag.viz.Viewport` whose
``container`` is a ``QGraphicsScene`` and ``backend`` is
:attr:`~kg_rag.viz.RenderBackend.QT2D`.

Window layout (mirrors code_kg/viz3d.py):
  Left  — control sidebar (registry path, kind filter, display-mode toggle,
           viewport size slider, status label)
  Right — scrollable canvas of KGViewportWidget tiles

Run via::

    kgrag viz2d
    kgrag viz2d --mode ontological
    kgrag viz2d --cols 3 --vp-width 420 --vp-height 320

Author: Eric G. Suchanek, PhD
"""

# pylint: disable=C0116,C0115,W0613

from __future__ import annotations

import logging
import math
import sys
from pathlib import Path
from typing import TYPE_CHECKING

from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtGui import QBrush, QColor, QFont, QPen
from PyQt5.QtWidgets import (
    QApplication,
    QButtonGroup,
    QDockWidget,
    QGraphicsEllipseItem,
    QGraphicsLineItem,
    QGraphicsRectItem,
    QGraphicsScene,
    QGraphicsTextItem,
    QGraphicsView,
    QGridLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMainWindow,
    QPushButton,
    QRadioButton,
    QScrollArea,
    QSizePolicy,
    QSlider,
    QVBoxLayout,
    QWidget,
)

from kg_rag.viz import DisplayMode, RenderBackend, Viewport

if TYPE_CHECKING:
    from kg_rag.adapters.base import KGAdapter
    from kg_rag.primitives import KGEntry

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

__version__ = "0.1.0"
__author__ = "Eric G. Suchanek, PhD"

SIDEBAR_W: int = 220
VIEWPORT_W_DEFAULT: int = 380
VIEWPORT_H_DEFAULT: int = 300
TITLE_H: int = 30
GRID_COLS_DEFAULT: int = 3

# Per-kind accent colours — mirrors app.py and viz3d.py palettes
KIND_COLOR: dict[str, str] = {
    "code":      "#4A90D9",
    "doc":       "#27AE60",
    "meta":      "#8E44AD",
    "diary":     "#E67E22",
    "verse":     "#1ABC9C",
    "memory":    "#F39C12",
    "disulfide": "#E74C3C",
    "pdbfile":   "#95A5A6",
    "legal":     "#8B4513",
    "person":    "#FF69B4",
}

# Node-kind colours for ontological mode
NODE_KIND_COLOR: dict[str, str] = {
    "module":   "#4A90D9",
    "class":    "#E67E22",
    "function": "#27AE60",
    "method":   "#8E44AD",
    "chunk":    "#F39C12",
    "section":  "#1ABC9C",
    "entity":   "#E74C3C",
}

BG_COLOR = "#0d0d1a"          # canvas background
VIEWPORT_BG = "#12122a"       # per-KG scene background
TITLE_BG = "#1a1a3a"          # title bar background
TEXT_COLOR = "#e0e0e0"
STUB_COLOR = "#2a2a4a"        # stub placeholder fill


# ---------------------------------------------------------------------------
# KGGraphView — QGraphicsView with zoom + pan
# ---------------------------------------------------------------------------


class KGGraphView(QGraphicsView):
    """A QGraphicsView configured for knowledge-graph rendering.

    Supports:
    * Scroll-wheel zoom (Ctrl + wheel)
    * Middle-button drag pan
    * Fit-to-viewport on double-click
    """

    def __init__(self, scene: QGraphicsScene, parent: QWidget | None = None) -> None:
        super().__init__(scene, parent)
        self.setRenderHint(self.renderHints() | self.RenderHint.Antialiasing)  # type: ignore[attr-defined]
        self.setDragMode(QGraphicsView.DragMode.ScrollHandDrag)
        self.setTransformationAnchor(QGraphicsView.ViewportAnchor.AnchorUnderMouse)
        self.setResizeAnchor(QGraphicsView.ViewportAnchor.AnchorViewCenter)
        self.setBackgroundBrush(QBrush(QColor(VIEWPORT_BG)))
        self.setFrameShape(QGraphicsView.Shape.NoFrame)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)

    def wheelEvent(self, event) -> None:  # type: ignore[override]
        """Zoom on Ctrl+wheel; scroll normally otherwise."""
        if event.modifiers() & Qt.KeyboardModifier.ControlModifier:
            factor = 1.15 if event.angleDelta().y() > 0 else 1 / 1.15
            self.scale(factor, factor)
        else:
            super().wheelEvent(event)

    def mouseDoubleClickEvent(self, event) -> None:  # type: ignore[override]
        """Fit the scene back into the view on double-click."""
        self.fitInView(self.scene().sceneRect(), Qt.AspectRatioMode.KeepAspectRatio)
        super().mouseDoubleClickEvent(event)


# ---------------------------------------------------------------------------
# KGViewportWidget — title bar + KGGraphView for one KG adapter
# ---------------------------------------------------------------------------


class KGViewportWidget(QWidget):
    """A titled viewport tile for a single KG adapter.

    Layout::

        ┌─────────────────────────────────────┐
        │ [kind] name                 N nodes  │  ← title bar (TITLE_H px)
        ├─────────────────────────────────────┤
        │                                     │
        │        QGraphicsScene               │  ← KGGraphView (fills remainder)
        │                                     │
        └─────────────────────────────────────┘

    The adapter's ``display(viewport)`` is called with a
    :class:`~kg_rag.viz.Viewport` wrapping the scene, so the adapter controls
    all drawing inside the lower region.
    """

    def __init__(
        self,
        adapter: KGAdapter,
        mode: DisplayMode,
        vp_width: int = VIEWPORT_W_DEFAULT,
        vp_height: int = VIEWPORT_H_DEFAULT,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self._adapter = adapter
        self._mode = mode
        self._vp_width = vp_width
        self._vp_height = vp_height

        self.setFixedSize(vp_width, vp_height)
        self._build_ui()
        self._render()

    # ------------------------------------------------------------------

    def _build_ui(self) -> None:
        entry = self._adapter.entry
        kind = entry.kind.value
        color = KIND_COLOR.get(kind, "#95A5A6")

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # ── Title bar ─────────────────────────────────────────────────
        title_bar = QWidget()
        title_bar.setFixedHeight(TITLE_H)
        title_bar.setStyleSheet(
            f"background:{TITLE_BG};border-left:4px solid {color};"
        )
        tb_layout = QHBoxLayout(title_bar)
        tb_layout.setContentsMargins(6, 0, 6, 0)

        badge = QLabel(kind)
        badge.setStyleSheet(
            f"background:{color};color:#fff;border-radius:3px;"
            f"padding:1px 6px;font-size:10px;font-weight:bold;font-family:monospace;"
        )
        badge.setFixedHeight(18)
        tb_layout.addWidget(badge)

        name_lbl = QLabel(entry.name)
        name_lbl.setStyleSheet(f"color:{TEXT_COLOR};font-size:12px;font-weight:bold;")
        tb_layout.addWidget(name_lbl, stretch=1)

        self._count_lbl = QLabel("…")
        self._count_lbl.setStyleSheet("color:#888;font-size:10px;font-family:monospace;")
        tb_layout.addWidget(self._count_lbl)

        layout.addWidget(title_bar)

        # ── Graph view ────────────────────────────────────────────────
        self._scene = QGraphicsScene()
        self._scene.setSceneRect(0, 0, self._vp_width - 4, self._vp_height - TITLE_H - 4)
        self._view = KGGraphView(self._scene)
        layout.addWidget(self._view)

    def _render(self) -> None:
        """Call adapter.display() with a Qt2D Viewport backed by our scene."""
        entry = self._adapter.entry
        self._scene.clear()

        # Update count label from graph stats (non-blocking)
        try:
            if self._adapter.is_available():
                gs = self._adapter._graph_stats()  # pylint: disable=protected-access
                n, e = gs["node_count"], gs["edge_count"]
                self._count_lbl.setText(f"{n}n · {e}e")
            else:
                self._count_lbl.setText("not built")
        except Exception:  # pylint: disable=broad-except
            self._count_lbl.setText("—")

        vp = Viewport(
            container=self._scene,
            mode=self._mode,
            backend=RenderBackend.QT2D,
            width=int(self._scene.width()),
            height=int(self._scene.height()),
            title=entry.name,
        )
        try:
            self._adapter.display(vp)
        except Exception as exc:  # pylint: disable=broad-except
            logger.warning("display() failed for %s: %s", entry.name, exc)
            self._draw_error(str(exc))

        self._view.fitInView(self._scene.sceneRect(), Qt.AspectRatioMode.KeepAspectRatio)

    def _draw_error(self, msg: str) -> None:
        """Draw a red error card into the scene."""
        w, h = self._scene.width(), self._scene.height()
        rect = QGraphicsRectItem(4, 4, w - 8, h - 8)
        rect.setBrush(QBrush(QColor("#3a0a0a")))
        rect.setPen(QPen(QColor("#E74C3C"), 1))
        self._scene.addItem(rect)
        txt = QGraphicsTextItem(f"display() error:\n{msg}")
        txt.setDefaultTextColor(QColor("#E74C3C"))
        txt.setPos(10, 10)
        self._scene.addItem(txt)

    def refresh(self, mode: DisplayMode | None = None) -> None:
        """Re-render with an optional new display mode."""
        if mode is not None:
            self._mode = mode
        self._render()


# ---------------------------------------------------------------------------
# _CanvasWidget — scrollable grid of KGViewportWidgets
# ---------------------------------------------------------------------------


class _CanvasWidget(QWidget):
    """Scrollable grid canvas that holds one KGViewportWidget per KG."""

    def __init__(self, cols: int = GRID_COLS_DEFAULT, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._cols = cols
        self._tiles: list[KGViewportWidget] = []
        self._grid = QGridLayout(self)
        self._grid.setSpacing(8)
        self._grid.setContentsMargins(8, 8, 8, 8)
        self.setStyleSheet(f"background:{BG_COLOR};")

    def populate(
        self,
        adapters: list[KGAdapter],
        mode: DisplayMode,
        vp_width: int,
        vp_height: int,
    ) -> None:
        """Clear the grid and create one tile per adapter."""
        # Remove existing tiles
        for tile in self._tiles:
            self._grid.removeWidget(tile)
            tile.deleteLater()
        self._tiles.clear()

        for idx, adapter in enumerate(adapters):
            tile = KGViewportWidget(adapter, mode, vp_width, vp_height)
            row, col = divmod(idx, self._cols)
            self._grid.addWidget(tile, row, col)
            self._tiles.append(tile)

        # Fill remaining cells in last row so grid aligns left
        n = len(adapters)
        remainder = n % self._cols
        if remainder:
            for col in range(remainder, self._cols):
                row = n // self._cols
                spacer = QWidget()
                spacer.setFixedSize(vp_width, vp_height)
                spacer.setStyleSheet(f"background:{BG_COLOR};")
                self._grid.addWidget(spacer, row, col)

    def refresh_all(self, mode: DisplayMode | None = None) -> None:
        for tile in self._tiles:
            tile.refresh(mode)

    def set_cols(self, cols: int) -> None:
        self._cols = max(1, cols)

    @property
    def tile_count(self) -> int:
        return len(self._tiles)


# ---------------------------------------------------------------------------
# KGRAGViz2DWindow — main application window
# ---------------------------------------------------------------------------


class KGRAGViz2DWindow(QMainWindow):
    """Main window for the KGRAG 2-D visualizer.

    Layout mirrors code_kg/viz3d.py:
      Left dock  — sidebar (registry path, kind filter, mode, size controls)
      Central    — QScrollArea wrapping the KG viewport grid canvas

    :param registry_path: Path to the KGRAG registry SQLite file.
    :param mode: Initial display mode (SEMANTIC or ONTOLOGICAL).
    :param cols: Number of viewport columns in the grid.
    :param vp_width: Width of each KG viewport in pixels.
    :param vp_height: Height of each KG viewport in pixels.
    """

    def __init__(
        self,
        registry_path: Path | None = None,
        mode: DisplayMode = DisplayMode.SEMANTIC,
        cols: int = GRID_COLS_DEFAULT,
        vp_width: int = VIEWPORT_W_DEFAULT,
        vp_height: int = VIEWPORT_H_DEFAULT,
    ) -> None:
        super().__init__()
        self._registry_path = registry_path
        self._mode = mode
        self._cols = cols
        self._vp_width = vp_width
        self._vp_height = vp_height
        self._kgrag = None

        self.setWindowTitle(f"KGRAG Visualizer 2D  v{__version__}")
        self.resize(1280, 800)
        self.setStyleSheet(f"background:{BG_COLOR};color:{TEXT_COLOR};")

        self._build_central()
        self._build_sidebar()
        self._schedule_load()

    # ------------------------------------------------------------------
    # UI construction
    # ------------------------------------------------------------------

    def _build_central(self) -> None:
        """Build the scrollable canvas as the central widget."""
        self._canvas = _CanvasWidget(self._cols)

        scroll = QScrollArea()
        scroll.setWidget(self._canvas)
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet(f"background:{BG_COLOR};border:none;")
        self.setCentralWidget(scroll)

    def _build_sidebar(self) -> None:
        """Build the left dock with registry, filter, mode, and size controls."""
        from kg_rag.registry import default_registry_path  # lazy import

        dock = QDockWidget("Controls", self)
        dock.setFeatures(
            QDockWidget.DockWidgetFeature.DockWidgetMovable
            | QDockWidget.DockWidgetFeature.DockWidgetFloatable
        )
        dock.setFixedWidth(SIDEBAR_W)
        dock.setStyleSheet(f"background:{TITLE_BG};color:{TEXT_COLOR};")

        body = QWidget()
        body.setStyleSheet(f"background:{TITLE_BG};")
        vlayout = QVBoxLayout(body)
        vlayout.setSpacing(10)
        vlayout.setContentsMargins(8, 8, 8, 8)

        # ── Title ─────────────────────────────────────────────────────
        title_lbl = QLabel("🕸 KGRAG Explorer 2D")
        title_lbl.setFont(QFont("Sans", 11, QFont.Weight.Bold))
        title_lbl.setStyleSheet(f"color:{TEXT_COLOR};")
        vlayout.addWidget(title_lbl)

        self._sep(vlayout)

        # ── Registry path ─────────────────────────────────────────────
        vlayout.addWidget(self._label("Registry path"))
        default_reg = str(self._registry_path or default_registry_path())
        self._reg_input = QLineEdit(default_reg)
        self._reg_input.setStyleSheet(
            "background:#22223a;color:#e0e0e0;border:1px solid #444;"
            "border-radius:3px;padding:2px 4px;font-size:11px;"
        )
        vlayout.addWidget(self._reg_input)

        refresh_btn = QPushButton("⟳  Refresh")
        refresh_btn.setStyleSheet(
            "background:#2d3a5a;color:#e0e0e0;border:none;border-radius:3px;"
            "padding:4px;font-size:11px;"
        )
        refresh_btn.clicked.connect(self._on_refresh)
        vlayout.addWidget(refresh_btn)

        self._sep(vlayout)

        # ── Display mode ──────────────────────────────────────────────
        vlayout.addWidget(self._label("Display mode"))
        mode_grp = QButtonGroup(self)

        self._radio_semantic = QRadioButton("Semantic (forest)")
        self._radio_semantic.setStyleSheet(f"color:{TEXT_COLOR};font-size:11px;")
        self._radio_semantic.setChecked(self._mode == DisplayMode.SEMANTIC)

        self._radio_onto = QRadioButton("Ontological (graph)")
        self._radio_onto.setStyleSheet(f"color:{TEXT_COLOR};font-size:11px;")
        self._radio_onto.setChecked(self._mode == DisplayMode.ONTOLOGICAL)

        mode_grp.addButton(self._radio_semantic)
        mode_grp.addButton(self._radio_onto)
        mode_grp.buttonClicked.connect(self._on_mode_changed)

        vlayout.addWidget(self._radio_semantic)
        vlayout.addWidget(self._radio_onto)

        self._sep(vlayout)

        # ── Grid columns ──────────────────────────────────────────────
        vlayout.addWidget(self._label(f"Columns: {self._cols}"))
        self._cols_lbl = vlayout.itemAt(vlayout.count() - 1).widget()

        cols_slider = QSlider(Qt.Orientation.Horizontal)
        cols_slider.setRange(1, 6)
        cols_slider.setValue(self._cols)
        cols_slider.setStyleSheet("color:#4A90D9;")
        cols_slider.valueChanged.connect(self._on_cols_changed)
        vlayout.addWidget(cols_slider)

        # ── Viewport size ─────────────────────────────────────────────
        self._sep(vlayout)
        vlayout.addWidget(self._label(f"Viewport width: {self._vp_width}px"))
        self._vpw_lbl = vlayout.itemAt(vlayout.count() - 1).widget()

        vpw_slider = QSlider(Qt.Orientation.Horizontal)
        vpw_slider.setRange(200, 700)
        vpw_slider.setValue(self._vp_width)
        vpw_slider.setStyleSheet("color:#4A90D9;")
        vpw_slider.valueChanged.connect(self._on_vp_width_changed)
        vlayout.addWidget(vpw_slider)

        # ── Status ────────────────────────────────────────────────────
        self._sep(vlayout)
        self._status_lbl = QLabel("Loading…")
        self._status_lbl.setWordWrap(True)
        self._status_lbl.setStyleSheet("color:#888;font-size:10px;font-family:monospace;")
        vlayout.addWidget(self._status_lbl)

        vlayout.addStretch()

        dock.setWidget(body)
        self.addDockWidget(Qt.DockWidgetArea.LeftDockWidgetArea, dock)

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _label(text: str) -> QLabel:
        lbl = QLabel(text)
        lbl.setStyleSheet(f"color:#aaa;font-size:10px;")
        return lbl

    @staticmethod
    def _sep(layout: QVBoxLayout) -> None:
        sep = QWidget()
        sep.setFixedHeight(1)
        sep.setStyleSheet("background:#2a2a4a;")
        layout.addWidget(sep)

    # ------------------------------------------------------------------
    # Loading
    # ------------------------------------------------------------------

    def _schedule_load(self) -> None:
        QTimer.singleShot(100, self._load_registry)

    def _load_registry(self) -> None:
        from kg_rag.adapters import make_adapter  # lazy import
        from kg_rag.orchestrator import KGRAG     # lazy import

        reg_path = Path(self._reg_input.text().strip())
        try:
            self._kgrag = KGRAG(registry_path=reg_path)
            entries = self._kgrag.registry.list()
        except Exception as exc:  # pylint: disable=broad-except
            self._status_lbl.setText(f"Registry error:\n{exc}")
            return

        if not entries:
            self._status_lbl.setText("No KGs registered.\nRun `kgrag init` first.")
            return

        adapters: list[KGAdapter] = []
        for entry in entries:
            try:
                adapters.append(make_adapter(entry))
            except Exception as exc:  # pylint: disable=broad-except
                logger.warning("Could not create adapter for %s: %s", entry.name, exc)

        self._canvas.set_cols(self._cols)
        self._canvas.populate(adapters, self._mode, self._vp_width, self._vp_height)
        self._canvas.adjustSize()

        total_n = sum(a._graph_stats()["node_count"] for a in adapters if a.is_available())  # pylint: disable=protected-access
        self._status_lbl.setText(
            f"{len(adapters)} KGs loaded\n"
            f"~{total_n:,} total nodes\n"
            f"mode: {self._mode.value}"
        )

    # ------------------------------------------------------------------
    # Slot handlers
    # ------------------------------------------------------------------

    def _on_refresh(self) -> None:
        self._status_lbl.setText("Refreshing…")
        QTimer.singleShot(50, self._load_registry)

    def _on_mode_changed(self, btn) -> None:
        self._mode = (
            DisplayMode.SEMANTIC if self._radio_semantic.isChecked()
            else DisplayMode.ONTOLOGICAL
        )
        self._canvas.refresh_all(self._mode)
        self._status_lbl.setText(f"mode: {self._mode.value}")

    def _on_cols_changed(self, value: int) -> None:
        self._cols = value
        self._cols_lbl.setText(f"Columns: {value}")
        if self._kgrag is not None:
            QTimer.singleShot(50, self._load_registry)

    def _on_vp_width_changed(self, value: int) -> None:
        self._vp_width = value
        self._vpw_lbl.setText(f"Viewport width: {value}px")
        if self._kgrag is not None:
            QTimer.singleShot(200, self._load_registry)


# ---------------------------------------------------------------------------
# Stub scene drawing — used by KGAdapter._display_stub_qt()
# ---------------------------------------------------------------------------


def draw_stub_semantic(scene: QGraphicsScene, adapter: KGAdapter) -> None:
    """Draw a synthetic semantic tree stub into a QGraphicsScene.

    Visual encoding (order of magnitude, not exact):
    * Tree height ∝ log2(node_count + 2)
    * Branch count per level ∝ sqrt(edge_count / max(node_count, 1))
    * Leaf node radius ∝ 4 px (fixed, for legibility)
    * Trunk width ∝ log2(node_count + 2)
    * Accent colour from KIND_COLOR per KG kind

    This is a placeholder that scales with topology.  Concrete adapters
    override ``display()`` to draw the real graph structure.
    """
    w, h = scene.width(), scene.height()
    kind = adapter.entry.kind.value
    color = QColor(KIND_COLOR.get(kind, "#95A5A6"))

    gs = {}
    try:
        if adapter.is_available():
            gs = adapter._graph_stats()  # pylint: disable=protected-access
    except Exception:  # pylint: disable=broad-except
        pass

    node_count = max(gs.get("node_count", 1), 1)
    edge_count = max(gs.get("edge_count", 0), 0)

    depth = max(2, min(6, int(math.log2(node_count + 2))))
    branch_factor = max(2, min(5, int(math.sqrt(edge_count / node_count) + 1.5)))
    trunk_w = max(2, min(8, int(math.log2(node_count + 2))))

    # Draw recursively into scene
    trunk_pen = QPen(color, trunk_w)
    trunk_pen.setCapStyle(Qt.PenCapStyle.RoundCap)

    def _draw_branch(x: float, y: float, angle: float, length: float, level: int) -> None:
        if level <= 0 or length < 4:
            # Leaf dot
            r = 4
            leaf_color = QColor(color)
            leaf_color.setAlphaF(0.7)
            dot = QGraphicsEllipseItem(x - r, y - r, r * 2, r * 2)
            dot.setBrush(QBrush(leaf_color))
            dot.setPen(QPen(Qt.PenStyle.NoPen))
            scene.addItem(dot)
            return

        end_x = x + length * math.cos(math.radians(angle))
        end_y = y - length * math.sin(math.radians(angle))

        alpha = max(0.3, level / depth)
        line_color = QColor(color)
        line_color.setAlphaF(alpha)
        pen = QPen(line_color, max(1, trunk_w * level // depth))
        pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        line = QGraphicsLineItem(x, y, end_x, end_y)
        line.setPen(pen)
        scene.addItem(line)

        spread = 80 / branch_factor
        start_angle = angle - spread * (branch_factor - 1) / 2
        for b in range(branch_factor):
            child_angle = start_angle + b * spread
            _draw_branch(
                end_x, end_y,
                child_angle,
                length * 0.65,
                level - 1,
            )

    # Start from bottom-centre
    _draw_branch(w / 2, h - 10, 90, h * 0.38, depth)

    # "Not built" overlay
    if not adapter.is_available():
        overlay = QGraphicsRectItem(0, 0, w, h)
        overlay.setBrush(QBrush(QColor(0, 0, 0, 160)))
        overlay.setPen(QPen(Qt.PenStyle.NoPen))
        scene.addItem(overlay)
        txt = QGraphicsTextItem("not built")
        txt.setDefaultTextColor(QColor("#888"))
        txt.setFont(QFont("Monospace", 9))
        txt.setPos(w / 2 - 28, h / 2 - 8)
        scene.addItem(txt)


def draw_stub_ontological(scene: QGraphicsScene, adapter: KGAdapter) -> None:
    """Draw a synthetic ontological node-link stub into a QGraphicsScene.

    Arranges representative node-kind circles in a radial layout and connects
    them with edges.  Node count and edge count drive the density of the
    diagram.  This is a placeholder; concrete adapters provide the real graph.
    """
    w, h = scene.width(), scene.height()
    kind = adapter.entry.kind.value
    accent = QColor(KIND_COLOR.get(kind, "#95A5A6"))

    gs = {}
    try:
        if adapter.is_available():
            gs = adapter._graph_stats()  # pylint: disable=protected-access
    except Exception:  # pylint: disable=broad-except
        pass

    node_count = max(gs.get("node_count", 1), 1)
    edge_count = max(gs.get("edge_count", 0), 0)

    # Determine display node count: log-scaled, capped at 24
    display_n = max(3, min(24, int(math.log(node_count + 2) * 3)))
    display_e = max(0, min(display_n * 2, int(math.log(edge_count + 1) * 3)))

    # Assign node kinds cyclically from NODE_KIND_COLOR keys
    kinds_cycle = list(NODE_KIND_COLOR.keys())
    node_colors = [
        QColor(NODE_KIND_COLOR[kinds_cycle[i % len(kinds_cycle)]])
        for i in range(display_n)
    ]

    # Radial layout
    cx, cy = w / 2, h / 2
    radius = min(w, h) * 0.38
    positions: list[tuple[float, float]] = []
    for i in range(display_n):
        angle = 2 * math.pi * i / display_n - math.pi / 2
        positions.append((cx + radius * math.cos(angle), cy + radius * math.sin(angle)))

    # Draw edges (connect sequential pairs + a few cross-edges)
    edge_pen = QPen(QColor(accent.red(), accent.green(), accent.blue(), 60), 1)
    drawn_edges = 0
    for i in range(display_n):
        if drawn_edges >= display_e:
            break
        j = (i + 1) % display_n
        x1, y1 = positions[i]
        x2, y2 = positions[j]
        line = QGraphicsLineItem(x1, y1, x2, y2)
        line.setPen(edge_pen)
        scene.addItem(line)
        drawn_edges += 1

    # Cross-edges (every other node to centre)
    cross_pen = QPen(QColor(accent.red(), accent.green(), accent.blue(), 40), 1,
                     Qt.PenStyle.DashLine)
    for i in range(0, display_n, 3):
        if drawn_edges >= display_e:
            break
        x1, y1 = positions[i]
        line = QGraphicsLineItem(x1, y1, cx, cy)
        line.setPen(cross_pen)
        scene.addItem(line)
        drawn_edges += 1

    # Centre hub node
    hub_r = 8
    hub = QGraphicsEllipseItem(cx - hub_r, cy - hub_r, hub_r * 2, hub_r * 2)
    hub.setBrush(QBrush(accent))
    hub.setPen(QPen(Qt.PenStyle.NoPen))
    scene.addItem(hub)

    # Peripheral nodes
    node_r = 5
    for i, (x, y) in enumerate(positions):
        nc = node_colors[i]
        dot = QGraphicsEllipseItem(x - node_r, y - node_r, node_r * 2, node_r * 2)
        dot.setBrush(QBrush(nc))
        dot.setPen(QPen(QColor(0, 0, 0, 80), 1))
        scene.addItem(dot)

    # "Not built" overlay
    if not adapter.is_available():
        overlay = QGraphicsRectItem(0, 0, w, h)
        overlay.setBrush(QBrush(QColor(0, 0, 0, 160)))
        overlay.setPen(QPen(Qt.PenStyle.NoPen))
        scene.addItem(overlay)
        txt = QGraphicsTextItem("not built")
        txt.setDefaultTextColor(QColor("#888"))
        txt.setFont(QFont("Monospace", 9))
        txt.setPos(w / 2 - 28, h / 2 - 8)
        scene.addItem(txt)


# ---------------------------------------------------------------------------
# Entrypoint
# ---------------------------------------------------------------------------


def launch(
    registry_path: Path | None = None,
    mode: DisplayMode = DisplayMode.SEMANTIC,
    cols: int = GRID_COLS_DEFAULT,
    vp_width: int = VIEWPORT_W_DEFAULT,
    vp_height: int = VIEWPORT_H_DEFAULT,
) -> None:
    """Create a QApplication and launch the KGRAG 2-D visualizer.

    Blocks until the window is closed.

    :param registry_path: Path to the KGRAG registry SQLite file.
        Defaults to the standard registry location.
    :param mode: Initial display mode.
    :param cols: Number of columns in the viewport grid.
    :param vp_width: Width of each KG viewport in pixels.
    :param vp_height: Height of each KG viewport in pixels.
    """
    app = QApplication.instance() or QApplication(sys.argv)
    window = KGRAGViz2DWindow(
        registry_path=registry_path,
        mode=mode,
        cols=cols,
        vp_width=vp_width,
        vp_height=vp_height,
    )
    window.show()
    sys.exit(app.exec_())
