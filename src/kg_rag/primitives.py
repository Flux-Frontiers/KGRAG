"""
primitives.py

Core data types for the KGRAG registry system.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import StrEnum
from pathlib import Path
from typing import Any


class KGKind(StrEnum):
    """Kind of knowledge graph."""

    CODE = "code"
    DOC = "doc"
    META = "meta"
    DIARY = "diary"
    VERSE = "verse"
    MEMORY = "memory"
    DISULFIDE = "disulfide"
    PDBFILE = "pdbfile"
    LEGAL = "legal"
    PERSON = "person"
    AGENT = "agent"
    FILETREE = "filetree"
    GUTENBERG = "gutenberg"
    IA = "ia"

    @classmethod
    def from_str(cls, s: str) -> KGKind:
        try:
            return cls(s.lower())
        except ValueError:
            raise ValueError(
                f"Unknown KG kind: {s!r}. Choose from: {[e.value for e in cls]}"
            ) from None


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
        **Deprecated** for builders that have migrated to sqlite-vec — use
        ``vectors_path``.  Still written for kinds that ship a LanceDB index
        (doc/memory/gutenberg corpora built by pre-sqlite-vec builders).
    :param vectors_path: Absolute path to the sqlite-vec vector store *file*
        (if any), e.g. ``<repo>/.pycodekg/vectors.sqlite``.  This is the
        vector backend for pycode-kg >=0.20.0 and supersedes ``lancedb_path``.
    :param version: Version of the source repository (from its pyproject.toml).
        Meaningful for code-like KGs where the repo is the source of truth;
        often ``"unknown"`` for doc/memory/diary corpora assembled from loose
        files.
    :param builder_version: Version of the KG builder package (doc_kg,
        pycode_kg, metabokg, …) that produced the database.  Captured at
        registration time by reading the ``_kgrag_meta`` table stamped
        inside the built SQLite.  This is the version that actually defines
        the database schema and ingestion contract.
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
    vectors_path: Path | None = None
    version: str = "unknown"
    builder_version: str = "unknown"
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
        if self.vectors_path is not None:
            self.vectors_path = Path(self.vectors_path).resolve()
        if isinstance(self.kind, str):
            self.kind = KGKind.from_str(self.kind)

    @property
    def is_built(self) -> bool:
        """True if at least one database exists and is populated."""
        if self.sqlite_path and self.sqlite_path.exists():
            return True
        if self.vectors_path and self.vectors_path.exists():
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
class PersonCorpusEntry:
    """A corpus representing a person — grouping all KGs relevant to that individual.

    Extends the corpus concept with personal metadata (birth year, address, etc.)
    and is intended to hold KGs of types such as DOC, MEMORY, DIARY, VERSE, and
    CODE that together describe or belong to a specific person.

    :param name: Full name of the person.
    :param id: Unique identifier (UUID string).
    :param kg_ids: List of KGEntry UUIDs associated with this person.
    :param birth_year: Year of birth (int).
    :param birth_date: Full birth date as ISO string (YYYY-MM-DD), if known.
    :param address: Mailing/home address.
    :param email: Primary email address.
    :param phone: Primary phone number.
    :param notes: Free-form notes about this person.
    :param tags: Optional list of tags for grouping/filtering.
    :param created_at: When this entry was created.
    :param updated_at: When this entry was last modified.
    :param metadata: Flexible extra key-value data.
    """

    name: str
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    kg_ids: list[str] = field(default_factory=list)
    birth_year: int | None = None
    birth_date: str | None = None
    address: str = ""
    email: str = ""
    phone: str = ""
    notes: str = ""
    tags: list[str] = field(default_factory=list)
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    metadata: dict[str, Any] = field(default_factory=dict)

    @property
    def size(self) -> int:
        """Number of KGs associated with this person."""
        return len(self.kg_ids)


@dataclass
class PersonCorpusStats:
    """Summary statistics for the person corpus registry.

    :param total: Total number of person corpus entries.
    :param total_kg_refs: Total KG references across all person entries.
    :param registry_path: Path to the registry SQLite file.
    """

    total: int
    total_kg_refs: int
    registry_path: Path


@dataclass(frozen=True)
class QueryScope:
    """Query-time scoping filter applied *inside* a KG before ranking is final.

    Lets a federated query restrict retrieval to a subtree and/or node kinds —
    e.g. one genre of a consolidated Gutenberg corpus — instead of querying the
    whole KG and post-filtering, which lets out-of-scope results starve the
    relevant ones.

    Adapters that support pushdown (``KGAdapter.supports_scope``) forward the
    constraints into their backend retrieval (vector prefilter + lexical SQL).
    For adapters that cannot, the orchestrator applies :meth:`matches` to the
    returned hits/snippets as a best-effort post-filter, so scoping degrades
    gracefully rather than being silently ignored.

    :param source_path_prefixes: Keep only results whose ``source_path`` starts
        with one of these prefixes (e.g. ``("science-fiction/",)``).  ``None``
        or empty imposes no path constraint.
    :param node_kinds: Keep only results whose node ``kind`` is in this set
        (e.g. ``("chunk", "section")`` to drop structural/topic nodes).  Note
        that snippet packs may not carry a ``kind``; kind filtering on snippets
        is therefore only reliable via adapter pushdown.
    :param metadata_eq: Reserved for future metadata-equality scoping.  Accepted
        for API stability but not yet enforced.
    """

    source_path_prefixes: tuple[str, ...] | None = None
    node_kinds: tuple[str, ...] | None = None
    metadata_eq: dict[str, str] | None = None

    def __post_init__(self) -> None:
        # Normalise list inputs to tuples so the dataclass stays hashable/frozen.
        if self.source_path_prefixes is not None:
            object.__setattr__(self, "source_path_prefixes", tuple(self.source_path_prefixes))
        if self.node_kinds is not None:
            object.__setattr__(self, "node_kinds", tuple(self.node_kinds))

    @property
    def is_empty(self) -> bool:
        """True if this scope imposes no constraints (a no-op filter)."""
        return not (self.source_path_prefixes or self.node_kinds or self.metadata_eq)

    def __bool__(self) -> bool:
        return not self.is_empty

    def matches(self, *, source_path: str = "", kind: str | None = None) -> bool:
        """Return True if a result with these attributes is in scope.

        Applied as a post-filter for adapters without pushdown.  A ``None``
        ``kind`` is treated as "unknown" and is **not** rejected by a
        ``node_kinds`` constraint, so kind filtering never silently drops
        snippets that simply lack a kind field.

        :param source_path: The result's source/document path.
        :param kind: The result's node kind, or None if unknown.
        :return: True if the result satisfies all enforced constraints.
        """
        if self.source_path_prefixes:
            sp = source_path or ""
            if not any(sp.startswith(p) for p in self.source_path_prefixes):
                return False
        if self.node_kinds and kind is not None and kind not in self.node_kinds:
            return False
        return True


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
class CorpusEntry:
    """A named collection of KG instances grouped under a single logical corpus.

    :param id: Unique identifier (UUID string).
    :param name: Human-readable name for this corpus.
    :param kg_ids: List of KGEntry UUIDs that belong to this corpus.
    :param description: Optional description of what this corpus represents.
    :param tags: Optional list of tags for grouping/filtering.
    :param created_at: When this corpus was created.
    :param updated_at: When this corpus was last modified.
    :param metadata: Flexible extra key-value data.
    """

    name: str
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    kg_ids: list[str] = field(default_factory=list)
    description: str = ""
    tags: list[str] = field(default_factory=list)
    created_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    updated_at: datetime = field(default_factory=lambda: datetime.now(UTC))
    metadata: dict[str, Any] = field(default_factory=dict)

    @property
    def size(self) -> int:
        """Number of KGs in this corpus."""
        return len(self.kg_ids)


@dataclass
class CorpusStats:
    """Summary statistics for the corpus registry.

    :param total: Total number of corpora.
    :param total_kg_refs: Total KG references across all corpora.
    :param registry_path: Path to the registry SQLite file.
    """

    total: int
    total_kg_refs: int
    registry_path: Path


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
            if len(s.content.strip()) < 30:
                continue
            header = f"## [{s.kg_kind.value}:{s.kg_name}] {s.source_path}"
            if s.lineno:
                header += f":{s.lineno}-{s.end_lineno}"
            parts.append(header)
            parts.append(f"```\n{s.content}\n```")
        return "\n\n".join(parts)
