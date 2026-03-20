#!/usr/bin/env bash
# apply-patches.sh — Apply all KGRAG patches to vendored dependencies.
#
# Usage:
#   ./scripts/apply-patches.sh              # Apply all patches
#   ./scripts/apply-patches.sh --dry-run    # Show what would be applied
#   ./scripts/apply-patches.sh --revert     # Revert all patches
#
# This script should be run AFTER `poetry install` to customize
# dependencies in `.venv/src/`.

set -e

cd "$(dirname "$0")/.." || exit 1
REPO_ROOT=$(pwd)
PATCHES_DIR="$REPO_ROOT/patches"

DRY_RUN=0
REVERT=0

# Parse arguments
while [[ $# -gt 0 ]]; do
  case $1 in
    --dry-run)
      DRY_RUN=1
      shift
      ;;
    --revert)
      REVERT=1
      shift
      ;;
    *)
      echo "Unknown argument: $1"
      exit 1
      ;;
  esac
done

if [ ! -d "$PATCHES_DIR" ]; then
  echo "ERROR: patches/ directory not found at $PATCHES_DIR"
  exit 1
fi

# Find all patches
PATCHES=$(find "$PATCHES_DIR" -name "*.patch" -type f | sort)

if [ -z "$PATCHES" ]; then
  echo "No patches found in $PATCHES_DIR"
  exit 0
fi

PATCH_COUNT=$(echo "$PATCHES" | wc -l)
echo "Found $PATCH_COUNT patch(es)."
echo ""

# Apply or revert patches
FAILED=0
SUCCEEDED=0

for patch_file in $PATCHES; do
  patch_name=$(basename "$patch_file")
  patch_dir=$(basename "$(dirname "$patch_file")")

  if [ $DRY_RUN -eq 1 ]; then
    echo "=== DRY RUN: $patch_dir/$patch_name ==="
    if patch -p0 --dry-run < "$patch_file" > /dev/null 2>&1; then
      echo "✓ Would apply successfully"
      SUCCEEDED=$((SUCCEEDED + 1))
    else
      echo "✗ Would FAIL to apply"
      FAILED=$((FAILED + 1))
    fi
  elif [ $REVERT -eq 1 ]; then
    echo "=== REVERT: $patch_dir/$patch_name ==="
    if patch -p0 -R < "$patch_file" > /dev/null 2>&1; then
      echo "✓ Reverted successfully"
      SUCCEEDED=$((SUCCEEDED + 1))
    else
      echo "✗ FAILED to revert"
      FAILED=$((FAILED + 1))
    fi
  else
    echo "=== APPLY: $patch_dir/$patch_name ==="
    if patch -p0 < "$patch_file" > /dev/null 2>&1; then
      echo "✓ Applied successfully"
      SUCCEEDED=$((SUCCEEDED + 1))
    else
      echo "✗ FAILED to apply"
      FAILED=$((FAILED + 1))
    fi
  fi

  echo ""
done

# Summary
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
if [ $DRY_RUN -eq 1 ]; then
  echo "DRY RUN SUMMARY"
elif [ $REVERT -eq 1 ]; then
  echo "REVERT SUMMARY"
else
  echo "APPLICATION SUMMARY"
fi
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "✓ Succeeded: $SUCCEEDED"
echo "✗ Failed:    $FAILED"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

if [ $FAILED -gt 0 ]; then
  exit 1
fi

exit 0
