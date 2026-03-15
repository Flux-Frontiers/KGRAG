"""cli.py — Click CLI for the diary transformer package.

Entry points::

    diary-transformer transform <input> <output>   # pipe-delimited chunk file
    diary-transformer ingest    <input> <corpus>   # DocKG-compatible .md corpus
    diary-transformer build     <corpus>           # index corpus → SQLite + LanceDB
"""

from __future__ import annotations

import subprocess
import sys
import warnings
from pathlib import Path

import click
from rich.console import Console

console = Console()


# ---------------------------------------------------------------------------
# Shared options
# ---------------------------------------------------------------------------

_chunking_option = click.option(
    "--chunking-strategy",
    type=click.Choice(["semantic", "sentence_group", "hybrid"]),
    default="sentence_group",
    show_default=True,
    help="Text chunking strategy.",
)
_chunk_size_option = click.option(
    "--chunk-size", "-c", default=512, show_default=True, help="Max characters per chunk."
)
_sentences_option = click.option(
    "--sentences-per-chunk", default=4, show_default=True, help="Sentences per chunk (sentence_group / hybrid)."
)
_batch_option = click.option(
    "--batch-size", "-b", default=20, show_default=True,
    help="Diverse entries to sample per run (0 = all).",
)
_seed_option = click.option("--seed", default=None, type=int, help="RNG seed for reproducibility.")
_max_chunks_option = click.option(
    "--max-chunks-per-entry", "-m", default=3, show_default=True,
    help="Max chunks emitted per diary entry.",
)
_workers_option = click.option(
    "--workers", "-w", default=1, show_default=True, help="Parallel workers for feature extraction."
)
_topics_option = click.option("--topics-file", "-t", default=None, help="Path to YAML topics file.")


def _make_transformer(chunking_strategy, chunk_size, sentences_per_chunk, workers, topics_file):
    """Instantiate DiaryTransformer with shared parameters."""
    warnings.filterwarnings("ignore", category=ResourceWarning, message="unclosed.*")
    from .transformer import DiaryTransformer  # pylint: disable=import-outside-toplevel

    return DiaryTransformer(
        max_chunk_length=chunk_size,
        num_workers=workers,
        topics_file=topics_file,
        chunking_strategy=chunking_strategy,
        sentences_per_chunk=sentences_per_chunk,
    )


# ---------------------------------------------------------------------------
# CLI group
# ---------------------------------------------------------------------------

@click.group()
def cli():
    """Diary Transformer — convert diary entries into semantic memory chunks."""


# ---------------------------------------------------------------------------
# transform command (original workflow)
# ---------------------------------------------------------------------------

@cli.command("transform")
@click.argument("input_path", metavar="INPUT", type=click.Path(exists=True, dir_okay=False))
@click.argument("output_path", metavar="OUTPUT")
@_chunking_option
@_chunk_size_option
@_sentences_option
@_batch_option
@_seed_option
@_max_chunks_option
@_workers_option
@_topics_option
@click.option("--resume", "--incremental", "resume", is_flag=True, help="Resume from existing state.")
@click.option("--state-file", default=None, help="State file path (default: <output-dir>/.diary_state.json).")
@click.option("--clear", is_flag=True, help="Clear all caches before running.")
@click.option(
    "--restart", is_flag=True,
    help="Clear injection state + chunk cache (preserve diversity cache).",
)
def transform(
    input_path, output_path,
    chunking_strategy, chunk_size, sentences_per_chunk,
    batch_size, seed, max_chunks_per_entry,
    workers, topics_file,
    resume, state_file, clear, restart,
):
    """Transform diary entries into pipe-delimited semantic chunk output.

    \b
    INPUT   Pipe-delimited diary source file.
    OUTPUT  Destination file for transformed chunks.

    Examples:

    \b
        diary-transformer transform pepys.txt out/chunks.txt
        diary-transformer transform pepys.txt out/chunks.txt --resume --batch-size 50
    """
    in_path = Path(input_path)
    out_path = Path(output_path)
    sf = Path(state_file) if state_file else out_path.parent / ".diary_state.json"

    if clear:
        import shutil  # pylint: disable=import-outside-toplevel
        cache_dir = in_path.parent / ".diary_cache"
        if cache_dir.exists():
            shutil.rmtree(cache_dir)
            console.print(f"[green]✓[/green] Cleared feature cache: {cache_dir}")
        for ext in (".pkl", ".json"):
            p = in_path.parent / f"{in_path.stem}_chunks{ext}"
            if p.exists():
                p.unlink()
                console.print(f"[green]✓[/green] Cleared chunk cache: {p}")

    if restart:
        if sf.exists():
            sf.unlink()
            console.print(f"[green]✓[/green] Cleared state: {sf}")
        for ext in (".pkl", ".json"):
            p = in_path.parent / f"{in_path.stem}_chunks{ext}"
            if p.exists():
                p.unlink()
                console.print(f"[green]✓[/green] Cleared chunk cache: {p}")

    console.print(f"[bold]Diary Transform[/bold]  {in_path} → {out_path}")

    try:
        dt = _make_transformer(chunking_strategy, chunk_size, sentences_per_chunk, workers, topics_file)
        if resume:
            dt.transform_file_incremental(
                str(in_path), str(out_path), str(sf),
                batch_size=batch_size, seed=seed,
                max_chunks_per_entry=max_chunks_per_entry, resume_mode=True,
            )
        else:
            dt.transform_file(
                str(in_path), str(out_path),
                batch_size=batch_size, seed=seed,
                max_chunks_per_entry=max_chunks_per_entry,
            )
        console.print(f"\n[green]Done![/green] Output: {out_path}")
    except KeyboardInterrupt:
        console.print("\n[yellow]Cancelled[/yellow]")
        sys.exit(1)
    except Exception as exc:  # pylint: disable=broad-exception-caught
        import traceback  # pylint: disable=import-outside-toplevel
        console.print(f"\n[red]Error:[/red] {exc}")
        traceback.print_exc()
        sys.exit(1)


# ---------------------------------------------------------------------------
# ingest command — write DocKG-compatible .md corpus
# ---------------------------------------------------------------------------

@cli.command("ingest")
@click.argument("input_path", metavar="INPUT", type=click.Path(exists=True, dir_okay=False))
@click.argument("corpus_dir", metavar="CORPUS_DIR")
@_chunking_option
@_chunk_size_option
@_sentences_option
@_batch_option
@_seed_option
@_max_chunks_option
@_workers_option
@_topics_option
@click.option(
    "--source-file", default=None,
    help="Provenance label written into frontmatter (default: basename of INPUT).",
)
@click.option("--wipe", is_flag=True, help="Delete existing .md files in CORPUS_DIR before writing.")
def ingest(
    input_path, corpus_dir,
    chunking_strategy, chunk_size, sentences_per_chunk,
    batch_size, seed, max_chunks_per_entry,
    workers, topics_file,
    source_file, wipe,
):
    """Ingest a diary file into a DocKG-compatible Markdown corpus.

    Segments the diary into chunks and writes one ``.md`` file per chunk with
    YAML frontmatter (source_file, entry_index, chunk_index, timestamp,
    category, context).  The corpus directory is then ready for ``build``.

    \b
    INPUT       Pipe-delimited diary source file.
    CORPUS_DIR  Output directory for generated .md chunk files.

    Examples:

    \b
        diary-transformer ingest pepys.txt pepys_corpus/
        diary-transformer ingest pepys.txt pepys_corpus/ --batch-size 0 --wipe
        diary-transformer ingest pepys.txt pepys_corpus/ --source-file pepys_diary.txt
    """
    corpus = Path(corpus_dir)

    if wipe and corpus.exists():
        for md in corpus.glob("*.md"):
            md.unlink()
        console.print(f"[yellow]Wiped[/yellow] existing .md files in {corpus}")

    console.print(f"[bold]Diary Ingest[/bold]  {input_path} → {corpus}")

    try:
        dt = _make_transformer(chunking_strategy, chunk_size, sentences_per_chunk, workers, topics_file)
        n = dt.ingest_to_corpus(
            str(input_path), str(corpus),
            batch_size=batch_size, seed=seed,
            max_chunks_per_entry=max_chunks_per_entry,
            source_file=source_file,
        )
        console.print(f"\n[green]Done![/green] Wrote {n} chunk files to [bold]{corpus}[/bold]")
        console.print(
            f"\nNext step: [bold]diary-transformer build {corpus}[/bold]"
        )
    except KeyboardInterrupt:
        console.print("\n[yellow]Cancelled[/yellow]")
        sys.exit(1)
    except Exception as exc:  # pylint: disable=broad-exception-caught
        import traceback  # pylint: disable=import-outside-toplevel
        console.print(f"\n[red]Error:[/red] {exc}")
        traceback.print_exc()
        sys.exit(1)


# ---------------------------------------------------------------------------
# build command — run dockg build + optionally register in kgrag
# ---------------------------------------------------------------------------

@cli.command("build")
@click.argument("corpus_dir", metavar="CORPUS_DIR", type=click.Path(exists=True, file_okay=False))
@click.option("--wipe", is_flag=True, help="Pass --wipe to dockg build (rebuild from scratch).")
@click.option(
    "--register", "kg_name", default=None, metavar="NAME",
    help="Register the built KG in the KGRAG registry under this name.",
)
@click.option(
    "--registry", default=None, metavar="PATH", envvar="KGRAG_REGISTRY",
    help="Path to KGRAG registry SQLite (default: KGRAG_REGISTRY env var).",
)
def build(corpus_dir, wipe, kg_name, registry):
    """Build DocKG databases from an ingested Markdown corpus.

    Invokes ``dockg build`` on CORPUS_DIR to populate ``.dockg/graph.sqlite``
    and ``.dockg/lancedb/``.  If ``--register NAME`` is given the resulting KG
    is registered in the KGRAG registry as a diary KG.

    \b
    CORPUS_DIR  Directory of .md chunk files produced by ``ingest``.

    Examples:

    \b
        diary-transformer build pepys_corpus/
        diary-transformer build pepys_corpus/ --wipe
        diary-transformer build pepys_corpus/ --register pepys-diary
    """
    corpus = Path(corpus_dir).resolve()

    # ---- Step 1: dockg build ----
    cmd = ["dockg", "build", "--repo", str(corpus)]
    if wipe:
        cmd.append("--wipe")

    console.print(f"[bold]Building DocKG[/bold] for corpus: {corpus}")
    console.print(f"  Running: {' '.join(cmd)}")

    try:
        result = subprocess.run(cmd, check=True)
    except FileNotFoundError:
        console.print(
            "[red]Error:[/red] [bold]dockg[/bold] not found on PATH. "
            "Install it with: pip install doc-kg"
        )
        sys.exit(1)
    except subprocess.CalledProcessError as exc:
        console.print(f"[red]dockg build failed[/red] (exit {exc.returncode})")
        sys.exit(exc.returncode)

    # Locate built DB paths
    db_dir = corpus / ".dockg"
    sqlite_path = db_dir / "graph.sqlite"
    lancedb_path = db_dir / "lancedb"

    console.print("\n[green]✓ DocKG build complete[/green]")
    if sqlite_path.exists():
        console.print(f"  SQLite  : {sqlite_path}")
    if lancedb_path.exists():
        console.print(f"  LanceDB : {lancedb_path}")

    # ---- Step 2: optional kgrag registration ----
    if kg_name:
        try:
            from datetime import date  # pylint: disable=import-outside-toplevel
            from pathlib import Path as _Path  # pylint: disable=import-outside-toplevel

            from kg_rag.primitives import KGEntry, KGKind  # pylint: disable=import-outside-toplevel
            from kg_rag.registry import KGRegistry  # pylint: disable=import-outside-toplevel

            entry = KGEntry(
                name=kg_name,
                kind=KGKind.DIARY,
                repo_path=corpus,
                venv_path=corpus / ".venv",
                sqlite_path=sqlite_path if sqlite_path.exists() else None,
                lancedb_path=lancedb_path if lancedb_path.exists() else None,
                tags=[date.today().isoformat()],
            )

            reg_path = _Path(registry).resolve() if registry else None
            with KGRegistry(db_path=reg_path) as reg:
                reg.register(entry)

            console.print(f"\n[green]✓ Registered[/green] [bold]{kg_name}[/bold] (diary) in KGRAG registry")
            if reg_path:
                console.print(f"  Registry: {reg_path}")
        except ImportError:
            console.print(
                "\n[yellow]Warning:[/yellow] kg-rag not installed — skipping registry step. "
                "Install it with: pip install kg-rag"
            )
        except Exception as exc:  # pylint: disable=broad-exception-caught
            console.print(f"\n[yellow]Warning:[/yellow] Registration failed: {exc}")
    else:
        console.print(
            f"\nTo register in KGRAG: "
            f"[bold]diary-transformer build {corpus_dir} --register <name>[/bold]"
        )


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main() -> None:
    """Console-script entry point."""
    cli()


if __name__ == "__main__":
    main()
