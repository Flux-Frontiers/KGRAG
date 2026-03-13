"""
cmd_init.py

kgrag init — auto-detect, build, and register all applicable KG layers for a
repository in one shot.

A *KG layer* is one KG backend tied to a single repo: a code layer (codekg),
a doc layer (dockg), or a meta layer (metakg).  Running ``kgrag init`` on a
repo detects which layers apply, invokes the appropriate build CLI for each,
and registers every successfully-built layer in the KGRAG registry.
"""

from __future__ import annotations

import os
import shutil
import subprocess
from pathlib import Path

import click
from rich import box
from rich.console import Console
from rich.table import Table

from kg_rag.cli.group import cli
from kg_rag.cli.options import registry_option
from kg_rag.primitives import KGEntry, KGKind
from kg_rag.registry import KGRegistry

console = Console()

# KG layer → (dot-directory, build CLI name)
_LAYER_SPEC: dict[str, tuple[str, str]] = {
    "code": (".codekg", "codekg"),
    "doc": (".dockg", "dockg"),
}


def _detect_layers(repo: Path) -> list[str]:
    """Scan *repo* for signals that indicate which KG layers are applicable.

    Walks the repository once, skipping hidden directories and common
    non-source trees (``.venv``, ``venv``, ``node_modules``).

    :param repo: Absolute path to the repository root.
    :return: Ordered list of applicable KG kind strings (e.g. ``["code", "doc"]``).
    """
    _PRUNE = frozenset({".venv", "venv", "node_modules", "__pycache__"})
    has_python = False
    has_docs = False

    for dirpath, dirnames, filenames in os.walk(repo):
        # Prune hidden dirs and common non-source trees in-place
        dirnames[:] = [d for d in dirnames if not d.startswith(".") and d not in _PRUNE]
        for fname in filenames:
            if fname.endswith(".py"):
                has_python = True
            if fname.endswith((".md", ".txt", ".rst")):
                has_docs = True
        if has_python and has_docs:
            break  # no need to keep walking

    layers = []
    if has_python:
        layers.append("code")
    if has_docs:
        layers.append("doc")
    return layers


@cli.command("init")
@click.argument(
    "repo_path",
    type=click.Path(exists=True, file_okay=False, resolve_path=True),
    default=".",
)
@click.option("--wipe", is_flag=True, help="Wipe and rebuild existing databases.")
@click.option(
    "--name",
    "name_prefix",
    default=None,
    help="Name prefix for registered KGs (default: repo directory name).",
)
@click.option(
    "--layer",
    "layers",
    type=click.Choice(list(_LAYER_SPEC)),
    multiple=True,
    help="KG layers to build (repeatable). Default: auto-detect.",
)
@registry_option
def init(repo_path, wipe, name_prefix, layers, registry):
    """Initialise a repo: detect, build, and register all applicable KG layers.

    A *KG layer* is one knowledge-graph backend for a single repo (code layer
    via codekg, doc layer via dockg).  ``kgrag init`` detects which layers
    apply, builds each one, and registers them in the KGRAG registry — all in
    one command.

    \b
    REPO_PATH  Path to the repository (default: current directory)

    Examples:

    \b
        kgrag init ~/repos/myproject
        kgrag init . --layer code --layer doc --wipe
        kgrag init ~/repos/myproject --name myproject
    """
    repo = Path(repo_path).resolve()
    prefix = name_prefix or repo.name

    console.print(f"Initialising KG layers for [bold]{repo}[/bold]...")

    # Determine which layers to build
    if layers:
        to_build = list(layers)
    else:
        console.print("Auto-detecting applicable KG layers...")
        to_build = _detect_layers(repo)
        if not to_build:
            console.print("[yellow]No applicable KG layers detected.[/yellow]")
            return
        console.print(f"Detected: [bold]{', '.join(to_build)}[/bold]")

    results: list[dict] = []

    for kind in to_build:
        marker, cli_name = _LAYER_SPEC[kind]
        name = f"{prefix}-{kind}"

        # Check build tool availability
        tool_path = shutil.which(cli_name)
        if tool_path is None:
            console.print(
                f"\n[yellow]Skipping {kind} layer[/yellow]: "
                f"[bold]{cli_name}[/bold] not found on PATH."
            )
            results.append({"kind": kind, "name": name, "status": "skipped", "entry": None})
            continue

        # Build
        console.rule(f"[bold]{kind} layer[/bold]")
        cmd = [cli_name, "build", "--repo", str(repo)]
        if wipe:
            cmd.append("--wipe")
        console.print(f"Running: {' '.join(cmd)}")

        try:
            subprocess.run(cmd, check=True)
            built_ok = True
        except subprocess.CalledProcessError:
            built_ok = False

        if not built_ok:
            console.print(f"[red]Build failed[/red] for {kind} layer.")
            results.append({"kind": kind, "name": name, "status": "build-failed", "entry": None})
            continue

        # Resolve DB paths from the well-known marker dir
        kg_dir = repo / marker
        sqlite_path = kg_dir / "graph.sqlite"
        lancedb_path = kg_dir / "lancedb"

        entry = KGEntry(
            name=name,
            kind=KGKind.from_str(kind),
            repo_path=repo,
            venv_path=repo / ".venv",
            sqlite_path=sqlite_path if sqlite_path.exists() else None,
            lancedb_path=lancedb_path if lancedb_path.exists() else None,
        )

        with KGRegistry(db_path=Path(registry) if registry else None) as reg:
            reg.register(entry)

        console.print(f"[green]Registered[/green] [bold]{name}[/bold]")
        results.append({"kind": kind, "name": name, "status": "ok", "entry": entry})

    # Summary
    console.rule("Summary")
    table = Table(title=f"KG Init — {repo.name}", box=box.ROUNDED)
    table.add_column("Layer", style="magenta")
    table.add_column("Name", style="bold cyan")
    table.add_column("Status", justify="center")
    table.add_column("SQLite", justify="center")
    table.add_column("LanceDB", justify="center")

    _STATUS_FMT = {
        "ok": "[green]registered[/green]",
        "skipped": "[yellow]skipped[/yellow]",
        "build-failed": "[red]build failed[/red]",
    }

    for r in results:
        e = r["entry"]
        table.add_row(
            r["kind"],
            r["name"],
            _STATUS_FMT.get(r["status"], r["status"]),
            "[green]yes[/green]" if (e and e.sqlite_path) else "-",
            "[green]yes[/green]" if (e and e.lancedb_path) else "-",
        )

    console.print(table)
