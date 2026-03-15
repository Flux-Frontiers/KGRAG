"""pdbfile_adapter.py — KGAdapter for PDBFileKG (stub until library is released)."""

from __future__ import annotations

from kg_rag.adapters._stub_adapter import StubKGAdapter
from kg_rag.primitives import KGEntry, KGKind


class PDBFileKGAdapter(StubKGAdapter):
    """Adapter for PDBFileKG — Protein Data Bank (PDB) file knowledge graph.

    :param entry: A KGEntry instance for this KG.
    """

    _pkg_name: str = "pdbfile_kg"
    _kind: KGKind = KGKind.PDBFILE

    def __init__(self, entry: KGEntry) -> None:
        super().__init__(entry)
