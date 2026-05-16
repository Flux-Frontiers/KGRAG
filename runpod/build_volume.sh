#!/usr/bin/env bash
# build_volume.sh — entrypoint for populating a RunPod Network Volume.
#
# Two workflows are available depending on where you want to build:
#
#   Workflow A: Push pre-built local indices  (~130 MB upload, minutes)
#   ─────────────────────────────────────────────────────────────────
#   Use this when you already have .dockg / .metabokg indices built
#   locally.  Rsyncs them over SSH to a temporary RunPod pod.
#
#     ./push_indices.sh
#
#   Workflow B: Build from scratch inside a RunPod pod  (full corpus)
#   ─────────────────────────────────────────────────────────────────
#   Use this when you want to build the full Gutenberg catalog
#   (more books than your local partial build), or when setting up
#   a volume in a new region without copying from your machine.
#
#   1. Create a Network Volume in the RunPod dashboard (≥ 50 GB).
#   2. Launch a temporary CPU pod with the volume attached at /workspace.
#      Any Ubuntu 22.04 image works — no GPU needed for index building.
#   3. SSH into the pod and run:
#
#        # Upload the builder script to the pod first
#        scp -P <PORT> build_kg.py root@ssh.runpod.io:/tmp/
#
#        # Then SSH in and run it
#        ssh -p <PORT> root@ssh.runpod.io
#        python3 /tmp/build_kg.py
#
#   Common flags:
#
#     --dest /workspace       volume mount path (default)
#     --genres "philosophy english-literature russian-literature"
#     --metabo-only           skip Gutenberg, only build MetaboKG
#     --gutenberg-only        skip MetaboKG, only build Gutenberg
#     --skip-download         skip corpus download if already present
#     --rebuild-only          skip venv/clone/install; just rebuild indices
#
#   Run  python3 /tmp/build_kg.py --help  for the full option list.
#
# Which workflow should I use?
# ─────────────────────────────
#   ┌─────────────────────────────────┬──────────────┬──────────────┐
#   │ Scenario                        │ Workflow A   │ Workflow B   │
#   ├─────────────────────────────────┼──────────────┼──────────────┤
#   │ Quick test / prototype          │ ✓ preferred  │              │
#   │ Local indices already built     │ ✓ preferred  │              │
#   │ Full Gutenberg catalog          │              │ ✓ preferred  │
#   │ New region / no local machine   │              │ ✓ preferred  │
#   │ Automated CI rebuild            │              │ ✓ preferred  │
#   └─────────────────────────────────┴──────────────┴──────────────┘
#
# After either workflow, terminate the temporary pod.
# The Network Volume persists and is ready to attach to the
# KGRAG serverless endpoint.

echo "Run  ./push_indices.sh          for Workflow A (push local indices)."
echo "Run  python3 /tmp/build_kg.py   inside a RunPod pod for Workflow B (build from scratch)."
