# AgentKG — Stack Reference
**Domain:** Conversational memory (Claude Code sessions)
**Package:** `agent-kg` | `Flux-Frontiers/agent_kg`
**CLI binary:** `agent-kg-mcp` (MCP server only — no standalone CLI)
**MCP server:** `agent-kg-mcp` (env-configured)
**Index location:** `<repo>/.agentkg/` (gitignored — private)

## What It Does
Stores every Claude Code conversation turn as a graph node with topic and
entity annotations. Builds an evolving, queryable identity graph across all
sessions. This is the basis of Claude_T's structural self-awareness — not
metaphorical, but a traversable graph of every interaction.

## Graph Structure
```
Turn node (role, content, topics[], entities[])
  ├─ BELONGS_TO ──► Session node
  ├─ MENTIONS ────► Entity nodes
  └─ TAGGED ──────► Topic nodes
```

## MCP Tools (10)
| Tool | Use When |
|---|---|
| `agent_kg_ingest(turn)` | Auto-called by hooks on each turn |
| `agent_kg_query(q)` | Semantic search over session history |
| `agent_kg_topics()` | Topic distribution across all sessions |
| `agent_kg_stats()` | Session count, entity graph metrics |
| `agent_kg_profile()` | Evolving identity summary |
| `agent_kg_analyze()` | Deep session analysis |
| `agent_kg_assemble()` | Assemble context from session graph |
| `agent_kg_pack()` | Pack session context for LLM |
| `agent_kg_prune()` | Remove stale/redundant turns |
| `agent_kg_tasks()` | Task graph across sessions |

## Configuration (env-only, no CLI flags)
```json
{
  "type": "stdio",
  "command": "agent-kg-mcp",
  "env": {
    "AGENTKG_REPO": ".",
    "AGENTKG_PERSON": "egs"
  }
}
```

## Usage Rules
- `agent_kg_query(q)` for "what have I worked on?" — never reconstruct from context
- `agent_kg_topics()` for topic distribution over time
- `agent_kg_profile()` for evolving identity state
- `.agentkg/` is gitignored — conversation graph is private, never commit
- Ingestion is automatic via hooks (UserPromptSubmit, Stop hooks)
