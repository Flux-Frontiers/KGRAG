"""ia_adapter.py — KGAdapter stub for IABookKG (Internet Archive book corpus)."""

from __future__ import annotations

from kg_rag.adapters._stub_adapter import StubKGAdapter
from kg_rag.primitives import KGEntry, KGKind


class IABookKGAdapter(StubKGAdapter):
    """Adapter for IABookKG — Internet Archive book and literature corpus.

    Backed by ``ia_kg``; downloads and indexes books from archive.org using
    DocKG-style indices per genre corpus.  Until the ``ia_kg`` library
    exposes a standalone query API this adapter remains a stub — registered
    KGs of this kind are visible in the registry but return empty results.

    :param entry: A KGEntry instance with ``kind=KGKind.IA``.
    """

    _pkg_name: str = "ia_kg"
    _kind: KGKind = KGKind.IA

    def __init__(self, entry: KGEntry, embedder=None) -> None:
        super().__init__(entry, embedder=embedder)
