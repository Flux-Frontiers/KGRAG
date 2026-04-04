"""mcp/server.py — MCP tool surface for AgentKG.

Exposes the following tools to MCP clients (e.g. Claude Code):

  agent_kg_ingest(turn_text, role, repo, person_id, session_id)
      Add a turn to the conversation graph. Returns IngestResult summary.

  agent_kg_query(query, k, repo, person_id)
      Semantic search over the conversation graph.

  agent_kg_pack(query, k, repo, person_id)
      Extract conversation snippets for LLM context.

  agent_kg_assemble(query, budget, repo, person_id, session_id)
      Assemble a full token-budgeted context block.

  agent_kg_prune(window, repo, person_id, session_id)
      Run KG Context Pruning.

  agent_kg_stats(repo, person_id)
      Node/edge counts, session info, topic distribution.

  agent_kg_topics(repo, person_id)
      List all tracked topics.

  agent_kg_tasks(repo, person_id)
      List all open tasks.

  agent_kg_profile(person_id)
      Return the UserProfile in Markdown.

  agent_kg_analyze(repo, person_id)
      Full Markdown analysis report.

Configuration via environment:
  AGENTKG_REPO      — default repo path (default: cwd)
  AGENTKG_PERSON    — default person ID (default: "default")
  AGENTKG_SESSION   — default session UUID (optional)
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

import mcp.server.stdio
import mcp.types as types
from mcp.server import Server

from agent_kg.graph import AgentKG

_DEFAULT_REPO = os.environ.get("AGENTKG_REPO", ".")
_DEFAULT_PERSON = os.environ.get("AGENTKG_PERSON", "default")
_DEFAULT_SESSION = os.environ.get("AGENTKG_SESSION", None)

app = Server("agent-kg")

# Tool definitions
_TOOLS = [
    types.Tool(
        name="agent_kg_ingest",
        description="Add a conversation turn to the AgentKG graph.",
        inputSchema={
            "type": "object",
            "properties": {
                "turn_text": {"type": "string", "description": "The turn text to ingest."},
                "role": {"type": "string", "enum": ["user", "assistant"], "default": "user"},
                "repo": {"type": "string", "description": "Repo root path.", "default": _DEFAULT_REPO},
                "person_id": {"type": "string", "description": "Person ID.", "default": _DEFAULT_PERSON},
                "session_id": {"type": "string", "description": "Session UUID (optional)."},
            },
            "required": ["turn_text"],
        },
    ),
    types.Tool(
        name="agent_kg_query",
        description="Semantic search over the conversation graph.",
        inputSchema={
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "Natural-language query."},
                "k": {"type": "integer", "default": 8, "description": "Number of results."},
                "repo": {"type": "string", "default": _DEFAULT_REPO},
                "person_id": {"type": "string", "default": _DEFAULT_PERSON},
            },
            "required": ["query"],
        },
    ),
    types.Tool(
        name="agent_kg_pack",
        description="Extract conversation snippets for LLM context.",
        inputSchema={
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "Natural-language query."},
                "k": {"type": "integer", "default": 6},
                "repo": {"type": "string", "default": _DEFAULT_REPO},
                "person_id": {"type": "string", "default": _DEFAULT_PERSON},
            },
            "required": ["query"],
        },
    ),
    types.Tool(
        name="agent_kg_assemble",
        description="Assemble a full token-budgeted context block from the conversation graph.",
        inputSchema={
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "Current query for semantic retrieval."},
                "budget": {"type": "integer", "default": 4000, "description": "Token budget."},
                "repo": {"type": "string", "default": _DEFAULT_REPO},
                "person_id": {"type": "string", "default": _DEFAULT_PERSON},
                "session_id": {"type": "string"},
            },
            "required": ["query"],
        },
    ),
    types.Tool(
        name="agent_kg_prune",
        description="Run KG Context Pruning — compress old turns into Summary nodes.",
        inputSchema={
            "type": "object",
            "properties": {
                "window": {"type": "integer", "default": 20, "description": "Hot window size."},
                "repo": {"type": "string", "default": _DEFAULT_REPO},
                "person_id": {"type": "string", "default": _DEFAULT_PERSON},
                "session_id": {"type": "string"},
            },
        },
    ),
    types.Tool(
        name="agent_kg_stats",
        description="Return AgentKG statistics: node/edge counts, session info.",
        inputSchema={
            "type": "object",
            "properties": {
                "repo": {"type": "string", "default": _DEFAULT_REPO},
                "person_id": {"type": "string", "default": _DEFAULT_PERSON},
            },
        },
    ),
    types.Tool(
        name="agent_kg_topics",
        description="List all topic nodes tracked in the conversation graph.",
        inputSchema={
            "type": "object",
            "properties": {
                "repo": {"type": "string", "default": _DEFAULT_REPO},
                "person_id": {"type": "string", "default": _DEFAULT_PERSON},
            },
        },
    ),
    types.Tool(
        name="agent_kg_tasks",
        description="List all open task nodes extracted from the conversation.",
        inputSchema={
            "type": "object",
            "properties": {
                "repo": {"type": "string", "default": _DEFAULT_REPO},
                "person_id": {"type": "string", "default": _DEFAULT_PERSON},
            },
        },
    ),
    types.Tool(
        name="agent_kg_profile",
        description="Return the UserProfile (preferences, commitments, expertise) as Markdown.",
        inputSchema={
            "type": "object",
            "properties": {
                "person_id": {"type": "string", "default": _DEFAULT_PERSON},
            },
        },
    ),
    types.Tool(
        name="agent_kg_analyze",
        description="Return a full Markdown analysis report for the AgentKG instance.",
        inputSchema={
            "type": "object",
            "properties": {
                "repo": {"type": "string", "default": _DEFAULT_REPO},
                "person_id": {"type": "string", "default": _DEFAULT_PERSON},
            },
        },
    ),
]


@app.list_tools()
async def list_tools() -> list[types.Tool]:
    return _TOOLS


@app.call_tool()
async def call_tool(name: str, arguments: dict[str, Any]) -> list[types.TextContent]:
    repo = arguments.get("repo", _DEFAULT_REPO)
    person_id = arguments.get("person_id", _DEFAULT_PERSON)
    session_id = arguments.get("session_id", _DEFAULT_SESSION) or None

    try:
        if name == "agent_kg_ingest":
            kg = AgentKG(repo_path=repo, person_id=person_id, session_id=session_id)
            result = kg.ingest(
                text=arguments["turn_text"],
                role=arguments.get("role", "user"),
            )
            kg.close()
            text = (
                f"Ingested turn (role={arguments.get('role', 'user')}).\n"
                f"Topics: {[t.label for t in result.topic_nodes]}\n"
                f"Entities: {[e.label for e in result.entity_nodes]}\n"
                f"Tasks: {[t.label for t in result.task_nodes]}\n"
                f"Profile updates: {len(result.profile_updates)}"
            )

        elif name == "agent_kg_query":
            kg = AgentKG(repo_path=repo, person_id=person_id)
            hits = kg.query(arguments["query"], k=arguments.get("k", 8))
            kg.close()
            if not hits:
                text = "No results found."
            else:
                lines = []
                for h in hits:
                    lines.append(
                        f"[{h.get('kind', '?')}] (score={h.get('score', 0):.3f}) "
                        f"{h.get('text', '')[:200]}"
                    )
                text = "\n".join(lines)

        elif name == "agent_kg_pack":
            kg = AgentKG(repo_path=repo, person_id=person_id)
            snippets = kg.pack(arguments["query"], k=arguments.get("k", 6))
            kg.close()
            parts = [f"[{s.get('kind')}] {s.get('content', '')}" for s in snippets]
            text = "\n\n---\n\n".join(parts) or "No snippets found."

        elif name == "agent_kg_assemble":
            kg = AgentKG(repo_path=repo, person_id=person_id, session_id=session_id)
            text = kg.assemble_context(
                arguments["query"],
                budget=arguments.get("budget", 4000),
            )
            kg.close()

        elif name == "agent_kg_prune":
            kg = AgentKG(repo_path=repo, person_id=person_id, session_id=session_id)
            if not kg.should_prune():
                text = "Not enough cold turns to prune yet."
            else:
                report = kg.prune(window=arguments.get("window", 20))
                text = (
                    f"Pruning pass {report.pruning_pass} complete.\n"
                    f"Summaries created: {report.summaries_created}\n"
                    f"Turns pruned: {report.turns_pruned}\n"
                    f"Nodes removed: {report.nodes_removed}\n"
                    f"Token savings ~{report.token_savings_approx}"
                )
            kg.close()

        elif name == "agent_kg_stats":
            kg = AgentKG(repo_path=repo, person_id=person_id)
            s = kg.stats()
            kg.close()
            lines = [f"AgentKG stats — {repo}"]
            for k, v in s.items():
                if k != "kind_counts":
                    lines.append(f"  {k}: {v}")
            if s.get("kind_counts"):
                lines.append("  By kind:")
                for kind, count in sorted(s["kind_counts"].items()):
                    lines.append(f"    {kind}: {count}")
            text = "\n".join(lines)

        elif name == "agent_kg_topics":
            kg = AgentKG(repo_path=repo, person_id=person_id)
            from agent_kg.schema import NodeKind  # noqa: PLC0415
            topics = kg._store.get_nodes_by_kind(NodeKind.TOPIC)
            kg.close()
            if not topics:
                text = "No topics tracked yet."
            else:
                lines = [f"- {t.label or t.text} (last seen: {t.last_seen.strftime('%Y-%m-%d')})"
                         for t in topics]
                text = f"Topics ({len(topics)}):\n" + "\n".join(lines)

        elif name == "agent_kg_tasks":
            kg = AgentKG(repo_path=repo, person_id=person_id)
            tasks = kg._store.get_open_tasks()
            kg.close()
            if not tasks:
                text = "No open tasks."
            else:
                lines = [f"- [{t.status}] {t.label or t.text}" for t in tasks]
                text = f"Open tasks ({len(tasks)}):\n" + "\n".join(lines)

        elif name == "agent_kg_profile":
            from agent_kg.profile import UserProfileStore  # noqa: PLC0415
            from pathlib import Path  # noqa: PLC0415
            profile_dir = Path.home() / ".kgrag" / "profiles" / person_id
            profile = UserProfileStore(profile_dir)
            text = profile.render_markdown()
            profile.close()

        elif name == "agent_kg_analyze":
            kg = AgentKG(repo_path=repo, person_id=person_id)
            text = kg.analyze()
            kg.close()

        else:
            text = f"Unknown tool: {name}"

    except Exception as exc:  # pylint: disable=broad-exception-caught
        text = f"Error in {name}: {exc}"

    return [types.TextContent(type="text", text=text)]


def main() -> None:
    """Start the AgentKG MCP server on stdio."""
    import asyncio  # noqa: PLC0415
    asyncio.run(mcp.server.stdio.stdio_server(app))


if __name__ == "__main__":
    main()
