#!/usr/bin/env bash
# install-kgs.sh — install the public KGRAG fleet as uv tools.
#
# Designed for clean machines with no local checkouts required.
# PyPI packages install directly; git-only packages install from GitHub.
# All CLI commands land on PATH automatically via uv.
#
# Usage:
#   ./install-kgs.sh             # install full public fleet
#   REINSTALL=1 ./install-kgs.sh # force --reinstall (rebuild tool venvs from scratch)
#
# Requires: uv  (https://docs.astral.sh/uv/)
#   curl -LsSf https://astral.sh/uv/install.sh | sh

set -euo pipefail

GH="https://github.com/Flux-Frontiers"

REINSTALL_FLAG=""
[ "${REINSTALL:-0}" = "1" ] && REINSTALL_FLAG="--reinstall"

install_pypi() {
  local spec="$1"
  echo "→ uv tool install $spec"
  uv tool install $REINSTALL_FLAG "$spec"
}

install_git() {
  local repo="$1"
  local spec="git+${GH}/${repo}.git"
  echo "→ uv tool install $spec"
  uv tool install $REINSTALL_FLAG "$spec"
}

# PyPI adaptors
install_pypi "pycode-kg"
install_pypi "doc-kg"
install_pypi "ftree-kg"
install_pypi "diary-kg"

# Git-only adaptors (not yet on PyPI)
install_git "gutenberg_kg"
install_git "metabo_kg"
install_git "agent_kg"

# Orchestrator — installs last so all adaptor packages are resolvable
install_pypi "kg-rag[all]"

echo
echo "✅ Done. Installed uv tools:"
uv tool list
