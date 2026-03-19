"""
kg_rag — cross-KG registry and federated query layer.

Manages CodeKG, DocKG, and MetaKG instances as a unified corpus.
"""

from kg_rag.corpus_registry import CorpusRegistry
from kg_rag.orchestrator import KGRAG
from kg_rag.person_registry import PersonCorpusRegistry
from kg_rag.primitives import (
    CorpusEntry,
    CorpusStats,
    CrossHit,
    CrossQueryResult,
    CrossSnippet,
    CrossSnippetPack,
    KGEntry,
    KGKind,
    PersonCorpusEntry,
    PersonCorpusStats,
    RegistryStats,
)
from kg_rag.registry import KGRegistry

__all__ = [
    "KGRAG",
    "KGRegistry",
    "CorpusRegistry",
    "PersonCorpusRegistry",
    "KGEntry",
    "KGKind",
    "RegistryStats",
    "CorpusEntry",
    "CorpusStats",
    "PersonCorpusEntry",
    "PersonCorpusStats",
    "CrossHit",
    "CrossQueryResult",
    "CrossSnippet",
    "CrossSnippetPack",
]

__version__ = "0.3.3"
