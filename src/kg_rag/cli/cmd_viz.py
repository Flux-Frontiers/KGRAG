"""
cmd_viz.py

Click subcommand for launching the KGRAG Streamlit visualizer:

  viz — Cross-KG registry manager and federated query explorer
"""

from __future__ import annotations

import importlib.util
import subprocess
import sys
from pathlib import Path

import click

from kg_rag.cli.group import cli

_VIZ_EXTRA = 'pip install "kg-rag[viz]"'


@cli.command("viz")
@click.option(
    "--registry",
    default=None,
    envvar="KGRAG_REGISTRY",
    show_default=True,
    help="Path to the KGRAG registry SQLite file (or set KGRAG_REGISTRY env var).",
)
@click.option(
    "--port",
    default="8501",
    show_default=True,
    help="Streamlit server port.",
)
@click.option(
    "--no-browser",
    is_flag=True,
    help="Do not open a browser window automatically.",
)
def viz(registry: str | None, port: str, no_browser: bool) -> None:
    """Launch the KGRAG Streamlit visualizer."""
    if importlib.util.find_spec("streamlit") is None:
        raise click.UsageError(
            f"streamlit is not installed. Install viz dependencies with:\n  {_VIZ_EXTRA}"
        )

    app_path = Path(__file__).parent.parent / "app.py"

    if not app_path.exists():
        click.echo(f"ERROR: Could not find app.py at {app_path}", err=True)
        sys.exit(1)

    cmd = [
        sys.executable,
        "-m",
        "streamlit",
        "run",
        str(app_path),
        "--server.port",
        str(port),
    ]

    if no_browser:
        cmd[5:5] = ["--server.headless", "true"]

    click.echo(f"Launching KGRAG Explorer on http://localhost:{port}")
    click.echo(f"  app      : {app_path}")
    if registry:
        click.echo(f"  registry : {registry}")
    click.echo("  Press Ctrl+C to stop.\n")

    env = None
    if registry:
        import os  # pylint: disable=import-outside-toplevel

        env = {**os.environ, "KGRAG_REGISTRY": registry}

    try:
        subprocess.run(cmd, check=True, env=env)
    except KeyboardInterrupt:
        click.echo("\nStopped.")
