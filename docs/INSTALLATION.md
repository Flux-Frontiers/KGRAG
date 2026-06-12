# KGRAG Installation Guide

## Prerequisites

- Python 3.12 or later
- [uv](https://docs.astral.sh/uv/) — the recommended package manager for the KGRAG fleet

Install uv if you don't have it:
```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

---

## Recommended: uv tool (full fleet)

Each KGRAG module installs as an isolated `uv tool` — its own environment, its
own dependencies, no conflicts between tools.  All CLI commands (`kgrag`,
`pycodekg`, `dockg`, `metabokg`, …) land on your PATH automatically.

### Install the full fleet from source

Clone all repos into a common parent directory, then run the installer:

```bash
# From the directory that contains your kgrag clone
bash scripts/install-kgs.sh
```

The script installs every public adaptor (`doc_kg`, `pycode_kg`, `gutenberg_kg`,
`metabo_kg`, `ftree_kg`, `diary_kg`, `agent_kg`) as an editable uv tool, then
installs the `kgrag` orchestrator with the `[all]` extra.  Editable means the running binary tracks your local source — no
reinstall needed after `git pull`.

To install only specific repos:
```bash
bash scripts/install-kgs.sh pycode_kg doc_kg
```

To force a full rebuild of all tool environments:
```bash
REINSTALL=1 bash scripts/install-kgs.sh
```

### Install individual tools

```bash
uv tool install --editable '/path/to/pycode_kg'
uv tool install --editable '/path/to/doc_kg'
uv tool install --editable '/path/to/kgrag[all]'
```

### Verify the fleet

```bash
uv tool list
```

You should see all installed tools with their versions and exposed entry points.

### Upgrade

```bash
# Upgrade everything at once
uv tool upgrade --all

# Upgrade a specific tool
uv tool upgrade pycode-kg

# Keep uv itself current
uv self update
```

---

## Embedding into a project (pip / Poetry / uv add)

Use these when you want KGRAG as a library dependency inside a project
virtualenv, not as a global CLI tool.

### pip

```bash
pip install kgrag
pip install 'kgrag[all]'          # include all adaptor extras
```

### uv (project dependency)

```bash
uv add kgrag
uv add 'kgrag[all]'
```

### Poetry

```bash
poetry add kgrag
poetry add 'kgrag[all]'
```

### From source (development)

```bash
git clone https://github.com/flux-frontiers/kgrag.git
cd kgrag
uv tool install --editable '.[all]'
kgrag --version
```

---

## Verify Installation

```bash
kgrag --version
kgrag --help
```

---

## Initial Setup

### 1. Initialize your first project

```bash
cd ~/repos/myproject
kgrag init
```

This auto-detects applicable KG layers (code, docs), builds the databases, and
registers them in the KGRAG registry.

### 2. Check registry status

```bash
kgrag status
```

Should show: `✅ 1 KG registered · 1 built`

### 3. Try a query

```bash
kgrag query "authentication flow"
```

### 4. Launch the visualizer

```bash
kgrag viz
```

Open browser to `http://localhost:8501`.

---

## Setting Up Multiple Projects

```bash
kgrag init ~/repos/backend
kgrag init ~/repos/frontend
kgrag init ~/repos/docs

# Verify all registered
kgrag list
kgrag status
```

KGRAG treats all registered projects as a federated corpus.

---

## Configure MCP for Claude Code

MCP exposes KGRAG tools to Claude Code and other MCP clients.

### Create `.mcp.json` in your project

```json
{
  "mcpServers": {
    "kgrag": {
      "command": "kgrag",
      "args": ["mcp", "--registry", "/absolute/path/to/registry.sqlite"]
    }
  }
}
```

Use absolute paths (not `~`). Find your registry path:
```bash
echo ${KGRAG_REGISTRY:-~/.kgrag/registry.sqlite}
```

### Restart Claude Code

MCP tools should appear after restart:
- `kgrag_query(q, k, kinds)`
- `kgrag_pack(q, k, context, kinds)`
- `kgrag_list()`
- `kgrag_info(name)`
- `kgrag_stats()`

---

## Environment Variables

```bash
export KGRAG_REGISTRY=$HOME/.kgrag/registry.sqlite   # custom registry location
export CODEKG_MODEL_DIR=$HOME/.models/codekg          # embedding model cache
export DOCKG_MODEL_DIR=$HOME/.models/dockg
```

Add to `~/.zshrc` or `~/.bashrc` for persistence.

---

## Offline Installation

```bash
# Download embedding models on a machine with internet access
pycodekg download-model
dockg download-model        # if doc-kg supports this command

# Copy ~/.models to your offline machine, then set env vars
export CODEKG_MODEL_DIR=$HOME/.models/codekg
export DOCKG_MODEL_DIR=$HOME/.models/dockg
```

---

## Troubleshooting

| Symptom | Fix |
|---|---|
| `command not found: kgrag` | Run `uv tool install --editable '/path/to/kgrag[all]'`; check `~/.local/bin` is on PATH |
| `uv: command not found` | Install uv: `curl -LsSf https://astral.sh/uv/install.sh \| sh` |
| Tool installed but old version running | `uv tool upgrade --all` |
| MCP server not appearing in Claude Code | Use absolute paths in `.mcp.json`; fully quit and reopen Claude Code |
| Registry file not found | Run `kgrag init ~/repos/myproject` to create `~/.kgrag/registry.sqlite` |
| Empty query results | Rebuild the KG: `pycodekg build --repo .` or `dockg build` |

---

## Uninstallation

```bash
uv tool uninstall kgrag
uv tool uninstall pycode-kg
# … repeat for each tool

# Optional: remove registry and databases
rm -rf ~/.kgrag
```

---

## Next Steps

- [USAGE.md](USAGE.md) — CLI reference and query workflows
- [MCP.md](MCP.md) — full MCP configuration guide
- [TROUBLESHOOTING.md](TROUBLESHOOTING.md) — debugging guide
