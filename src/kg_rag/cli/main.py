"""
main.py

Root Click group for the KGRAG CLI.

Usage::

    kgrag --help
    kgrag --version
"""

from __future__ import annotations

import kg_rag.cli.cmd_analyze  # noqa: F401 — registers commands
import kg_rag.cli.cmd_corpus  # noqa: F401
import kg_rag.cli.cmd_corpus_io  # noqa: F401 — export / import
import kg_rag.cli.cmd_health  # noqa: F401
import kg_rag.cli.cmd_hooks  # noqa: F401
import kg_rag.cli.cmd_init  # noqa: F401
import kg_rag.cli.cmd_mcp  # noqa: F401
import kg_rag.cli.cmd_models  # noqa: F401
import kg_rag.cli.cmd_query  # noqa: F401
import kg_rag.cli.cmd_registry  # noqa: F401
import kg_rag.cli.cmd_synthesize  # noqa: F401
import kg_rag.cli.cmd_viz  # noqa: F401
import kg_rag.cli.cmd_viz2d  # noqa: F401
from kg_rag.cli.group import cli  # noqa: F401 — re-exported as entrypoint

if __name__ == "__main__":
    cli()
