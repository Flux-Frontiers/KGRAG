"""
primitives.py

Core data types for the KGRAG registry system.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import Enum
from pathlib import Path
from typing import Any


class KGKind(str, Enum):
    """Kind of knowledge graph."""

    CODE = "code"
    DOC = "doc"
    META = "meta"

    @classmethod
    def from_str(cls, s: str) -> KGKind:
        try:
            return cls(s.lower())
        except ValueError:
            raise ValueError(f"Unknown KG kind: {s!r}. Choose from: {[e.value for e in cls]}")


@dataclass
class KGEntry:
    """Registry entry for a single knowledge graph instance.

    :param id: Unique identifier (UUID string).
    :param name: Human-readable name for this KG instance.
    :param kind: Kind of knowledge graph (code, doc, meta).
    :param repo_path: Absolute path to the repository/project root.
    :param venv_path: Absolute path to the Python virtual environment.
    :param sqlite_path: Absolute path to the SQLite database file (if any).
    :param lancedb_path: Absolute path to the LanceDB directory (if any).
    :param version: Version string of the KG package.
    :param tags: Optional list of tags for grouping/filtering.
    :param created_at: When this entry was registered.
    :param updated_at: When this entry was last updated.
    :param metadata: Flexible extra key-value data.
    """

    name: str
    kind: KGKind
    repo_path: Path
    venv_path: Path
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    sqlite_path: Path | None = None
    lancedb_path: Path | None = None
    version: str = "unknown"
    tags: list[str] = field(default_factory=list)
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        # Normalize to absolute Paths
        self.repo_path = Path(self.repo_path).resolve()
        self.venv_path = Path(self.venv_path).resolve()
        if self.sqlite_path is not None:
            self.sqlite_path = Path(self.sqlite_path).resolve()
        if self.lancedb_path is not None:
            self.lancedb_path = Path(self.lancedb_path).resolve()
        if isinstance(self.kind, str):
            self.kind = KGKind.from_str(self.kind)

    @property
    def is_built(self) -> bool:
        """True if at least one database exists and is populated."""
        if self.sqlite_path and self.sqlite_path.exists():
            return True
        if self.lancedb_path and self.lancedb_path.exists():
            return True
        return False

    @property
    def label(self) -> str:
        """Short display label: name (kind)."""
        return f"{self.name} ({self.kind.value})"


@dataclass
class RegistryStats:
    """Summary statistics for the KGRAG registry.

    :param total: Total number of registered KGs.
    :param by_kind: Count per KGKind.
    :param built: Number of KGs with at least one built database.
    :param registry_path: Path to the registry SQLite file.
    """

    total: int
    by_kind: dict[str, int]
    built: int
    registry_path: Path


@dataclass
class CrossHit:
    """A single result hit from a cross-KG query.

    :param kg_name: Name of the source KG.
    :param kg_kind: Kind of the source KG.
    :param node_id: Node identifier in the source KG.
    :param name: Node name.
    :param kind: Node kind within its KG (function/class/chunk/etc).
    :param score: Relevance score (higher is better).
    :param summary: Short description or docstring snippet.
    :param source_path: File/document path within the repo.
    """

    kg_name: str
    kg_kind: KGKind
    node_id: str
    name: str
    kind: str
    score: float
    summary: str = ""
    source_path: str = ""


@dataclass
class CrossQueryResult:
    """Aggregated results from a cross-KG query.

    :param query: The original query string.
    :param hits: All hits ranked by score.
    :param by_kg: Hits grouped by KG name.
    :param total_hits: Total number of hits.
    :param kgs_queried: Number of KGs that were queried.
    """

    query: str
    hits: list[CrossHit]
    by_kg: dict[str, list[CrossHit]]
    total_hits: int
    kgs_queried: int


@dataclass
class CrossSnippet:
    """A source snippet from a cross-KG pack operation.

    :param kg_name: Name of the source KG.
    :param kg_kind: Kind of the source KG.
    :param node_id: Node identifier.
    :param source_path: File/document path.
    :param lineno: Starting line number (code KGs).
    :param end_lineno: Ending line number (code KGs).
    :param content: The raw source text.
    :param score: Relevance score.
    """

    kg_name: str
    kg_kind: KGKind
    node_id: str
    source_path: str
    content: str
    score: float = 0.0
    lineno: int | None = None
    end_lineno: int | None = None


@dataclass
class CrossSnippetPack:
    """Aggregated snippet pack from a cross-KG query.

    :param query: The original query string.
    :param snippets: All snippets.
    :param total_tokens_approx: Approximate token count.
    :param kgs_queried: Number of KGs that contributed snippets.
    """

    query: str
    snippets: list[CrossSnippet]
    total_tokens_approx: int
    kgs_queried: int

    def render(self) -> str:
        """Render the pack as a single LLM-ready string."""
        parts = [f"# Cross-KG Pack: {self.query!r}\n"]
        for s in self.snippets:
            header = f"## [{s.kg_kind.value}:{s.kg_name}] {s.source_path}"
            if s.lineno:
                header += f":{s.lineno}-{s.end_lineno}"
            parts.append(header)
            parts.append(f"```\n{s.content}\n```")
        return "\n\n".join(parts)
