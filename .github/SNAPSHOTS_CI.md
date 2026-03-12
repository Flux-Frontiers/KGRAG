# Automated Temporal Snapshots (GitHub Actions)

Snapshots are automatically captured on every commit to the `develop` branch via GitHub Actions CI.

## How It Works

The **Temporal Snapshots** workflow (`.github/workflows/snapshots.yml`):

1. **Triggers on:** Every push to `develop` branch or manual workflow dispatch
2. **Builds:** CodeKG database (SQLite + LanceDB vector index)
3. **Captures:** Temporal snapshot with current metrics:
   - Total nodes/edges
   - Docstring coverage
   - Complexity hotspots
   - Critical issues
4. **Commits:** Snapshot back to `.codekg/snapshots/` in the repository
5. **Archives:** Snapshot as build artifact (90-day retention)

## Snapshot Contents

Each snapshot stores:
- **Commit hash** — Immutable git reference
- **Branch name** — Track separate release/develop lines
- **Timestamp** — ISO 8601 UTC for auditability
- **Version** — Semantic version from `pyproject.toml`
- **Metrics** — Full graph statistics and analysis results
- **Deltas** — Changes vs. previous and baseline snapshots

## Viewing Results

### In Git History
Snapshots are committed to `.codekg/snapshots/{commit}.json`:

```bash
git log --oneline -- .codekg/snapshots/
```

### In GitHub Actions
Snapshots are available as artifacts in the workflow run:

1. Go to **Actions** → **Temporal Snapshots**
2. Click any run to view results
3. Download snapshots artifact (`.codekg/snapshots/`)

### Via CLI

```bash
# List all captured snapshots
codekg snapshot list

# Show details for a specific snapshot
codekg snapshot show <commit>

# Compare two snapshots
codekg snapshot diff <commit-a> <commit-b>
```

## Manual Snapshot

Trigger a snapshot manually without committing:

```bash
codekg snapshot save 0.5.2-rc1 --repo .
```

## Configuration

### Trigger Branches
Edit `.github/workflows/snapshots.yml` to change trigger branches:

```yaml
on:
  push:
    branches: [develop, main, release/*]
```

### Bot Credentials
The workflow uses GitHub's built-in `actions/checkout@v4` and pushes with:
- **Author:** CodeKG Bot `<codekg@flux-frontiers.dev>`
- **Permissions:** Requires `contents: write` (already set in workflow)

### Artifact Retention
Snapshots are kept for 90 days:

```yaml
retention-days: 90
```

## What Gets Committed

Only changes to `.codekg/snapshots/` are committed:
- `.codekg/snapshots/{commit}.json` — Full snapshot
- `.codekg/snapshots/manifest.json` — Index of all snapshots

Other generated files (analysis reports, graphs) are not committed.

## Example Workflow Output

```
✓ Snapshot saved: .codekg/snapshots/dd1b9d3a707ab18c22bdc9963ed42bd8930f2747.json
  Commit:  dd1b9d3a707ab18c22bdc9963ed42bd8930f2747
  Version: 0.5.2
  Nodes:   3818
  Edges:   3717
  Coverage: 97.0%

✓ Snapshot committed to .codekg/snapshots/
```

## Using Snapshots in Your Workflow

Import and compare snapshots programmatically:

```python
from code_kg.snapshots import SnapshotManager

mgr = SnapshotManager(".codekg/snapshots")

# Get all snapshots
snapshots = mgr.list_snapshots()

# Load specific snapshot by commit
snapshot = mgr.load_snapshot("dd1b9d3a70")

# Compare two snapshots
diff = mgr.diff_snapshots("commit_a", "commit_b")

# Analyze metrics over time
for snap in snapshots:
    print(f"{snap['version']}: {snap['metrics']['coverage']*100:.1f}% coverage")
```

## Troubleshooting

### Workflow didn't run
- Check branch name matches `on.push.branches`
- Ensure `permissions.contents: write` is present
- Manual trigger: **Actions** → **Temporal Snapshots** → **Run workflow**

### Snapshot commit failed
- Database build may have failed — check logs
- Check CodeKG output for analysis errors
- Artifact will still be uploaded even if commit fails

### Out of space on runner
- Large repositories may need more disk
- Check `.codekg/lancedb/` size
- Consider adding cleanup step if needed

## Next Steps

- [ ] Integrate snapshots into CI/CD gates (fail if coverage drops)
- [ ] Generate metric reports from snapshots
- [ ] Visualize snapshots in viz3d timeline mode
- [ ] Set up alerts for regression detection

## See Also

- [Snapshots Guide](../../docs/SNAPSHOTS.md) — User manual
- [Architecture Analysis](../../docs/ARCHITECTURE.md) — Architecture snapshots
- [README](../../README.md) — Project overview
