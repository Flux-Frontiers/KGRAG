"""
cmd_models.py

CLI commands for centralized model and embedder management.
"""

from __future__ import annotations

from pathlib import Path

import click
from rich.console import Console
from rich.table import Table

from kg_rag.cli.group import cli

console = Console()


@cli.group("models")
def models_group():
    """Manage cached embedding models and embedders (~/.kgrag/models/)."""
    pass


@models_group.command("list")
@click.option("--model-dir", default=None, metavar="PATH", help="Override model cache directory.")
def list_models(model_dir):
    """List all cached models."""
    from kg_rag.model_coordinator import ModelCoordinator  # pylint: disable=import-outside-toplevel

    mc = ModelCoordinator(model_dir=Path(model_dir) if model_dir else None)
    cached = mc.list_cached()
    if not cached:
        console.print("[dim]No models cached yet.[/dim]")
        console.print(f"[dim]Cache directory: {mc.model_dir}[/dim]")
        console.print("\nRun [bold]kgrag models download[/bold] to fetch the default model.")
        return

    table = Table(title="Cached Models & Embedders", show_lines=True)
    table.add_column("Model", style="cyan")
    table.add_column("Size", justify="right", style="green")
    table.add_column("Downloaded", style="yellow")
    table.add_column("Path", style="dim")

    for m in cached:
        size_mb = m.size_bytes / (1024 * 1024) if m.size_bytes else 0
        table.add_row(
            m.repo_id,
            f"{size_mb:.1f} MB",
            m.downloaded_at.strftime("%Y-%m-%d %H:%M") if m.downloaded_at else "unknown",
            str(m.local_path),
        )

    console.print(table)
    total_mb = mc.total_size() / (1024 * 1024)
    console.print(f"\n[dim]Total: {total_mb:.1f} MB in {mc.model_dir}[/dim]")


@models_group.command("download")
@click.argument("model_id", default="default")
@click.option("--model-dir", default=None, metavar="PATH", help="Override model cache directory.")
def download_model(model_id, model_dir):
    """Download an embedding model to the shared cache.

    MODEL_ID is a HuggingFace repo ID or alias (default: nomic-embed-text-v1.5).

    \b
    Built-in aliases:
      default, nomic     → nomic-ai/nomic-embed-text-v1.5
      nomic-v1           → nomic-ai/nomic-embed-text-v1
      all-MiniLM-L6-v2   → sentence-transformers/all-MiniLM-L6-v2
      bge-small-en-v1.5  → BAAI/bge-small-en-v1.5
    """
    from kg_rag.model_coordinator import (  # pylint: disable=import-outside-toplevel
        KNOWN_MODELS,
        ModelCoordinator,
    )

    mc = ModelCoordinator(model_dir=Path(model_dir) if model_dir else None)

    if model_id in KNOWN_MODELS:
        resolved = KNOWN_MODELS[model_id]
        console.print(f"Alias [cyan]{model_id}[/cyan] → [bold]{resolved}[/bold]")
    else:
        resolved = model_id

    with console.status(f"Downloading [bold]{resolved}[/bold]..."):
        path = mc.ensure(resolved)

    size_mb = mc.total_size() / (1024 * 1024)
    console.print(f"[green]✓[/green] Model cached at: {path}")
    console.print(f"[dim]Total cache size: {size_mb:.1f} MB[/dim]")


@models_group.command("remove")
@click.argument("model_id")
@click.option("--model-dir", default=None, metavar="PATH", help="Override model cache directory.")
def remove_model(model_id, model_dir):
    """Remove a cached model and its embedder."""
    from kg_rag.model_coordinator import ModelCoordinator  # pylint: disable=import-outside-toplevel

    mc = ModelCoordinator(model_dir=Path(model_dir) if model_dir else None)
    if mc.remove(model_id):
        console.print(f"[green]✓[/green] Removed {model_id}")
    else:
        console.print(f"[yellow]Model {model_id} not found in cache.[/yellow]")


@models_group.command("path")
@click.argument("model_id", default="default")
@click.option("--model-dir", default=None, metavar="PATH", help="Override model cache directory.")
def model_path(model_id, model_dir):
    """Print the cache path for a model (download if needed)."""
    from kg_rag.model_coordinator import ModelCoordinator  # pylint: disable=import-outside-toplevel

    mc = ModelCoordinator(model_dir=Path(model_dir) if model_dir else None)
    path = mc.ensure(model_id)
    click.echo(str(path))


@models_group.command("env")
@click.option("--model-dir", default=None, metavar="PATH", help="Override model cache directory.")
def show_env(model_dir):
    """Show environment variables for downstream modules."""
    from kg_rag.model_coordinator import ModelCoordinator  # pylint: disable=import-outside-toplevel

    mc = ModelCoordinator(model_dir=Path(model_dir) if model_dir else None)
    env = mc.export_env()
    console.print("[bold]Add to your shell profile:[/bold]\n")
    for key, value in env.items():
        console.print(f"export {key}={value}")


@models_group.command("aliases")
def show_aliases():
    """Show all known model aliases."""
    from kg_rag.model_coordinator import KNOWN_MODELS  # pylint: disable=import-outside-toplevel

    table = Table(title="Known Model Aliases", show_lines=True)
    table.add_column("Alias", style="cyan")
    table.add_column("HuggingFace Repo ID", style="bold")

    for alias, repo_id in sorted(KNOWN_MODELS.items()):
        table.add_row(alias, repo_id)

    console.print(table)
    console.print(f"\n[bold]Default:[/bold] {KNOWN_MODELS['default']}")


@models_group.command("cleanup")
@click.option("--model-dir", default=None, metavar="PATH", help="Override model cache directory.")
def cleanup_models(model_dir):
    """Remove orphan model directories not in the manifest."""
    from kg_rag.model_coordinator import ModelCoordinator  # pylint: disable=import-outside-toplevel

    mc = ModelCoordinator(model_dir=Path(model_dir) if model_dir else None)
    removed = mc.cleanup()
    if removed:
        console.print(
            f"[green]✓[/green] Removed {removed} orphan director{'y' if removed == 1 else 'ies'}."
        )
    else:
        console.print("[dim]No orphan directories found.[/dim]")


@models_group.command("test-embed")
@click.argument("text")
@click.option("--model-id", default="default", help="Model alias or HuggingFace repo ID.")
@click.option("--model-dir", default=None, metavar="PATH", help="Override model cache directory.")
def test_embed(text, model_id, model_dir):
    """Encode a text string and show the embedding shape and first values.

    Useful for verifying that the embedder loads and runs correctly.
    """
    from kg_rag.model_coordinator import ModelCoordinator  # pylint: disable=import-outside-toplevel

    mc = ModelCoordinator(model_dir=Path(model_dir) if model_dir else None)

    with console.status("Loading embedder..."):
        vectors = mc.encode([text], model_id=model_id)

    vec = vectors[0]
    console.print(f"[bold]Model:[/bold] {mc._resolve_alias(model_id)}")
    console.print(f"[bold]Dimensions:[/bold] {len(vec)}")
    console.print(f"[bold]First 8 values:[/bold] {vec[:8]}")
    console.print(f"[bold]Norm:[/bold] {float(sum(v**2 for v in vec) ** 0.5):.6f}")
