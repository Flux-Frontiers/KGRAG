# Release Workflow (kgrag)

You will create a new versioned release of **kgrag** by promoting the
`[Unreleased]` section of `CHANGELOG.md` into a dated version entry, writing
`release-notes.md`, bumping the version in source files (if not already done
via `/bump`), updating the README badge, committing the changes, tagging the
commit, and pushing the tag to the remote.

This skill is scoped to the **kgrag** repository
(`/Users/egs/repos/kgrag/`). The Python package lives at `src/kg_rag/`, and
the GitHub repo is `Flux-Frontiers/KGRAG`.

Execute the steps in sequence.

---

## Step 0: Gather Release Context

1. Read `CHANGELOG.md` in full.
2. Read `pyproject.toml` and `src/kg_rag/__init__.py` to find the current
   version string.
3. Run `git status` and `git log --oneline -10` to understand the state of
   the working tree.
4. Confirm there is content under `## [Unreleased]`; if the section is
   empty, stop and tell the user there is nothing to release.

---

## Step 1: Determine the New Version

1. Parse the current version from `pyproject.toml` (e.g. `0.7.5`).
2. If the user already ran `/bump` and `pyproject.toml` /
   `src/kg_rag/__init__.py` are already at the target version, **adopt
   that as the new version and skip Step 3**.
3. Otherwise, ask the user which semver component to bump — **patch**,
   **minor**, or **major** — unless they already specified it in their
   message (e.g. `/release minor`).
4. Compute the new version string (e.g. `0.7.5` → `0.8.0` for minor).
5. Confirm the new tag will be `v<new_version>` (e.g. `v0.8.0`).

---

## Step 2: Update CHANGELOG.md

1. Replace `## [Unreleased]` with `## [<new_version>] - <today's date in
   YYYY-MM-DD>`.
2. Insert a fresh `## [Unreleased]` section with empty `### Added`,
   `### Changed`, `### Fixed`, `### Removed` subsections **above** the
   newly-versioned section.
3. Write the updated file.

---

## Step 3: Bump the Version in Source Files

**Skip this step if `/bump` was already run** and both files are already
at `<new_version>`.

Otherwise update the version string in **both** of the following files:

- `pyproject.toml` — the `version = "..."` field under `[tool.poetry]`
- `src/kg_rag/__init__.py` — the `__version__` assignment

Set both to the new version string (without the `v` prefix).

If you bump here, also refresh the lock file:

```bash
poetry lock
```

---

## Step 4: Write release-notes.md

Create (or overwrite) `release-notes.md` in the project root with the
following structure:

```markdown
# Release Notes - v<new_version>

> Released: <today's date in YYYY-MM-DD>

<copy the full content of the promoted [Unreleased] section verbatim — all
subsections and bullet points>

---

_Full changelog: [CHANGELOG.md](CHANGELOG.md)_
```

Do not summarise or rewrite the changelog content — copy it exactly.

---

## Step 4b: Update Version Badge in README.md

In `README.md`, find the version badge line:

```
[![Version](https://img.shields.io/badge/version-<current_version>-blue.svg)](https://github.com/Flux-Frontiers/KGRAG/releases)
```

Replace `<current_version>` with `<new_version>` (e.g. `0.7.5` → `0.8.0`).

---

## Step 5: Commit the Release Files

1. Stage the following files (only those that exist / changed):
   - `CHANGELOG.md`
   - `release-notes.md`
   - `README.md`
   - `pyproject.toml`   (only if bumped in Step 3)
   - `poetry.lock`      (only if bumped in Step 3)
   - `src/kg_rag/__init__.py`  (only if bumped in Step 3)

2. Create a commit with message:

   ```
   chore(release): v<new_version> release notes

   Co-Authored-By: Claude Opus 4.7 <noreply@anthropic.com>
   ```

   Pre-commit hooks (ruff, mypy, pylint, pytest, dockg snapshot) must pass
   before the commit lands. If any hook fails, fix the underlying issue
   and re-stage; do **not** use `--no-verify`.

---

## Step 6: Create the Git Tag

Run:

```bash
git tag -a v<new_version> -m "v<new_version>"
```

---

## Step 7: Push the Tag (ask first)

**Before pushing**, display the tag name and ask the user to confirm:

> Ready to push tag `v<new_version>` (and the release commits) to
> `origin/main`. Proceed? (yes / no)

If confirmed, push both the branch and the tag:

```bash
git push origin main
git push origin v<new_version>
```

If the user declines, tell them they can push later with the two commands
above.

Per the user's standing instructions
(`feedback_no_commit_without_permission.md`), never push autonomously —
always wait for explicit approval at this step.

---

## Completion

After all steps succeed, print a summary:

```
✓ CHANGELOG.md promoted [Unreleased] → [<new_version>] - <date>
✓ release-notes.md written
✓ README.md badge updated to <new_version>
✓ pyproject.toml + src/kg_rag/__init__.py at <new_version>   (or: already bumped via /bump)
✓ Commit created
✓ Tag v<new_version> created
✓ Tag pushed to origin   (or: ready to push manually)
```
