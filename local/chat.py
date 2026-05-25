"""
chat.py — KGRAG Worker Chat Interface

Streamlit chat UI that sends queries to the running kgrag-worker container
(or any compatible /runsync endpoint) and displays synthesized answers with
collapsible source hit cards.

Run with:
    cd runpod/
    streamlit run chat.py

The worker must be running first:
    docker compose up -d
"""

from __future__ import annotations

import httpx
import streamlit as st

# ---------------------------------------------------------------------------
# Page config (must be first Streamlit call)
# ---------------------------------------------------------------------------

st.set_page_config(
    page_title="KGRAG Chat",
    page_icon="💬",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ---------------------------------------------------------------------------
# Constants — reused from app.py conventions
# ---------------------------------------------------------------------------

_KG_KIND_COLOR: dict[str, str] = {
    "code": "#4A90D9",
    "doc": "#27AE60",
    "meta": "#8E44AD",
    "gutenberg": "#8B4513",
    "ia": "#C0392B",
    "diary": "#D4A017",
    "verse": "#C2185B",
    "memory": "#00838F",
    "agent": "#4527A0",
    "filetree": "#00695C",
    "legal": "#1A237E",
    "disulfide": "#E65100",
    "pdbfile": "#37474F",
    "person": "#F57F17",
}

_KG_KIND_ICON: dict[str, str] = {
    "code": "💻",
    "doc": "📄",
    "meta": "🧬",
    "gutenberg": "📚",
    "ia": "🏛️",
    "diary": "📔",
    "verse": "📜",
    "memory": "🧠",
    "agent": "🤖",
    "filetree": "🌲",
    "legal": "⚖️",
    "disulfide": "🔗",
    "pdbfile": "🗂️",
    "person": "👤",
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

_CORPUS_OPTIONS = ["all", "gutenberg", "metabo_hsa", "metabo_cge", "metabo_icho"]

# ---------------------------------------------------------------------------
# CSS
# ---------------------------------------------------------------------------

st.markdown(
    """
    <style>
    .stTabs [data-baseweb="tab-list"] { gap: 12px; }
    .stTabs [data-baseweb="tab"] { font-size: 1rem; padding: 6px 18px; }
    </style>
    """,
    unsafe_allow_html=True,
)

# ---------------------------------------------------------------------------
# Helpers — badges and score bar (same as app.py)
# ---------------------------------------------------------------------------


def _kg_kind_badge(kind: str, name: str = "") -> str:
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


def _render_hit_card(hit: dict) -> None:
    kg_kind = hit.get("kg_kind", "")
    kg_name = hit.get("kg_name", "")
    node_kind = hit.get("kind", "")
    name = hit.get("name", "")
    source = hit.get("source_path") or "—"
    score = float(hit.get("score", 0.0))
    summary = hit.get("summary") or ""
    summary_short = summary[:200] + ("…" if len(summary) > 200 else "")
    kg_color = _KG_KIND_COLOR.get(kg_kind, "#95A5A6")

    st.markdown(
        f"""
        <div style="background:#1e1e2e;border-left:4px solid {kg_color};
                    border-radius:6px;padding:10px 14px;margin-bottom:8px;">
          {_kg_kind_badge(kg_kind, kg_name)}
          &nbsp;
          {_node_kind_badge(node_kind)}
          &nbsp;&nbsp;
          <b style="font-size:14px;color:#f0f0f0;">{name}</b>
          <br>
          <span style="color:#888;font-size:11px;font-family:monospace;">📄 {source}</span>
          &nbsp;&nbsp;
          {_score_bar(score)}
          {"<br><span style='color:#ccc;font-size:12px;'>" + summary_short + "</span>" if summary_short else ""}
        </div>
        """,
        unsafe_allow_html=True,
    )


# ---------------------------------------------------------------------------
# Worker call
# ---------------------------------------------------------------------------


class WorkerError(Exception):
    pass


def _query_worker(
    query: str,
    *,
    worker_url: str,
    corpus: str,
    k: int,
    min_score: float,
    semantic_floor: float,
    synthesize: bool,
    secret: str,
) -> dict:
    payload: dict = {
        "input": {
            "query": query,
            "corpus": corpus,
            "k": k,
            "min_score": min_score,
            "semantic_floor": semantic_floor,
            "synthesize": synthesize,
        }
    }
    if secret:
        payload["input"]["secret"] = secret

    resp = httpx.post(
        worker_url.rstrip("/") + "/runsync",
        json=payload,
        timeout=httpx.Timeout(connect=5.0, read=600.0, write=30.0, pool=5.0),
    )
    resp.raise_for_status()
    data = resp.json()

    # RunPod wraps successful output under "output"; failed jobs have a top-level "error" dict
    if data.get("status") == "FAILED" or "error_type" in data:
        error_data = data.get("error", data)
        err_type = error_data.get("error_type", "Unknown")
        err_msg = error_data.get("error_message", str(error_data))
        raise WorkerError(f"{err_type}: {err_msg}")

    return data.get("output", data)


# ---------------------------------------------------------------------------
# Session state
# ---------------------------------------------------------------------------


def _init_state() -> None:
    if "messages" not in st.session_state:
        st.session_state.messages = []  # list of {"role", "content", "result"}


# ---------------------------------------------------------------------------
# Sidebar
# ---------------------------------------------------------------------------


def _render_sidebar() -> dict:
    st.sidebar.title("💬 KGRAG Chat")
    st.sidebar.markdown("---")

    st.sidebar.subheader("🔌 Worker")
    worker_url = st.sidebar.text_input(
        "Worker URL",
        value="http://localhost:8000",
        help="Base URL of the running kgrag-worker container",
    )

    secret = st.sidebar.text_input(
        "Secret (optional)",
        value="",
        type="password",
        help="Set only when HANDLER_SECRET is configured in the worker",
    )

    st.sidebar.markdown("---")
    st.sidebar.subheader("⚙️ Query Parameters")

    corpus = st.sidebar.selectbox("Corpus", options=_CORPUS_OPTIONS, index=0)
    k = st.sidebar.slider("Top-K hits", min_value=1, max_value=20, value=8)
    semantic_floor = st.sidebar.slider(
        "Semantic floor",
        min_value=0.0,
        max_value=0.9,
        value=0.0,
        step=0.05,
        help="Drop a KG entirely if its best hit is below this score",
    )
    min_score = st.sidebar.slider(
        "Min score",
        min_value=0.0,
        max_value=0.9,
        value=0.0,
        step=0.05,
        help="Drop individual hits below this score",
    )
    synthesize = st.sidebar.toggle(
        "Synthesize answer",
        value=False,
        help="Ask the worker to generate an answer via Ollama (requires VLLM_ENDPOINT_URL in worker)",
    )

    st.sidebar.markdown("---")
    if st.sidebar.button("🗑️ Clear chat", use_container_width=True):
        st.session_state.messages = []
        st.rerun()

    return {
        "worker_url": worker_url,
        "secret": secret,
        "corpus": corpus,
        "k": k,
        "min_score": min_score,
        "semantic_floor": semantic_floor,
        "synthesize": synthesize,
    }


# ---------------------------------------------------------------------------
# Render one assistant turn
# ---------------------------------------------------------------------------


def _render_assistant_turn(result: dict) -> None:
    synthesis = result.get("synthesis")
    synthesis_error = result.get("synthesis_error")
    hits = result.get("hits", [])
    total_hits = result.get("total_hits", 0)
    kgs_queried = result.get("kgs_queried", 0)
    corpus = result.get("corpus", "")

    if not hits:
        st.warning(
            f"No hits found in corpus **{corpus}** — the query may not match anything indexed. "
            "Try a different corpus or lower the semantic floor."
        )
        st.caption(f"📊 0 hits · {kgs_queried} KGs queried · corpus: `{corpus}`")
        return

    if synthesis:
        st.markdown(synthesis)
    elif synthesis_error:
        st.warning(
            f"Synthesis failed — **{synthesis_error}**\n\n"
            "Check that Ollama is running (`ollama serve`) and reachable from the container. "
            "Or disable the **Synthesize answer** toggle in the sidebar."
        )
    else:
        st.info("Synthesis off — see sources below.")

    st.caption(f"📊 {total_hits} hits across {kgs_queried} KGs · corpus: `{corpus}`")

    if hits:
        with st.expander(f"📄 Sources ({len(hits)} shown)", expanded=False):
            for hit in hits:
                _render_hit_card(hit)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


def main() -> None:
    _init_state()
    cfg = _render_sidebar()

    st.title("💬 KGRAG Chat")
    st.caption(
        "Ask questions across your knowledge graphs. Answers are grounded in retrieved excerpts."
    )

    # Replay chat history
    for msg in st.session_state.messages:
        with st.chat_message(msg["role"]):
            if msg["role"] == "user":
                st.markdown(msg["content"])
            else:
                _render_assistant_turn(msg["result"])

    # New input
    if prompt := st.chat_input("Ask a question…"):
        # Show user message immediately
        with st.chat_message("user"):
            st.markdown(prompt)
        st.session_state.messages.append({"role": "user", "content": prompt, "result": None})

        # Query worker and stream result
        with st.chat_message("assistant"):
            with st.spinner("Querying knowledge graphs…"):
                try:
                    result = _query_worker(
                        prompt,
                        worker_url=cfg["worker_url"],
                        corpus=cfg["corpus"],
                        k=cfg["k"],
                        min_score=cfg["min_score"],
                        semantic_floor=cfg["semantic_floor"],
                        synthesize=cfg["synthesize"],
                        secret=cfg["secret"],
                    )
                except httpx.ConnectError:
                    st.error(
                        f"Cannot connect to worker at **{cfg['worker_url']}**. "
                        "Is the container running? (`docker compose up -d`)"
                    )
                    st.session_state.messages.pop()
                    st.stop()
                except httpx.HTTPStatusError as exc:
                    st.error(
                        f"Worker returned HTTP {exc.response.status_code}: {exc.response.text}"
                    )
                    st.session_state.messages.pop()
                    st.stop()
                except WorkerError as exc:
                    st.error(f"Worker error: {exc}")
                    st.session_state.messages.pop()
                    st.stop()
                except Exception as exc:  # pylint: disable=broad-exception-caught
                    st.error(f"Unexpected error: {exc}")
                    st.session_state.messages.pop()
                    st.stop()

            if "error" in result:
                st.error(f"Worker error: {result['error']}")
                st.session_state.messages.pop()
                st.stop()

            _render_assistant_turn(result)

        st.session_state.messages.append(
            {"role": "assistant", "content": result.get("synthesis", ""), "result": result}
        )


if __name__ == "__main__":
    main()
