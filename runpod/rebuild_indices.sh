#!/usr/bin/env bash
# rebuild_indices.sh
#
# Rebuild KG indices from an already-populated workspace.
# Assumes setup_volume.sh has been run at least once (repos cloned, venv built,
# corpus downloaded).  Skips all of that and goes straight to index building.
#
# Usage (inside a RunPod pod):
#   bash /tmp/rebuild_indices.sh [OPTIONS]
#
# Options (env vars)
# ------------------
#   DEST             Volume mount path. Default: /workspace
#   GENRES           Space-separated Gutenberg genres. Default: all present
#   METABO_ONLY      Set to 1 to skip Gutenberg.
#   GUTENBERG_ONLY   Set to 1 to skip MetaboKG.

set -euo pipefail

DEST="${DEST:-/workspace}"
WORK_DIR="${DEST}/kgrag_build"
VENV="${WORK_DIR}/venv"
METABO_ONLY="${METABO_ONLY:-0}"
GUTENBERG_ONLY="${GUTENBERG_ONLY:-0}"

export TMPDIR="${DEST}/.tmp"
export PIP_CACHE_DIR="${DEST}/.pip_cache"
mkdir -p "${TMPDIR}" "${PIP_CACHE_DIR}"

if [[ ! -x "${VENV}/bin/pip" ]]; then
    echo "ERROR: venv not found at ${VENV} — run setup_volume.sh first."
    exit 1
fi

GUTENKG="${VENV}/bin/gutenkg"
METABOKG="${VENV}/bin/metabokg"

# ---------------------------------------------------------------------------
# MetaboKG
# ---------------------------------------------------------------------------

if [[ "${GUTENBERG_ONLY}" != "1" ]]; then
    echo "==> Rebuilding MetaboKG indices …"
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
        "${METABOKG}" build \
            --data "${DATA_DIR}" \
            --db "${SQLITE_PATH}" \
            --lancedb "${LANCEDB_PATH}" \
            2>&1 | sed 's/^/    /'
        dest_dir="${DEST}/metabo_kg/data/${dataset}/.metabokg"
        mkdir -p "${dest_dir}"
        rsync -a "${DATA_DIR}/.metabokg/" "${dest_dir}/"
        echo "    Synced → ${dest_dir}  ($(du -sh ${dest_dir} | cut -f1))"
    done
fi

# ---------------------------------------------------------------------------
# GutenbergKG
# ---------------------------------------------------------------------------

if [[ "${METABO_ONLY}" != "1" ]]; then
    echo ""
    echo "==> Rebuilding GutenbergKG indices …"
    GUTENBERG_SRC="${WORK_DIR}/gutenberg_kg"

    # Determine genres: use GENRES env var, or auto-detect from corpus/
    if [[ -n "${GENRES:-}" ]]; then
        genre_list="${GENRES}"
    else
        genre_list=$(ls "${GUTENBERG_SRC}/corpus/" | grep -v authors | grep -v genres.json | tr '\n' ' ')
    fi
    echo "    Genres: ${genre_list}"

    for genre in ${genre_list}; do
        GENRE_DIR="${GUTENBERG_SRC}/corpus/${genre}"
        if [[ ! -d "${GENRE_DIR}" ]]; then
            echo "    WARNING: corpus/${genre} not found, skipping"
            continue
        fi
        book_count=$(ls "${GENRE_DIR}" 2>/dev/null | wc -l)
        echo ""
        echo "    [${genre}] ${book_count} books — ingesting …"
        (cd "${GUTENBERG_SRC}" && "${GUTENKG}" ingest --genre "${genre}" --force-build) \
            2>&1 | sed 's/^/    /'
    done

    echo ""
    echo "    Syncing to volume …"
    GUTENBERG_DEST="${DEST}/gutenberg_kg"
    mkdir -p "${GUTENBERG_DEST}"
    rsync -a "${GUTENBERG_SRC}/.dockg/" "${GUTENBERG_DEST}/.dockg/"
    echo "    Done: $(du -sh ${GUTENBERG_DEST}/.dockg | cut -f1)"
fi

# ---------------------------------------------------------------------------
# Summary
# ---------------------------------------------------------------------------

echo ""
echo "============================================================"
echo "  Rebuilt indices:"
du -sh "${DEST}"/gutenberg_kg/.dockg \
       "${DEST}"/metabo_kg/data/*/.metabokg 2>/dev/null || true
echo "============================================================"
