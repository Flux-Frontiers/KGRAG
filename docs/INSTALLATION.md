# KGRAG Installation Guide

## Prerequisites

- Python 3.12 or later
- pip or Poetry
- (Optional) PyCodeKG, DocKG, or MetaboKG already installed in your projects

## Installation

### Option 1: Via pip

```bash
pip install kgrag
```

### Option 1b: Via pipx (fully contained)

Use this when you want KGRAG, its adapter backends, and all visualization
dependencies isolated inside one pipx virtual environment.

Using local editable checkouts:

```bash
pipx install --force --editable '/absolute/path/to/kgrag[kg,viz,viz3d]'

pipx inject --force --editable kg-rag \
  '/absolute/path/to/pycode_kg[viz,viz3d]' \
  '/absolute/path/to/doc_kg[viz]' \
  '/absolute/path/to/ftree_kg' \
  '/absolute/path/to/agent_kg[viz]' \
  '/absolute/path/to/diary_kg[viz,viz3d]' \
  '/absolute/path/to/memory_kg[viz]' \
  '/absolute/path/to/metabo_kg[viz,viz3d]'
```

Using GitHub or package specs instead of local checkouts:

```bash
pipx install --force 'kg-rag[kg,viz,viz3d] @ git+https://github.com/Flux-Frontiers/KGRAG.git'

pipx inject --force kg-rag \
  'pycode-kg[viz,viz3d]' \
  'doc-kg[viz]' \
  'ftree-kg' \
  'agent-kg[viz] @ git+https://github.com/Flux-Frontiers/agent_kg.git' \
  'diary-kg[viz,viz3d] @ git+https://github.com/Flux-Frontiers/diary_kg.git' \
  'memory-kg[viz] @ git+https://github.com/Flux-Frontiers/memory_kg.git' \
  'metabo-kg[viz,viz3d] @ git+https://github.com/Flux-Frontiers/metabo_kg.git'
```

Notes:

- This keeps the adapter libraries and visualization stacks inside the pipx
  environment used by `kgrag`.
- `pipx install` and `pipx inject` pass these package specs through to `pip`,
  so local paths, PyPI package names, and `git+https` URLs all work.
- To keep the setup contained, do not pass `--include-apps` to `pipx inject`
  unless you explicitly want adapter CLI commands like `dockg` or `pycodekg`
  exposed on your global `PATH`.

To verify the pipx environment:

```bash
pipx runpip kg-rag list | egrep 'kg-rag|pycode-kg|doc-kg|ftree-kg|agent-kg|diary-kg|memory-kg|metabo-kg|pyvista|pyvistaqt|PyQt5|pyvis|plotly|streamlit|param|trame-vtk'
kgrag analyze
```

### Option 2: Via Poetry

```bash
poetry add kgrag
```

### Option 3: From source (development)

```bash
git clone https://github.com/flux-frontiers/kgrag.git
cd kgrag
poetry install
poetry run kgrag --version
```

## Verify Installation

```bash
kgrag --version
kgrag --help
```

Should display version info and help text.

---

## Initial Setup

### 1. Initialize Your First Project

```bash
cd ~/repos/myproject
kgrag init
```

This will:
- Auto-detect applicable KG layers (code, doc)
- Build CodeKG and/or DocKG databases
- Register them in the KGRAG registry

### 2. Check Registry Status

```bash
kgrag status
```

Should show: `✅ 1 KG registered · 1 built`

### 3. Try a Query

```bash
kgrag query "authentication flow"
```

Should return results ranked by relevance.

### 4. Launch the Visualizer

```bash
kgrag viz
```

Open browser to `http://localhost:8501` and explore interactively.

---

## Setting Up Multiple Projects

```bash
# Use the batch-init script (from KGRAG skill)
bash ~/.claude/skills/kgrag/scripts/batch-init.sh \
  ~/repos/backend \
  ~/repos/frontend \
  ~/repos/docs

# Or initialize manually
kgrag init ~/repos/backend
kgrag init ~/repos/frontend
kgrag init ~/repos/docs

# Verify all registered
kgrag list
kgrag status
```

Now KGRAG treats all projects as a federated corpus.

---

## Configure MCP for Claude Code

MCP (Model Context Protocol) exposes KGRAG tools to Claude Code and other MCP clients.

### 1. Create `.mcp.json` in Your Project

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

**Important:** Use absolute paths (not `~`).

**Find your registry path:**
```bash
echo $KGRAG_REGISTRY
# If not set, default is: ~/.kgrag/registry.sqlite
```

### 2. Use the Setup Script

```bash
cd ~/repos/myproject
bash ~/.claude/skills/kgrag/scripts/setup-kgrag-mcp.sh
```

This automatically creates `.mcp.json` with correct paths.

### 3. Restart Claude Code

Fully quit and reopen Claude Code. MCP tools should now appear:
- `kgrag_query(q, k, kinds)`
- `kgrag_pack(q, k, context, kinds)`
- `kgrag_list()`
- `kgrag_info(name)`
- `kgrag_stats()`

---

## Environment Variables

**Optional configuration via environment variables:**

```bash
# Custom registry location
export KGRAG_REGISTRY=$HOME/.kgrag/registry.sqlite

# Pre-download embedding models for offline use
export CODEKG_MODEL_DIR=$HOME/.models/codekg
export DOCKG_MODEL_DIR=$HOME/.models/dockg
```

Add to `~/.bashrc` or `~/.zshrc` for persistence:

```bash
cat >> ~/.bashrc << 'EOF'
export KGRAG_REGISTRY=$HOME/.kgrag/registry.sqlite
export CODEKG_MODEL_DIR=$HOME/.models/codekg
export DOCKG_MODEL_DIR=$HOME/.models/dockg
EOF
source ~/.bashrc
```

---

## Installing Dependent Libraries

KGRAG works with CodeKG, DocKG, and MetaKG. These are optional — if not installed, those KG types are skipped.

### CodeKG (required for code analysis)

```bash
pip install pycode-kg
# or
poetry add pycode-kg
```

### DocKG (required for documentation analysis)

```bash
pip install doc-kg
# or
poetry add doc-kg
```

### MetaKG (required for metabolic data)

```bash
pip install metakg
# or
poetry add metakg
```

---

## Troubleshooting Installation

### "Command not found: kgrag"

**Solution:** Install KGRAG:
```bash
pip install kgrag
```

If using Poetry:
```bash
poetry add kgrag
poetry run kgrag --version
```

### "No module named 'code_kg'" (when initializing)

**Solution:** Install CodeKG:
```bash
pip install pycode-kg
```

Then retry:
```bash
kgrag init ~/repos/myproject
```

### Permission denied when running scripts

**Solution:** Make scripts executable:
```bash
chmod +x ~/.claude/skills/kgrag/scripts/*.sh
```

### Registry file not found

**Solution:** Create it with first initialization:
```bash
kgrag init ~/repos/myproject
# Creates ~/.kgrag/registry.sqlite
```

Or explicitly set path:
```bash
export KGRAG_REGISTRY=/custom/path/registry.sqlite
kgrag init ~/repos/myproject
```

---

## Next Steps

1. **Learn the CLI:** See [USAGE.md](USAGE.md)
2. **Explore workflows:** Check the `/usage` section in [USAGE.md](USAGE.md)
3. **Troubleshoot issues:** See [TROUBLESHOOTING.md](TROUBLESHOOTING.md)
4. **Understand the vision:** Read [VISION.md](VISION.md)

---

## Offline Installation

If you need to use KGRAG without network access:

```bash
# 1. Download embedding models on a machine with internet
CODEKG_MODEL_DIR=~/.models/codekg codekg download-model
DOCKG_MODEL_DIR=~/.models/dockg dockg download-model

# 2. Copy ~/.models to your offline machine
# 3. Set environment variables on offline machine
export CODEKG_MODEL_DIR=$HOME/.models/codekg
export DOCKG_MODEL_DIR=$HOME/.models/dockg

# 4. KGRAG will use cached models
kgrag init ~/repos/myproject
```

---

## Uninstallation

If you need to remove KGRAG:

```bash
# Remove package
pip uninstall kgrag

# (Optional) Clean up registry and databases
rm -rf ~/.kgrag
```

This removes KGRAG but keeps your source code intact.
