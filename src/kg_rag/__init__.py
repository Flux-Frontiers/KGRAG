"""
kg_rag — cross-KG registry and federated query layer.

Manages CodeKG, DocKG, and MetaKG instances as a unified corpus.
"""
from kg_rag.primitives import (
    CrossHit,
    CrossQueryResult,
    CrossSnippet,
    CrossSnippetPack,
    KGEntry,
    KGKind,
    RegistryStats,
)
from kg_rag.registry import KGRegistry
from kg_rag.orchestrator import KGRAG

__all__ = [
    "KGRAG",
    "KGRegistry",
    "KGEntry",
    "KGKind",
    "RegistryStats",
    "CrossHit",
    "CrossQueryResult",
    "CrossSnippet",
    "CrossSnippetPack",
]
