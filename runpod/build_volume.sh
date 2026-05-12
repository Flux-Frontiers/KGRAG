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
#   2. Launch a temporary CPU pod with the volume attached at /mnt/kgdata.
#      Any Ubuntu 22.04 image works — no GPU needed for index building.
#   3. SSH into the pod and run:
#
#        # Upload setup_volume.sh to the pod first
#        scp -P <PORT> setup_volume.sh root@ssh.runpod.io:/tmp/
#
#        # Then SSH in and run it
#        ssh -p <PORT> root@ssh.runpod.io
#        bash /tmp/setup_volume.sh
#
#   Optionally override these env vars before running setup_volume.sh:
#
#     DEST=/mnt/kgdata          # volume mount path
#     GENRES="philosophy english-literature russian-literature"
#     METABO_ONLY=1             # skip Gutenberg, only build MetaboKG
#     GUTENBERG_ONLY=1          # skip MetaboKG, only build Gutenberg
#     SKIP_DOWNLOAD=1           # skip corpus download if already present
#     GITHUB_TOKEN=ghp_...      # only needed if metabo_kg repo is private
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

echo "Run  ./push_indices.sh   for Workflow A (push local indices)."
echo "Run  ./setup_volume.sh   inside a RunPod pod for Workflow B (build from scratch)."
