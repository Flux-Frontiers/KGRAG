#!/usr/bin/env python3
"""
app.py — KGRAG Streamlit Visualizer

Cross-KG registry manager and federated query explorer with:
  • Sidebar: configure registry path, select KGs, set query parameters
  • Registry tab: view all registered KG instances with live stats
  • Query tab: federated semantic query across selected KGs
  • Snippets tab: cross-KG source snippet pack viewer

Run with:
    poetry run kgrag viz
"""

from __future__ import annotations

import json
from pathlib import Path

import streamlit as st

from kg_rag.primitives import KGKind
from kg_rag.registry import default_registry_path

# ---------------------------------------------------------------------------
# Constants — colours per KG kind and node kind
# ---------------------------------------------------------------------------

_KG_KIND_COLOR: dict[str, str] = {
    "code": "#4A90D9",  # blue
    "doc": "#27AE60",  # green
    "meta": "#8E44AD",  # purple
}

_KG_KIND_ICON: dict[str, str] = {
    "code": "💻",
    "doc": "📄",
    "meta": "🧬",
}

_NODE_KIND_COLOR: dict[str, str] = {
    "module": "#4A90D9",
    "class": "#E67E22",
    "function": "#27AE60",
    "method": "#8E44AD",
    "chunk": "#F39C12",
    "section": "#1ABC9C",
    "entity": "#E74C3C",
}

_DEFAULT_REGISTRY = str(default_registry_path())

# ---------------------------------------------------------------------------
# Page config (must be first Streamlit call)
# ---------------------------------------------------------------------------

st.set_page_config(
    page_title="KGRAG Explorer",
    page_icon="🕸️",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ---------------------------------------------------------------------------
# CSS tweaks
# ---------------------------------------------------------------------------

st.markdown(
    """
    <style>
    .stTabs [data-baseweb="tab-list"] { gap: 12px; }
    .stTabs [data-baseweb="tab"] { font-size: 1rem; padding: 6px 18px; }
    .hit-card {
        border-radius: 6px;
        padding: 10px 14px;
        margin-bottom: 8px;
        font-family: monospace;
        font-size: 0.85rem;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

# ---------------------------------------------------------------------------
# Session-state initialisation
# ---------------------------------------------------------------------------


def _init_state() -> None:
    defaults = {
        "registry_path": _DEFAULT_REGISTRY,
        "query_result": None,
        "pack_result": None,
        "analysis_result": None,
    }
    for k, v in defaults.items():
        if k not in st.session_state:
            st.session_state[k] = v


# ---------------------------------------------------------------------------
# KGRAG orchestrator — cached per registry path
# ---------------------------------------------------------------------------


@st.cache_resource(show_spinner="Opening KGRAG registry…")
def _load_kgrag(registry_path: str):
    from kg_rag.orchestrator import KGRAG  # pylint: disable=import-outside-toplevel

    return KGRAG(registry_path=Path(registry_path))


def _get_kgrag():
    return _load_kgrag(st.session_state.registry_path)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _kg_kind_badge(kind: str, name: str = "") -> str:
    """Return an HTML badge for a KG kind."""
    color = _KG_KIND_COLOR.get(kind, "#95A5A6")
    icon = _KG_KIND_ICON.get(kind, "⬡")
    label = f"{icon} {kind}" + (f" · {name}" if name else "")
    return (
        f"<span style='background:{color};color:#fff;border-radius:4px;"
        f"padding:2px 9px;font-size:11px;font-weight:bold;font-family:monospace;'>"
        f"{label}</span>"
    )


def _node_kind_badge(kind: str) -> str:
    color = _NODE_KIND_COLOR.get(kind, "#95A5A6")
    return (
        f"<span style='background:{color};color:#fff;border-radius:3px;"
        f"padding:1px 6px;font-size:11px;font-weight:bold;font-family:monospace;'>"
        f"{kind}</span>"
    )


def _score_bar(score: float, width: int = 80) -> str:
    pct = min(int(score * 100), 100)
    color = "#27AE60" if score >= 0.7 else "#F39C12" if score >= 0.4 else "#E74C3C"
    return (
        f"<div style='display:inline-block;vertical-align:middle;"
        f"width:{width}px;height:8px;background:#2a2a3e;border-radius:4px;overflow:hidden;'>"
        f"<div style='width:{pct}%;height:100%;background:{color};'></div></div>"
        f"&nbsp;<small style='color:#aaa;font-size:10px;'>{score:.3f}</small>"
    )


# ---------------------------------------------------------------------------
# Sidebar
# ---------------------------------------------------------------------------


def _render_sidebar() -> dict:
    """Render sidebar controls and return configuration dict."""
    st.sidebar.title("🕸️ KGRAG Explorer")
    st.sidebar.markdown("---")

    # ── Registry path ────────────────────────────────────────────────────
    st.sidebar.subheader("📂 Registry")
    registry_path = st.sidebar.text_input(
        "Registry path",
        value=st.session_state.registry_path,
        help="Path to the KGRAG registry SQLite file (or set KGRAG_REGISTRY env var)",
    )
    st.session_state.registry_path = registry_path

    if st.sidebar.button("🔄 Refresh Registry", use_container_width=True):
        _load_kgrag.clear()  # type: ignore[attr-defined]
        st.rerun()

    kgrag = _get_kgrag()
    reg_stats = kgrag.registry.stats()

    if reg_stats.total == 0:
        st.sidebar.warning(
            "⚠️ No KGs registered.\n\nRun `kgrag init` in a project directory to register a KG."
        )
    else:
        built = reg_stats.built
        total = reg_stats.total
        st.sidebar.success(f"✅ {total} KGs registered · {built} built")
        with st.sidebar.expander("By kind"):
            for kind, count in sorted(reg_stats.by_kind.items()):
                icon = _KG_KIND_ICON.get(kind, "⬡")
                st.write(f"{icon} **{kind}**: {count}")

    # ── KG selection ─────────────────────────────────────────────────────
    st.sidebar.markdown("---")
    st.sidebar.subheader("🔎 KG Selection")

    kind_filter = st.sidebar.multiselect(
        "Filter by kind",
        options=[k.value for k in KGKind],
        default=[k.value for k in KGKind],
        format_func=lambda k: f"{_KG_KIND_ICON.get(k, '⬡')} {k}",
    )

    all_entries = kgrag.registry.list()
    filtered_entries = [e for e in all_entries if e.kind.value in kind_filter]
    entry_labels = {e.name: e for e in filtered_entries}

    selected_names = st.sidebar.multiselect(
        "Select KGs to query",
        options=list(entry_labels.keys()),
        default=list(entry_labels.keys()),
        help="Leave empty to query all KGs matching the kind filter",
    )

    # ── Query parameters ─────────────────────────────────────────────────
    st.sidebar.markdown("---")
    st.sidebar.subheader("⚙️ Query Parameters")
    k = st.sidebar.slider("Top-K results per KG", min_value=1, max_value=30, value=8)
    context = st.sidebar.slider("Context lines (snippets)", min_value=0, max_value=20, value=5)

    # Resolve selected kinds for orchestrator filtering
    selected_kinds = [KGKind(kv) for kv in kind_filter] if kind_filter else None

    return {
        "registry_path": registry_path,
        "kgrag": kgrag,
        "selected_names": selected_names,
        "selected_kinds": selected_kinds,
        "all_entries": all_entries,
        "filtered_entries": filtered_entries,
        "k": k,
        "context": context,
        "reg_stats": reg_stats,
    }


# ---------------------------------------------------------------------------
# Tab 1 — Registry browser
# ---------------------------------------------------------------------------


def _tab_registry(cfg: dict) -> None:
    """Render the Registry tab."""
    st.header("📋 KG Registry")

    entries = cfg["all_entries"]

    if not entries:
        st.info(
            "No KGs registered yet.\n\n"
            "Run `kgrag init` in a project directory to register CodeKG, DocKG, or MetaKG instances."
        )
        return

    # ── Summary metrics ───────────────────────────────────────────────────
    reg_stats = cfg["reg_stats"]
    c1, c2, c3 = st.columns(3)
    c1.metric("Registered KGs", reg_stats.total)
    c2.metric("Built", reg_stats.built)
    c3.metric("Not Built", reg_stats.total - reg_stats.built)

    st.markdown("---")

    # ── KG cards ─────────────────────────────────────────────────────────
    for entry in entries:
        kind = entry.kind.value
        color = _KG_KIND_COLOR.get(kind, "#95A5A6")
        icon = _KG_KIND_ICON.get(kind, "⬡")
        built_indicator = "✅ Built" if entry.is_built else "⚠️ Not built"

        with st.expander(
            f"{icon} **{entry.name}** ({kind}) — {built_indicator}",
            expanded=False,
        ):
            col_meta, col_stats = st.columns([3, 2])

            with col_meta:
                st.markdown(
                    f"""
                    <div style="border-left:4px solid {color};padding-left:12px;">
                    <b style="font-size:16px;">{entry.name}</b><br>
                    <span style="color:#888;font-size:12px;font-family:monospace;">
                        📁 {entry.repo_path}
                    </span><br>
                    <span style="color:#888;font-size:12px;font-family:monospace;">
                        🐍 {entry.venv_path}
                    </span>
                    </div>
                    """,
                    unsafe_allow_html=True,
                )
                st.write("")

                if entry.sqlite_path:
                    exists = entry.sqlite_path.exists()
                    icon_db = "✅" if exists else "❌"
                    st.caption(f"{icon_db} SQLite: `{entry.sqlite_path}`")
                if entry.lancedb_path:
                    exists = entry.lancedb_path.exists()
                    icon_db = "✅" if exists else "❌"
                    st.caption(f"{icon_db} LanceDB: `{entry.lancedb_path}`")

                if entry.tags:
                    st.caption("🏷️ Tags: " + ", ".join(f"`{t}`" for t in entry.tags))

                st.caption(
                    f"Version: `{entry.version}` · "
                    f"ID: `{entry.id[:8]}…` · "
                    f"Updated: `{entry.updated_at.strftime('%Y-%m-%d %H:%M')}`"
                )

            with col_stats:
                if entry.is_built:
                    with st.spinner("Loading stats…"):
                        try:
                            from kg_rag.adapters import (  # pylint: disable=import-outside-toplevel
                                make_adapter,
                            )

                            adapter = make_adapter(entry)
                            if adapter.is_available():
                                stats = adapter.stats()
                                for stat_key, stat_val in stats.items():
                                    if isinstance(stat_val, int | float | str):
                                        st.metric(
                                            stat_key.replace("_", " ").title(),
                                            stat_val,
                                        )
                            else:
                                st.warning("KG library not available.")
                        except Exception as exc:  # pylint: disable=broad-exception-caught
                            st.caption(f"Stats unavailable: {exc}")
                else:
                    st.warning(
                        "KG not built yet.\n\n"
                        f"Run the appropriate build command in `{entry.repo_path}`."
                    )

    # ── Raw table view ────────────────────────────────────────────────────
    st.markdown("---")
    with st.expander("📊 Registry table (all entries)"):
        import pandas as pd  # pylint: disable=import-outside-toplevel

        rows = [
            {
                "name": e.name,
                "kind": e.kind.value,
                "built": e.is_built,
                "version": e.version,
                "tags": ", ".join(e.tags),
                "repo_path": str(e.repo_path),
                "sqlite": str(e.sqlite_path) if e.sqlite_path else "—",
                "lancedb": str(e.lancedb_path) if e.lancedb_path else "—",
                "updated": e.updated_at.strftime("%Y-%m-%d %H:%M"),
            }
            for e in entries
        ]
        df = pd.DataFrame(rows)
        st.dataframe(df, use_container_width=True, hide_index=True)


# ---------------------------------------------------------------------------
# Tab 2 — Federated query
# ---------------------------------------------------------------------------


def _tab_query(cfg: dict) -> None:
    """Render the federated Query tab."""
    st.header("🔍 Federated Query")

    kgrag = cfg["kgrag"]
    if cfg["reg_stats"].total == 0:
        st.warning("No KGs registered. Add KGs via `kgrag init`.")
        return

    query_text = st.text_input(
        "Natural-language query",
        placeholder="e.g. database connection setup",
        key="query_input",
    )

    col_btn, col_group = st.columns([1, 2])
    with col_btn:
        run_btn = st.button("▶ Run Query", type="primary", key="run_query_btn")
    with col_group:
        group_by = st.radio(
            "Display",
            ["Ranked globally", "Grouped by KG"],
            horizontal=True,
            key="query_group_by",
        )

    if run_btn and query_text.strip():
        with st.spinner("Running federated query…"):
            try:
                kinds = cfg["selected_kinds"] if cfg["selected_kinds"] else None
                result = kgrag.query(query_text.strip(), k=cfg["k"], kinds=kinds)
                # Filter to selected KG names if specified
                selected = cfg["selected_names"]
                if selected:
                    result.hits = [h for h in result.hits if h.kg_name in selected]
                    result.by_kg = {
                        name: hits for name, hits in result.by_kg.items() if name in selected
                    }
                st.session_state.query_result = result
            except Exception as exc:  # pylint: disable=broad-exception-caught
                st.error(f"Query failed: {exc}")
                return

    result = st.session_state.query_result
    if result is None:
        st.info("Enter a query above and click **Run Query**.")
        return

    # ── Metrics ───────────────────────────────────────────────────────────
    c1, c2, c3 = st.columns(3)
    c1.metric("Total Hits", result.total_hits)
    c2.metric("KGs Queried", result.kgs_queried)
    c3.metric("Query", f'"{result.query[:40]}…"' if len(result.query) > 40 else f'"{result.query}"')

    st.markdown("---")

    if not result.hits:
        st.info("No results found.")
        return

    # ── Download ──────────────────────────────────────────────────────────
    hits_json = json.dumps(
        [
            {
                "kg_name": h.kg_name,
                "kg_kind": h.kg_kind.value,
                "node_id": h.node_id,
                "name": h.name,
                "kind": h.kind,
                "score": h.score,
                "summary": h.summary,
                "source_path": h.source_path,
            }
            for h in result.hits
        ],
        indent=2,
    )
    st.download_button(
        "⬇ Download JSON",
        data=hits_json,
        file_name="query_result.json",
        mime="application/json",
    )

    # ── Results display ───────────────────────────────────────────────────
    def _render_hit(hit) -> None:
        kg_color = _KG_KIND_COLOR.get(hit.kg_kind.value, "#95A5A6")
        source = hit.source_path or "—"
        summary = hit.summary or ""
        summary_short = summary[:200] + ("…" if len(summary) > 200 else "")

        st.markdown(
            f"""
            <div style="background:#1e1e2e;border-left:4px solid {kg_color};
                        border-radius:6px;padding:10px 14px;margin-bottom:8px;">
              {_kg_kind_badge(hit.kg_kind.value, hit.kg_name)}
              &nbsp;
              {_node_kind_badge(hit.kind)}
              &nbsp;&nbsp;
              <b style="font-size:14px;color:#f0f0f0;">{hit.name}</b>
              <br>
              <span style="color:#888;font-size:11px;font-family:monospace;">
                📄 {source}
              </span>
              &nbsp;&nbsp;
              {_score_bar(hit.score)}
              {"<br><span style='color:#ccc;font-size:12px;'>" + summary_short + "</span>" if summary_short else ""}
            </div>
            """,
            unsafe_allow_html=True,
        )

    if group_by == "Ranked globally":
        st.subheader(f"Results ({len(result.hits)} hits)")
        for hit in result.hits:
            _render_hit(hit)
    else:
        for kg_name, hits in result.by_kg.items():
            if not hits:
                continue
            entry = kgrag.registry.find_by_name(kg_name)
            kind = entry.kind.value if entry else "code"
            color = _KG_KIND_COLOR.get(kind, "#95A5A6")
            icon = _KG_KIND_ICON.get(kind, "⬡")
            st.markdown(
                f"<h3 style='color:{color};'>{icon} {kg_name} ({len(hits)} hits)</h3>",
                unsafe_allow_html=True,
            )
            for hit in hits:
                _render_hit(hit)
            st.markdown("---")


# ---------------------------------------------------------------------------
# Tab 3 — Analysis
# ---------------------------------------------------------------------------


def _tab_analysis(cfg: dict) -> None:
    """Render the Analysis tab."""
    st.header("🧪 Analysis Control")

    kgrag = cfg["kgrag"]
    if cfg["reg_stats"].total == 0:
        st.warning("No KGs registered. Add KGs via `kgrag init`.")
        return

    # Filter to code KGs only (analysis is primarily for code repos)
    code_entries = [e for e in cfg["all_entries"] if e.kind == KGKind.CODE]
    if not code_entries:
        st.info("Analysis is available for CodeKG instances. No CodeKGs registered.")
        return

    col_kg, col_btn = st.columns([3, 1])
    with col_kg:
        selected_kg = st.selectbox(
            "Select CodeKG to analyze",
            options=[e.name for e in code_entries],
            help="Choose a registered CodeKG instance to run analysis on",
        )
    with col_btn:
        run_analysis_btn = st.button("▶ Run Analysis", type="primary", key="run_analysis_btn")

    if run_analysis_btn and selected_kg:
        with st.spinner(f"Analyzing {selected_kg}…"):
            try:
                analysis_md = kgrag.analyze(selected_kg)
                st.session_state.analysis_result = {
                    "kg_name": selected_kg,
                    "markdown": analysis_md,
                }
            except Exception as exc:  # pylint: disable=broad-exception-caught
                st.error(f"Analysis failed: {exc}")
                return

    result = st.session_state.get("analysis_result")
    if result is None:
        st.info("Select a CodeKG above and click **Run Analysis**.")
        return

    st.markdown("---")

    # ── Analysis markdown ──────────────────────────────────────────────────
    st.markdown(result["markdown"])

    # ── Download buttons ───────────────────────────────────────────────────
    st.markdown("---")
    st.download_button(
        "⬇ Download Markdown",
        data=result["markdown"],
        file_name=f"{result['kg_name']}_analysis.md",
        mime="text/markdown",
    )


# ---------------------------------------------------------------------------
# Tab 4 — Snippet pack
# ---------------------------------------------------------------------------


def _tab_snippets(cfg: dict) -> None:
    """Render the cross-KG Snippet Pack tab."""
    st.header("📦 Cross-KG Snippet Pack")

    kgrag = cfg["kgrag"]
    if cfg["reg_stats"].total == 0:
        st.warning("No KGs registered. Add KGs via `kgrag init`.")
        return

    col_q, col_ctx = st.columns([4, 1])
    with col_q:
        pack_query = st.text_input(
            "Query for snippet pack",
            placeholder="e.g. configuration loading",
            key="pack_query_input",
        )
    with col_ctx:
        context_lines = st.number_input(
            "Context lines", min_value=0, max_value=20, value=cfg["context"], key="pack_context"
        )

    pack_btn = st.button("📦 Build Pack", type="primary", key="pack_btn")

    if pack_btn and pack_query.strip():
        with st.spinner("Building cross-KG snippet pack…"):
            try:
                kinds = cfg["selected_kinds"] if cfg["selected_kinds"] else None
                pack = kgrag.pack(
                    pack_query.strip(),
                    k=cfg["k"],
                    context=int(context_lines),
                    kinds=kinds,
                )
                # Filter by selected KG names
                selected = cfg["selected_names"]
                if selected:
                    pack.snippets = [s for s in pack.snippets if s.kg_name in selected]
                st.session_state.pack_result = pack
            except Exception as exc:  # pylint: disable=broad-exception-caught
                st.error(f"Pack failed: {exc}")
                return

    pack = st.session_state.pack_result
    if pack is None:
        st.info("Enter a query above and click **Build Pack**.")
        return

    # ── Metrics ───────────────────────────────────────────────────────────
    c1, c2, c3 = st.columns(3)
    c1.metric("Snippets", len(pack.snippets))
    c2.metric("KGs", pack.kgs_queried)
    c3.metric("~Tokens", pack.total_tokens_approx)

    # ── Download buttons ──────────────────────────────────────────────────
    dl1, dl2 = st.columns(2)
    dl1.download_button(
        "⬇ Download Markdown",
        data=pack.render(),
        file_name="snippet_pack.md",
        mime="text/markdown",
    )
    pack_json = json.dumps(
        [
            {
                "kg_name": s.kg_name,
                "kg_kind": s.kg_kind.value,
                "node_id": s.node_id,
                "source_path": s.source_path,
                "lineno": s.lineno,
                "end_lineno": s.end_lineno,
                "score": s.score,
                "content": s.content,
            }
            for s in pack.snippets
        ],
        indent=2,
    )
    dl2.download_button(
        "⬇ Download JSON",
        data=pack_json,
        file_name="snippet_pack.json",
        mime="application/json",
    )

    st.markdown("---")

    if not pack.snippets:
        st.info("No snippets found.")
        return

    # ── Snippet cards ─────────────────────────────────────────────────────
    st.subheader(f"Snippets ({len(pack.snippets)})")
    for snippet in pack.snippets:
        icon = _KG_KIND_ICON.get(snippet.kg_kind.value, "⬡")
        source = snippet.source_path or "unknown"
        line_info = ""
        if snippet.lineno:
            line_info = (
                f":{snippet.lineno}–{snippet.end_lineno}"
                if snippet.end_lineno and snippet.end_lineno != snippet.lineno
                else f":{snippet.lineno}"
            )

        header = (
            f"{icon} **[{snippet.kg_name}]** `{source}{line_info}`  ·  score `{snippet.score:.3f}`"
        )
        with st.expander(header, expanded=True):
            # Use code block for code KGs, markdown for doc KGs
            if snippet.kg_kind == KGKind.CODE:
                st.code(snippet.content, language="python")
            elif snippet.kg_kind == KGKind.DOC:
                st.markdown(snippet.content)
            else:
                st.code(snippet.content)

            st.markdown(
                f"<small style='color:#888;font-family:monospace;'>"
                f"{_kg_kind_badge(snippet.kg_kind.value, snippet.kg_name)}"
                f"&nbsp; 📄 {source}{line_info}"
                f"&nbsp; {_score_bar(snippet.score, width=60)}"
                f"</small>",
                unsafe_allow_html=True,
            )


# ---------------------------------------------------------------------------
# Tab 5 — Synthesize (Ollama inference)
# ---------------------------------------------------------------------------

_DEFAULT_OLLAMA_URL = "http://localhost:11434"
_DEFAULT_MODEL = "llama3.2"

_SYNTH_SYSTEM = (
    "You are a knowledgeable literary and research assistant. "
    "You are given excerpts retrieved from a knowledge graph built from books and documents. "
    "Use these excerpts as your primary source and synthesize a clear, accurate answer. "
    "If the excerpts do not contain enough information, say so honestly."
)


def _call_ollama_stream(prompt: str, model: str, base_url: str):
    """Yield tokens from Ollama /api/generate (streaming).

    :param prompt: Full prompt string.
    :param model: Ollama model name.
    :param base_url: Ollama server base URL.
    :yields: Response token strings.
    :raises RuntimeError: On connection or HTTP errors.
    """
    import json  # pylint: disable=import-outside-toplevel

    try:
        import httpx  # pylint: disable=import-outside-toplevel
    except ImportError as exc:
        raise RuntimeError("httpx is required — run `pip install httpx`") from exc

    url = base_url.rstrip("/") + "/api/generate"
    payload = {"model": model, "prompt": prompt, "system": _SYNTH_SYSTEM, "stream": True}
    try:
        with httpx.stream("POST", url, json=payload, timeout=120) as resp:
            if resp.status_code != 200:
                raise RuntimeError(
                    f"Ollama returned HTTP {resp.status_code}. Is Ollama running?"
                )
            for line in resp.iter_lines():
                if not line:
                    continue
                chunk = json.loads(line)
                yield chunk.get("response", "")
                if chunk.get("done"):
                    break
    except httpx.ConnectError as exc:
        raise RuntimeError(
            f"Cannot connect to Ollama at {base_url}. Start it with: ollama serve"
        ) from exc


def _tab_synthesize(cfg: dict) -> None:
    """Render the Synthesize tab — KG-grounded Ollama inference."""
    st.header("🧠 Synthesize")
    st.caption(
        "Retrieve relevant excerpts from your KGs, then synthesize an answer "
        "using a local [Ollama](https://ollama.com) model."
    )

    kgrag = cfg["kgrag"]
    if cfg["reg_stats"].total == 0:
        st.warning("No KGs registered. Add KGs via `kgrag init`.")
        return

    # ── Controls ──────────────────────────────────────────────────────────
    col_q, col_model = st.columns([4, 2])
    with col_q:
        synth_query = st.text_input(
            "Question / topic",
            placeholder="e.g. What motivates Victor Frankenstein?",
            key="synth_query",
        )
    with col_model:
        model = st.text_input("Ollama model", value=_DEFAULT_MODEL, key="synth_model")

    col_url, col_k = st.columns([3, 1])
    with col_url:
        ollama_url = st.text_input(
            "Ollama URL",
            value=_DEFAULT_OLLAMA_URL,
            key="synth_ollama_url",
            help="Set OLLAMA_URL env var to override default.",
        )
    with col_k:
        synth_k = st.number_input("Top-K snippets", min_value=1, max_value=20, value=6, key="synth_k")

    show_ctx = st.checkbox("Show retrieved context", value=False, key="synth_show_ctx")

    synth_btn = st.button("🧠 Synthesize", type="primary", key="synth_btn")

    if not synth_btn or not synth_query.strip():
        if not synth_btn:
            st.info("Enter a question above and click **Synthesize**.")
        return

    # ── Retrieve context ──────────────────────────────────────────────────
    with st.spinner("Retrieving KG context…"):
        try:
            kinds = cfg["selected_kinds"] if cfg["selected_kinds"] else None
            pack = kgrag.pack(synth_query.strip(), k=int(synth_k), context=5, kinds=kinds)
            selected = cfg["selected_names"]
            if selected:
                pack.snippets = [s for s in pack.snippets if s.kg_name in selected]
        except Exception as exc:  # pylint: disable=broad-exception-caught
            st.error(f"Context retrieval failed: {exc}")
            return

    if not pack.snippets:
        st.warning("No relevant content found in the selected KGs.")
        return

    c1, c2 = st.columns(2)
    c1.metric("Snippets retrieved", len(pack.snippets))
    c2.metric("KGs queried", pack.kgs_queried)

    if show_ctx:
        with st.expander("📄 Retrieved context", expanded=False):
            for i, snip in enumerate(pack.snippets, 1):
                icon = _KG_KIND_ICON.get(snip.kg_kind.value, "⬡")
                st.markdown(
                    f"**{i}. {icon} [{snip.kg_name}]** `{snip.source_path or 'unknown'}` "
                    f"· score `{snip.score:.3f}`"
                )
                if snip.kg_kind == KGKind.CODE:
                    st.code(snip.content, language="python")
                else:
                    st.markdown(snip.content)
                st.markdown("---")

    # ── Build prompt ──────────────────────────────────────────────────────
    context_parts = []
    for i, snip in enumerate(pack.snippets, 1):
        header = (
            f"[Excerpt {i} | KG: {snip.kg_name} | "
            f"source: {snip.source_path or 'unknown'} | score: {snip.score:.3f}]"
        )
        context_parts.append(f"{header}\n{snip.content.strip()}")

    full_prompt = (
        f"Question: {synth_query.strip()}\n\n"
        f"Relevant excerpts:\n\n"
        + "\n\n---\n\n".join(context_parts)
        + "\n\nAnswer:"
    )

    # ── Stream from Ollama ────────────────────────────────────────────────
    st.markdown("---")
    st.subheader(f"Answer · `{model}`")

    answer_box = st.empty()
    full_answer = ""

    try:
        for token in _call_ollama_stream(full_prompt, model=model, base_url=ollama_url):
            full_answer += token
            answer_box.markdown(full_answer + "▌")
        answer_box.markdown(full_answer)
    except RuntimeError as exc:
        st.error(str(exc))
        return

    # ── Download ──────────────────────────────────────────────────────────
    st.download_button(
        "⬇ Download answer",
        data=full_answer,
        file_name="synthesized_answer.md",
        mime="text/markdown",
    )


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def main() -> None:
    """Application entry point for the KGRAG Streamlit visualizer."""
    _init_state()
    cfg = _render_sidebar()

    st.title("🕸️ KGRAG Explorer")
    st.caption(
        "Cross-KG registry manager and federated query explorer. "
        "Powered by [KGRAG](https://github.com/Flux-Frontiers/kgrag) · Streamlit."
    )

    tab1, tab2, tab3, tab4, tab5 = st.tabs(
        [
            "📋 Registry",
            "🔍 Federated Query",
            "🧪 Analysis",
            "📦 Snippet Pack",
            "🧠 Synthesize",
        ]
    )

    with tab1:
        _tab_registry(cfg)

    with tab2:
        _tab_query(cfg)

    with tab3:
        _tab_analysis(cfg)

    with tab4:
        _tab_snippets(cfg)

    with tab5:
        _tab_synthesize(cfg)


if __name__ == "__main__":
    main()
