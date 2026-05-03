"""gutenberg_adapter.py — KGAdapter stub for GutenbergKG (Project Gutenberg book corpus)."""

from __future__ import annotations

from kg_rag.adapters._stub_adapter import StubKGAdapter
from kg_rag.primitives import KGEntry, KGKind


class GutenbergKGAdapter(StubKGAdapter):
    """Adapter for GutenbergKG — Project Gutenberg book and literature corpus.

    Backed by ``gutenberg_kg``; builds DocKG-style indices per genre corpus.
    Until the ``gutenberg_kg`` library exposes a standalone query API this
    adapter remains a stub — registered KGs of this kind are visible in the
    registry but return empty results.

    :param entry: A KGEntry instance with ``kind=KGKind.GUTENBERG``.
    """

    _pkg_name: str = "gutenberg_kg"
    _kind: KGKind = KGKind.GUTENBERG

    def __init__(self, entry: KGEntry, embedder=None) -> None:
        super().__init__(entry, embedder=embedder)
