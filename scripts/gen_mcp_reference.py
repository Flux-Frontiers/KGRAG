#!/usr/bin/env python3
"""Regenerate the tool reference in docs/MCP.md from the live server manifest.

The fleet rule (kgrag_priv FLEET_STANDARDS, "MCP tool names"): a tool's
docstring is its documentation, and references are generated from
``<server> mcp --manifest``, never kept by hand. This rewrites the block
between the GENERATED markers in docs/MCP.md.

Usage::

    python scripts/gen_mcp_reference.py           # rewrite docs/MCP.md
    python scripts/gen_mcp_reference.py --check   # exit 1 if it is stale
"""

from __future__ import annotations

import re
import sys
from pathlib import Path
from typing import Any

BEGIN = "<!-- BEGIN GENERATED TOOL REFERENCE (scripts/gen_mcp_reference.py) -->"
END = "<!-- END GENERATED TOOL REFERENCE -->"
DOC = Path(__file__).resolve().parents[1] / "docs" / "MCP.md"

_GROUPS = (
    ("Canonical tools -- the same five on every fleet server", lambda n, canon: n in canon),
    ("Registry", lambda n, _c: n in ("list_kgs", "kg_info")),
    ("Corpora", lambda n, _c: n.startswith("corpus_")),
    ("Person corpora", lambda n, _c: n.startswith("person_")),
)


def _signature(tool: dict[str, Any]) -> str:
    schema = tool["input_schema"]
    required = set(schema.get("required", []))
    parts = []
    for name, prop in schema.get("properties", {}).items():
        if name in required:
            parts.append(f"**{name}**")
        elif "default" in prop and prop["default"] is not None:
            parts.append(f"{name}={prop['default']!r}")
        else:
            parts.append(name)
    return f"`{tool['name']}`({', '.join(parts)})"


def _markdown(description: str) -> str:
    """A docstring as Markdown: its ``:param x:`` lines become a bullet list."""
    lines, params = [], []
    for line in description.strip().splitlines():
        m = re.match(r"\s*:param (\w+):\s*(.*)", line)
        if m:
            params.append(f"- `{m.group(1)}` -- {m.group(2)}")
        elif params and line.startswith((" ", "\t")) and line.strip():
            params[-1] += " " + line.strip()
        elif not params:
            lines.append(line.strip())
    body = "\n".join(lines).strip().replace("``", "`")
    return body + ("\n\n" + "\n".join(params).replace("``", "`") if params else "")


def render(manifest: dict[str, Any]) -> str:
    canon = set(manifest["canonical"])
    tools = manifest["tools"]
    out = [
        BEGIN,
        "",
        f"The server registers **{len(tools)} tools**. Required parameters are shown in "
        "**bold**; the rest show their defaults. Generated from `kgrag mcp --manifest`.",
        "",
    ]
    for title, member in _GROUPS:
        group = [t for t in tools if member(t["name"], canon)]
        if not group:
            continue
        out += [f"### {title}", ""]
        for tool in group:
            out += [f"#### {_signature(tool)}", "", _markdown(tool["description"]), ""]
    out.append(END)
    return "\n".join(out)


def main(argv: list[str]) -> int:
    from kg_utils.mcp import manifest  # noqa: PLC0415

    from kg_rag.mcp_server import build_server  # noqa: PLC0415

    text = DOC.read_text(encoding="utf-8")
    start, end = text.index(BEGIN), text.index(END) + len(END)
    fresh = text[:start] + render(manifest(build_server())) + text[end:]
    if "--check" in argv:
        if fresh != text:
            print("docs/MCP.md tool reference is stale: run scripts/gen_mcp_reference.py")
            return 1
        return 0
    DOC.write_text(fresh, encoding="utf-8")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
