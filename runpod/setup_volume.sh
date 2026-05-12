#!/usr/bin/env bash
# setup_volume.sh
#
# Run INSIDE a RunPod pod (with the Network Volume attached) to build all KG
# indices from scratch.  Clones the public repos, downloads the Gutenberg
# corpus for the requested genres, ingests everything, and leaves the built
# indices under /mnt/kgdata ready for the KGRAG serverless worker.
#
# Use this when:
#   • You want a fresh build from the full Gutenberg catalog (not just local)
#   • You don't have local indices to push (or they are stale)
#   • You're setting up a new volume region and want to rebuild there
#
# Usage (run inside the pod after SSH-ing in)
# -------------------------------------------
#   bash setup_volume.sh [OPTIONS]
#
# Options (env vars)
# ------------------
#   DEST          Mount path of the Network Volume.  Default: /mnt/kgdata
#   GENRES        Space-separated Gutenberg genres to ingest.
#                 Default: "philosophy english-literature russian-literature"
#   METABO_ONLY   Set to 1 to skip Gutenberg and only build MetaboKG.
#   GUTENBERG_ONLY Set to 1 to skip MetaboKG.
#   SKIP_DOWNLOAD Set to 1 to skip re-downloading if corpus already exists.
#
# Recommended pod spec (RunPod)
# -----------------------------
#   Template: runpod/pytorch:2.4.0-py3.11-cuda12.4.1-devel-ubuntu22.04
#   OR any Ubuntu 22.04 image — GPU is NOT required for building indices.
#   CPU pod: 8 vCPU, 32 GB RAM  (~$0.20/hr)
#   Storage: 100 GB container disk (corpus + build workspace)
#   Volume:  attach at /mnt/kgdata

set -euo pipefail

DEST="${DEST:-/mnt/kgdata}"
GENRES="${GENRES:-philosophy english-literature russian-literature}"
METABO_ONLY="${METABO_ONLY:-0}"
GUTENBERG_ONLY="${GUTENBERG_ONLY:-0}"
SKIP_DOWNLOAD="${SKIP_DOWNLOAD:-0}"
WORK_DIR="${DEST}/kgrag_build"

# Redirect all temp/cache I/O to the volume immediately —
# the container root fs is typically only 5 GB.
mkdir -p "${DEST}/.tmp" "${DEST}/.pip_cache" "${DEST}/.hf_cache"
export TMPDIR="${DEST}/.tmp"
export PIP_CACHE_DIR="${DEST}/.pip_cache"
export PIP_TMPDIR="${DEST}/.tmp"

# Force HuggingFace online mode and cache models on the volume (not the 5GB root fs)
export HF_HOME="${DEST}/.hf_cache"
export HF_HUB_OFFLINE=0
export TRANSFORMERS_OFFLINE=0
export HF_DATASETS_OFFLINE=0

echo "============================================================"
echo "  KGRAG Volume Setup"
echo "  Destination : ${DEST}"
if [[ "${METABO_ONLY}" != "1" ]]; then
    echo "  Genres      : ${GENRES}"
fi
echo "============================================================"
echo ""

# ---------------------------------------------------------------------------
# System dependencies + Python 3.12
# ---------------------------------------------------------------------------

echo "==> Installing system dependencies …"
apt-get update -qq
apt-get install -y --no-install-recommends \
    python3.12 python3.12-venv python3-pip \
    git rsync libgomp1 libglib2.0-0 curl \
    > /dev/null
echo "    python3.12 ready"

# ---------------------------------------------------------------------------
# Python virtual environment
# ---------------------------------------------------------------------------

VENV="${WORK_DIR}/venv"
mkdir -p "${WORK_DIR}"

if [[ ! -x "${VENV}/bin/pip" ]]; then
    echo "==> Creating venv at ${VENV} …"
    rm -rf "${VENV}"
    python3.12 -m venv "${VENV}"
fi
PY="${VENV}/bin/python"
PIP="${VENV}/bin/pip"
# (pip cache + TMPDIR already set at top of script)
${PIP} install --quiet --upgrade pip

# ---------------------------------------------------------------------------
# Clone and install repos
# ---------------------------------------------------------------------------

echo "==> Cloning repos …"
cd "${WORK_DIR}"
export GIT_TERMINAL_PROMPT=0
git config --global credential.helper ""

clone_or_pull() {
    local repo_url="$1"
    local dir="$2"
    if [[ -d "${dir}/.git" ]]; then
        echo "    ${dir}: pulling latest"
        git -C "${dir}" pull --quiet
    else
        echo "    cloning ${repo_url}"
        git clone --quiet "${repo_url}" "${dir}"
    fi
}

clone_or_pull "https://github.com/Flux-Frontiers/KGRAG.git"        kgrag
clone_or_pull "https://github.com/Flux-Frontiers/gutenberg_kg.git" gutenberg_kg

# metabo_kg: install from the kgrag kgdeps group (references the git URL)
# If the repo is private, supply a GITHUB_TOKEN env var.
if [[ "${GUTENBERG_ONLY}" != "1" ]]; then
    METABO_URL="${METABO_REPO_URL:-https://github.com/Flux-Frontiers/metabo_kg.git}"
    if [[ -n "${GITHUB_TOKEN:-}" ]]; then
        METABO_URL="${METABO_URL/https:\/\//https:\/\/${GITHUB_TOKEN}@}"
    fi
    clone_or_pull "${METABO_URL}" Metabo_kg
fi

echo "==> Installing Python packages …"
${PIP} install --quiet -e "${WORK_DIR}/kgrag[kg]"
${PIP} install --quiet -e "${WORK_DIR}/gutenberg_kg"
if [[ "${GUTENBERG_ONLY}" != "1" && -d "${WORK_DIR}/Metabo_kg" ]]; then
    ${PIP} install --quiet -e "${WORK_DIR}/Metabo_kg"
fi

GUTENKG="${VENV}/bin/gutenkg"
DOCKG="${VENV}/bin/dockg"

# ---------------------------------------------------------------------------
# Build MetaboKG indices
# ---------------------------------------------------------------------------

if [[ "${GUTENBERG_ONLY}" != "1" ]]; then
    echo ""
    echo "==> Building MetaboKG indices …"
    METABO_SRC="${WORK_DIR}/Metabo_kg"

    declare -A DATASET_DB=(
        [hsa_pathways]="hsa.sqlite"
        [cge_pathways]="cge.sqlite"
        [icho_model]="icho.sqlite"
    )

    for dataset in "${!DATASET_DB[@]}"; do
        DATA_DIR="${METABO_SRC}/data/${dataset}"
        if [[ ! -d "${DATA_DIR}" ]]; then
            echo "    WARNING: ${DATA_DIR} not found, skipping"
            continue
        fi

        echo "    Building ${dataset} …"
        SQLITE_PATH="${DATA_DIR}/.metabokg/${DATASET_DB[$dataset]}"
        LANCEDB_PATH="${DATA_DIR}/.metabokg/lancedb"
        mkdir -p "${DATA_DIR}/.metabokg"
        "${VENV}/bin/metabokg" build \
            --data "${DATA_DIR}" \
            --db "${SQLITE_PATH}" \
            --lancedb "${LANCEDB_PATH}" \
            2>&1 | sed 's/^/    /'

        # Sync to volume
        dest_dir="${DEST}/metabo_kg/data/${dataset}/.metabokg"
        mkdir -p "${dest_dir}"
        rsync -a "${DATA_DIR}/.metabokg/" "${dest_dir}/"
        echo "    Synced to ${dest_dir}"
        du -sh "${dest_dir}"
    done
fi

# ---------------------------------------------------------------------------
# Build GutenbergKG indices
# ---------------------------------------------------------------------------

if [[ "${METABO_ONLY}" != "1" ]]; then
    echo ""
    echo "==> Building GutenbergKG indices …"
    GUTENBERG_SRC="${WORK_DIR}/gutenberg_kg"

    # Download books for each genre into the repo's corpus/ directory,
    # then ingest (builds per-book .dockg indices + the top-level .dockg/).
    for genre in ${GENRES}; do
        echo ""
        echo "  Genre: ${genre}"

        if [[ "${SKIP_DOWNLOAD}" != "1" ]]; then
            echo "    Downloading catalog …"
            # The gutenkg fetch-genre command downloads books for a genre
            # using the Gutenberg catalog.  It places books under corpus/<genre>/.
            (cd "${GUTENBERG_SRC}" && \
                "${GUTENKG}" download fetch-genre "${genre}" --max-results 200 --yes
            ) 2>&1 | sed 's/^/    /'
        fi

        echo "    Ingesting (building DocKG) …"
        (cd "${GUTENBERG_SRC}" && \
            "${GUTENKG}" ingest --genre "${genre}" --force-build
        ) 2>&1 | sed 's/^/    /'
    done

    # The top-level .dockg is built by gutenkg ingest across all genres.
    # Sync the entire .dockg tree to the volume.
    echo ""
    echo "  Syncing GutenbergKG indices to volume …"
    GUTENBERG_DEST="${DEST}/gutenberg_kg"
    mkdir -p "${GUTENBERG_DEST}"
    rsync -a "${GUTENBERG_SRC}/.dockg/" "${GUTENBERG_DEST}/.dockg/"
    echo "  Done:"
    du -sh "${GUTENBERG_DEST}/.dockg"
fi

# ---------------------------------------------------------------------------
# Final summary
# ---------------------------------------------------------------------------

echo ""
echo "============================================================"
echo "  Volume contents:"
du -sh "${DEST}"/*/.dockg "${DEST}"/metabo_kg/data/*/.metabokg 2>/dev/null || true
echo ""
echo "  All done. Terminate this pod — the Network Volume is ready."
echo "  Attach it to the KGRAG serverless endpoint at: ${DEST}"
echo "============================================================"
