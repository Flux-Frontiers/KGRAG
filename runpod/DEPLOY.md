# KGRAG RunPod Serverless Deployment

## 1. Build & push the Docker image

```bash
cd runpod/
./build_image.sh
docker push egsuchanek/kgrag-worker:latest
```

---

## 2. Store secrets in RunPod

RunPod Dashboard → **Settings → Secrets** — add each of these:

| Secret key | Value |
|---|---|
| `HANDLER_SECRET` | `908b2fcb516f3ff35a0d20d5d4d88351f1baebe52e50685a040f954296387f21` |
| `AWS_ACCESS_KEY_ID` | your RunPod S3 access key |
| `AWS_SECRET_ACCESS_KEY` | your RunPod S3 secret key |
| `RUNPOD_API_KEY` | your RunPod API key (only needed for synthesis) |

---

## 3. Create the serverless endpoint

RunPod Dashboard → **Serverless → + New Endpoint → Custom**

| Setting | Value |
|---|---|
| Container image | `egsuchanek/kgrag-worker:latest` |
| Container disk | `10 GB` |
| GPU | AMPERE\_16 or ADA\_24 |
| Min workers | `0` |
| Max workers | `3` |
| FlashBoot | Enabled |

---

## 4. Set environment variables on the endpoint

| Variable | Value |
|---|---|
| `KG_VOLUME` | `/tmp/kgdata` |
| `S3_BUCKET` | `7dijxszwbi` |
| `S3_ENDPOINT_URL` | `https://s3api-us-il-1.runpod.io` |
| `S3_REGION` | `us-il-1` |
| `AWS_ACCESS_KEY_ID` | `{{ RUNPOD_SECRET_AWS_ACCESS_KEY_ID }}` |
| `AWS_SECRET_ACCESS_KEY` | `{{ RUNPOD_SECRET_AWS_SECRET_ACCESS_KEY }}` |
| `HANDLER_SECRET` | `{{ RUNPOD_SECRET_HANDLER_SECRET }}` |
| `EMBED_MODEL` | `BAAI/bge-small-en-v1.5` |

---

## 5. Test the endpoint

```bash
export RUNPOD_API_KEY=your_actual_key
export ENDPOINT_ID=your_endpoint_id

curl -X POST https://api.runpod.ai/v2/${ENDPOINT_ID}/runsync \
  -H 'Content-Type: application/json' \
  -H "Authorization: Bearer $RUNPOD_API_KEY" \
  -d '{"input":{"query":"Marcus Aurelius on virtue","corpus":"gutenberg","k":5,"secret":"<your-handler-secret>"}}'
```

### Check job status (if using /run instead of /runsync)

```bash
curl -X GET https://api.runpod.ai/v2/${ENDPOINT_ID}/status/<job-id> \
  -H "Authorization: Bearer $RUNPOD_API_KEY"
```

---

## Notes

- **Cold start**: ~1-2 min on first request (S3 sync + registry bootstrap + embedder load). Warm requests: < 2s.
- **S3 sync** is incremental — files already present are skipped on subsequent cold starts if the worker is reused.
- **Synthesis** (`"synthesize": true`) requires `VLLM_ENDPOINT_URL` and `RUNPOD_API_KEY` to be set. Optional — search works without it.
- The embedding model (`BAAI/bge-small-en-v1.5`) is baked into the image — no HuggingFace download at cold start.
