# KGRAG RunPod Serverless Worker

Serves federated semantic search across **GutenbergKG** (Project Gutenberg
literary corpus) and **MetaboKG** (metabolic pathway corpus) as a
cost-efficient RunPod serverless endpoint that scales to zero.

---

## Architecture

```
Client
  │ POST /v2/<endpoint-id>/runsync
  ▼
RunPod Serverless — KGRAG Query Worker
  • handler.py bootstraps a KGRegistry from the Network Volume on startup
  • BAAI/bge-small-en-v1.5 baked into the image (no cold-start download)
  • LanceDB + SQLite indices served from Network Volume (~200 MB total)
  │ (optional, synthesize=true)
  ▼
RunPod vLLM Endpoint — Qwen3-8B-Instruct

RunPod Network Volume (~50 GB reserved)
  /workspace/                        (RunPod default mount point)
  ├── gutenberg_kg/.dockg/          (DocKG index)
  └── metabo_kg/data/
      ├── hsa_pathways/.metabokg/
      ├── cge_pathways/.metabokg/
      └── icho_model/.metabokg/
```

---

## Step 1 — Build and push the Docker image

```bash
chmod +x build_image.sh
./build_image.sh kgrag-worker:latest

docker tag kgrag-worker:latest <your-registry>/kgrag-worker:latest
docker push <your-registry>/kgrag-worker:latest
```

`build_image.sh` builds local Python wheels for `kg-rag`, `gutenberg-kg`,
and `metabo-kg` (which are not yet on PyPI), then runs `docker build`.

Assumed repo layout (all siblings of `kgrag/`):
```
repos/
├── kgrag/          ← this repo
├── gutenberg_kg/
└── Metabo_kg/
```

---

## Step 2 — Create a Network Volume

1. RunPod dashboard → **Storage** → **+ Network Volume**
2. Size: **50 GB** (currently ~200 MB used; room to grow the Gutenberg corpus)
3. Region: same datacenter you'll deploy the worker to

---

## Step 3 — Populate the volume

Spin up a temporary RunPod dev pod with the volume attached at `/workspace`
(any cheap CPU pod — no GPU needed for index building).

**Option A — push pre-built local indices** (~130 MB, minutes):

```bash
./push_indices.sh
```

**Option B — build from scratch inside the pod** (full Gutenberg catalog):

```bash
# Upload the builder to the pod
scp -P <PORT> runpod/build_kg.py root@ssh.runpod.io:/tmp/

# SSH in and run
ssh -p <PORT> root@ssh.runpod.io
python3 /tmp/build_kg.py

# Rebuild indices only (repos + venv already present):
python3 /tmp/build_kg.py --rebuild-only

# One corpus only:
python3 /tmp/build_kg.py --metabo-only
python3 /tmp/build_kg.py --gutenberg-only --skip-download

# Full help:
python3 /tmp/build_kg.py --help
```

---

## Step 4 — Deploy the serverless endpoint

RunPod dashboard → **Serverless** → **+ New Endpoint**

| Setting | Value |
|---|---|
| Container image | `<your-registry>/kgrag-worker:latest` |
| GPU | RTX 3080 16 GB (or any — embedding runs on CPU too) |
| Min workers | 0 |
| Max workers | 3 |
| FlashBoot | Enabled |
| Network Volume | Attach at `/workspace` |

**Environment variables:**

| Variable | Value |
|---|---|
| `KG_VOLUME` | `/workspace` |
| `RUNPOD_API_KEY` | your RunPod API key |
| `VLLM_ENDPOINT_URL` | `https://api.runpod.ai/v2/<vllm-endpoint-id>` (optional) |
| `VLLM_MODEL` | `Qwen/Qwen3-8B-Instruct` (optional) |

---

## Calling the endpoint

```bash
curl -s -X POST \
  "https://api.runpod.ai/v2/<ENDPOINT_ID>/runsync" \
  -H "Authorization: Bearer $RUNPOD_API_KEY" \
  -H "Content-Type: application/json" \
  -d '{
    "input": {
      "query": "Marcus Aurelius on suffering and stoic virtue",
      "corpus": "gutenberg",
      "k": 8
    }
  }' | jq .
```

**Request fields:**

| Field | Type | Default | Description |
|---|---|---|---|
| `query` | str | — | Natural-language query (required) |
| `corpus` | str | `"all"` | `"gutenberg"`, `"metabo_hsa"`, `"metabo_cge"`, `"metabo_icho"`, or `"all"` |
| `k` | int | `8` | Top-k hits |
| `min_score` | float | `0.0` | Drop hits below this score |
| `semantic_floor` | float | `0.0` | Discard an entire KG if its best hit is below this |
| `synthesize` | bool | `false` | Generate an answer via the vLLM endpoint |

**Example response:**

```json
{
  "output": {
    "query": "Marcus Aurelius on suffering and stoic virtue",
    "corpus": "gutenberg",
    "total_hits": 8,
    "kgs_queried": 1,
    "hits": [
      {
        "kg_name": "gutenberg",
        "kg_kind": "gutenberg",
        "node_id": "...",
        "name": "...",
        "kind": "chunk",
        "score": 0.8912,
        "summary": "The impediment to action advances action. What stands in the way becomes the way.",
        "source_path": "meditations/book5.md"
      }
    ],
    "synthesis": null
  }
}
```

---

## Optional: vLLM generation endpoint

Deploy via RunPod Hub → **vLLM**:
- Model: `Qwen/Qwen3-8B-Instruct`
- GPU: RTX 4090
- `MAX_MODEL_LEN=8192`

Then set `VLLM_ENDPOINT_URL` in the query worker's environment variables
and pass `"synthesize": true` in requests to get a generated answer.

---

## Local smoke test

```bash
cd runpod/
KG_VOLUME=/tmp/kgvol python test_local.py
```

The test script creates symlinks under `/tmp/kgvol` pointing at your local
repo indices so you can validate the handler without Docker.

---

## Adding more corpora

1. Build the index in the new repo (`dockg build --wipe` or equivalent)
2. `rsync` it to the Network Volume under a new subdirectory
3. Add an entry to `_CORPUS_MAP` in `handler.py` with the correct paths and `KGKind`
4. Rebuild and push the Docker image
