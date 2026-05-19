# KGRAG RunPod serverless worker
# Serves GutenbergKG + MetaboKG semantic search via the KGRAG orchestrator.
#
# Build with:   ./build_image.sh
# Test locally: docker run --rm -e RUNPOD_WEBHOOK_GET_JOB=<url> kgrag-worker
#
# Required at runtime:
#   KG_VOLUME        — path to mounted Network Volume (default /mnt/kgdata)
#   RUNPOD_API_KEY   — RunPod API key

FROM python:3.12-slim

WORKDIR /app

# System deps needed by sentence-transformers / lancedb
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        libgomp1 \
        libglib2.0-0 \
        git \
    && rm -rf /var/lib/apt/lists/*

# CPU-only torch first to prevent GPU wheels being pulled in by sentence-transformers
RUN pip install --no-cache-dir \
    --extra-index-url https://download.pytorch.org/whl/cpu \
    "torch>=2.5.0"

# PyPI dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Local wheel packages (kg-rag, gutenberg-kg, metabo-kg)
# These are built by build_image.sh before docker build runs.
COPY wheels/ wheels/
RUN pip install --no-cache-dir wheels/*.whl && rm -rf wheels/

# Pre-download the embedding model into the image layer so cold starts
# don't need to pull from HuggingFace. Model: BAAI/bge-small-en-v1.5 (~130 MB)
ARG EMBED_MODEL=BAAI/bge-small-en-v1.5
RUN python - <<'EOF'
from sentence_transformers import SentenceTransformer
import os
model = os.environ.get("EMBED_MODEL", "BAAI/bge-small-en-v1.5")
print(f"Pre-downloading {model} …")
SentenceTransformer(model)
print("Done.")
EOF

COPY handler.py .

CMD ["python", "-u", "handler.py"]
