# Version Bump Workflow

You will update the project version in both `pyproject.toml` and `src/kg_rag/__init__.py`, then stage the changes.

## Step 1: Determine New Version

Ask the user which version component to bump:
- **major**: X.0.0 (breaking changes)
- **minor**: x.Y.0 (new features, backward compatible)

Parse their response and calculate the new version:
- Current version is 0.2.0
- If major: bump to 1.0.0
- If minor: bump to 0.3.0

## Step 2: Update pyproject.toml

1. Read the current `pyproject.toml`
2. Find the line: `version = "0.2.0"`
3. Replace with new version: `version = "X.Y.Z"`
4. Save the file

## Step 3: Update __init__.py

1. Read `src/kg_rag/__init__.py`
2. Find the line: `__version__ = "0.2.0"`
3. Replace with new version: `__version__ = "X.Y.Z"`
4. Save the file

## Step 4: Stage Changes

Run the following git command to stage both files:
```bash
git add pyproject.toml src/kg_rag/__init__.py
```

Verify with `git status`

## Step 5: Confirm

Display:
```
✓ Updated version to X.Y.Z
✓ Modified: pyproject.toml
✓ Modified: src/kg_rag/__init__.py
✓ Staged changes

Ready to commit with: git commit -m "chore(release): bump version to X.Y.Z"
```
