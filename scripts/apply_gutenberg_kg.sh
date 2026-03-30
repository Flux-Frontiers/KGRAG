#!/usr/bin/env bash
# apply_gutenberg_kg.sh — Apply gutenberg_kg reorganization to a local clone.
#
# Usage (run from the root of your local gutenberg_kg clone):
#   bash apply_gutenberg_kg.sh
#
# What it does:
#   1. Creates 8 genre subdirectories
#   2. Moves all 64 books (128 files) via git mv
#   3. Writes ingest.sh, scripts/catalog.txt, scripts/download_gutenberg.py
#   4. Commits everything

set -euo pipefail

if [[ ! -f "scripts/catalog.txt" ]]; then
    echo "ERROR: Run this script from the root of the gutenberg_kg repository."
    exit 1
fi

echo "=== GutenbergKG: applying reorganization ==="
echo ""

# ── 1. Genre directories ─────────────────────────────────────────────────────
echo "[1/4] Creating genre directories..."
mkdir -p ancient-classical shakespeare english-literature american-literature \
         french-literature russian-literature philosophy spanish

# ── 2. git mv ────────────────────────────────────────────────────────────────
echo "[2/4] Moving books into genre directories..."

git mv "Adventures of Huckleberry Finn/adventures_of_huckleberry_finn.md" "american-literature/Adventures of Huckleberry Finn/adventures_of_huckleberry_finn.md"
git mv "Adventures of Huckleberry Finn/reference.md" "american-literature/Adventures of Huckleberry Finn/reference.md"
git mv "Leaves of Grass/leaves_of_grass.md" "american-literature/Leaves of Grass/leaves_of_grass.md"
git mv "Leaves of Grass/reference.md" "american-literature/Leaves of Grass/reference.md"
git mv "Moby Dick/moby_dick.md" "american-literature/Moby Dick/moby_dick.md"
git mv "Moby Dick/reference.md" "american-literature/Moby Dick/reference.md"
git mv "The Call of the Wild/reference.md" "american-literature/The Call of the Wild/reference.md"
git mv "The Call of the Wild/the_call_of_the_wild.md" "american-literature/The Call of the Wild/the_call_of_the_wild.md"
git mv "The Red Badge of Courage/reference.md" "american-literature/The Red Badge of Courage/reference.md"
git mv "The Red Badge of Courage/the_red_badge_of_courage.md" "american-literature/The Red Badge of Courage/the_red_badge_of_courage.md"
git mv "The Scarlet Letter/reference.md" "american-literature/The Scarlet Letter/reference.md"
git mv "The Scarlet Letter/the_scarlet_letter.md" "american-literature/The Scarlet Letter/the_scarlet_letter.md"
git mv "The Yellow Wallpaper/reference.md" "american-literature/The Yellow Wallpaper/reference.md"
git mv "The Yellow Wallpaper/the_yellow_wallpaper.md" "american-literature/The Yellow Wallpaper/the_yellow_wallpaper.md"
git mv "Uncle Toms Cabin/reference.md" "american-literature/Uncle Toms Cabin/reference.md"
git mv "Uncle Toms Cabin/uncle_toms_cabin.md" "american-literature/Uncle Toms Cabin/uncle_toms_cabin.md"
git mv "Walden/reference.md" "american-literature/Walden/reference.md"
git mv "Walden/walden.md" "american-literature/Walden/walden.md"
git mv "Meditations/meditations.md" "ancient-classical/Meditations/meditations.md"
git mv "Meditations/reference.md" "ancient-classical/Meditations/reference.md"
git mv "Oedipus King of Thebes/oedipus_king_of_thebes.md" "ancient-classical/Oedipus King of Thebes/oedipus_king_of_thebes.md"
git mv "Oedipus King of Thebes/reference.md" "ancient-classical/Oedipus King of Thebes/reference.md"
git mv "The Aeneid/reference.md" "ancient-classical/The Aeneid/reference.md"
git mv "The Aeneid/the_aeneid.md" "ancient-classical/The Aeneid/the_aeneid.md"
git mv "The Bible/reference.md" "ancient-classical/The Bible/reference.md"
git mv "The Bible/the_bible.md" "ancient-classical/The Bible/the_bible.md"
git mv "The Divine Comedy/reference.md" "ancient-classical/The Divine Comedy/reference.md"
git mv "The Divine Comedy/the_divine_comedy.md" "ancient-classical/The Divine Comedy/the_divine_comedy.md"
git mv "The Iliad/reference.md" "ancient-classical/The Iliad/reference.md"
git mv "The Iliad/the_iliad.md" "ancient-classical/The Iliad/the_iliad.md"
git mv "The Odyssey/reference.md" "ancient-classical/The Odyssey/reference.md"
git mv "The Odyssey/the_odyssey.md" "ancient-classical/The Odyssey/the_odyssey.md"
git mv "The Republic/reference.md" "ancient-classical/The Republic/reference.md"
git mv "The Republic/the_republic.md" "ancient-classical/The Republic/the_republic.md"
git mv "A Modest Proposal/a_modest_proposal.md" "english-literature/A Modest Proposal/a_modest_proposal.md"
git mv "A Modest Proposal/reference.md" "english-literature/A Modest Proposal/reference.md"
git mv "A Tale of Two Cities/a_tale_of_two_cities.md" "english-literature/A Tale of Two Cities/a_tale_of_two_cities.md"
git mv "A Tale of Two Cities/reference.md" "english-literature/A Tale of Two Cities/reference.md"
git mv "Alices Adventures in Wonderland/alices_adventures_in_wonderland.md" "english-literature/Alices Adventures in Wonderland/alices_adventures_in_wonderland.md"
git mv "Alices Adventures in Wonderland/reference.md" "english-literature/Alices Adventures in Wonderland/reference.md"
git mv "Dracula/dracula.md" "english-literature/Dracula/dracula.md"
git mv "Dracula/reference.md" "english-literature/Dracula/reference.md"
git mv "Emma/emma.md" "english-literature/Emma/emma.md"
git mv "Emma/reference.md" "english-literature/Emma/reference.md"
git mv "Frankenstein/frankenstein.md" "english-literature/Frankenstein/frankenstein.md"
git mv "Frankenstein/reference.md" "english-literature/Frankenstein/reference.md"
git mv "Great Expectations/great_expectations.md" "english-literature/Great Expectations/great_expectations.md"
git mv "Great Expectations/reference.md" "english-literature/Great Expectations/reference.md"
git mv "Grimms Fairy Tales/grimms_fairy_tales.md" "english-literature/Grimms Fairy Tales/grimms_fairy_tales.md"
git mv "Grimms Fairy Tales/reference.md" "english-literature/Grimms Fairy Tales/reference.md"
git mv "Gullivers Travels/gullivers_travels.md" "english-literature/Gullivers Travels/gullivers_travels.md"
git mv "Gullivers Travels/reference.md" "english-literature/Gullivers Travels/reference.md"
git mv "Heart of Darkness/heart_of_darkness.md" "english-literature/Heart of Darkness/heart_of_darkness.md"
git mv "Heart of Darkness/reference.md" "english-literature/Heart of Darkness/reference.md"
git mv "Jane Eyre/jane_eyre.md" "english-literature/Jane Eyre/jane_eyre.md"
git mv "Jane Eyre/reference.md" "english-literature/Jane Eyre/reference.md"
git mv "Middlemarch/middlemarch.md" "english-literature/Middlemarch/middlemarch.md"
git mv "Middlemarch/reference.md" "english-literature/Middlemarch/reference.md"
git mv "Pride and Prejudice/pride_and_prejudice.md" "english-literature/Pride and Prejudice/pride_and_prejudice.md"
git mv "Pride and Prejudice/reference.md" "english-literature/Pride and Prejudice/reference.md"
git mv "Robinson Crusoe/reference.md" "english-literature/Robinson Crusoe/reference.md"
git mv "Robinson Crusoe/robinson_crusoe.md" "english-literature/Robinson Crusoe/robinson_crusoe.md"
git mv "Sense and Sensibility/reference.md" "english-literature/Sense and Sensibility/reference.md"
git mv "Sense and Sensibility/sense_and_sensibility.md" "english-literature/Sense and Sensibility/sense_and_sensibility.md"
git mv "The Adventures of Sherlock Holmes/reference.md" "english-literature/The Adventures of Sherlock Holmes/reference.md"
git mv "The Adventures of Sherlock Holmes/the_adventures_of_sherlock_holmes.md" "english-literature/The Adventures of Sherlock Holmes/the_adventures_of_sherlock_holmes.md"
git mv "The Picture of Dorian Gray/reference.md" "english-literature/The Picture of Dorian Gray/reference.md"
git mv "The Picture of Dorian Gray/the_picture_of_dorian_gray.md" "english-literature/The Picture of Dorian Gray/the_picture_of_dorian_gray.md"
git mv "The Strange Case of Dr Jekyll and Mr Hyde/reference.md" "english-literature/The Strange Case of Dr Jekyll and Mr Hyde/reference.md"
git mv "The Strange Case of Dr Jekyll and Mr Hyde/the_strange_case_of_dr_jekyll_and_mr_hyde.md" "english-literature/The Strange Case of Dr Jekyll and Mr Hyde/the_strange_case_of_dr_jekyll_and_mr_hyde.md"
git mv "The Time Machine/reference.md" "english-literature/The Time Machine/reference.md"
git mv "The Time Machine/the_time_machine.md" "english-literature/The Time Machine/the_time_machine.md"
git mv "The War of the Worlds/reference.md" "english-literature/The War of the Worlds/reference.md"
git mv "The War of the Worlds/the_war_of_the_worlds.md" "english-literature/The War of the Worlds/the_war_of_the_worlds.md"
git mv "Treasure Island/reference.md" "english-literature/Treasure Island/reference.md"
git mv "Treasure Island/treasure_island.md" "english-literature/Treasure Island/treasure_island.md"
git mv "Wuthering Heights/reference.md" "english-literature/Wuthering Heights/reference.md"
git mv "Wuthering Heights/wuthering_heights.md" "english-literature/Wuthering Heights/wuthering_heights.md"
git mv "Candide/candide.md" "french-literature/Candide/candide.md"
git mv "Candide/reference.md" "french-literature/Candide/reference.md"
git mv "Les Miserables/les_miserables.md" "french-literature/Les Miserables/les_miserables.md"
git mv "Les Miserables/reference.md" "french-literature/Les Miserables/reference.md"
git mv "Madame Bovary/madame_bovary.md" "french-literature/Madame Bovary/madame_bovary.md"
git mv "Madame Bovary/reference.md" "french-literature/Madame Bovary/reference.md"
git mv "The Count of Monte Cristo/reference.md" "french-literature/The Count of Monte Cristo/reference.md"
git mv "The Count of Monte Cristo/the_count_of_monte_cristo.md" "french-literature/The Count of Monte Cristo/the_count_of_monte_cristo.md"
git mv "The Three Musketeers/reference.md" "french-literature/The Three Musketeers/reference.md"
git mv "The Three Musketeers/the_three_musketeers.md" "french-literature/The Three Musketeers/the_three_musketeers.md"
git mv "Twenty Thousand Leagues Under the Sea/reference.md" "french-literature/Twenty Thousand Leagues Under the Sea/reference.md"
git mv "Twenty Thousand Leagues Under the Sea/twenty_thousand_leagues_under_the_sea.md" "french-literature/Twenty Thousand Leagues Under the Sea/twenty_thousand_leagues_under_the_sea.md"
git mv "Beyond Good and Evil/beyond_good_and_evil.md" "philosophy/Beyond Good and Evil/beyond_good_and_evil.md"
git mv "Beyond Good and Evil/reference.md" "philosophy/Beyond Good and Evil/reference.md"
git mv "Common Sense/common_sense.md" "philosophy/Common Sense/common_sense.md"
git mv "Common Sense/reference.md" "philosophy/Common Sense/reference.md"
git mv "Leviathan/leviathan.md" "philosophy/Leviathan/leviathan.md"
git mv "Leviathan/reference.md" "philosophy/Leviathan/reference.md"
git mv "On the Origin of Species/on_the_origin_of_species.md" "philosophy/On the Origin of Species/on_the_origin_of_species.md"
git mv "On the Origin of Species/reference.md" "philosophy/On the Origin of Species/reference.md"
git mv "The Federalist Papers/reference.md" "philosophy/The Federalist Papers/reference.md"
git mv "The Federalist Papers/the_federalist_papers.md" "philosophy/The Federalist Papers/the_federalist_papers.md"
git mv "The Prince/reference.md" "philosophy/The Prince/reference.md"
git mv "The Prince/the_prince.md" "philosophy/The Prince/the_prince.md"
git mv "The Wealth of Nations/reference.md" "philosophy/The Wealth of Nations/reference.md"
git mv "The Wealth of Nations/the_wealth_of_nations.md" "philosophy/The Wealth of Nations/the_wealth_of_nations.md"
git mv "Thus Spake Zarathustra/reference.md" "philosophy/Thus Spake Zarathustra/reference.md"
git mv "Thus Spake Zarathustra/thus_spake_zarathustra.md" "philosophy/Thus Spake Zarathustra/thus_spake_zarathustra.md"
git mv "Anna Karenina/anna_karenina.md" "russian-literature/Anna Karenina/anna_karenina.md"
git mv "Anna Karenina/reference.md" "russian-literature/Anna Karenina/reference.md"
git mv "Crime and Punishment/crime_and_punishment.md" "russian-literature/Crime and Punishment/crime_and_punishment.md"
git mv "Crime and Punishment/reference.md" "russian-literature/Crime and Punishment/reference.md"
git mv "Dead Souls/dead_souls.md" "russian-literature/Dead Souls/dead_souls.md"
git mv "Dead Souls/reference.md" "russian-literature/Dead Souls/reference.md"
git mv "The Brothers Karamazov/reference.md" "russian-literature/The Brothers Karamazov/reference.md"
git mv "The Brothers Karamazov/the_brothers_karamazov.md" "russian-literature/The Brothers Karamazov/the_brothers_karamazov.md"
git mv "The Idiot/reference.md" "russian-literature/The Idiot/reference.md"
git mv "The Idiot/the_idiot.md" "russian-literature/The Idiot/the_idiot.md"
git mv "War and Peace/reference.md" "russian-literature/War and Peace/reference.md"
git mv "War and Peace/war_and_peace.md" "russian-literature/War and Peace/war_and_peace.md"
git mv "A Midsummer Nights Dream/a_midsummer_nights_dream.md" "shakespeare/A Midsummer Nights Dream/a_midsummer_nights_dream.md"
git mv "A Midsummer Nights Dream/reference.md" "shakespeare/A Midsummer Nights Dream/reference.md"
git mv "Hamlet/hamlet.md" "shakespeare/Hamlet/hamlet.md"
git mv "Hamlet/reference.md" "shakespeare/Hamlet/reference.md"
git mv "Macbeth/macbeth.md" "shakespeare/Macbeth/macbeth.md"
git mv "Macbeth/reference.md" "shakespeare/Macbeth/reference.md"
git mv "Romeo and Juliet/reference.md" "shakespeare/Romeo and Juliet/reference.md"
git mv "Romeo and Juliet/romeo_and_juliet.md" "shakespeare/Romeo and Juliet/romeo_and_juliet.md"
git mv "Don Quixote/don_quixote.md" "spanish/Don Quixote/don_quixote.md"
git mv "Don Quixote/reference.md" "spanish/Don Quixote/reference.md"

# ── 3. Write updated files ───────────────────────────────────────────────────
echo "[3/4] Writing ingest.sh and updated scripts..."

cat > ingest.sh << 'INGEST_EOF'
#!/usr/bin/env bash
# ingest.sh — Build a DocKG for each genre directory and register them all
# under a "gutenberg" corpus in KGRAG.
#
# Usage (from the gutenberg_kg repo root):
#   bash ingest.sh [--wipe]
#
# Prerequisites:
#   pip install kg-rag   OR   use the KGRAG repo with poetry run kgrag
#   kgrag corpus create gutenberg --desc "Project Gutenberg library"
#
# Each genre directory gets its own .dockg/ (SQLite + LanceDB), registered as
# "gutenberg-<genre>" and added to the "gutenberg" corpus.

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
WIPE="${1:-}"
CORPUS="gutenberg"

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

echo "=== GutenbergKG Ingest ==="
echo "Repo: $REPO_ROOT"
[[ "$WIPE" == "--wipe" ]] && echo "Mode: WIPE + rebuild"
echo ""

# Ensure corpus exists
if ! kgrag corpus info "$CORPUS" &>/dev/null 2>&1; then
    echo "Creating corpus '$CORPUS'..."
    kgrag corpus create "$CORPUS" --desc "Project Gutenberg library"
fi

for GENRE in "${GENRES[@]}"; do
    GENRE_DIR="$REPO_ROOT/$GENRE"
    KG_NAME="gutenberg-$GENRE"

    echo "--- $GENRE ---"

    if [[ ! -d "$GENRE_DIR" ]]; then
        echo "  [!] Directory not found: $GENRE_DIR - skipping"
        echo ""
        continue
    fi

    MD_COUNT=$(find "$GENRE_DIR" -name "*.md" ! -name "README.md" | wc -l)
    if [[ "$MD_COUNT" -eq 0 ]]; then
        echo "  [!] No .md files found - skipping"
        echo ""
        continue
    fi

    echo "  [.] $MD_COUNT .md files"

    # Wipe existing .dockg if requested
    if [[ "$WIPE" == "--wipe" ]] && [[ -d "$GENRE_DIR/.dockg" ]]; then
        rm -rf "$GENRE_DIR/.dockg"
        echo "  [.] Wiped existing .dockg"
    fi

    # Build DocKG
    if ! command -v dockg &>/dev/null; then
        echo "  [!] dockg not found - skipping build (install doc-kg first)"
        echo ""
        continue
    fi

    echo "  [.] Building DocKG..."
    if dockg build --repo "$GENRE_DIR"; then
        echo "  [+] DocKG built"
    else
        echo "  [x] dockg build failed"
        echo ""
        continue
    fi

    # Register with kgrag
    SQLITE="$GENRE_DIR/.dockg/graph.sqlite"
    LANCEDB="$GENRE_DIR/.dockg/lancedb"
    ARGS=(kgrag register "$KG_NAME" doc "$GENRE_DIR")
    [[ -f "$SQLITE" ]]  && ARGS+=(--sqlite  "$SQLITE")
    [[ -d "$LANCEDB" ]] && ARGS+=(--lancedb "$LANCEDB")

    if "${ARGS[@]}" 2>&1; then
        echo "  [+] Registered: $KG_NAME"
    else
        echo "  [!] Already registered (continuing)"
    fi

    # Add to corpus
    kgrag corpus add "$CORPUS" "$KG_NAME" 2>&1 && echo "  [+] Added to corpus: $CORPUS" || true

    echo ""
done

echo "=== Done ==="
echo ""
echo "Query your library:"
echo "  kgrag corpus query gutenberg \"your question\""
echo "  kgrag synthesize \"your question\" --corpus gutenberg"
echo "  kgrag viz"
INGEST_EOF
chmod +x ingest.sh

cat > scripts/catalog.txt << 'CATALOG_EOF'
# Project Gutenberg Book Catalog
# Format: <ebook_id>[\t<title_override>[\t<genre_override>]]
#
# Genre is auto-detected from section headers below.
# To override: add a third tab-separated column with the genre directory name.
#
# Genre directories:
#   ancient-classical, shakespeare, english-literature, american-literature,
#   french-literature, russian-literature, philosophy, spanish
#
# Find ebook IDs: python scripts/download_gutenberg.py search --author "Author Name"
# Download all:  python scripts/download_gutenberg.py catalog scripts/catalog.txt

# Ancient & Classical
1727	The Odyssey
6130	The Iliad
228	The Aeneid
1497	The Republic
1004	The Divine Comedy
27673	Oedipus King of Thebes
2680	Meditations
10	The Bible

# Shakespeare
1524	Hamlet
1513	Romeo and Juliet
1533	Macbeth
1514	A Midsummer Nights Dream

# English Literature
1260	Jane Eyre
768	Wuthering Heights
1400	Great Expectations
145	Middlemarch
161	Sense and Sensibility
158	Emma
1342	Pride and Prejudice
84	Frankenstein
345	Dracula
219	Heart of Darkness
35	The Time Machine
36	The War of the Worlds
120	Treasure Island
521	Robinson Crusoe
829	Gullivers Travels
43	The Strange Case of Dr Jekyll and Mr Hyde
1661	The Adventures of Sherlock Holmes
174	The Picture of Dorian Gray
11	Alices Adventures in Wonderland
98	A Tale of Two Cities
1080	A Modest Proposal
2591	Grimms Fairy Tales

# American Literature
2701	Moby Dick
33	The Scarlet Letter
205	Walden
1322	Leaves of Grass
76	Adventures of Huckleberry Finn
215	The Call of the Wild
73	The Red Badge of Courage
203	Uncle Toms Cabin
1952	The Yellow Wallpaper

# French Literature
135	Les Miserables
1184	The Count of Monte Cristo
1257	The Three Musketeers
2413	Madame Bovary
164	Twenty Thousand Leagues Under the Sea
19942	Candide

# Russian Literature
2554	Crime and Punishment
28054	The Brothers Karamazov
1399	Anna Karenina
2600	War and Peace
2638	The Idiot
1081	Dead Souls

# Philosophy & Non-Fiction
1228	On the Origin of Species
147	Common Sense
3207	Leviathan
1998	Thus Spake Zarathustra
4363	Beyond Good and Evil
3300	The Wealth of Nations
1404	The Federalist Papers
1232	The Prince

# Spanish
996	Don Quixote
CATALOG_EOF

# ── 4. Commit ────────────────────────────────────────────────────────────────
echo "[4/4] Committing..."
git add -A
git -c commit.gpgsign=false commit -m "Reorganize books into genre subdirectories; add ingest.sh"

echo ""
echo "=== Done! Now push with: git push origin main ==="
