"""
base.py

Abstract adapter protocol for all KG backends.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

from kg_rag.primitives import CrossHit, CrossSnippet, KGEntry


class KGAdapter(ABC):
    """Abstract base for KG adapters (CodeKG, DocKG, MetaKG).

    Each adapter wraps the specific KG library and exposes a uniform
    interface for querying, packing, and introspecting a single KG instance.

    :param entry: The KGEntry this adapter serves.
    """

    def __init__(self, entry: KGEntry) -> None:
        self.entry = entry

    @abstractmethod
    def is_available(self) -> bool:
        """Return True if the underlying KG library is installed and the DB exists.

        :return: True if this adapter can serve queries.
        """

    @abstractmethod
    def query(self, q: str, k: int = 8) -> list[CrossHit]:
        """Query the KG and return ranked hits.

        :param q: Natural-language query string.
        :param k: Number of results to return.
        :return: List of CrossHit objects ranked by score.
        """

    @abstractmethod
    def pack(self, q: str, k: int = 8, context: int = 5) -> list[CrossSnippet]:
        """Query the KG and return source snippets.

        :param q: Natural-language query string.
        :param k: Number of snippets to return.
        :param context: Lines of context around code (code KGs only).
        :return: List of CrossSnippet objects.
        """

    @abstractmethod
    def stats(self) -> dict[str, Any]:
        """Return basic statistics about this KG instance.

        :return: Dict with node_count, edge_count, or equivalent metrics.
        """
