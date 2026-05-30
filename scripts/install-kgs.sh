#!/usr/bin/env bash
# install-kgs.sh — install/refresh the KGRAG fleet as editable uv tools.
#
# One source of truth for the whole knowledge-graph toolchain. Each adaptor is
# installed with `uv tool install --editable`, so the global command (e.g.
# `gutenkg`, `dockg`, `metabokg`) tracks the live repo source — no `poetry run`,
# no cwd dance, commands available from anywhere.
#
# Usage:
#   ./install-kgs.sh             # install/refresh every adaptor + the kgrag orchestrator
#   ./install-kgs.sh gutenberg_kg metabo_kg   # only the named repos
#   REINSTALL=1 ./install-kgs.sh  # force --reinstall (rebuild venvs from scratch)
#
# Toolchain: uv only. (pipx is reserved for non-KG tools like fabric / poethepoet.)

set -euo pipefail

REPOS="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# The orchestrator carries the [all] extra so it can import every adaptor for
# federation. Adaptors install with their default extras.
KGRAG_REPO="kgrag"
KGRAG_EXTRAS="all"

# Adaptor repos, in dependency-friendly order (doc/pycode first — others lean on
# the same DocKG/embedding stack).
ADAPTORS=(
  doc_kg          # dockg
  pycode_kg       # pycodekg
  gutenberg_kg    # gutenkg
  metabo_kg       # metabokg
  ftree_kg        # ftreekg
  diary_kg        # diarykg, diary-transformer, diary-embedder
  memory_kg       # memorykg
  agent_kg        # agent-kg
  ia_kg           # iakg
)

REINSTALL_FLAG=""
[ "${REINSTALL:-0}" = "1" ] && REINSTALL_FLAG="--reinstall"

install_one() {
  local repo="$1" extras="${2:-}"
  local path="$REPOS/$repo"
  if [ ! -f "$path/pyproject.toml" ]; then
    echo "  ⚠️  skip $repo — no pyproject.toml at $path"
    return
  fi
  local spec="$path"
  [ -n "$extras" ] && spec="${path}[${extras}]"
  echo "→ uv tool install --editable $spec"
  uv tool install --editable $REINSTALL_FLAG "$spec"
}

# If repo args were given, install only those; otherwise the full fleet + kgrag.
if [ "$#" -gt 0 ]; then
  for repo in "$@"; do
    if [ "$repo" = "$KGRAG_REPO" ]; then
      install_one "$KGRAG_REPO" "$KGRAG_EXTRAS"
    else
      install_one "$repo"
    fi
  done
else
  for repo in "${ADAPTORS[@]}"; do
    install_one "$repo"
  done
  install_one "$KGRAG_REPO" "$KGRAG_EXTRAS"
fi

echo
echo "✅ Done. Installed uv tools:"
uv tool list
