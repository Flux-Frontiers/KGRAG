"""
cmd_synthesize.py

kgrag synthesize — retrieve KG context and synthesize an answer via Ollama or
any OpenAI-compatible inference server (e.g. omlx, LM Studio, vLLM).

Usage::

    kgrag synthesize "What motivates Victor Frankenstein?"
    kgrag synthesize "theme of isolation in 19th century novels" --kind doc -k 8
    kgrag synthesize "Watson's role" --corpus gutenberg-fiction --model llama3.2
    kgrag synthesize "entropy" --ollama-url http://myserver:11434

    # omlx (OpenAI-compatible):
    kgrag synthesize "entropy" --backend openai --model mlx-community/Qwen3-8B-4bit
    kgrag synthesize "entropy" --backend openai --openai-url http://myserver:8000/v1

    Author: Eric G. Suchanek, PhD
    Last Revision: 2026-05-30

    License: Elastic 2.0
"""

from __future__ import annotations

import sys
from pathlib import Path

import click
from rich.console import Console
from rich.markdown import Markdown
from rich.rule import Rule

from kg_rag.cli.group import cli
from kg_rag.cli.options import k_option, kind_option, registry_option
from kg_rag.orchestrator import KGRAG
from kg_rag.primitives import KGKind

console = Console()

_DEFAULT_OLLAMA_URL = "http://localhost:11434"
_DEFAULT_OPENAI_URL = "http://127.0.0.1:8000/v1"
_DEFAULT_MODEL = "qwen3:8b"
_DEFAULT_OPENAI_MODEL = "Qwen3-4B-Instruct-2507-MLX-8bit"

_SYSTEM_PROMPT = """\
You are a knowledgeable literary and research assistant. You are given excerpts \
retrieved from a knowledge graph built from books and documents. Use these excerpts \
as your primary source and summarize a clear, accurate answer to the user's question. \
If the excerpts do not contain enough information, say so honestly.\
"""


def _call_ollama(
    prompt: str,
    model: str,
    base_url: str,
    stream: bool,
) -> str:
    """Send a prompt to Ollama and return the response text.

    :param prompt: Full prompt to send.
    :param model: Ollama model name (e.g. ``llama3.2``).
    :param base_url: Ollama base URL (e.g. ``http://localhost:11434``).
    :param stream: If True, stream tokens to stdout as they arrive.
    :return: Full response text.
    """
    try:
        import httpx  # pylint: disable=import-outside-toplevel
    except ImportError as e:
        raise click.ClickException("httpx is required: pip install httpx") from e

    import json  # pylint: disable=import-outside-toplevel

    url = base_url.rstrip("/") + "/api/generate"
    payload = {
        "model": model,
        "prompt": prompt,
        "system": _SYSTEM_PROMPT,
        "stream": stream,
    }

    _timeout = httpx.Timeout(connect=10.0, read=600.0, write=60.0, pool=10.0)

    try:
        if stream:
            full_text = ""
            with httpx.stream("POST", url, json=payload, timeout=_timeout) as resp:
                if resp.status_code != 200:
                    raise click.ClickException(
                        f"Ollama returned HTTP {resp.status_code}. "
                        "Is Ollama running? Try: ollama serve"
                    )
                for line in resp.iter_lines():
                    if not line:
                        continue
                    chunk = json.loads(line)
                    token = chunk.get("response", "")
                    full_text += token
                    console.print(token, end="", highlight=False)
                    if chunk.get("done"):
                        break
            console.print()  # final newline
            return full_text
        else:
            resp = httpx.post(url, json=payload, timeout=_timeout)
            if resp.status_code != 200:
                raise click.ClickException(
                    f"Ollama returned HTTP {resp.status_code}. Is Ollama running? Try: ollama serve"
                )
            return resp.json().get("response", "")
    except httpx.ConnectError as e:
        raise click.ClickException(
            f"Cannot connect to Ollama at {base_url}.\nStart Ollama with: ollama serve\n  ({e})"
        ) from e


def _call_openai_compat(
    prompt: str,
    model: str,
    base_url: str,
    stream: bool,
    api_key: str | None = None,
) -> str:
    """Send a prompt to an OpenAI-compatible endpoint and return the response.

    Works with omlx, LM Studio, vLLM, llama.cpp server, or any server that
    implements ``POST /chat/completions``.

    :param prompt: Full user prompt (KG context already embedded).
    :param model: Model identifier as expected by the server.
    :param base_url: Server base URL including ``/v1`` suffix.
    :param stream: If True, stream tokens to stdout as they arrive.
    :param api_key: Bearer token if the server requires one (e.g. omlx).
    :return: Full response text.
    """
    try:
        import httpx  # pylint: disable=import-outside-toplevel
    except ImportError as e:
        raise click.ClickException("httpx is required: pip install httpx") from e

    import json  # pylint: disable=import-outside-toplevel

    url = base_url.rstrip("/") + "/chat/completions"
    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": _SYSTEM_PROMPT},
            {"role": "user", "content": prompt},
        ],
        "stream": stream,
    }
    headers = {"Content-Type": "application/json"}
    if api_key:
        headers["Authorization"] = f"Bearer {api_key}"
    _timeout = httpx.Timeout(connect=10.0, read=600.0, write=60.0, pool=10.0)

    try:
        if stream:
            full_text = ""
            with httpx.stream("POST", url, json=payload, headers=headers, timeout=_timeout) as resp:
                if resp.status_code != 200:
                    raise click.ClickException(
                        f"Server returned HTTP {resp.status_code} from {url}"
                    )
                for line in resp.iter_lines():
                    line = line.strip()
                    if not line or line == "data: [DONE]":
                        continue
                    if line.startswith("data: "):
                        line = line[6:]
                    try:
                        chunk = json.loads(line)
                    except json.JSONDecodeError:
                        continue
                    token = (
                        chunk.get("choices", [{}])[0].get("delta", {}).get("content", "")
                    ) or ""
                    full_text += token
                    if token:
                        console.print(token, end="", highlight=False)
            console.print()
            return full_text
        else:
            resp = httpx.post(url, json=payload, headers=headers, timeout=_timeout)
            if resp.status_code != 200:
                raise click.ClickException(f"Server returned HTTP {resp.status_code} from {url}")
            data = resp.json()
            return data.get("choices", [{}])[0].get("message", {}).get("content", "")
    except httpx.ConnectError as e:
        raise click.ClickException(
            f"Cannot connect to OpenAI-compatible server at {base_url}.\n"
            f"Is omlx (or your server) running?  ({e})"
        ) from e


@cli.command("synthesize")
@click.argument("query_text")
@k_option
@kind_option
@click.option(
    "--corpus",
    default=None,
    metavar="NAME",
    help="Scope retrieval to a named corpus (default: all registered KGs).",
)
@click.option(
    "--backend",
    default="ollama",
    show_default=True,
    type=click.Choice(["ollama", "openai"], case_sensitive=False),
    help=(
        "Inference backend. 'ollama' uses the native Ollama API; "
        "'openai' uses any OpenAI-compatible server (omlx, LM Studio, vLLM, …)."
    ),
)
@click.option(
    "--model",
    default=None,
    show_default=False,
    metavar="MODEL",
    help=(
        f"Model name. Defaults to '{_DEFAULT_MODEL}' for ollama "
        f"or '{_DEFAULT_OPENAI_MODEL}' for openai backend."
    ),
)
@click.option(
    "--ollama-url",
    default=_DEFAULT_OLLAMA_URL,
    show_default=True,
    envvar="OLLAMA_URL",
    metavar="URL",
    help="Ollama server base URL. Also read from $OLLAMA_URL.",
)
@click.option(
    "--openai-url",
    default=_DEFAULT_OPENAI_URL,
    show_default=True,
    envvar="OPENAI_BASE_URL",
    metavar="URL",
    help=(
        "Base URL for the OpenAI-compatible server (used with --backend openai). "
        "Also read from $OPENAI_BASE_URL. Default targets omlx on localhost."
    ),
)
@click.option(
    "--api-key",
    default=None,
    envvar="OPENAI_API_KEY",
    metavar="KEY",
    help=(
        "Bearer API key for the OpenAI-compatible server (used with --backend openai). "
        "Also read from $OPENAI_API_KEY."
    ),
)
@click.option(
    "--no-stream",
    is_flag=True,
    default=False,
    help="Disable token streaming (collect full response before printing).",
)
@click.option(
    "--show-context",
    is_flag=True,
    default=False,
    help="Print the retrieved KG context before the synthesized answer.",
)
@click.option(
    "--context-lines",
    default=5,
    show_default=True,
    metavar="N",
    help="Lines of surrounding context per snippet.",
)
@click.option(
    "--max-context",
    default=20,
    show_default=True,
    metavar="N",
    help="Maximum total snippets passed to the LLM (top-N by score). "
    "Prevents oversized prompts when many KGs are registered.",
)
@registry_option
def synthesize(
    query_text,
    k,
    kind,
    corpus,
    backend,
    model,
    ollama_url,
    openai_url,
    api_key,
    no_stream,
    show_context,
    context_lines,
    max_context,
    registry,
):
    """Retrieve KG context and synthesize an answer via Ollama or an OpenAI-compatible server.

    Retrieves the top-K most relevant snippets from registered KGs (or a
    specific corpus), assembles them into a prompt, and calls a local inference
    server (Ollama or omlx/LM Studio/vLLM via --backend openai) to generate a
    synthesized answer.

    \b
    QUERY_TEXT  Natural-language question or topic

    Examples:

    \b
        kgrag synthesize "What motivates Victor Frankenstein?"
        kgrag synthesize "theme of isolation" --kind doc -k 8
        kgrag synthesize "entropy" --corpus gutenberg-science --model mistral
        kgrag synthesize "Watson's role" --show-context --no-stream
        kgrag synthesize "entropy" --backend openai --model mlx-community/Qwen3-8B-4bit
        kgrag synthesize "entropy" --backend openai --openai-url http://myserver:8000/v1
    """
    # Resolve default model per backend when caller omits --model
    if model is None:
        model = _DEFAULT_MODEL if backend == "ollama" else _DEFAULT_OPENAI_MODEL
    kinds = [KGKind.from_str(kind)] if kind else None
    reg_path = Path(registry).resolve() if registry else None

    # ── 1. Retrieve context from KGs ────────────────────────────────────────
    console.print(f"[dim]Retrieving context for:[/dim] [bold]{query_text}[/bold]")

    with KGRAG(registry_path=reg_path) as kg:
        if corpus:
            # Scoped corpus query — use the corpus registry
            from kg_rag.corpus_registry import (  # pylint: disable=import-outside-toplevel
                CorpusRegistry,
            )
            from kg_rag.registry import (  # pylint: disable=import-outside-toplevel
                KGRegistry,
            )

            with KGRegistry(db_path=reg_path) as kreg, CorpusRegistry(db_path=reg_path) as creg:
                corpus_entry = creg.get(corpus)
                if corpus_entry is None:
                    raise click.ClickException(f"Corpus not found: {corpus!r}")
                kg_ids = corpus_entry.kg_ids
                entries = [kreg.get(gid) for gid in kg_ids]
                entries = [e for e in entries if e is not None]

            if not entries:
                console.print(f"[yellow]Corpus {corpus!r} has no registered KGs.[/yellow]")
                sys.exit(0)

            from kg_rag.adapters import (  # pylint: disable=import-outside-toplevel
                make_adapter,
            )
            from kg_rag.primitives import (  # pylint: disable=import-outside-toplevel
                CrossSnippet,
            )

            snippets: list[CrossSnippet] = []
            for entry in entries:
                if kinds and entry.kind not in kinds:
                    continue
                adapter = make_adapter(entry)
                if adapter.is_available():
                    snippets.extend(adapter.pack(query_text, k=k, context=context_lines))
            snippets.sort(key=lambda s: s.score, reverse=True)
            snippets = snippets[:max_context]
            kgs_queried = len(entries)
        else:
            pack_result = kg.pack(query_text, k=k, context=context_lines, kinds=kinds)
            snippets = pack_result.snippets[:max_context]
            kgs_queried = pack_result.kgs_queried

    if not snippets:
        console.print("[yellow]No relevant content found in registered KGs.[/yellow]")
        console.print("[dim]Register and build KGs first (kgrag init / kgrag register).[/dim]")
        sys.exit(0)

    console.print(f"[green]Found[/green] {len(snippets)} snippet(s) from {kgs_queried} KG(s)")

    # ── 2. Build context block ───────────────────────────────────────────────
    context_parts: list[str] = []
    for i, snip in enumerate(snippets, 1):
        header = f"[Excerpt {i} | KG: {snip.kg_name} | source: {snip.source_path or 'unknown'} | score: {snip.score:.3f}]"
        context_parts.append(f"{header}\n{snip.content.strip()}")

    context_block = "\n\n---\n\n".join(context_parts)

    full_prompt = f"Question: {query_text}\n\nRelevant excerpts:\n\n{context_block}\n\nAnswer:"

    if show_context:
        console.print(Rule("Retrieved Context"))
        console.print(context_block)
        console.print(Rule())

    # ── 3. Call inference backend ────────────────────────────────────────────
    if backend == "openai":
        server_label = openai_url
        console.print(
            Rule(f"Synthesizing with [bold]{model}[/bold] via omlx/openai at {server_label}")
        )
        answer = _call_openai_compat(
            prompt=full_prompt,
            model=model,
            base_url=openai_url,
            stream=not no_stream,
            api_key=api_key,
        )
    else:
        server_label = ollama_url
        console.print(Rule(f"Synthesizing with [bold]{model}[/bold] via ollama at {server_label}"))
        answer = _call_ollama(
            prompt=full_prompt,
            model=model,
            base_url=ollama_url,
            stream=not no_stream,
        )

    if no_stream:
        console.print(Markdown(answer))

    console.print(Rule())
