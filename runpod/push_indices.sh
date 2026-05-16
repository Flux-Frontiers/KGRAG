#!/usr/bin/env bash
# push_indices.sh
#
# Push pre-built KG indices from your local machine to a RunPod Network Volume
# via SSH.  Total upload is ~130 MB (just the indices, not the raw text corpus).
#
# This is the fastest way to get the volume populated: build locally once,
# push the resulting .dockg / .metabokg directories.  The raw text corpus
# stays on your machine.
#
# Prerequisites
# -------------
#   1. A RunPod Network Volume exists (≥ 10 GB is plenty for current indices).
#   2. A temporary RunPod pod has the volume attached and is running.
#      ("Mount path" in RunPod UI should be /mnt/kgdata)
#   3. SSH key added to RunPod account (Settings → SSH Public Keys).
#
# Usage
# -----
#   # Basic (prompts for connection details)
#   ./push_indices.sh
#
#   # Non-interactive
#   POD_HOST=ssh.runpod.io POD_PORT=12345 ./push_indices.sh
#
# The pod's SSH address is shown in the RunPod dashboard:
#   Pods → <your pod> → Connect → "SSH over exposed TCP"
#   It looks like:  ssh root@ssh.runpod.io -p 12345
#                                  ──────── host  ──── port

set -euo pipefail

# ---------------------------------------------------------------------------
# Config — override via env vars or interactive prompts
# ---------------------------------------------------------------------------

POD_HOST="${POD_HOST:-}"
POD_PORT="${POD_PORT:-}"
DEST_BASE="${DEST_BASE:-/workspace}"
SSH_KEY="${SSH_KEY:-${HOME}/.ssh/id_ed25519}"

if [[ -z "${POD_HOST}" ]]; then
    read -rp "Pod SSH host (e.g. ssh.runpod.io): " POD_HOST
fi
if [[ -z "${POD_PORT}" ]]; then
    read -rp "Pod SSH port (e.g. 12345): " POD_PORT
fi

SSH_TARGET="root@${POD_HOST}"
SSH_OPTS="-p ${POD_PORT} -i ${SSH_KEY} -o StrictHostKeyChecking=no"
RSYNC_SSH="ssh ${SSH_OPTS}"

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
KGRAG_REPO="$(dirname "${SCRIPT_DIR}")"
GUTENBERG_REPO="$(dirname "${KGRAG_REPO}")/gutenberg_kg"
METABO_REPO="$(dirname "${KGRAG_REPO}")/Metabo_kg"

echo ""
echo "==> Target: ${SSH_TARGET} -p ${POD_PORT} : ${DEST_BASE}"
echo ""

# ---------------------------------------------------------------------------
# Verify local indices exist
# ---------------------------------------------------------------------------

missing=0
for path in \
    "${GUTENBERG_REPO}/.dockg/graph.sqlite" \
    "${METABO_REPO}/data/hsa_pathways/.metabokg/hsa.sqlite"; do
    if [[ ! -f "${path}" ]]; then
        echo "ERROR: missing local index: ${path}"
        echo "       Run the build pipeline locally first (dockg build / metabokg build)"
        missing=1
    fi
done
[[ "${missing}" -eq 1 ]] && exit 1

# ---------------------------------------------------------------------------
# Create remote directory structure
# ---------------------------------------------------------------------------

ssh ${SSH_OPTS} "${SSH_TARGET}" \
    "mkdir -p \
        ${DEST_BASE}/gutenberg_kg/.dockg \
        ${DEST_BASE}/metabo_kg/data/hsa_pathways/.metabokg \
        ${DEST_BASE}/metabo_kg/data/cge_pathways/.metabokg \
        ${DEST_BASE}/metabo_kg/data/icho_model/.metabokg"

# ---------------------------------------------------------------------------
# Push indices
# ---------------------------------------------------------------------------

echo "--- GutenbergKG .dockg/ ---"
rsync -avz --progress -e "${RSYNC_SSH}" \
    "${GUTENBERG_REPO}/.dockg/" \
    "${SSH_TARGET}:${DEST_BASE}/gutenberg_kg/.dockg/"

echo ""
echo "--- MetaboKG hsa_pathways ---"
rsync -avz --progress -e "${RSYNC_SSH}" \
    "${METABO_REPO}/data/hsa_pathways/.metabokg/" \
    "${SSH_TARGET}:${DEST_BASE}/metabo_kg/data/hsa_pathways/.metabokg/"

echo ""
echo "--- MetaboKG cge_pathways ---"
rsync -avz --progress -e "${RSYNC_SSH}" \
    "${METABO_REPO}/data/cge_pathways/.metabokg/" \
    "${SSH_TARGET}:${DEST_BASE}/metabo_kg/data/cge_pathways/.metabokg/"

echo ""
echo "--- MetaboKG icho_model ---"
rsync -avz --progress -e "${RSYNC_SSH}" \
    "${METABO_REPO}/data/icho_model/.metabokg/" \
    "${SSH_TARGET}:${DEST_BASE}/metabo_kg/data/icho_model/.metabokg/"

# ---------------------------------------------------------------------------
# Verify
# ---------------------------------------------------------------------------

echo ""
echo "==> Remote volume contents:"
ssh "${SSH_TARGET}" -p "${POD_PORT}" \
    "du -sh \
        ${DEST_BASE}/gutenberg_kg/.dockg \
        ${DEST_BASE}/metabo_kg/data/hsa_pathways/.metabokg \
        ${DEST_BASE}/metabo_kg/data/cge_pathways/.metabokg \
        ${DEST_BASE}/metabo_kg/data/icho_model/.metabokg 2>/dev/null"

echo ""
echo "Done. Detach or terminate the temporary pod."
echo "The Network Volume now has all indices — attach it to the KGRAG endpoint."
