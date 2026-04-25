"""person_adapter.py — KGAdapter for PersonKG (stub until library is released)."""

from __future__ import annotations

from kg_rag.adapters._stub_adapter import StubKGAdapter
from kg_rag.primitives import KGEntry, KGKind


class PersonKGAdapter(StubKGAdapter):
    """Adapter for PersonKG — individual person knowledge graph.

    Intended to hold biographical, relational, and contextual knowledge
    about a specific person (biography, relationships, affiliations, etc.).

    :param entry: A KGEntry instance for this KG.
    """

    _pkg_name: str = "person_kg"
    _kind: KGKind = KGKind.PERSON

    def __init__(self, entry: KGEntry, embedder=None) -> None:
        super().__init__(entry, embedder=embedder)
