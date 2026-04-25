"""verse_adapter.py — KGAdapter for VerseKG (stub until library is released)."""

from __future__ import annotations

from kg_rag.adapters._stub_adapter import StubKGAdapter
from kg_rag.primitives import KGEntry, KGKind


class VerseKGAdapter(StubKGAdapter):
    """Adapter for VerseKG — poetry / verse knowledge graph.

    :param entry: A KGEntry instance for this KG.
    """

    _pkg_name: str = "verse_kg"
    _kind: KGKind = KGKind.VERSE

    def __init__(self, entry: KGEntry, embedder=None) -> None:
        super().__init__(entry, embedder=embedder)
