#!/usr/bin/env bash
# apply-doc-kg-patches.sh
#
# Apply pending KGRAG patches to a local doc_kg checkout and push.
#
# Usage:
#   ./apply-doc-kg-patches.sh /path/to/doc_kg
#
# The doc_kg repo must already be cloned and have a push-capable remote.

set -euo pipefail

DOC_KG_REPO="${1:-}"

if [[ -z "$DOC_KG_REPO" ]]; then
  echo "Usage: $0 /path/to/doc_kg" >&2
  exit 1
fi

if [[ ! -d "$DOC_KG_REPO/.git" ]]; then
  echo "Error: '$DOC_KG_REPO' is not a git repository." >&2
  exit 1
fi

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PATCH_DIR="$SCRIPT_DIR/patches/doc_kg"

if [[ ! -d "$PATCH_DIR" ]]; then
  echo "Error: patch directory '$PATCH_DIR' not found." >&2
  exit 1
fi

PATCHES=("$PATCH_DIR"/*.patch)
if [[ ${#PATCHES[@]} -eq 0 ]]; then
  echo "No patches found in $PATCH_DIR" >&2
  exit 1
fi

echo "Applying ${#PATCHES[@]} patch(es) to $DOC_KG_REPO ..."
cd "$DOC_KG_REPO"

for patch in "${PATCHES[@]}"; do
  echo "  -> $(basename "$patch")"
  git am < "$patch"
done

echo "Pushing to origin ..."
git push -u origin "$(git rev-parse --abbrev-ref HEAD)"

echo "Done."
