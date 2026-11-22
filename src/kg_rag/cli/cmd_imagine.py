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

import base64
import os
import re
import time
import warnings
from io import BytesIO
from pathlib import Path

import click

from kg_rag.cli.group import cli
from kg_rag.cli.options import k_option, kind_option, registry_option
from kg_rag.cli.retrieval import retrieve_snippets
from kg_rag.orchestrator import KGRAG
from kg_rag.primitives import CrossSnippet, KGKind

#: KG kinds whose passages are prose; a top hit from one of these is rewritten
#: with the historical-prose prompt, any other kind with the technical one.
PROSE_KINDS = frozenset({KGKind.DOC, KGKind.GUTENBERG, KGKind.DIARY})

#: Lines of surrounding context per retrieved snippet.
_CONTEXT_LINES = 5

#: Most characters of joined passages sent to the rewrite, or to the image
#: model when the rewrite is skipped or fails.
_MAX_PASSAGE_CHARS = 800

_INSTALL_HINT = 'kgrag imagine needs the imagine extra: pip install "kg-rag[imagine]"'


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


def passages_text(snippets: list[CrossSnippet]) -> str:
    """Join retrieved passages into one text, capped at ``_MAX_PASSAGE_CHARS``.

    :param snippets: Retrieved snippets, best first.
    :return: The passages, separated by blank lines.
    """
    joined = "\n\n".join(s.content.strip() for s in snippets if s.content.strip())
    return joined[:_MAX_PASSAGE_CHARS]


def rewrite_system(snippets: list[CrossSnippet]) -> str | None:
    """Choose the rewrite system prompt from the top-ranked hit's KG kind.

    :param snippets: Retrieved snippets, best first (non-empty).
    :return: None (the default historical-prose prompt) when the top hit is
        from a kind in :data:`PROSE_KINDS`, else ``IMAGE_REWRITE_TECHNICAL_SYSTEM``.
    """
    from kg_utils.synthesis import IMAGE_REWRITE_TECHNICAL_SYSTEM

    return None if snippets[0].kg_kind in PROSE_KINDS else IMAGE_REWRITE_TECHNICAL_SYSTEM


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

    try:
        import imagewright
        from kg_utils.synthesis import text_synthesizer_from_env
        from kg_utils.worker import WorkerClient
    except ImportError as exc:
        raise click.ClickException(_INSTALL_HINT) from exc

    client = WorkerClient(worker, os.environ.get("HANDLER_SECRET", "")) if worker else None
    if client and seed is not None:
        click.echo("Warning: --seed is ignored with --worker.", err=True)

    # Resolve the backend before retrieval, so "nothing available" fails fast.
    config = None
    if not (client or context_only):
        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter("always")
            try:
                config = imagewright.resolve_image_config(backend=backend, endpoint=endpoint)
            except (imagewright.NoImageBackendError, ValueError) as exc:
                raise click.ClickException(str(exc)) from exc
        for w in caught:
            click.echo(f"Warning: {w.message}", err=True)

    final_prompt = prompt
    if query is not None:
        reg_path = Path(registry).resolve() if registry else None
        with KGRAG(registry_path=reg_path) as kg:
            snippets, kgs_queried = retrieve_snippets(
                kg,
                query,
                k=k,
                kinds=[KGKind.from_str(kind)] if kind else None,
                corpus=corpus,
                reg_path=reg_path,
                context_lines=_CONTEXT_LINES,
                max_context=k,
            )
        if not snippets:
            raise click.ClickException(f"No passages found for {query!r} in the registered KGs.")
        click.echo(f"Found {len(snippets)} passage(s) from {kgs_queried} KG(s).")

        text = passages_text(snippets)
        if prompt:
            text = f"{text}\n\nAdditional style/scene notes: {prompt}"
        if context_only:
            click.echo(text)

        final_prompt = text
        if not no_rewrite:
            system = rewrite_system(snippets)
            if client:
                final_prompt, error = client.rewrite(text, system=system or "")
            else:
                final_prompt, error = text_synthesizer_from_env().rewrite_for_image(
                    text, system=system
                )
            if error:
                click.echo(f"Warning: rewrite failed ({error}); using the raw passages.", err=True)
                final_prompt = text
            elif context_only:
                click.echo(f"\nRewritten prompt:\n{final_prompt}")
        if context_only:
            return

    click.echo(f"Prompt: {final_prompt}")
    if client:
        b64, _, _, error = client.imagine(final_prompt, steps=steps, size=size)
        if error or not b64:
            raise click.ClickException(f"Worker {worker} failed: {error or 'no image returned'}")
        from PIL import Image

        image = Image.open(BytesIO(base64.b64decode(b64)))
    else:
        assert config is not None  # resolved above whenever there is no worker
        click.echo(f"Rendering with {config.backend.value}...")
        try:
            image = imagewright.ImageSynthesizer(config).generate(
                final_prompt, seed=seed, steps=steps, size=size
            )
        except imagewright.MissingExtraError as exc:
            raise click.ClickException(str(exc)) from exc
        except Exception as exc:
            raise click.ClickException(f"Image generation failed: {exc}") from exc

    out_path = output or Path(time.strftime("imagine_%Y%m%d_%H%M%S.png"))
    image.save(out_path, format="PNG")
    click.echo(f"Saved {out_path}")
    if open_image:
        click.launch(str(out_path))
