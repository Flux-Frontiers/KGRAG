"""legal_adapter.py — KGAdapter for LegalKG (stub until library is released)."""

from __future__ import annotations

from kg_rag.adapters._stub_adapter import StubKGAdapter
from kg_rag.primitives import KGEntry, KGKind


class LegalKGAdapter(StubKGAdapter):
    """Adapter for LegalKG — legal corpus knowledge graph (US code, case law, etc.).

    :param entry: A KGEntry instance for this KG.
    """

    _pkg_name: str = "legal_kg"
    _kind: KGKind = KGKind.LEGAL

    def __init__(self, entry: KGEntry) -> None:
        super().__init__(entry)
