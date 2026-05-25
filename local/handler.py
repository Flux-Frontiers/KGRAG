"""
RunPod serverless handler -KGRAG query service.

Serves federated semantic search across GutenbergKG and MetaboKG corpora
mounted from a RunPod Network Volume.

Volume layout (KG_VOLUME)
--------------------------
  gutenberg_kg/
    corpus/
      <genre>/
        <book>/
          .dockg/
            graph.sqlite
            lancedb/
  metabo_kg/
    data/
      hsa_pathways/.metabokg/{hsa.sqlite,lancedb/}
      cge_pathways/.metabokg/{cge.sqlite,lancedb/}
      icho_model/.metabokg/{icho.sqlite,lancedb/}

Environment variables
---------------------
KG_VOLUME        Path where indices are stored. Default: /tmp/kgdata
EMBED_MODEL      Sentence-transformer model ID. Default: BAAI/bge-small-en-v1.5
HANDLER_SECRET   Optional shared secret. When set, requests must include {"secret": "<value>"}.
VLLM_ENDPOINT_URL   Optional: RunPod vLLM endpoint base URL for synthesis.
RUNPOD_API_KEY   RunPod API key (used for vLLM auth when synthesize=true).
VLLM_MODEL       Model ID served by the vLLM endpoint. Default: Qwen/Qwen3-8B-Instruct
S3_BUCKET        S3 bucket name holding the KG indices.
S3_ENDPOINT_URL  S3-compatible endpoint URL (e.g. https://s3api-us-il-1.runpod.io).
S3_REGION        S3 region name (e.g. us-il-1).
AWS_ACCESS_KEY_ID     S3 access key.
AWS_SECRET_ACCESS_KEY S3 secret key.

Request schema
--------------
{
  "query":          str   -natural-language query (required)
  "secret":         str   -required when HANDLER_SECRET is set
  "corpus":         str   -"gutenberg" | "metabo_hsa" | "metabo_cge" |
                           "metabo_icho" | "all"  (default: "all")
  "k":              int   -top-k hits to return (default: 8)
  "min_score":      float -drop hits below this score (default: 0.0)
  "semantic_floor": float -discard a KG entirely if its best hit is below
                           this value (default: 0.0)
  "synthesize":     bool  -call vLLM endpoint for a generated answer
                           (default: false)
}
"""

from __future__ import annotations

import os
import uuid
from datetime import UTC, datetime
from pathlib import Path

import runpod

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

VOLUME = Path(os.environ.get("KG_VOLUME", "/tmp/kgdata"))
REGISTRY_PATH = Path("/tmp/kgrag_worker/registry.sqlite")
VLLM_ENDPOINT = os.environ.get("VLLM_ENDPOINT_URL", "")
RUNPOD_API_KEY = os.environ.get("RUNPOD_API_KEY", "")
VLLM_MODEL = os.environ.get("VLLM_MODEL", "Qwen/Qwen3-8B-Instruct")
EMBED_MODEL = os.environ.get("EMBED_MODEL", "BAAI/bge-small-en-v1.5")
HANDLER_SECRET = os.environ.get("HANDLER_SECRET", "")
S3_BUCKET = os.environ.get("S3_BUCKET", "")
S3_ENDPOINT_URL = os.environ.get("S3_ENDPOINT_URL", "")
S3_REGION = os.environ.get("S3_REGION", "us-il-1")

# Static MetaboKG entries: name → (kind_str, repo_path, sqlite_path, lancedb_path)
_METABO_MAP = {
    "metabo_hsa": (
        "meta",
        VOLUME / "metabo_kg",
        VOLUME / "metabo_kg" / "data" / "hsa_pathways" / ".metabokg" / "hsa.sqlite",
        VOLUME / "metabo_kg" / "data" / "hsa_pathways" / ".metabokg" / "lancedb",
    ),
    "metabo_cge": (
        "meta",
        VOLUME / "metabo_kg",
        VOLUME / "metabo_kg" / "data" / "cge_pathways" / ".metabokg" / "cge.sqlite",
        VOLUME / "metabo_kg" / "data" / "cge_pathways" / ".metabokg" / "lancedb",
    ),
    "metabo_icho": (
        "meta",
        VOLUME / "metabo_kg",
        VOLUME / "metabo_kg" / "data" / "icho_model" / ".metabokg" / "icho.sqlite",
        VOLUME / "metabo_kg" / "data" / "icho_model" / ".metabokg" / "lancedb",
    ),
}

_METABO_CORPORA = {"metabo_hsa", "metabo_cge", "metabo_icho"}
_GUTENBERG_CORPUS_DIR = VOLUME / "gutenberg_kg" / "corpus"


# ---------------------------------------------------------------------------
# Startup: bootstrap registry, load embedder, initialise orchestrator
# ---------------------------------------------------------------------------


def _bootstrap_registry():
    from kg_rag.primitives import KGEntry, KGKind
    from kg_rag.registry import KGRegistry

    REGISTRY_PATH.parent.mkdir(parents=True, exist_ok=True)
    reg = KGRegistry(db_path=REGISTRY_PATH)

    # --- Gutenberg: one entry per book from corpus/<genre>/<book>/.dockg/ ---
    gb_count = 0
    if _GUTENBERG_CORPUS_DIR.is_dir():
        for genre_dir in sorted(_GUTENBERG_CORPUS_DIR.iterdir()):
            if not genre_dir.is_dir() or genre_dir.name == "authors":
                continue
            for book_dir in sorted(genre_dir.iterdir()):
                if not book_dir.is_dir():
                    continue
                # diary pipeline uses .diarykg/; standard uses .dockg/
                for kg_subdir in (".diarykg", ".dockg"):
                    sqlite = book_dir / kg_subdir / "graph.sqlite"
                    lancedb = book_dir / kg_subdir / "lancedb"
                    if sqlite.exists():
                        break
                else:
                    continue
                slug = book_dir.name.lower().replace(" ", "-").replace("(", "").replace(")", "")
                name = f"gutenberg-{genre_dir.name}-{slug}"
                entry = KGEntry(
                    id=str(uuid.uuid4()),
                    name=name,
                    kind=KGKind.GUTENBERG,
                    repo_path=book_dir,
                    venv_path=Path("/usr"),
                    sqlite_path=sqlite,
                    lancedb_path=lancedb,
                    created_at=datetime.now(UTC),
                    updated_at=datetime.now(UTC),
                )
                reg.register(entry)
                gb_count += 1
    print(f"[bootstrap] registered {gb_count} gutenberg book indices")

    # --- MetaboKG: static entries ---
    for name, (kind_str, repo_path, sqlite_path, lancedb_path) in _METABO_MAP.items():
        if not sqlite_path.exists():
            print(f"[bootstrap] {name}: index not found at {sqlite_path}, skipping")
            continue
        entry = KGEntry(
            id=str(uuid.uuid4()),
            name=name,
            kind=KGKind.from_str(kind_str),
            repo_path=repo_path,
            venv_path=Path("/usr"),
            sqlite_path=sqlite_path,
            lancedb_path=lancedb_path,
            created_at=datetime.now(UTC),
            updated_at=datetime.now(UTC),
        )
        reg.register(entry)
        print(f"[bootstrap] registered {name} ({kind_str})")

    registered = [e.name for e in reg.list()]
    print(
        f"[bootstrap] active corpora: {len(registered)} total ({gb_count} gutenberg, {len(registered) - gb_count} metabo)"
    )
    return reg


def _make_embedder():
    from kg_rag._embedders import SentenceTransformerEmbedder

    print(f"[startup] loading embedder: {EMBED_MODEL}")
    emb = SentenceTransformerEmbedder(EMBED_MODEL)
    # warm up
    emb.embed_texts(["warm up"])
    print("[startup] embedder ready")
    return emb


def _sync_from_s3() -> None:
    if not S3_BUCKET or not S3_ENDPOINT_URL:
        print("[s3] S3_BUCKET/S3_ENDPOINT_URL not set — skipping sync")
        return
    import boto3
    from botocore.config import Config

    VOLUME.mkdir(parents=True, exist_ok=True)
    s3 = boto3.client(
        "s3",
        endpoint_url=S3_ENDPOINT_URL,
        region_name=S3_REGION,
        config=Config(signature_version="s3v4"),
    )
    paginator = s3.get_paginator("list_objects_v2")
    total = 0
    for page in paginator.paginate(Bucket=S3_BUCKET):
        for obj in page.get("Contents", []):
            key = obj["Key"]
            dest = VOLUME / key
            dest.parent.mkdir(parents=True, exist_ok=True)
            if not dest.exists() or dest.stat().st_size != obj["Size"]:
                s3.download_file(S3_BUCKET, key, str(dest))
                total += 1
    print(f"[s3] synced {total} file(s) from s3://{S3_BUCKET} → {VOLUME}")


print("[startup] syncing indices from S3 ...")
_sync_from_s3()

print("[startup] bootstrapping registry ...")
_registry = _bootstrap_registry()

print("[startup] loading embedder ...")
_embedder = _make_embedder()

print("[startup] initialising KGRAG orchestrator ...")
from kg_rag.orchestrator import KGRAG  # noqa: E402 (after env setup)

_kgrag = KGRAG(registry_path=REGISTRY_PATH, embedder=_embedder)
print("[startup] ready")


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _hit_to_dict(hit) -> dict:
    return {
        "kg_name": hit.kg_name,
        "kg_kind": str(hit.kg_kind),
        "node_id": hit.node_id,
        "name": hit.name,
        "kind": hit.kind,
        "score": round(float(hit.score), 4),
        "summary": hit.summary,
        "source_path": hit.source_path,
    }


def _synthesize(query: str, hits: list[dict]) -> str | None:
    if not VLLM_ENDPOINT:
        return None
    import httpx

    ctx = "\n\n".join(f"[{h['source_path']}]\n{h['summary']}" for h in hits if h.get("summary"))
    resp = httpx.post(
        f"{VLLM_ENDPOINT}/v1/chat/completions",
        headers={"Authorization": f"Bearer {RUNPOD_API_KEY}"},
        json={
            "model": VLLM_MODEL,
            "messages": [
                {"role": "system", "content": "Answer using only the provided context."},
                {"role": "user", "content": f"Context:\n{ctx}\n\nQuestion: {query}"},
            ],
            "max_tokens": 2048,
        },
        timeout=httpx.Timeout(connect=10.0, read=600.0, write=60.0, pool=10.0),
    )
    resp.raise_for_status()
    return resp.json()["choices"][0]["message"]["content"]


# ---------------------------------------------------------------------------
# Handler
# ---------------------------------------------------------------------------


def handler(job: dict) -> dict:
    inp = job.get("input", {})

    if HANDLER_SECRET and inp.get("secret") != HANDLER_SECRET:
        return {"error": "unauthorized"}

    query = inp.get("query", "").strip()
    corpus = inp.get("corpus", "all")
    k = max(1, int(inp.get("k", 8)))
    min_score = float(inp.get("min_score", 0.0))
    semantic_floor = float(inp.get("semantic_floor", 0.0))
    synthesize = bool(inp.get("synthesize", False))

    if not query:
        return {"error": "query is required"}

    from kg_rag.primitives import KGKind

    # Resolve kind filter from corpus selector
    if corpus == "all":
        kind_filter = None
    elif corpus == "gutenberg":
        kind_filter = [KGKind.GUTENBERG]
    elif corpus in _METABO_CORPORA:
        kind_filter = [KGKind.META]
    else:
        return {
            "error": f"unknown corpus {corpus!r}; choose: gutenberg, metabo_hsa, metabo_cge, metabo_icho, all"
        }

    result = _kgrag.query(
        query,
        k=k,
        kinds=kind_filter,
        min_score=min_score,
        semantic_floor=semantic_floor,
    )

    hits = [_hit_to_dict(h) for h in result.hits]
    synthesis = _synthesize(query, hits) if synthesize else None

    return {
        "query": query,
        "corpus": corpus,
        "total_hits": result.total_hits,
        "kgs_queried": result.kgs_queried,
        "hits": hits,
        "synthesis": synthesis,
    }


if __name__ == "__main__":
    runpod.serverless.start({"handler": handler})
