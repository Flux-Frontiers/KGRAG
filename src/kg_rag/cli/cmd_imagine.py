"""
cmd_imagine.py

kgrag imagine -- generate an image from a prompt, or from passages retrieved
across the registered KGs.

Usage::

    kgrag imagine "a lighthouse in a storm, oil painting"
    kgrag imagine --query "great fire of London"
    kgrag imagine --query "registry schema" --kind code --no-rewrite
    kgrag imagine --query "great fire" --corpus diaries --context-only
    kgrag imagine --query "great fire" --worker http://tesla:8000

    Author: Eric G. Suchanek, PhD

    License: Elastic 2.0
"""

from __future__ import annotations

import os
import re
import time
from pathlib import Path

import click

from kg_rag.cli.group import cli
from kg_rag.cli.options import k_option, kind_option, registry_option
from kg_rag.cli.retrieval import retrieve_snippets
from kg_rag.imagine import CONTEXT_LINES, ImagineError
from kg_rag.imagine import imagine as run_imagine
from kg_rag.orchestrator import KGRAG
from kg_rag.primitives import CrossSnippet, KGKind


def _check_size(ctx: click.Context, param: click.Parameter, value: str | None) -> str | None:
    """Reject a ``--size`` that is not ``WIDTHxHEIGHT``.

    :param ctx: Click context.
    :param param: The ``--size`` parameter.
    :param value: The value given, or None.
    :return: The value, unchanged.
    :raises click.BadParameter: If the value is not two positive integers joined by ``x``.
    """
    if value is not None and not re.fullmatch(r"[1-9]\d*x[1-9]\d*", value.lower()):
        raise click.BadParameter(f"expected WIDTHxHEIGHT, e.g. 1536x1024; got {value!r}")
    return value


@cli.command("imagine")
@click.argument("prompt", required=False, default=None)
@click.option(
    "--query",
    "-q",
    default=None,
    metavar="TEXT",
    help="Retrieve passages for this query from the registered KGs and picture them.",
)
@kind_option
@click.option(
    "--corpus",
    default=None,
    metavar="NAME",
    help="Scope retrieval to a named corpus (default: all registered KGs).",
)
@k_option
@click.option(
    "--size",
    default=None,
    callback=_check_size,
    metavar="WxH",
    help="Image size, e.g. 1536x1024 (the default) or 768x512. OpenAI ignores it.",
)
@click.option("--seed", default=None, type=int, help="Random seed for a reproducible image.")
@click.option(
    "--steps",
    default=None,
    type=int,
    help="Inference steps (4 fast, 25 quality). Default: IMAGE_STEPS, else 4.",
)
@click.option(
    "--backend",
    default=None,
    type=click.Choice(["mflux-serve", "mflux-local", "openai"], case_sensitive=False),
    help="Image backend. Default: IMAGE_BACKEND, else a discovered server, else in-process FLUX.",
)
@click.option(
    "--endpoint",
    default=None,
    metavar="URL",
    help="Image server base URL (mflux-serve). Default: IMAGE_ENDPOINT, else discovery.",
)
@click.option(
    "--worker",
    default=None,
    metavar="URL",
    help="Send the rewrite and the render to a LAN worker; secret from HANDLER_SECRET.",
)
@click.option(
    "-o",
    "--output",
    default=None,
    type=click.Path(dir_okay=False, path_type=Path),
    help="PNG path to write. Default: imagine_YYYYMMDD_HHMMSS.png in the current directory.",
)
@click.option(
    "--open/--no-open",
    "open_image",
    default=True,
    show_default=True,
    help="Open the image in the default viewer when it is written.",
)
@click.option(
    "--context-only",
    is_flag=True,
    default=False,
    help="Print the retrieved passages (and the rewritten prompt) and exit without rendering.",
)
@click.option(
    "--no-rewrite",
    is_flag=True,
    default=False,
    help="Send the retrieved passages to the image model as they are, without the text model.",
)
@registry_option
def imagine(
    prompt,
    query,
    kind,
    corpus,
    k,
    size,
    seed,
    steps,
    backend,
    endpoint,
    worker,
    output,
    open_image,
    context_only,
    no_rewrite,
    registry,
):
    """Generate an image from PROMPT, or from passages retrieved for --query.

    PROMPT alone is rendered as given. With --query, the top passages from
    the registered KGs (or --corpus) are rewritten into a scene description
    by the text model (SYNTH_* settings), then rendered. PROMPT given with
    --query is added to the passages as style and scene notes.

    The image renders on a server (--endpoint, IMAGE_ENDPOINT, or one found
    on localhost:8090/8091), in process with FLUX (kg-rag[imagine-local]),
    with OpenAI (--backend openai), or on a LAN worker (--worker).

    Examples:

    \b
        kgrag imagine "a lighthouse in a storm, oil painting"
        kgrag imagine --query "great fire of London" -o fire.png
        kgrag imagine "woodcut" --query "great fire" --corpus diaries
        kgrag imagine --query "registry schema" --kind code --context-only
        kgrag imagine --query "great fire" --worker http://tesla:8000
    """
    if prompt is None and query is None:
        raise click.UsageError("Provide a PROMPT argument or --query.")
    if worker and (backend or endpoint):
        raise click.UsageError("--worker cannot be combined with --backend or --endpoint.")
    if (context_only or no_rewrite) and query is None:
        raise click.UsageError("--context-only and --no-rewrite need --query.")
    if worker and seed is not None:
        click.echo("Warning: --seed is ignored with --worker.", err=True)

    reg_path = Path(registry).resolve() if registry else None

    def retrieve(query_text: str) -> tuple[list[CrossSnippet], int]:
        with KGRAG(registry_path=reg_path) as kg:
            try:
                return retrieve_snippets(
                    kg,
                    query_text,
                    k=k,
                    kinds=[KGKind.from_str(kind)] if kind else None,
                    corpus=corpus,
                    reg_path=reg_path,
                    context_lines=CONTEXT_LINES,
                    max_context=k,
                )
            except SystemExit:
                # An empty corpus: retrieve_snippets has said so and exits 0,
                # which suits synthesize; an image command with no image fails.
                return [], 0

    try:
        result = run_imagine(
            prompt,
            query=query,
            retrieve=retrieve,
            rewrite=not no_rewrite,
            render=not context_only,
            size=size,
            seed=seed,
            steps=steps,
            backend=backend,
            endpoint=endpoint,
            worker=worker,
            worker_secret=os.environ.get("HANDLER_SECRET", ""),
            notify=click.echo,
            warn=lambda message: click.echo(f"Warning: {message}", err=True),
        )
    except ImagineError as exc:
        raise click.ClickException(str(exc)) from exc
    if context_only:
        return

    out_path = output or Path(time.strftime("imagine_%Y%m%d_%H%M%S.png"))
    result.image.save(out_path, format="PNG")
    click.echo(f"Saved {out_path}")
    if open_image:
        click.launch(str(out_path))
