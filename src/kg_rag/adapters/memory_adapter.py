"""memory_adapter.py — KGAdapter for MemoryKG (stub until library is released)."""

from __future__ import annotations

from kg_rag.adapters._stub_adapter import StubKGAdapter
from kg_rag.primitives import KGEntry, KGKind


class MemoryKGAdapter(StubKGAdapter):
    """Adapter for MemoryKG — episodic / long-term memory knowledge graph.

    :param entry: A KGEntry instance for this KG.
    """

    _pkg_name: str = "memory_kg"
    _kind: KGKind = KGKind.MEMORY

    def __init__(self, entry: KGEntry, embedder=None) -> None:
        super().__init__(entry, embedder=embedder)
