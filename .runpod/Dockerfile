# KGRAG RunPod Hub worker
# Hub-compatible build: packages installed from GitHub (no local wheels needed).
# The runpod/Dockerfile is for local/manual builds using build_image.sh.

FROM python:3.12-slim

WORKDIR /app

RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        libgomp1 \
        libglib2.0-0 \
        git \
        curl \
    && rm -rf /var/lib/apt/lists/*

# PyPI deps — transformers pinned <4.57 to match doc-kg 0.15.2 constraint
RUN pip install --no-cache-dir \
    "transformers>=4.40.0,<4.57" \
    runpod>=1.7.0 \
    "doc-kg>=0.15.2" \
    "sentence-transformers>=5.4.1" \
    "lancedb>=0.29.0" \
    "numpy>=1.24.0" \
    "httpx>=0.27.0" \
    "rich>=13.0.0,<15.0.0" \
    "click>=8.1.0" \
    "pandas>=2.0.0"

# GitHub-only packages (not yet on PyPI)
RUN pip install --no-cache-dir \
    git+https://github.com/Flux-Frontiers/KGRAG.git \
    git+https://github.com/Flux-Frontiers/gutenberg_kg.git \
    git+https://github.com/Flux-Frontiers/metabo_kg.git

# Pre-download the embedding model so cold starts don't hit HuggingFace
ARG EMBED_MODEL=BAAI/bge-small-en-v1.5
RUN python - <<'EOF'
from sentence_transformers import SentenceTransformer
import os
model = os.environ.get("EMBED_MODEL", "BAAI/bge-small-en-v1.5")
print(f"Pre-downloading {model} …")
SentenceTransformer(model)
print("Done.")
EOF

RUN curl -fsSL https://raw.githubusercontent.com/Flux-Frontiers/KGRAG/main/runpod/handler.py -o handler.py

CMD ["python", "-u", "handler.py"]
