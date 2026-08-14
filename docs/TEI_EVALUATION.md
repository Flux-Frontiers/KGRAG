# Text Embeddings Inference (TEI) — Evaluation & Adoption Plan

**Status:** proposal (evaluated 2026-08-14)
**Subject:** [huggingface/text-embeddings-inference](https://github.com/huggingface/text-embeddings-inference) (Apache-2.0)
**Verdict:** useful — as an **opt-in remote embedding backend** behind the existing
`Embedder` seam, not as a replacement for in-process sentence-transformers.
The default stays local-first.

---

## 1. What TEI is

TEI is HuggingFace's Rust (candle) inference server for embedding and
sequence-classification models. Relevant properties for this fleet:

- **Serves the models we already use.** BERT-family embedders including
  `BAAI/bge-*` (our default `bge-small-en-v1.5`), `nomic-embed-text-v1.5`,
  `all-MiniLM-L6-v2` / `all-mpnet-base-v2` — plus newer options
  (GTE, Jina, Qwen3-Embedding) with no client-side code change.
- **Token-based dynamic batching** — the server packs requests by token
  count rather than item count, so throughput self-tunes without the manual
  `batch × seq² × model` memory arithmetic we maintain by hand (see
  `KG_utils/docs/encode-batch-memory-postmortem.md`).
- **API:** native `/embed` and `/rerank`, plus an OpenAI-compatible
  `/v1/embeddings` — the latter matters because the fleet already ships the
  `openai` client and a tested endpoint-config pattern for it
  (`kg_utils/synthesis/_config.py`).
- **Deployment:** small Docker images (CPU x86_64/ARM64, CUDA by compute
  capability), or a local `cargo install` build with Metal support on
  Apple Silicon. Fast boot via safetensors; no graph-compilation step.
  Prometheus metrics + OpenTelemetry built in.
- **Reranking:** serves cross-encoders (`BAAI/bge-reranker-*`) — a component
  the fleet currently does not have at all.

## 2. Where the fleet stands today

One real provider fleet-wide: `sentence-transformers` (PyTorch), canonical
implementation in `KG_utils/src/kg_utils/embedder.py`
(`SentenceTransformerEmbedder`), with a `LlamaCppEmbedder` (GGUF) alternative
in KGRAG only. Default model `BAAI/bge-small-en-v1.5`, 384-dim, normalized,
stored in `SqliteVecBackend` (LanceDB retiring, see `TODO.md`).

The abstraction is already right for a new backend:

- Universal contract: `embed_query(text) -> list[float]` +
  `embed_texts(texts, encode_batch_size)` + `dim`
  (`kg_utils/embed.py:50` Protocol, `kg_utils/embedder.py:62` ABC).
- Fully injection-based chain: `make_embedder()`
  (`KGRAG/src/kg_rag/embed.py:42-88`, dispatching on `embed_backend` from
  `[tool.kgrag]`) → `Orchestrator` → `make_adapter(embedder=...)` →
  `SemanticIndex(embedder=...)`. No interface changes needed downstream.
- A proven config template for HTTP backends already exists:
  `TextBackend` enum + defaults + `*_config_from_env()` in
  `kg_utils/synthesis/_config.py` (used for LLM synthesis endpoints).

Known pain a server-side embedder addresses directly:

- **The encode-batch memory postmortem** (2026-07-09): oversized batches
  ballooned to 25 GB RSS CPU / 32.7 GB MPS on a 528k-node build; MPS
  hard-stalled at ~230k rows; the fix was a hand-tuned
  `DEFAULT_ENCODE_BATCH = 128` cap. TEI moves batch/memory management
  server-side.
- **`CorpusEmbedder`'s multiprocess machinery exists to work around local
  inference limits**: GPU-never-fans-out guards, `maxtasksperchild=1`,
  worker recycling at 25k items, MPS SIGBUS avoidance in
  `load_sentence_transformer()`. Against a remote endpoint, fan-out is safe
  and most of these guards are moot.
- **The open architecture question**
  (`kgrag_priv/docs/RUNPOD_KGRAG_ARCHITECTURE.md:280-281`): "Embedding
  in-worker vs. dedicated endpoint — no need … unless throughput demands
  it." This document is the considered answer to that question.

## 3. Assessment

### Where TEI genuinely helps

1. **Bulk ingest throughput and stability** (the strongest case).
   Gutenberg-scale corpus builds are the workloads that produced the
   postmortem. A TEI endpoint (GPU box or even CPU container) with dynamic
   batching replaces per-worker model copies and lets `CorpusEmbedder`
   fan out HTTP calls freely instead of guarding against GPU contention.
2. **Cross-encoder reranking for near-free.** `pipeline.py`'s rerank is a
   pure arithmetic semantic/lexical blend (0.7/0.3). TEI's `/rerank` with
   `bge-reranker-base` would add a real quality lever as a new
   `rerank_mode` without adding torch inference to the client.
3. **Isolating torch/MPS instability.** The MPS SIGBUS, allocator drift,
   and spawn-worker env plumbing (`KG_EMBED_DEVICE`) all stem from running
   PyTorch in-process. A subprocess/sidecar boundary makes those failures
   non-fatal to the build.
4. **Serving-image hygiene (marginal today).** The RunPod worker installs
   CPU torch + sentence-transformers to embed *one query at a time*. A TEI
   sidecar could shrink that image — but `bge-small` is 130 MB, pre-baked,
   and CPU-fast, so this is not a driver on its own.

### Where TEI does not help / costs

- **A new infra component.** Docker container (or cargo-built binary) to
  run, version, and health-check. For laptop-local single-query use the
  current in-process path is simpler and stays the default.
- **`dim` must not require a network round trip.** Both vector backends
  need `dim` at table-creation time and `semantic.py` defers embedder
  loading deliberately. A TEI backend must take `dim` from config or probe
  once and cache.
- **`CorpusEmbedder` bypasses the seam.** It calls
  `load_sentence_transformer()` directly (`corpus_embedder.py:104,155`),
  so the bulk path — the one with the most to gain — needs explicit
  plumbing, not just a new factory branch.
- **Offline/air-gapped builds** must keep working; TEI is additive, never
  required.

### Verdict

Adopt as an **optional backend**: one new `Embedder` implementation, one
factory branch, config via the existing pattern. Gate the bulk-ingest
integration on a measured benchmark. Reranking is a separate, worthwhile
follow-on. Do **not** make TEI a dependency of the default path.

## 4. Plan

### Phase 0 — Spike & benchmark (decision gate)

- Run TEI CPU image with `BAAI/bge-small-en-v1.5`; verify parity: cosine
  similarity of TEI vectors vs `SentenceTransformerEmbedder` on a sample
  (expect ≥0.999 after normalization; confirm `normalize` semantics and
  the nomic `search_document:` prefix behave identically).
- Benchmark end-to-end ingest on the scratch Moby Dick corpus (10,910
  vectors, the LanceDB-migration test corpus) three ways: in-process CPU,
  TEI-CPU sidecar, TEI-GPU (RunPod 3080 class).
- **Gate:** proceed to Phase 3 (bulk path) only if TEI ≥2× ingest
  throughput or eliminates a stability class we care about; Phases 1–2 are
  cheap enough to land on operational grounds alone.

#### Phase 0 results (run 2026-08-14, CPU-only)

Environment: 4 vCPU / 15 GB RAM Linux container (no GPU available), TEI
1.9.3 `cpu-latest` image, sentence-transformers 5.x with CPU torch, both
given the same 4 cores (never benchmarked concurrently). Corpus: Moby
Dick chunked to 2,370 passages (~90 words each), tiled to 10,910 items to
match the reference corpus size. Fleet contract kept: 128-item batches,
normalized vectors. TEI served the model from a local mount (no network
at boot; boot-to-ready ≈ 2 s).

**Parity — PASSED, vectors are interchangeable:**

| Metric | Value |
|---|---|
| cosine(ST, TEI) min / mean over 2,370 chunks | 0.999997 / 0.999999 |
| top-10 retrieval agreement (50 queries) | 99.8% mean, 90% worst |

TEI's warning about GeLU-tanh approximation vs exact GeLU is real but
negligible at these magnitudes. Vectors from either backend can share a
`SqliteVecBackend` store.

**Throughput — TEI-CPU FAILED the ≥2× gate (it is ~0.5×):**

| Backend | items/s | wall (10,910 items) |
|---|---|---|
| in-process ST, CPU, batch 128 | **41.0** | 266 s |
| TEI-CPU, 1 client thread | 18.8 | 582 s |
| TEI-CPU, 2 client threads | 19.3 | 566 s |
| TEI-CPU, 4 client threads | 19.4 | 563 s |
| TEI-CPU, 8 client threads | HTTP 429 | — |

Torch's MKL/oneDNN kernels beat TEI's candle backend on x86 CPU, and
client concurrency cannot help a server that is already core-saturated
(flat 19 items/s from 1→4 threads; at 8 the queue overflows and TEI
sheds load with an explicit 429 rather than stalling — good behavior,
but not more throughput). **Conclusion: on CPU, keep bulk ingest
in-process.** The Phase 3 bulk-path work is deferred until a GPU
benchmark (RunPod 3080-class) can be run; TEI's published numbers are
GPU numbers, and the gate decision for GPU ingest remains open.

**Memory — TEI wins decisively on the serving path:**

| | RSS |
|---|---|
| in-process torch + ST serving bge-small (130 MB weights) | 1,500 MiB |
| TEI container serving the same model | **176 MiB** |

8.5× smaller. For the RunPod worker (embeds one query at a time) this —
not throughput — is the argument for a TEI sidecar: it would remove
torch + sentence-transformers from the worker image entirely.

**Reranking demo (`BAAI/bge-reranker-base`, TEI `/rerank`):** works as
designed — on "how do sailors boil blubber into oil" the cross-encoder
promoted the whale-oil lamps passage from dense rank 10 to 1; on the
doubloon query it correctly signaled (all scores ≤0.12) that no retrieved
passage actually explains the meaning. Cost on shared 4-CPU: **~10–12 s
to rerank 50 candidates** (~220 ms/pair; the 278M-param XLM-R
cross-encoder is ~8× bge-small). CPU reranking is viable only for small
K (top-10 ≈ 2.4 s) or batch/offline use; interactive reranking wants the
GPU pod. Container RSS: 1.7 GiB.

**Net Phase 0 verdict:** parity is a non-issue; adopt Phases 1–2 (the
`TEIEmbedder` seam) on operational grounds — the serving-memory win is
real today and the seam is required for any future GPU decision — but do
not move bulk ingest to TEI-CPU, and treat GPU throughput + interactive
reranking as one combined follow-up benchmark on real GPU hardware.

### Phase 1 — `TEIEmbedder` in KG_utils

- Add `TEIEmbedder(Embedder)` to `kg_utils/src/kg_utils/embedder.py`
  alongside `SentenceTransformerEmbedder`, so every KG module inherits it.
  Native `/embed` API via `httpx` (already a fleet dependency); chunked
  requests honoring the caller's `encode_batch_size` contract
  (`DEFAULT_ENCODE_BATCH = 128` stays the ceiling per request).
- `dim`: explicit constructor/config value, else probe `/info` once at
  construction and cache.
- Config: mirror the `synthesis/_config.py` trio —
  `KG_EMBED_BACKEND` / `KG_EMBED_ENDPOINT` / `KG_EMBED_API_KEY` env vars
  with sensible defaults (`http://localhost:8080`). Reuse
  `normalize_openai_base_url()` if we expose the OpenAI-wire variant.
- Tests: mocked HTTP (respx or httpx.MockTransport), parity fixtures,
  timeout/retry behavior (bounded retries, fail loud — no silent fallback
  to a different model, which would poison a 384-dim store).

### Phase 2 — Factory & config in KGRAG

- `make_embedder()` (`kg_rag/embed.py`): add `embed_backend = "tei"`
  branch reading endpoint/model/dim from `[tool.kgrag]`; update the
  exhaustiveness `ValueError`.
- Document in `docs/USAGE.md` + `settings.json.template`; note in
  `TODO.md`'s coordination section that `kgrag_priv` picks this up via
  its own `[tool.kgrag]` (no code change expected there).

### Phase 3 — Bulk-ingest path (gated on Phase 0)

- Give `CorpusEmbedder` an injected embedder (default: current behavior)
  instead of hard-calling `load_sentence_transformer()`.
- When the embedder is remote: skip the GPU no-fan-out guard and worker
  recycling (both exist to manage local model state), and raise worker
  concurrency — the server does the batching.
- Re-run the postmortem's 528k-node scenario as the acceptance test:
  flat client RSS, no MPS involvement.

### Phase 4 — Reranking (independent follow-on)

- New `rerank_mode = "cross"` in `kg_utils/pipeline.py` calling TEI
  `/rerank` (`bge-reranker-base`) over the top-k candidates, blended or
  pure. Off by default; measure on existing eval queries before promoting.

### Phase 5 — Deployment

- `runpod/docker-compose.yml`: optional TEI sidecar service; handler swap
  is one call site (`runpod/handler.py:174-182` `_make_embedder()`),
  selected by `EMBED_BACKEND` env. Keep in-process as the default until
  Phase 0 numbers justify flipping it for GPU pods.
- Local dev on Apple Silicon: document `cargo install` with Metal, or
  TEI-CPU via Docker; never required.

## 5. Out of scope

- Replacing `LlamaCppEmbedder` (serves a different niche: zero-server GGUF).
- Model upgrades (Qwen3-Embedding etc.) — TEI makes them easy later, but
  changing models means re-embedding the fleet and is a separate decision
  entangled with the LanceDB retirement in `TODO.md`.
- Sparse/SPLADE embeddings (`/embed_sparse`) — no consumer today.
