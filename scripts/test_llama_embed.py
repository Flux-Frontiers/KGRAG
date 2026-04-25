"""Compare LlamaCppEmbedder vs SentenceTransformerEmbedder on DocKG."""

import time
from pathlib import Path

from doc_kg.kg import DocKG

from kg_rag.embed import LlamaCppEmbedder, SentenceTransformerEmbedder

MODEL_GGUF = Path("~/.kgrag/bge-small-en-v1.5-Q8_0.gguf").expanduser()
MODEL_ST = "BAAI/bge-small-en-v1.5"
DOC_ROOT = Path("/Users/egs/repos/doc_kg")
QUERIES = [
    "how does SemanticIndex work?",
    "how do I build a knowledge graph?",
    "chunk strategy configuration options",
]
K = 8


def run(label: str, embedder, query: str) -> tuple[float, list[str]]:
    kg = DocKG(corpus_root=DOC_ROOT, embedder=embedder)
    t0 = time.perf_counter()
    result = kg.query(query, k=K)
    elapsed = time.perf_counter() - t0
    ids = [n.get("node_id", "?") for n in result.nodes[:K]]
    return elapsed, ids


def jaccard(a: list[str], b: list[str]) -> float:
    sa, sb = set(a), set(b)
    return len(sa & sb) / len(sa | sb) if sa | sb else 1.0


# ── load embedders ──────────────────────────────────────────────────────────
print("Loading LlamaCppEmbedder...")
t0 = time.perf_counter()
llama_emb = LlamaCppEmbedder(MODEL_GGUF, verbose=False)
llama_load = time.perf_counter() - t0
print(f"  {llama_load:.2f}s  dim={llama_emb.dim}")

print("Loading SentenceTransformerEmbedder...")
t0 = time.perf_counter()
st_emb = SentenceTransformerEmbedder(MODEL_ST)
st_load = time.perf_counter() - t0
print(f"  {st_load:.2f}s  dim={st_emb.dim}")

# ── per-query comparison ────────────────────────────────────────────────────
print(f"\n{'Query':<45} {'llama':>7} {'ST':>7} {'Jaccard':>8}  Top-1 match?")
print("-" * 80)

total_jac = 0.0
for q in QUERIES:
    t_llama, ids_llama = run("llama", llama_emb, q)
    t_st, ids_st = run("ST", st_emb, q)
    jac = jaccard(ids_llama, ids_st)
    total_jac += jac
    top1_match = "✓" if ids_llama and ids_st and ids_llama[0] == ids_st[0] else "✗"
    print(f"{q:<45} {t_llama:>6.2f}s {t_st:>6.2f}s {jac:>8.3f}  {top1_match}")

print("-" * 80)
print(f"{'Mean Jaccard similarity':<45} {'':>7} {'':>7} {total_jac / len(QUERIES):>8.3f}")
print(f"\nLoad times: llama={llama_load:.1f}s  ST={st_load:.1f}s")
