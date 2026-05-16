# KGRAG RunPod Serverless Worker

Serves federated semantic search across **GutenbergKG** (203 per-book DocKG
indices) and **MetaboKG** (hsa / cge / icho metabolic pathway corpora) as a
cost-efficient RunPod serverless endpoint that scales to zero.

---

## Architecture

```
Client
  │ POST /v2/<endpoint-id>/runsync
  ▼
RunPod Serverless — KGRAG Query Worker
  • handler.py bootstraps a fresh KGRegistry at every cold start
    by walking the Network Volume corpus directory
  • 203 per-book GutenbergKGAdapter entries + 3 MetaKGAdapter entries
  • BAAI/bge-small-en-v1.5 (384-dim) baked into the image layer
  │ (optional: synthesize=true)
  ▼
RunPod vLLM Endpoint — Qwen3-8B-Instruct

RunPod Network Volume (KG_VOLUME=/workspace/kgdata)
  ├── gutenberg_kg/
  │   └── corpus/
  │       ├── philosophy/
  │       │   ├── Meditations (Marcus Aurelius)/
  │       │   │   └── .dockg/  {graph.sqlite, lancedb/}
  │       │   └── ...
  │       ├── english-literature/...
  │       └── <genre>/<book>/.dockg/  ← one index per book
  └── metabo_kg/
      └── data/
          ├── hsa_pathways/.metabokg/  {hsa.sqlite, lancedb/}
          ├── cge_pathways/.metabokg/
          └── icho_model/.metabokg/
```

### How the registry works

`handler.py` runs at cold-start module load time (before the first request):

1. Walks `$KG_VOLUME/gutenberg_kg/corpus/<genre>/<book>/` — registers every
   book whose `.dockg/graph.sqlite` exists as a `KGKind.GUTENBERG` entry.
2. Registers the three static MetaboKG entries if their `.metabokg/*.sqlite`
   files exist (missing ones are skipped with a warning, not an error).
3. Creates the KGRAG orchestrator with this ephemeral registry at
   `/tmp/kgrag_worker/registry.sqlite`.

The `~/.kgrag/registry.sqlite` on your laptop is **never used** — the worker
builds its own from whatever is on the volume.

---

## Step 1 — Build and push the Docker image

```bash
chmod +x build_image.sh
./build_image.sh                          # tags as kgrag-worker:latest

docker tag kgrag-worker:latest <your-registry>/kgrag-worker:latest
docker push <your-registry>/kgrag-worker:latest
```

`build_image.sh` builds local Python wheels for `kg-rag`, `gutenberg-kg`,
and `metabo-kg` (not yet on PyPI), then runs `docker build`.

Assumed repo layout (siblings of `kgrag/`):
```
repos/
├── kgrag/           ← this repo
├── gutenberg_kg/    ← corpus/  must be built first (gutenkg ingest)
└── Metabo_kg/       ← data/*/metabokg/ must be built first
```

---

## Step 2 — Create a Network Volume

1. RunPod dashboard → **Storage** → **+ Network Volume**
2. Size: **50 GB** (indices are ~2 GB; room to grow the corpus)
3. Region: same datacenter as the worker endpoint

---

## Step 3 — Populate the volume

Attach the volume to a temporary cheap CPU pod (`/workspace` mount path).

**Option A — push pre-built local indices** (fastest, ~2 GB upload):

```bash
cd runpod/
./push_indices.sh
# prompts for POD_HOST and POD_PORT (from RunPod dashboard → Connect)
```

`push_indices.sh` rsyncs the per-book `.dockg/` index directories only —
raw text files are excluded. MetaboKG `.metabokg/` directories are pushed
in full.

**Option B — build from scratch inside the pod**:

```bash
# Upload the builder
scp -P <PORT> runpod/build_kg.py root@ssh.runpod.io:/tmp/

# SSH in and run
ssh -p <PORT> root@ssh.runpod.io
python3 /tmp/build_kg.py                      # full build
python3 /tmp/build_kg.py --rebuild-only       # skip clone/venv
python3 /tmp/build_kg.py --gutenberg-only     # skip MetaboKG
python3 /tmp/build_kg.py --help               # all flags
```

After either option, verify the layout:
```bash
du -sh /workspace/kgdata/gutenberg_kg/corpus
du -sh /workspace/kgdata/metabo_kg/data/hsa_pathways/.metabokg
```

Detach or terminate the temporary pod — the volume is now ready.

---

## Step 4 — Deploy the serverless endpoint

RunPod dashboard → **Serverless** → **+ New Endpoint**

| Setting | Value |
|---|---|
| Container image | `<your-registry>/kgrag-worker:latest` |
| GPU | Any (embedding runs on CPU; GPU speeds up first query batch) |
| Min workers | `0` (scales to zero when idle) |
| Max workers | `3` |
| FlashBoot | Enabled |
| Network Volume | Attach; set mount path to `/workspace/kgdata` |

**Environment variables** (set in the endpoint UI):

| Variable | Required | Value |
|---|---|---|
| `KG_VOLUME` | yes | `/workspace/kgdata` |
| `RUNPOD_API_KEY` | yes | your RunPod API key |
| `EMBED_MODEL` | no | `BAAI/bge-small-en-v1.5` (default; must match index build model) |
| `VLLM_ENDPOINT_URL` | no | `https://api.runpod.ai/v2/<vllm-endpoint-id>` |
| `VLLM_MODEL` | no | `Qwen/Qwen3-8B-Instruct` |

> **Important:** The Network Volume is always mounted read-write by RunPod.
> Do **not** mount it read-only — LanceDB writes lock files when opening
> indices, even for read-only queries.

The Dockerfile CMD (`python -u handler.py`) calls
`runpod.serverless.start()` which is the correct production entrypoint.
No extra flags are needed.

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
| `corpus` | str | `"all"` | `"gutenberg"` / `"metabo_hsa"` / `"metabo_cge"` / `"metabo_icho"` / `"all"` |
| `k` | int | `8` | Top-k hits per KG |
| `min_score` | float | `0.0` | Drop hits below this score |
| `semantic_floor` | float | `0.0` | Discard a KG entirely if its best hit is below this |
| `synthesize` | bool | `false` | Call the vLLM endpoint for a generated answer |

**Example response:**

```json
{
  "output": {
    "query": "Marcus Aurelius on suffering and stoic virtue",
    "corpus": "gutenberg",
    "kgs_queried": 203,
    "total_hits": 808,
    "hits": [
      {
        "kg_name": "gutenberg-philosophy-meditations-marcus-aurelius",
        "kg_kind": "gutenberg",
        "node_id": "chunk-042",
        "name": "Book V",
        "kind": "chunk",
        "score": 0.8734,
        "summary": "Confine yourself to the present. The impediment to action ...",
        "source_path": "meditations_marcus_aurelius.md"
      }
    ],
    "synthesis": null
  }
}
```

---

## Cold start time

On first request after scale-to-zero:

1. Container pulls (skipped after first pull per worker node)
2. Module-level startup: registry bootstrap (~203 book dir walks) + embedder
   warmup — typically **8–15 s** on a warm node with the volume attached
3. First query embeds the input and fans out to all registered KGs

Subsequent requests on a warm worker: **< 2 s** (embedder and adapters cached
in memory).

---

## Local smoke test (without Docker)

```bash
cd runpod/
python test_local.py
# auto-creates symlinks under /tmp/ pointing at local repo indices
```

## Local Docker test

```bash
docker run --rm -d \
  --name kgrag-test \
  -p 8000:8000 \
  -e KG_VOLUME=/workspace/kgdata \
  -v /path/to/gutenberg_kg/corpus:/workspace/kgdata/gutenberg_kg/corpus \
  -v /path/to/Metabo_kg:/workspace/kgdata/metabo_kg \
  <your-registry>/kgrag-worker:latest \
  python handler.py --rp_serve_api --rp_api_host 0.0.0.0

# wait for "[startup] ready ✓" in logs, then:
docker logs -f kgrag-test

curl -s -X POST http://localhost:8000/runsync \
  -H "Content-Type: application/json" \
  -d '{"input":{"query":"glycolysis ATP production","corpus":"metabo_hsa","k":4}}' \
  | python3 -m json.tool

docker stop kgrag-test
```

> **Note:** `--rp_serve_api --rp_api_host 0.0.0.0` is for local testing only.
> The production Dockerfile CMD does not include these flags.
> The volume must **not** be mounted `:ro` — LanceDB needs write access for
> lock files even during read queries.

---

## Adding more Gutenberg genres

1. Run `gutenkg ingest --genre <genre>` locally to build per-book indices
2. Run `push_indices.sh` (or rsync the new genre dir manually) to push the
   new `.dockg/` subdirectories to the Network Volume
3. The worker picks them up automatically on next cold start — no image
   rebuild needed

## Adding a new corpus type

1. Build the index (e.g. a new DocKG or DiaryKG)
2. Add the static entry to `_METABO_MAP` in `handler.py` (or extend
   `_bootstrap_registry()` for dynamic discovery)
3. Add the corpus name to the `handler()` selector block
4. Rebuild and push the Docker image
