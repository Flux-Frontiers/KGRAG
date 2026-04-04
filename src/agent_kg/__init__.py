"""agent_kg — Conversational memory as a live, queryable knowledge graph.

AgentKG gives AI agents persistent, semantically searchable memory that
survives across sessions and defeats context rot via KG Context Pruning.

Quick start::

    from agent_kg import AgentKG

    kg = AgentKG(repo_path="/path/to/repo", person_id="alice")
    kg.ingest("We decided to use OAuth for authentication.", role="user")
    kg.ingest("Understood. I'll use OAuth.", role="assistant")

    ctx = kg.assemble_context("authentication strategy", budget=2000)
    print(ctx)

    kg.close()

Architecture:
  - Conversation tree: Turn, Topic, Intent, Entity, Task, Summary nodes
  - UserProfile tree: Preference, Style, Interest, Expertise, Commitment nodes
  - Storage: SQLite (topology) + LanceDB (embeddings)
  - KG Context Pruning: LLM-compresses old turns into Summary nodes
  - MCP server: Exposes all tools to Claude Code and other MCP clients
"""

from agent_kg import assemble, consolidate, prune, query, snapshots
from agent_kg.graph import AgentKG
from agent_kg.profile import UserProfileStore
from agent_kg.schema import (
    Edge,
    EdgeRelation,
    IntentCategory,
    Node,
    NodeKind,
    PruneReport,
    TaskStatus,
)
from agent_kg.session import Session
from agent_kg.store import AgentKGStore
from agent_kg.summarize import Summarizer, SummarizerConfig

__version__ = "0.1.0"
__author__ = "Eric G. Suchanek, PhD"

__all__ = [
    "AgentKG",
    "AgentKGStore",
    "UserProfileStore",
    "Session",
    "Summarizer",
    "SummarizerConfig",
    "Node",
    "Edge",
    "NodeKind",
    "EdgeRelation",
    "TaskStatus",
    "IntentCategory",
    "PruneReport",
    "assemble",
    "consolidate",
    "prune",
    "query",
    "snapshots",
]
