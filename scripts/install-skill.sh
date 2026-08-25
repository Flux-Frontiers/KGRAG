#!/usr/bin/env bash
# =============================================================================
# install-skill.sh — Bootstrap the kgrag AI integration layer
#
# Installs the kgrag SKILL.md into agent skill directories and the kgrag
# slash commands for AI agents, then configures MCP server integration for
# the specified providers.
#
# Supported providers:
#   claude   — Claude Code  (.mcp.json)
#   kilo     — Kilo Code    (.mcp.json, shared with Claude Code)
#   copilot  — GitHub Copilot (.vscode/mcp.json)
#   cline    — Cline        (reads .mcp.json automatically; no extra command)
#
# Usage (from a target repo, no clone needed):
#   curl -fsSL https://raw.githubusercontent.com/Flux-Frontiers/KGRAG/main/scripts/install-skill.sh | bash
#
# With provider selection:
#   curl -fsSL .../install-skill.sh | bash -s -- --providers all
#   curl -fsSL .../install-skill.sh | bash -s -- --providers claude,copilot
#   bash scripts/install-skill.sh --providers kilo,cline
#
# Flags:
#   --providers <list>   Comma-separated provider names, or "all" (default: all)
#   --wipe               Force rebuild of every KG layer kgrag registers
#   --dry-run            Print what would be done without making any changes
#
# What it does:
#   1. Installs SKILL.md into each agent's skill directory
#   2. Installs Claude Code slash commands (setup-kgrag-mcp, continue,
#      protocol) to ~/.claude/commands/
#   3. Installs kg-rag if kgrag is not found:
#        a. pip install from latest GitHub release wheel (preferred, no git needed)
#        b. pip install from git+https (fallback, needs git)
#        c. poetry add (fallback for Poetry-managed repos)
#   4. Runs `kgrag init` to detect, build, and register every applicable KG
#      layer for the target repo (skips already-registered layers unless
#      --wipe)
#   5. Writes provider MCP configs as requested (.mcp.json and/or .vscode/mcp.json)
#   6. Prints a final summary
#
# NOTE: MCP server registration is written to the workspace-local .mcp.json only.
# Cline reads .mcp.json automatically when opening a workspace, so it needs no
# separate per-repo command install.
#
# Author: Eric G. Suchanek, PhD
# =============================================================================

set -eo pipefail

# ── Parse arguments ───────────────────────────────────────────────────────────
PROVIDERS_ARG="all"
WIPE_FLAG=""
DRY_RUN=""

while [[ $# -gt 0 ]]; do
    case "$1" in
        --providers)
            PROVIDERS_ARG="${2:-all}"
            shift 2
            ;;
        --providers=*)
            PROVIDERS_ARG="${1#*=}"
            shift
            ;;
        --wipe)
            WIPE_FLAG="1"
            shift
            ;;
        --dry-run)
            DRY_RUN="1"
            shift
            ;;
        *)
            echo "Unknown flag: $1"
            echo "Usage: $0 [--providers all|claude,kilo,copilot,cline] [--wipe] [--dry-run]"
            exit 1
            ;;
    esac
done

# Run a command, or in dry-run mode just print what would be executed.
_exec() {
    if [ -n "$DRY_RUN" ]; then
        echo "  [dry-run] $*"
    else
        "$@"
    fi
}

# Normalise to a set of boolean flags
DO_CLAUDE=0; DO_KILO=0; DO_COPILOT=0; DO_CLINE=0

_enable_provider() {
    case "$1" in
        all)    DO_CLAUDE=1; DO_KILO=1; DO_COPILOT=1; DO_CLINE=1 ;;
        claude) DO_CLAUDE=1 ;;
        kilo)   DO_KILO=1 ;;
        copilot)DO_COPILOT=1 ;;
        cline)  DO_CLINE=1 ;;
        *)
            echo "Unknown provider: $1  (valid: all, claude, kilo, copilot, cline)"
            exit 1
            ;;
    esac
}

IFS=',' read -ra _PLIST <<< "$PROVIDERS_ARG"
for _p in "${_PLIST[@]}"; do
    _enable_provider "$(echo "$_p" | tr -d ' ')"
done

# GitHub repo names are case-sensitive on raw.githubusercontent.com; the repo
# is KGRAG (uppercase), not the pre-rename kg_rag/codekg spelling.
REPO="Flux-Frontiers/KGRAG"
BRANCH="main"
RAW_BASE="https://raw.githubusercontent.com/${REPO}/${BRANCH}"

# Install to Claude Code, Kilo Code, and other agent skill directories
SKILL_DIRS=(
    "${HOME}/.claude/skills/kgrag"
    "${HOME}/.kilocode/skills/kgrag"
    "${HOME}/.agents/skills/kgrag"
)

# Global Claude Code command files to install to ~/.claude/commands/.
# changelog-commit.md and release.md are fleet-wide and live in
# ~/.claude/commands already — shipping repo copies would overwrite the
# global ones with a stale, kgrag-specific fork.
CLAUDE_COMMAND_FILES=(
    "setup-kgrag-mcp.md"
    "continue.md"
    "protocol.md"
)

# ── Detect if we're running from inside the repo ─────────────────────────────
# BASH_SOURCE[0] is unbound when piped via curl | bash.
# Use ${BASH_SOURCE:-} (no array index) which is safe even when unset.
_BASH_SOURCE="${BASH_SOURCE:-}"
if [ -n "$_BASH_SOURCE" ] && [ "$_BASH_SOURCE" != "bash" ]; then
    SCRIPT_DIR="$(cd "$(dirname "$_BASH_SOURCE")" && pwd)"
    REPO_ROOT="$(dirname "$SCRIPT_DIR")"
else
    # Running via curl | bash — no local clone available
    SCRIPT_DIR=""
    REPO_ROOT=""
fi
LOCAL_SKILL="${REPO_ROOT:+${REPO_ROOT}/.claude/skills/kgrag/SKILL.md}"

# The target repo is where the user ran the script from (CWD).
TARGET_REPO="${PWD}"

echo "╔══════════════════════════════════════════════════╗"
echo "║       kgrag Integration Installer                ║"
echo "╚══════════════════════════════════════════════════╝"
echo ""
[ -n "$DRY_RUN" ] && echo "  *** DRY RUN — no changes will be made ***"
echo "  Target repo: ${TARGET_REPO}"
_PNAMES=""
[ "$DO_CLAUDE"  = "1" ] && _PNAMES="${_PNAMES} claude"
[ "$DO_KILO"    = "1" ] && _PNAMES="${_PNAMES} kilo"
[ "$DO_COPILOT" = "1" ] && _PNAMES="${_PNAMES} copilot"
[ "$DO_CLINE"   = "1" ] && _PNAMES="${_PNAMES} cline"
echo "  Providers:   ${_PNAMES# }"
echo ""

# ── Step 1: Install SKILL.md to agent skill directories ──────────────────────
echo "── Step 1: Installing skill file ────────────────────"
echo ""

for SKILL_DIR in "${SKILL_DIRS[@]}"; do
    _exec mkdir -p "$SKILL_DIR"

    if [ -f "$LOCAL_SKILL" ]; then
        if [ "${FIRST_RUN:-1}" = "1" ]; then
            echo "→ Local repo detected at: $REPO_ROOT"
            echo "  Copying skill file from local clone..."
            FIRST_RUN=0
        fi
        _exec cp "$LOCAL_SKILL" "${SKILL_DIR}/SKILL.md"
    else
        if [ "${FIRST_RUN:-1}" = "1" ]; then
            echo "→ No local clone detected. Downloading from GitHub..."
            FIRST_RUN=0
        fi
        if [ -n "$DRY_RUN" ]; then
            echo "  [dry-run] would download ${RAW_BASE}/.claude/skills/kgrag/SKILL.md → ${SKILL_DIR}/SKILL.md"
        elif command -v curl &>/dev/null; then
            curl -fsSL "${RAW_BASE}/.claude/skills/kgrag/SKILL.md" -o "${SKILL_DIR}/SKILL.md"
        elif command -v wget &>/dev/null; then
            wget -q "${RAW_BASE}/.claude/skills/kgrag/SKILL.md" -O "${SKILL_DIR}/SKILL.md"
        else
            echo "ERROR: Neither curl nor wget found. Install one and retry."
            exit 1
        fi
    fi

    # Verify (skip in dry-run — file may not exist yet)
    if [ -z "$DRY_RUN" ] && [ ! -f "${SKILL_DIR}/SKILL.md" ]; then
        echo "ERROR: Installation failed for ${SKILL_DIR}"
        exit 1
    fi

    echo "  ✓ ${SKILL_DIR}/SKILL.md"
done

# ── Step 2: Install Claude Code commands to ~/.claude/commands/ ───────────────
echo ""
echo "── Step 2: Installing Claude Code commands ──────────"
echo ""

CLAUDE_CMD_DIR="${HOME}/.claude/commands"
_exec mkdir -p "$CLAUDE_CMD_DIR"

for _CMD_FILE in "${CLAUDE_COMMAND_FILES[@]}"; do
    _DST="${CLAUDE_CMD_DIR}/${_CMD_FILE}"
    _LOCAL_CMD="${REPO_ROOT:+${REPO_ROOT}/.claude/commands/${_CMD_FILE}}"

    if [ -n "$_LOCAL_CMD" ] && [ -f "$_LOCAL_CMD" ]; then
        _exec cp "$_LOCAL_CMD" "$_DST"
        echo "  ✓ Copied from local repo → ${_DST}"
    else
        if [ -n "$DRY_RUN" ]; then
            echo "  [dry-run] would download ${RAW_BASE}/.claude/commands/${_CMD_FILE} → ${_DST}"
        elif command -v curl &>/dev/null; then
            curl -fsSL "${RAW_BASE}/.claude/commands/${_CMD_FILE}" -o "$_DST"
            echo "  ✓ Downloaded → ${_DST}"
        elif command -v wget &>/dev/null; then
            wget -q "${RAW_BASE}/.claude/commands/${_CMD_FILE}" -O "$_DST"
            echo "  ✓ Downloaded → ${_DST}"
        else
            echo "  ⚠ Neither curl nor wget found — skipping ${_CMD_FILE}"
        fi
    fi
done

echo ""
echo "── Cline ─────────────────────────────────────────────"
echo ""
if [ "$DO_CLINE" = "1" ]; then
    echo "  – No separate command needed: Cline reads .mcp.json automatically"
    echo "    (written in Step 5 below)."
else
    echo "  – Skipped (cline not selected)"
fi

# ── Step 3: Install kg-rag if not already present ────────────────────────────
echo ""
echo "── Step 3: Checking kgrag installation ───────────────"
echo ""

# Resolve the latest GitHub release wheel URL (requires curl or wget + python3).
# Returns empty string if no release exists yet.
_latest_wheel_url() {
    local _api="https://api.github.com/repos/${REPO}/releases/latest"
    local _json=""
    if command -v curl &>/dev/null; then
        _json="$(curl -fsSL "$_api" 2>/dev/null || true)"
    elif command -v wget &>/dev/null; then
        _json="$(wget -qO- "$_api" 2>/dev/null || true)"
    fi
    [ -z "$_json" ] && return
    python3 - <<PYEOF
import json, sys
try:
    data = json.loads('''$_json''')
    assets = data.get("assets", [])
    whl = next((a["browser_download_url"] for a in assets if a["name"].endswith(".whl")), None)
    if whl:
        print(whl)
except Exception:
    pass
PYEOF
}

KGRAG_BIN=""

# Probe for an existing installation in order of priority:
#   1. Local .venv in the target repo (Poetry project that added kg-rag)
#   2. Local .venv in the kg_rag source repo (running the script from the repo itself)
#   3. Importable in the active Python environment
#   4. On $PATH
if [ -x "${TARGET_REPO}/.venv/bin/kgrag" ]; then
    KGRAG_BIN="${TARGET_REPO}/.venv/bin/kgrag"
    echo "  ✓ Found kgrag in local venv: ${KGRAG_BIN}"
elif [ -n "${REPO_ROOT}" ] && [ -x "${REPO_ROOT}/.venv/bin/kgrag" ]; then
    KGRAG_BIN="${REPO_ROOT}/.venv/bin/kgrag"
    echo "  ✓ Found kgrag in source venv: ${KGRAG_BIN}"
elif python3 -c "import kg_rag" &>/dev/null 2>&1; then
    # Importable — resolve the binary from the same interpreter's Scripts/bin
    KGRAG_BIN="$(python3 -c "import sysconfig; print(sysconfig.get_path('scripts'))")/kgrag"
    [ -x "$KGRAG_BIN" ] || KGRAG_BIN="kgrag"   # fallback to PATH entry
    echo "  ✓ Found kg_rag in Python environment — kgrag: ${KGRAG_BIN}"
elif command -v kgrag &>/dev/null; then
    KGRAG_BIN="$(command -v kgrag)"
    echo "  ✓ Found kgrag on PATH: ${KGRAG_BIN}"
fi

if [ -z "$KGRAG_BIN" ]; then
    if [ -n "$DRY_RUN" ]; then
        echo "  [dry-run] would install kg-rag from GitHub (wheel or git source)"
        KGRAG_BIN="kgrag"
    else
        # ── Preferred: latest GitHub release wheel (no git needed) ────────────
        WHEEL_URL="$(_latest_wheel_url || true)"
        if [ -n "$WHEEL_URL" ]; then
            echo "  → Installing kg-rag from GitHub release wheel..."
            pip install --quiet "kg-rag @ ${WHEEL_URL}"
        else
            # ── Fallback: pip from git source ─────────────────────────────────
            echo "  → Installing kg-rag from GitHub source..."
            pip install --quiet "kg-rag @ git+https://github.com/${REPO}.git"
        fi
        # Re-probe after install
        KGRAG_BIN="$(command -v kgrag 2>/dev/null || true)"
        if [ -n "$KGRAG_BIN" ]; then
            echo "  ✓ Installed kg-rag — kgrag at: ${KGRAG_BIN}"
        else
            echo "  ✗ Installation failed. Install manually:"
            echo "      pip install 'kg-rag @ git+https://github.com/${REPO}.git'"
            exit 1
        fi
    fi
fi

# ── Step 4: Register this repo's KG layers ────────────────────────────────────
echo ""
echo "── Step 4: Registering KG layers (kgrag init) ────────"
echo ""

if [ -n "$DRY_RUN" ]; then
    echo "  [dry-run] would run: kgrag init ${TARGET_REPO}${WIPE_FLAG:+ --wipe}"
else
    _WIPE_ARG=${WIPE_FLAG:+--wipe}
    (cd "${TARGET_REPO}" && "${KGRAG_BIN}" init "${TARGET_REPO}" ${_WIPE_ARG})
fi

# ── Step 5: Write .mcp.json (Claude Code + Kilo Code) ────────────────────────
echo ""
echo "── Step 5: Configuring .mcp.json (Claude Code + Kilo Code) ──"
echo ""

MCP_JSON="${TARGET_REPO}/.mcp.json"

if [ "$DO_KILO" = "0" ] && [ "$DO_CLAUDE" = "0" ]; then
    echo "  – Skipped (neither claude nor kilo selected)"
elif [ -n "$DRY_RUN" ]; then
    echo "  [dry-run] would upsert kgrag entry in ${MCP_JSON}"
elif [ ! -f "$MCP_JSON" ]; then
    cat > "$MCP_JSON" <<EOF
{
  "mcpServers": {
    "kgrag": {
      "command": "${KGRAG_BIN}",
      "args": ["mcp"]
    }
  }
}
EOF
    echo "  ✓ Created ${MCP_JSON}"
else
    python3 - "$MCP_JSON" "$KGRAG_BIN" <<'PYEOF'
import json, sys
mcp_json  = sys.argv[1]
kgrag_bin = sys.argv[2]
with open(mcp_json, "r") as f:
    data = json.load(f)
if "mcpServers" not in data:
    data["mcpServers"] = {}
data["mcpServers"]["kgrag"] = {
    "command": kgrag_bin,
    "args": ["mcp"]
}
with open(mcp_json, "w") as f:
    json.dump(data, f, indent=2)
    f.write("\n")
PYEOF
    echo "  ✓ Updated kgrag entry in ${MCP_JSON}"
fi

# ── Step 6: Write .vscode/mcp.json (GitHub Copilot) ──────────────────────────
echo ""
echo "── Step 6: Configuring .vscode/mcp.json (GitHub Copilot) ──"
echo ""

VSCODE_DIR="${TARGET_REPO}/.vscode"
VSCODE_MCP="${VSCODE_DIR}/mcp.json"

if [ "$DO_COPILOT" = "0" ]; then
    echo "  – Skipped (copilot not selected)"
elif [ -n "$DRY_RUN" ]; then
    if [ ! -f "$VSCODE_MCP" ]; then
        echo "  [dry-run] would create ${VSCODE_MCP}"
    else
        echo "  [dry-run] would upsert kgrag entry in existing ${VSCODE_MCP}"
    fi
else
    _exec mkdir -p "$VSCODE_DIR"

    if [ ! -f "$VSCODE_MCP" ]; then
        cat > "$VSCODE_MCP" <<EOF
{
  "servers": {
    "kgrag": {
      "type": "stdio",
      "command": "${KGRAG_BIN}",
      "args": ["mcp"]
    }
  }
}
EOF
        echo "  ✓ Created ${VSCODE_MCP}"
    else
        python3 - "$VSCODE_MCP" "$KGRAG_BIN" <<'PYEOF'
import json, sys
vscode_mcp = sys.argv[1]
kgrag_bin  = sys.argv[2]
with open(vscode_mcp, "r") as f:
    data = json.load(f)
if "servers" not in data:
    data["servers"] = {}
data["servers"]["kgrag"] = {
    "type": "stdio",
    "command": kgrag_bin,
    "args": ["mcp"]
}
with open(vscode_mcp, "w") as f:
    json.dump(data, f, indent=2)
    f.write("\n")
PYEOF
        echo "  ✓ Updated kgrag entry in ${VSCODE_MCP}"
    fi
fi  # DO_COPILOT

# ── Done ──────────────────────────────────────────────────────────────────────
echo ""
if [ -n "$DRY_RUN" ]; then
echo "╔══════════════════════════════════════════════════╗"
echo "║   kgrag dry-run complete — no changes made.      ║"
echo "╚══════════════════════════════════════════════════╝"
else
echo "╔══════════════════════════════════════════════════╗"
echo "║   kgrag installed and configured successfully!   ║"
echo "╚══════════════════════════════════════════════════╝"
fi
echo ""
echo "  Repo: ${TARGET_REPO}"
echo ""
echo "  Claude commands installed:"
for _CMD_FILE in "${CLAUDE_COMMAND_FILES[@]}"; do
    echo "    ✓ ~/.claude/commands/${_CMD_FILE}"
done
echo ""
echo "  Providers configured:"
( [ "$DO_CLAUDE" = "1" ] || [ "$DO_KILO" = "1" ] ) && echo "    ✓ Claude Code + Kilo Code  (.mcp.json)"
[ "$DO_COPILOT" = "1" ] && echo "    ✓ GitHub Copilot (.vscode/mcp.json)"
[ "$DO_CLINE"   = "1" ] && echo "    ✓ Cline          (reads .mcp.json automatically)"
echo ""
echo "  ⚠ One manual step required:"
echo "    Reload VS Code to activate the MCP servers:"
echo "    Cmd+Shift+P → 'Developer: Reload Window'"
echo ""
[ "$DO_COPILOT" = "1" ] && echo "  GitHub Copilot: VS Code will prompt you to Trust the kgrag server on first use."
echo ""
echo "  Full docs: https://github.com/Flux-Frontiers/KGRAG/blob/main/docs/INSTALLATION.md"
