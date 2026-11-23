"""
imagine.py

The image flow behind ``kgrag imagine`` and the ``kg_imagine`` MCP tool:
resolve the image backend, retrieve passages, rewrite them into an image
prompt with the text model, and render.

:func:`imagine` takes plain arguments and raises :class:`ImagineError` with a
message ready to show; the CLI and the MCP tool are thin wrappers around it.
Retrieval is passed in as a callable, so each surface reaches the registry its
own way. ``imagewright`` and ``kg_utils.synthesis`` are imported inside
:func:`imagine`, so importing this module needs neither: a core-only install
still loads ``kgrag`` and ``kgrag-mcp``.

    Author: Eric G. Suchanek, PhD

    License: Elastic 2.0
"""

from __future__ import annotations

import base64
import threading
import warnings
from collections.abc import Callable
from dataclasses import dataclass, field
from io import BytesIO
from typing import Any

from kg_rag.primitives import CrossSnippet, KGKind

#: KG kinds whose passages are prose; a top hit from one of these is rewritten
#: with the historical-prose prompt, any other kind with the technical one.
PROSE_KINDS = frozenset({KGKind.DOC, KGKind.GUTENBERG, KGKind.DIARY})

#: Lines of surrounding context per retrieved snippet.
CONTEXT_LINES = 5

#: A caller fetches this many times the passages it wants, so that dropping
#: hits with no text still leaves enough.
FETCH_FACTOR = 4

#: Most characters of joined passages sent to the rewrite, or to the image
#: model when the rewrite is skipped or fails.
MAX_PASSAGE_CHARS = 800

INSTALL_HINT = 'kgrag imagine needs the imagine extra: pip install "kg-rag[imagine]"'

#: Added under imagewright's own install advice, which names imagewright's extras.
KG_RAG_HINT = (
    'With kg-rag: pip install "kg-rag[imagine-local]" for in-process FLUX; '
    '"kg-rag[imagine]" already includes the OpenAI client.'
)

# One render at a time, and one kept synthesizer, so an in-process model loads
# once per process rather than once per call (as imagewright's MCP server does).
_render_lock = threading.Lock()
_kept: tuple[Any, Any] | None = None  # (ImageConfig, ImageSynthesizer)


class ImagineError(RuntimeError):
    """The flow could not produce what was asked; the message says why and how to fix it."""


@dataclass
class Imagined:
    """What :func:`imagine` produced.

    :param prompt: The final prompt: sent to the image model, or with
        ``render=False``, the one that would have been.
    :param image: The PIL image, or None with ``render=False``.
    :param warnings: Warnings raised along the way, in order.
    """

    prompt: str
    image: Any = None
    warnings: list[str] = field(default_factory=list)


def usable_passages(snippets: list[CrossSnippet], limit: int | None = None) -> list[CrossSnippet]:
    """Keep the hits a rewrite can use: those with text, each node once.

    A retrieval can rank a hit with no source text first, or return one node
    several times. A rewrite given no text invents a scene, so those hits are
    dropped before the best *limit* are kept.

    :param snippets: Retrieved snippets, best first.
    :param limit: Most snippets to keep; None keeps all.
    :return: The usable snippets, best first.
    """
    seen: set[tuple[str, str]] = set()
    kept: list[CrossSnippet] = []
    for snip in snippets:
        key = (snip.kg_name, snip.node_id)
        if not (snip.content or "").strip() or key in seen:
            continue
        seen.add(key)
        kept.append(snip)
    return kept if limit is None else kept[:limit]


def passages_text(snippets: list[CrossSnippet]) -> str:
    """Join retrieved passages into one text, capped at :data:`MAX_PASSAGE_CHARS`.

    :param snippets: Retrieved snippets, best first.
    :return: The passages, separated by blank lines.
    """
    joined = "\n\n".join(s.content.strip() for s in snippets if s.content.strip())
    return joined[:MAX_PASSAGE_CHARS]


def rewrite_system(snippets: list[CrossSnippet]) -> str | None:
    """Choose the rewrite system prompt from the top-ranked hit's KG kind.

    :param snippets: Retrieved snippets, best first (non-empty).
    :return: None (the default historical-prose prompt) when the top hit is
        from a kind in :data:`PROSE_KINDS`, else ``IMAGE_REWRITE_TECHNICAL_SYSTEM``.
    """
    from kg_utils.synthesis import IMAGE_REWRITE_TECHNICAL_SYSTEM

    return None if snippets[0].kg_kind in PROSE_KINDS else IMAGE_REWRITE_TECHNICAL_SYSTEM


def _synthesizer(imagewright: Any, config: Any) -> Any:
    """Return the kept synthesizer for *config*, replacing one kept for another config."""
    global _kept  # pylint: disable=global-statement
    if _kept is None or _kept[0] != config:
        if _kept is not None and _kept[1].model_loaded:
            _kept[1].unload_model()
        _kept = (config, imagewright.ImageSynthesizer(config))
    return _kept[1]


def imagine(
    prompt: str | None = None,
    *,
    query: str | None = None,
    retrieve: Callable[[str], tuple[list[CrossSnippet], int]] | None = None,
    max_passages: int | None = None,
    rewrite: bool = True,
    render: bool = True,
    size: str | None = None,
    seed: int | None = None,
    steps: int | None = None,
    backend: str | None = None,
    endpoint: str | None = None,
    worker: str | None = None,
    worker_secret: str = "",
    notify: Callable[[str], None] | None = None,
    warn: Callable[[str], None] | None = None,
) -> Imagined:
    """Generate an image from *prompt*, or from passages retrieved for *query*.

    *prompt* alone is rendered as given. With *query*, *retrieve* fetches the
    passages, they are joined (capped at :data:`MAX_PASSAGE_CHARS`) with
    *prompt* added as style and scene notes, and the text model rewrites them
    into a scene description, with the prompt :func:`rewrite_system` chooses.
    A failed rewrite warns and falls back to the raw passages.

    The backend is resolved before retrieval, so "nothing available" fails
    fast: *worker* if given, else ``imagewright.resolve_image_config``
    (*backend* and *endpoint*, then the environment, then discovery, then
    in-process FLUX with a warning).

    :param prompt: The image prompt, or with *query*, style and scene notes.
    :param query: Retrieve passages for this query and picture them.
    :param retrieve: Called with *query*; returns ``(snippets, kgs_queried)``,
        snippets best first. Required with *query*.
    :param max_passages: Most passages to use, after hits with no text and
        repeats of one node are dropped. None uses all that *retrieve* returns.
    :param rewrite: Rewrite the passages with the text model; False sends them as they are.
    :param render: Render the image; False stops after the rewrite and
        reports the passages and the rewritten prompt through *notify*.
    :param size: Image size ``WIDTHxHEIGHT``; None for the backend's default.
    :param seed: Random seed; ignored by a worker.
    :param steps: Inference steps; None for ``IMAGE_STEPS``, else the backend's default.
    :param backend: Image backend name, e.g. ``"mflux-serve"``; None to resolve it.
    :param endpoint: Image server base URL for ``mflux-serve``.
    :param worker: LAN worker URL; it does both the rewrite and the render.
    :param worker_secret: The worker's shared secret.
    :param notify: Called with each progress line as it happens.
    :param warn: Called with each warning as it happens; all are also in the result.
    :return: The :class:`Imagined` result.
    :raises ValueError: If neither *prompt* nor *query* is given, or *query*
        is given without *retrieve*.
    :raises ImagineError: If the imagine extra is missing, no backend is
        available, no passages are found, or the render fails.
    """
    if prompt is None and query is None:
        raise ValueError("give a prompt or a query")
    if query is not None and retrieve is None:
        raise ValueError("a query needs a retrieve callable")

    try:
        import imagewright
        from kg_utils.synthesis import text_synthesizer_from_env
        from kg_utils.worker import WorkerClient
    except ImportError as exc:
        raise ImagineError(INSTALL_HINT) from exc

    result = Imagined(prompt=prompt or "")

    def say(line: str) -> None:
        if notify:
            notify(line)

    def warned(message: str) -> None:
        result.warnings.append(message)
        if warn:
            warn(message)

    client = WorkerClient(worker, worker_secret) if worker else None

    config = None
    if render and not client:
        # Under the lock: catch_warnings swaps process-wide state, and the
        # MCP tool may run two calls on two threads.
        with _render_lock, warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter("always")
            try:
                config = imagewright.resolve_image_config(backend=backend, endpoint=endpoint)
            except imagewright.NoImageBackendError as exc:
                raise ImagineError(f"{exc}\n{KG_RAG_HINT}") from exc
            except ValueError as exc:
                raise ImagineError(str(exc)) from exc
        for w in caught:
            warned(str(w.message))

    if query is not None:
        assert retrieve is not None  # checked above
        snippets, kgs_queried = retrieve(query)
        snippets = usable_passages(snippets, max_passages)
        if not snippets:
            raise ImagineError(f"No passages found for {query!r} in the registered KGs.")
        say(f"Found {len(snippets)} passage(s) from {kgs_queried} KG(s).")

        text = passages_text(snippets)
        if prompt:
            text = f"{text}\n\nAdditional style/scene notes: {prompt}"
        if not render:
            say(text)

        result.prompt = text
        if rewrite:
            system = rewrite_system(snippets)
            if client:
                rewritten, error = client.rewrite(text, system=system or "")
            else:
                rewritten, error = text_synthesizer_from_env().rewrite_for_image(
                    text, system=system
                )
            if error:
                warned(f"rewrite failed ({error}); using the raw passages.")
            else:
                result.prompt = rewritten
                if not render:
                    say(f"\nRewritten prompt:\n{rewritten}")
        if not render:
            return result

    say(f"Prompt: {result.prompt}")
    if client:
        b64, _, _, error = client.imagine(result.prompt, steps=steps, size=size)
        if error or not b64:
            raise ImagineError(f"Worker {worker} failed: {error or 'no image returned'}")
        from PIL import Image

        result.image = Image.open(BytesIO(base64.b64decode(b64)))
        return result

    assert config is not None  # resolved above whenever there is no worker
    say(f"Rendering with {config.backend.value}...")
    try:
        with _render_lock:
            result.image = _synthesizer(imagewright, config).generate(
                result.prompt, seed=seed, steps=steps, size=size
            )
    except imagewright.MissingExtraError as exc:
        raise ImagineError(f"{exc}\n{KG_RAG_HINT}") from exc
    except Exception as exc:
        raise ImagineError(f"Image generation failed: {exc}") from exc
    return result
