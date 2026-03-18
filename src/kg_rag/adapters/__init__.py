"""Adapters for individual KG backends."""

from kg_rag.adapters._stub_adapter import StubKGAdapter
from kg_rag.adapters.base import KGAdapter
from kg_rag.adapters.codekg_adapter import CodeKGAdapter
from kg_rag.adapters.diary_adapter import DiaryKGAdapter
from kg_rag.adapters.disulfide_adapter import DisulfideKGAdapter
from kg_rag.adapters.dockg_adapter import DocKGAdapter
from kg_rag.adapters.legal_adapter import LegalKGAdapter
from kg_rag.adapters.memory_adapter import MemoryKGAdapter
from kg_rag.adapters.metakg_adapter import MetaKGAdapter
from kg_rag.adapters.pdbfile_adapter import PDBFileKGAdapter
from kg_rag.adapters.person_adapter import PersonKGAdapter
from kg_rag.adapters.verse_adapter import VerseKGAdapter
from kg_rag.primitives import KGKind


def make_adapter(entry) -> KGAdapter:
    """Factory: return the correct adapter for a KGEntry.

    :param entry: A KGEntry instance.
    :return: The appropriate KGAdapter subclass.
    :raises ValueError: If the KGKind is unknown.
    """
    _map = {
        KGKind.CODE: CodeKGAdapter,
        KGKind.DOC: DocKGAdapter,
        KGKind.META: MetaKGAdapter,
        KGKind.DIARY: DiaryKGAdapter,
        KGKind.VERSE: VerseKGAdapter,
        KGKind.MEMORY: MemoryKGAdapter,
        KGKind.DISULFIDE: DisulfideKGAdapter,
        KGKind.PDBFILE: PDBFileKGAdapter,
        KGKind.LEGAL: LegalKGAdapter,
        KGKind.PERSON: PersonKGAdapter,
    }
    cls = _map.get(entry.kind)
    if cls is None:
        raise ValueError(f"Unknown KGKind: {entry.kind}")
    return cls(entry)  # type: ignore[abstract]


__all__ = [
    "KGAdapter",
    "StubKGAdapter",
    "CodeKGAdapter",
    "DocKGAdapter",
    "MetaKGAdapter",
    "DiaryKGAdapter",
    "VerseKGAdapter",
    "MemoryKGAdapter",
    "DisulfideKGAdapter",
    "PDBFileKGAdapter",
    "LegalKGAdapter",
    "PersonKGAdapter",
    "make_adapter",
]
