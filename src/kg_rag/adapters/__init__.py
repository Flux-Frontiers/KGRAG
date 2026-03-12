"""Adapters for individual KG backends."""
from kg_rag.adapters.base import KGAdapter
from kg_rag.adapters.codekg_adapter import CodeKGAdapter
from kg_rag.adapters.dockg_adapter import DocKGAdapter
from kg_rag.adapters.metakg_adapter import MetaKGAdapter
from kg_rag.primitives import KGKind


def make_adapter(entry) -> KGAdapter:
    """Factory: return the correct adapter for a KGEntry.

    :param entry: A KGEntry instance.
    :return: The appropriate KGAdapter subclass.
    :raises ValueError: If the KGKind is unknown.
    """
    if entry.kind == KGKind.CODE:
        return CodeKGAdapter(entry)
    if entry.kind == KGKind.DOC:
        return DocKGAdapter(entry)
    if entry.kind == KGKind.META:
        return MetaKGAdapter(entry)
    raise ValueError(f"Unknown KGKind: {entry.kind}")


__all__ = ["KGAdapter", "CodeKGAdapter", "DocKGAdapter", "MetaKGAdapter", "make_adapter"]
