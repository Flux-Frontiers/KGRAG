#!/usr/bin/env bash
# ingest.sh — Build a DocKG for each Gutenberg genre directory and register
# them all under the "gutenberg" corpus.
#
# Usage:
#   cd /path/to/KGRAG
#   bash books/ingest.sh [--wipe]
#
# Prerequisites:
#   poetry install          (done once)
#   kgrag corpus create gutenberg --desc "Project Gutenberg library"
#
# Each genre directory becomes one DocKG named gutenberg-<genre>.
# The .dockg/ subdirectory (SQLite + LanceDB) is created inside that dir.

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
WIPE="${1:-}"

GENRES=(fiction poetry history science philosophy)
CORPUS="gutenberg"

echo "=== KGRAG Gutenberg Ingest ==="
echo "Repo root : $REPO_ROOT"
echo "Corpus    : $CORPUS"
echo ""

# Ensure corpus exists (idempotent — create only if missing)
if ! kgrag corpus info "$CORPUS" &>/dev/null; then
    echo "Creating corpus '$CORPUS'..."
    kgrag corpus create "$CORPUS" --desc "Project Gutenberg library"
fi

for GENRE in "${GENRES[@]}"; do
    DIR="$SCRIPT_DIR/$GENRE"
    NAME="gutenberg-$GENRE"

    # Count non-README files
    BOOK_COUNT=$(find "$DIR" -maxdepth 1 -type f ! -name "README.md" | wc -l)

    if [ "$BOOK_COUNT" -eq 0 ]; then
        echo "⚠  $GENRE — no books found, skipping (add .txt files to $DIR)"
        continue
    fi

    echo "--- $GENRE ($BOOK_COUNT book file(s)) ---"

    INIT_ARGS=(kgrag init "$DIR" --layer doc --name "$NAME" --corpus "$CORPUS")
    if [ "$WIPE" = "--wipe" ]; then
        INIT_ARGS+=(--wipe)
    fi

    "${INIT_ARGS[@]}"
    echo ""
done

echo "=== Done ==="
echo "Query your library:"
echo "  kgrag corpus query gutenberg \"your question here\""
echo "  kgrag synthesize \"your question here\" --corpus gutenberg"
