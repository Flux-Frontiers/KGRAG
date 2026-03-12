---
name: publish
description: Step-by-step release workflow for publishing code-kg to PyPI using Poetry. Use this skill when the user wants to cut a release, bump the version, update the CHANGELOG, tag a commit, build and publish to PyPI, or run any part of the release pipeline for the code-kg project.
---

# Publish Skill — code-kg Release Workflow

## Prerequisites

- Clean working tree (`git status` shows no uncommitted changes)
- All tests passing (`poetry run pytest`)
- Pre-commit checks passing (`pre-commit run --all-files`)
- PyPI credentials configured (`poetry config pypi-token.pypi <token>`)

---

## Release Steps

### 1. Decide the version bump

Follow [Semantic Versioning](https://semver.org/):

| Change | Bump |
|--------|------|
| Bug fixes only | `patch` (0.5.2 → 0.5.3) |
| New features, backward-compatible | `minor` (0.5.2 → 0.6.0) |
| Breaking changes | `major` (0.5.2 → 1.0.0) |

### 2. Update CHANGELOG.md

Move items from `## [Unreleased]` to a new versioned section:

```markdown
## [X.Y.Z] - YYYY-MM-DD
```

Leave `## [Unreleased]` empty at the top for future entries.

### 3. Bump version in pyproject.toml

```bash
poetry version patch   # or minor / major
```

Verify: `grep '^version' pyproject.toml`

### 4. Commit the release

```bash
git add pyproject.toml CHANGELOG.md
CODEKG_SKIP_SNAPSHOT=1 git commit -m "chore: release vX.Y.Z"
```

> Use `CODEKG_SKIP_SNAPSHOT=1` to prevent the post-commit hook from creating a snapshot on a release commit.

### 5. Tag the release

```bash
git tag -a vX.Y.Z -m "Release vX.Y.Z"
```

### 6. Build the distribution

```bash
poetry build
```

Artifacts appear in `dist/`. Verify they look correct:

```bash
ls -lh dist/
```

### 7. Publish to PyPI

```bash
poetry publish
```

To test against TestPyPI first:

```bash
poetry publish -r testpypi
```

### 8. Push to GitHub

```bash
git push origin main --tags
```

---

## After Release

- Update `.claude/skills/codekg/SKILL.md` if the install command or version references changed
- Save a snapshot: `codekg snapshot save X.Y.Z --repo . --branch main`

---

## Rollback

If something went wrong after `poetry publish`:

- PyPI releases cannot be deleted (only yanked): `poetry run twine yank code-kg X.Y.Z`
- Revert the commit: `git revert HEAD` then `git push`
- Delete the tag: `git tag -d vX.Y.Z && git push origin :refs/tags/vX.Y.Z`
