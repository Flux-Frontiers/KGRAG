# Release Workflow

You will create a new versioned release by promoting the `[Unreleased]` section of `CHANGELOG.md` into a dated version entry, writing `release-notes.md`, committing the changes, tagging the commit, and pushing the tag to the remote. Execute the following steps in sequence.

---

## Step 0: Gather Release Context

1. Read `CHANGELOG.md` in full.
2. Read `pyproject.toml` and `src/code_kg/__init__.py` to find the current version string.
3. Run `git status` and `git log --oneline -10` to understand the state of the working tree.
4. Confirm there is content under `## [Unreleased]`; if the section is empty, stop and tell the user there is nothing to release.

---

## Step 1: Determine the New Version

1. Parse the current version from `pyproject.toml` (e.g. `0.2.1`).
2. Ask the user which semver component to bump — **patch**, **minor**, or **major** — unless they already specified it in their message (e.g. `/release minor`).
3. Compute the new version string (e.g. `0.2.1` → `0.3.0` for minor).
4. Confirm the new tag will be `v<new_version>` (e.g. `v0.3.0`).

---

## Step 2: Update CHANGELOG.md

1. Replace `## [Unreleased]` with `## [<new_version>] - <today's date in YYYY-MM-DD>`.
2. Insert a fresh `## [Unreleased]` section with empty `### Added`, `### Changed`, `### Removed`, `### Fixed` subsections **above** the newly-versioned section.
3. Write the updated file.

---

## Step 3: Bump the Version in Source Files

Update the version string in **both** of the following files:

- `pyproject.toml` — the `version = "..."` field under `[tool.poetry]`
- `src/code_kg/__init__.py` — the `__version__` assignment

Set both to the new version string (without the `v` prefix).

---

## Step 4: Write release-notes.md

Create (or overwrite) `release-notes.md` in the project root with the following structure:

```markdown
# Release Notes — v<new_version>

> Released: <today's date in YYYY-MM-DD>

<copy the full content of the promoted [Unreleased] section verbatim — all subsections and bullet points>

---

_Full changelog: [CHANGELOG.md](CHANGELOG.md)_
```

Do not summarise or rewrite the changelog content — copy it exactly.

---

## Step 4b: Update Version Badge in README.md

In `README.md`, find the version badge line:

```
[![Version](https://img.shields.io/badge/version-<current_version>-blue.svg)](https://github.com/Flux-Frontiers/code_kg/releases)
```

Replace `<current_version>` with `<new_version>` (e.g. `0.2.3` → `0.2.4`).

---

## Step 4c: Generate Versioned CodeKG Analysis

1. Rebuild the CodeKG index against the current source:
   ```bash
   poetry run codekg-build-sqlite --repo . --wipe
   poetry run codekg-build-lancedb --repo . --wipe
   ```
2. Run the thorough analysis:
   ```bash
   poetry run codekg-analyze --repo . --output docs/analysis_v<new_version>.md
   ```
   If the `--output` flag is not available, run the analysis and write stdout to the file:
   ```bash
   poetry run codekg-analyze --repo . > docs/analysis_v<new_version>.md
   ```
3. Open `docs/analysis_v<new_version>.md` and ensure the header contains:
   ```
   **Version:** <new_version>
   **Generated:** <today's date in YYYY-MM-DD>
   ```
   Add or update these fields if missing.
4. Delete any previous `docs/analysis_v<old_version>.md` file if it exists and differs from the new version.
5. Stage the generated artifacts — the rebuild and analysis both produce new files:
   ```bash
   git add docs/analysis_v<new_version>.md
   git add .codekg/
   ```
   If an old analysis file was deleted, also run `git rm docs/analysis_v<old_version>.md`.

---

## Step 5: Commit the Release Files

1. Stage the following files:
   - `CHANGELOG.md`
   - `release-notes.md`
   - `pyproject.toml`
   - `src/code_kg/__init__.py`
   - `README.md`
   - `docs/analysis_v<new_version>.md`
2. Create a commit with message:
   ```
   chore(release): v<new_version> release notes

   Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>
   ```

---

## Step 6: Create the Git Tag

Run:
```bash
git tag -a v<new_version> -m "v<new_version>"
```

---

## Step 7: Push the Tag

**Before pushing**, display the tag name and ask the user to confirm:

> Ready to push tag `v<new_version>` to `origin`. Proceed? (yes / no)

If confirmed, run:
```bash
git push origin v<new_version>
```

If the user declines, tell them they can push later with:
```bash
git push origin v<new_version>
```

---

## Completion

After all steps succeed, print a summary:

```
✓ CHANGELOG.md promoted [Unreleased] → [<new_version>] - <date>
✓ release-notes.md written
✓ pyproject.toml + __init__.py bumped to <new_version>
✓ docs/analysis_v<new_version>.md generated
✓ Commit created
✓ Tag v<new_version> created
✓ Tag pushed to origin   (or: tag ready to push manually)
```
