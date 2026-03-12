"""
main.py

Root Click group for the KGRAG CLI.

Usage::

    kgrag --help
    kgrag --version
"""
from __future__ import annotations

from kg_rag.cli.group import cli  # noqa: F401 — re-exported as entrypoint

import kg_rag.cli.cmd_registry  # noqa: F401 — registers commands
import kg_rag.cli.cmd_query     # noqa: F401
import kg_rag.cli.cmd_analyze   # noqa: F401
import kg_rag.cli.cmd_mcp       # noqa: F401


if __name__ == "__main__":
    cli()
