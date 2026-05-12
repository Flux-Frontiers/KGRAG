#!/usr/bin/env bash
# build_image.sh — build local package wheels then build the Docker image.
#
# Usage:
#   ./build_image.sh [IMAGE_TAG]
#
# Default IMAGE_TAG: kgrag-worker:latest
#
# Prereqs: pip, docker, the three repos checked out at the expected paths.

set -euo pipefail

IMAGE="${1:-kgrag-worker:latest}"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
WHEEL_DIR="${SCRIPT_DIR}/wheels"

# Repo paths — adjust if your layout differs
KGRAG_REPO="$(dirname "${SCRIPT_DIR}")"                  # ../kgrag  (this repo)
GUTENBERG_REPO="$(dirname "${KGRAG_REPO}")/gutenberg_kg"
METABO_REPO="$(dirname "${KGRAG_REPO}")/Metabo_kg"

echo "==> Building local wheels into ${WHEEL_DIR}/"
rm -rf "${WHEEL_DIR}"
mkdir -p "${WHEEL_DIR}"

for repo in "${KGRAG_REPO}" "${GUTENBERG_REPO}" "${METABO_REPO}"; do
    if [[ ! -d "${repo}" ]]; then
        echo "ERROR: repo not found at ${repo}" >&2
        exit 1
    fi
    echo "  building wheel for ${repo##*/} …"
    pip wheel --no-deps -w "${WHEEL_DIR}" "${repo}" -q
done

echo "==> Wheels built:"
ls -lh "${WHEEL_DIR}"/*.whl

echo "==> Building Docker image: ${IMAGE}"
docker build -t "${IMAGE}" "${SCRIPT_DIR}"

echo ""
echo "Done. Push with:"
echo "  docker tag ${IMAGE} <your-registry>/${IMAGE}"
echo "  docker push <your-registry>/${IMAGE}"
