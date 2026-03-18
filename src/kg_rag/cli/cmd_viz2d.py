"""
cmd_viz2d.py

Click subcommand for launching the KGRAG PyQt5 2-D visualizer:

  viz2d — Split-viewport Qt5 canvas; one tile per registered KG.
"""

from __future__ import annotations

import importlib.util
import sys
from pathlib import Path

import click

from kg_rag.cli.group import cli

_QT_EXTRA = 'pip install "kg-rag[qt]"'


@cli.command("viz2d")
@click.option(
    "--registry",
    default=None,
    envvar="KGRAG_REGISTRY",
    show_default=True,
    help="Path to the KGRAG registry SQLite file (or set KGRAG_REGISTRY env var).",
)
@click.option(
    "--mode",
    type=click.Choice(["semantic", "ontological"], case_sensitive=False),
    default="semantic",
    show_default=True,
    help="Display mode: semantic (forest tree) or ontological (node-link graph).",
)
@click.option(
    "--cols",
    default=3,
    show_default=True,
    type=int,
    help="Number of viewport columns in the canvas grid.",
)
@click.option(
    "--vp-width",
    default=380,
    show_default=True,
    type=int,
    help="Width of each KG viewport in pixels.",
)
@click.option(
    "--vp-height",
    default=300,
    show_default=True,
    type=int,
    help="Height of each KG viewport in pixels.",
)
def viz2d(
    registry: str | None,
    mode: str,
    cols: int,
    vp_width: int,
    vp_height: int,
) -> None:
    """Launch the KGRAG 2-D Qt5 visualizer.

    Opens a split-viewport canvas with one tile per registered KG.
    Each tile renders the KG's display() output — a synthetic forest tree
    (semantic) or node-link diagram (ontological) — into a QGraphicsScene.

    Zoom: Ctrl+scroll wheel.  Pan: click-drag.  Fit: double-click.
    """
    if importlib.util.find_spec("PyQt5") is None:
        raise click.UsageError(
            f"PyQt5 is not installed. Install Qt dependencies with:\n  {_QT_EXTRA}"
        )

    from kg_rag.viz import DisplayMode                    # noqa: PLC0415
    from kg_rag.viz_qt import launch                      # noqa: PLC0415

    reg_path = Path(registry) if registry else None
    disp_mode = DisplayMode.SEMANTIC if mode == "semantic" else DisplayMode.ONTOLOGICAL

    click.echo("Launching KGRAG 2-D visualizer…")
    if reg_path:
        click.echo(f"  registry : {reg_path}")
    click.echo(f"  mode     : {mode}")
    click.echo(f"  grid     : {cols} cols  {vp_width}×{vp_height}px per tile")

    launch(
        registry_path=reg_path,
        mode=disp_mode,
        cols=cols,
        vp_width=vp_width,
        vp_height=vp_height,
    )
