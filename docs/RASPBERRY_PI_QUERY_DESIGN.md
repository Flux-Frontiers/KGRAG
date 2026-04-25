# KGRAG on Raspberry Pi — Design & Implementation

**Author:** Eric G. Suchanek, PhD  
**Date:** 2026-04-25  
**Branch:** `claude/raspberry-pi-query-design-dOWGL`

---

## Problem

The KGRAG query path requires generating a neural embedding for every query string. The
current stack (`torch` + `transformers` + `sentence-transformers`) is ~3–4 GB and has no
viable ARM path:

- ONNX Runtime — rejected: no working ARM64 Linux wheels (confirmed on Snapdragon)
- PyTorch — rejected for Pi: 2 GB install, slow on ARM, no Metal on Linux
- Remote embed server — viable fallback but requires LAN connectivity

---

## Solution: llama-cpp-python + GGUF

`llama-cpp-python` is a Python binding for llama.cpp, a C++ inference engine designed
for CPU-first, cross-platform use. It supports ARM64 natively via NEON/ASIMD and
integrates with OpenBLAS on Linux and Metal on macOS Apple Silicon.

### Platform matrix

| Platform | Acceleration | Install |
|---|---|---|
| Raspberry Pi 4/5 (ARM64) | CPU + OpenBLAS | Compile from source (~15 min) |
| Apple Silicon (M1–M4) | Metal GPU | Prebuilt wheel or `METAL=ON` |
| Intel/AMD Linux | CPU / CUDA | Prebuilt wheel |
| Snapdragon ARM64 | CPU | Compile from source |

### Canonical embedding model

`BAAI/bge-small-en-v1.5` — confirmed by the pycode_kg embedder benchmark
(`analysis/embedder_benchmark_summary.md`):

| Model | Size (Q8_0) | Dims | MTEB | Verdict |
|---|---|---|---|---|
| **bge-small-en-v1.5** | **~34 MB** | **384** | **~62** | **Canonical winner** |
| all-MiniLM-L6-v2 | ~25 MB | 384 | ~56 | Viable, lower quality |
| all-mpnet-base-v2 | ~340 MB | 768 | — | Rejected: worse than bge-small |
| nomic-embed-text-v1.5 | ~83 MB | 768 | 62.3 | Rejected: fails identifier queries |
| codebert-base | ~440 MB | 768 | — | Rejected: degenerate embedding space |

**Why nomic was rejected:** encodes compound Python identifiers (e.g. `_snapshot_freshness`,
`KGModule.build_graph`) into a near-flat region of the embedding space. All short-docstring
nodes cluster at ~0.493 cosine similarity — a hard blocker for code retrieval.

GGUF download: [`ggml-org/bge-small-en-v1.5-Q8_0-GGUF`](https://huggingface.co/ggml-org/bge-small-en-v1.5-Q8_0-GGUF)

---

## Architecture

### Injection chain

The embedding happens inside each KG library (`pycode_kg`, `doc_kg`, etc.) via their
`KGModule` base class. KGRAG injects a shared embedder instance without requiring any
changes to those libraries:

```
KGRAG.__init__
  └── make_embedder(load_kgrag_config())   # one shared LlamaCppEmbedder
        └── make_adapter(entry, embedder=…)
              └── CodeKGAdapter._load()
                    self._kg._embedder = self._embedder   # inject before lazy-init
                        └── KGModule.index               # lazy property
                              └── SemanticIndex(embedder=our_backend)
                                    └── search() → embed_query(q) → llama.cpp
```

The key: `KGModule._embedder` is `None` until first access. Setting it before any query
means `KGModule.index` passes our backend to `SemanticIndex` rather than creating a
`SentenceTransformerEmbedder`. No pycode_kg code changes required.

### Dependency direction

```
kg_rag  →  pycode_kg  (existing, optional dep)
pycode_kg  →  kg_rag  (never — zero coupling added)
```

`LlamaCppEmbedder` satisfies `pycode_kg.index.Embedder` via structural typing (duck typing).
No shared base class or import is needed.

---

## Implementation

### New: `src/kg_rag/embed.py`

Three classes + one factory:

```python
class Embedder(Protocol):            # structural protocol, matches pycode_kg's
    dim: int
    def embed_texts(self, texts: list[str]) -> list[list[float]]: ...
    def embed_query(self, text: str) -> list[float]: ...

class LlamaCppEmbedder:              # ARM/Pi/macOS — no torch
    dim: int                         # from llm.n_embd()
    def embed_texts(...) -> ...      # batch via llm.embed(list)
    def embed_query(...) -> ...      # single via llm.embed(str)

class SentenceTransformerEmbedder:   # back-compat shim for torch environments
    dim: int
    def embed_texts(...) -> ...
    def embed_query(...) -> ...

def make_embedder(config: dict) -> Embedder | None:
    # reads [tool.kgrag] embed_backend / llama_model_path
    # returns None → each KG uses its own built-in default
```

### Modified files

| File | Change |
|---|---|
| `src/kg_rag/embed.py` | New — `Embedder`, `LlamaCppEmbedder`, `make_embedder` |
| `src/kg_rag/adapters/base.py` | `KGAdapter.__init__` accepts `embedder=None` |
| `src/kg_rag/adapters/__init__.py` | `make_adapter(entry, embedder=None)` |
| `src/kg_rag/adapters/pycodekg_adaptor.py` | Injects `_embedder` in `_load()` |
| `src/kg_rag/adapters/dockg_adapter.py` | Injects `_embedder` in `_load()` |
| `src/kg_rag/orchestrator.py` | `KGRAG.__init__` auto-creates embedder from config |
| `pyproject.toml` | `llama-cpp-python` optional dep; `[pi]` extra |

---

## Configuration

Add to `pyproject.toml` in any project using KGRAG:

```toml
[tool.kgrag]
embed_backend    = "llama"
llama_model_path = "~/.kgrag/bge-small-en-v1.5-Q8_0.gguf"
```

Or via environment variable:

```bash
export KGRAG_LLAMA_MODEL=~/.kgrag/bge-small-en-v1.5-Q8_0.gguf
```

Optional tuning:

```toml
[tool.kgrag]
embed_backend       = "llama"
llama_model_path    = "~/.kgrag/bge-small-en-v1.5-Q8_0.gguf"
llama_n_ctx         = 512    # context window; 512 sufficient for queries
llama_n_batch       = 512    # must not exceed 512 (known llama-cpp-python crash)
llama_n_gpu_layers  = -1     # -1 = all layers on GPU (Metal on macOS, 0 for Pi)
llama_verbose       = false
```

---

## Installation

### Raspberry Pi 4/5

```bash
# Prerequisites
sudo apt update && sudo apt install -y build-essential cmake libopenblas-dev

# Install kg-rag with the pi extra (triggers llama-cpp-python compilation)
CMAKE_ARGS="-DGGML_BLAS=ON -DGGML_BLAS_VENDOR=OpenBLAS -DCMAKE_BUILD_TYPE=Release" \
  pip install "kg-rag[pi]" --no-binary llama-cpp-python

# Download the GGUF model (~34 MB)
mkdir -p ~/.kgrag
wget -O ~/.kgrag/bge-small-en-v1.5-Q8_0.gguf \
  https://huggingface.co/ggml-org/bge-small-en-v1.5-Q8_0-GGUF/resolve/main/bge-small-en-v1.5-Q8_0.gguf
```

Compilation takes ~15 minutes on Pi 5. The model loads in ~1 s and embeds a query
string in ~2–10 ms — fast enough for interactive use.

### macOS Apple Silicon (Metal)

```bash
CMAKE_ARGS="-DGGML_METAL=ON" pip install "kg-rag[pi]"
```

Set `llama_n_gpu_layers = -1` in config to offload all layers to the GPU.

---

## KG Artifact Workflow

KGs must be **built on a desktop** (where torch is available) and **deployed to Pi**
as read-only artifacts. The Pi only embeds the query string — all document vectors are
pre-computed at build time.

```
Desktop                              Raspberry Pi
──────────────────────────           ──────────────────────────
kgrag build  (torch, full stack)
→ .pycodekg/lancedb/  ──── rsync ──► .pycodekg/lancedb/  (read-only)
→ .pycodekg/graph.sqlite ─ rsync ──► .pycodekg/graph.sqlite
→ ~/.kgrag/registry.sqlite  rsync ──► ~/.kgrag/registry.sqlite
                                      kgrag query "…"  (llama.cpp only)
```

The model used at build time (`bge-small-en-v1.5`) must match the GGUF deployed to Pi.
The builder version is stamped in `_kgrag_meta` (see `docs/KG_BUILDER_VERSION_SPEC.md`).

---

## Known Limitations

- **Other adapters** (`DiaryKGAdapter`, `AgentKGAdapter`, etc.) use the same `KGModule`
  pattern and will benefit from the embedder injection, but have not been explicitly
  wired yet — follow the same `_kg._embedder = self._embedder` pattern in their `_load()`.
- **llama-cpp-python compilation** on Pi takes ~15 minutes and requires build tools.
  No prebuilt ARM64 Linux wheels are available on PyPI for all Python versions.
- **KG rebuild required** for any KG previously built with `all-mpnet-base-v2` (doc_kg
  default) — vector spaces are incompatible across models.
