"""Compare DocKG full build timing: LlamaCppEmbedder vs SentenceTransformerEmbedder."""

import shutil
import tempfile
import time
from pathlib import Path

from doc_kg.kg import DocKG

from kg_rag.embed import LlamaCppEmbedder, SentenceTransformerEmbedder

MODEL_GGUF = Path("~/.kgrag/bge-small-en-v1.5-Q8_0.gguf").expanduser()
MODEL_ST = "BAAI/bge-small-en-v1.5"
CORPUS = Path("/Users/egs/repos/doc_kg/docs")  # small real corpus


def build_with(label: str, embedder) -> None:
    tmp = Path(tempfile.mkdtemp(prefix=f"dockg_{label}_"))
    try:
        kg = DocKG(
            corpus_root=CORPUS,
            db_path=tmp / "graph.sqlite",
            lancedb_dir=tmp / "lancedb",
            embedder=embedder,
        )
        t0 = time.perf_counter()
        stats = kg.build(wipe=True)
        elapsed = time.perf_counter() - t0
        print(f"\n{label}")
        print(f"  total time   : {elapsed:.2f}s")
        print(f"  graph nodes  : {sum(stats.node_counts.values())}")
        print(f"  graph edges  : {sum(stats.edge_counts.values())}")
        print(f"  indexed vecs : {stats.indexed_rows}")
        print(f"  embed dim    : {stats.index_dim}")
        if stats.indexed_rows:
            print(f"  ms/vector    : {elapsed * 1000 / stats.indexed_rows:.1f}")
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


print("Loading embedders...")
t0 = time.perf_counter()
llama_emb = LlamaCppEmbedder(MODEL_GGUF, verbose=False)
print(f"  llama.cpp  loaded in {time.perf_counter() - t0:.2f}s")

t0 = time.perf_counter()
st_emb = SentenceTransformerEmbedder(MODEL_ST)
print(f"  ST         loaded in {time.perf_counter() - t0:.2f}s")

print(f"\nCorpus: {CORPUS}")

build_with("LlamaCppEmbedder", llama_emb)
build_with("SentenceTransformerEmbedder", st_emb)
