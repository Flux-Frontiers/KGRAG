"""disulfide_adapter.py — KGAdapter for DisulfideKG (stub until library is released)."""

from __future__ import annotations

from kg_rag.adapters._stub_adapter import StubKGAdapter
from kg_rag.primitives import KGEntry, KGKind


class DisulfideKGAdapter(StubKGAdapter):
    """Adapter for DisulfideKG — protein disulfide bond knowledge graph.

    :param entry: A KGEntry instance for this KG.
    """

    _pkg_name: str = "disulfide_kg"
    _kind: KGKind = KGKind.DISULFIDE

    def __init__(self, entry: KGEntry) -> None:
        super().__init__(entry)
