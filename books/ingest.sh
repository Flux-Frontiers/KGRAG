#!/usr/bin/env bash
# ingest.sh — Stage gutenberg_kg books by genre, build per-genre DocKGs,
# and register them all under a "gutenberg" corpus in KGRAG.
#
# Usage:
#   cd /path/to/KGRAG
#   bash books/ingest.sh /path/to/gutenberg_kg [--wipe]
#
# Prerequisites:
#   poetry install          (run once)
#   kgrag corpus create gutenberg --desc "Project Gutenberg library"
#
# What it does:
#   For each genre directory under books/ it:
#     1. Copies the relevant book directories from gutenberg_kg into the
#        genre dir (preserving <Title>/<slug>.md + <Title>/reference.md)
#     2. Runs `dockg build` → creates books/<genre>/.dockg/
#     3. Registers the resulting KG as "gutenberg-<genre>"
#     4. Adds it to the "gutenberg" corpus
#
# Each genre dir keeps a .book_manifest file listing its books so re-runs
# only copy books that are missing (add --wipe to force a full rebuild).

set -euo pipefail

BOOKS_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$BOOKS_DIR/.." && pwd)"
GUTENBERG_PATH="${1:-}"
WIPE="${2:-}"

if [[ -z "$GUTENBERG_PATH" ]]; then
    echo "Usage: bash books/ingest.sh /path/to/gutenberg_kg [--wipe]"
    echo ""
    echo "Clone the source repo first:"
    echo "  git clone https://github.com/Flux-Frontiers/gutenberg_kg.git /path/to/gutenberg_kg"
    exit 1
fi

if [[ ! -d "$GUTENBERG_PATH" ]]; then
    echo "ERROR: gutenberg_kg path not found: $GUTENBERG_PATH"
    exit 1
fi

CORPUS="gutenberg"

# ---------------------------------------------------------------------------
# Genre → book directory name mapping
# Book directory names must match exactly what is in gutenberg_kg/
# ---------------------------------------------------------------------------

declare -A GENRE_BOOKS

GENRE_BOOKS["ancient-classical"]="
The Odyssey
The Iliad
The Aeneid
The Republic
The Divine Comedy
Oedipus King of Thebes
Meditations
The Bible
"

GENRE_BOOKS["shakespeare"]="
Hamlet
Romeo and Juliet
Macbeth
A Midsummer Nights Dream
"

GENRE_BOOKS["english-literature"]="
Jane Eyre
Wuthering Heights
Great Expectations
Middlemarch
Sense and Sensibility
Emma
Pride and Prejudice
Frankenstein
Dracula
Heart of Darkness
The Time Machine
The War of the Worlds
Treasure Island
Robinson Crusoe
Gullivers Travels
The Strange Case of Dr Jekyll and Mr Hyde
The Adventures of Sherlock Holmes
The Picture of Dorian Gray
Alices Adventures in Wonderland
A Tale of Two Cities
A Modest Proposal
Grimms Fairy Tales
"

GENRE_BOOKS["american-literature"]="
Moby Dick
The Scarlet Letter
Walden
Leaves of Grass
Adventures of Huckleberry Finn
The Call of the Wild
The Red Badge of Courage
Uncle Toms Cabin
The Yellow Wallpaper
"

GENRE_BOOKS["french-literature"]="
Les Miserables
The Count of Monte Cristo
The Three Musketeers
Madame Bovary
Twenty Thousand Leagues Under the Sea
Candide
"

GENRE_BOOKS["russian-literature"]="
Crime and Punishment
The Brothers Karamazov
Anna Karenina
War and Peace
The Idiot
Dead Souls
"

GENRE_BOOKS["philosophy"]="
On the Origin of Species
Common Sense
Leviathan
Thus Spake Zarathustra
Beyond Good and Evil
The Wealth of Nations
The Federalist Papers
The Prince
"

GENRE_BOOKS["spanish"]="
Don Quixote
"

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

log_info()  { echo "  [·] $*"; }
log_ok()    { echo "  [✓] $*"; }
log_warn()  { echo "  [⚠] $*"; }
log_error() { echo "  [✗] $*" >&2; }

stage_books() {
    local genre_dir="$1"
    local books="$2"
    local staged=0
    local missing=0

    while IFS= read -r book; do
        book="$(echo "$book" | xargs)"   # trim whitespace
        [[ -z "$book" ]] && continue

        src="$GUTENBERG_PATH/$book"
        dst="$genre_dir/$book"

        if [[ ! -d "$src" ]]; then
            log_warn "Book not found in gutenberg_kg: '$book' — skipping"
            ((missing++)) || true
            continue
        fi

        if [[ "$WIPE" == "--wipe" ]] && [[ -d "$dst" ]]; then
            rm -rf "$dst"
        fi

        if [[ ! -d "$dst" ]]; then
            cp -r "$src" "$dst"
            log_info "Staged: $book"
            ((staged++)) || true
        else
            log_info "Already staged: $book"
        fi
    done <<< "$books"

    echo "$staged staged, $missing missing"
}

# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

echo "=== KGRAG Gutenberg Ingest ==="
echo "Gutenberg source : $GUTENBERG_PATH"
echo "KGRAG repo root  : $REPO_ROOT"
echo "Corpus           : $CORPUS"
[[ "$WIPE" == "--wipe" ]] && echo "Mode             : WIPE + rebuild"
echo ""

# Ensure the corpus exists
if ! kgrag corpus info "$CORPUS" &>/dev/null 2>&1; then
    echo "Creating corpus '$CORPUS'..."
    kgrag corpus create "$CORPUS" --desc "Project Gutenberg library"
fi

GENRES=(
    ancient-classical
    shakespeare
    english-literature
    american-literature
    french-literature
    russian-literature
    philosophy
    spanish
)

declare -A RESULTS

for GENRE in "${GENRES[@]}"; do
    GENRE_DIR="$BOOKS_DIR/$GENRE"
    KG_NAME="gutenberg-$GENRE"

    echo "━━━ $GENRE ━━━"

    # Stage books from gutenberg_kg
    books="${GENRE_BOOKS[$GENRE]}"
    result=$(stage_books "$GENRE_DIR" "$books")
    echo "  Books: $result"

    # Count .md files (excluding README.md)
    MD_COUNT=$(find "$GENRE_DIR" -name "*.md" ! -name "README.md" | wc -l)
    if [[ "$MD_COUNT" -eq 0 ]]; then
        log_warn "No .md files after staging — skipping build"
        RESULTS[$GENRE]="skipped (no books)"
        echo ""
        continue
    fi

    # Check if dockg is available
    if ! command -v dockg &>/dev/null; then
        log_warn "dockg not found on PATH — skipping build"
        RESULTS[$GENRE]="skipped (dockg missing)"
        echo ""
        continue
    fi

    # Wipe existing .dockg if requested
    if [[ "$WIPE" == "--wipe" ]] && [[ -d "$GENRE_DIR/.dockg" ]]; then
        rm -rf "$GENRE_DIR/.dockg"
        log_info "Wiped existing .dockg"
    fi

    # Build DocKG
    log_info "Building DocKG ($MD_COUNT .md files)..."
    if dockg build --repo "$GENRE_DIR" 2>&1 | grep -v "^$"; then
        log_ok "DocKG built"
    else
        log_error "dockg build failed"
        RESULTS[$GENRE]="build failed"
        echo ""
        continue
    fi

    # Register with kgrag
    SQLITE="$GENRE_DIR/.dockg/graph.sqlite"
    LANCEDB="$GENRE_DIR/.dockg/lancedb"

    REGISTER_ARGS=(kgrag register "$KG_NAME" doc "$GENRE_DIR")
    [[ -f "$SQLITE" ]]  && REGISTER_ARGS+=(--sqlite  "$SQLITE")
    [[ -d "$LANCEDB" ]] && REGISTER_ARGS+=(--lancedb "$LANCEDB")

    if "${REGISTER_ARGS[@]}" 2>&1; then
        log_ok "Registered: $KG_NAME"
    else
        log_warn "kgrag register failed (may already be registered)"
    fi

    # Add to corpus
    if kgrag corpus add "$CORPUS" "$KG_NAME" 2>&1; then
        log_ok "Added to corpus: $CORPUS"
    else
        log_warn "corpus add failed (may already be a member)"
    fi

    RESULTS[$GENRE]="ok"
    echo ""
done

# ---------------------------------------------------------------------------
# Summary
# ---------------------------------------------------------------------------

echo "=== Summary ==="
for GENRE in "${GENRES[@]}"; do
    status="${RESULTS[$GENRE]:-unknown}"
    if [[ "$status" == "ok" ]]; then
        echo "  ✓ gutenberg-$GENRE"
    else
        echo "  ⚠ gutenberg-$GENRE: $status"
    fi
done

echo ""
echo "Query your library:"
echo "  kgrag corpus query gutenberg \"your question here\""
echo "  kgrag synthesize \"your question here\" --corpus gutenberg"
echo "  kgrag viz   # then open http://localhost:8501"
