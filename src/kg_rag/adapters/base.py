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

    @abstractmethod
    def analyze(self) -> str:
        """Run full analysis on this KG and return a Markdown-formatted report.

        Every adapter must implement this method. The report format is
        adapter-specific but must be valid Markdown so callers can render,
        save, or forward it uniformly.

        :return: Markdown-formatted analysis report string.
        """
        return ""

    @abstractmethod
    def snapshot(self, version: str, label: str | None = None) -> dict[str, Any]:
        """Capture a point-in-time snapshot of this KG's state.

        Implementations must persist the snapshot (e.g. to disk or an in-memory
        store) and return a serialisable dict that includes at minimum:

        * ``version`` — the caller-supplied version string
        * ``timestamp`` — ISO 8601 UTC timestamp of capture
        * ``node_count`` — integer node count at capture time
        * ``edge_count`` — integer edge count at capture time

        Adapters that back a library with native snapshot support should
        delegate to that library.  Adapters without native support should
        capture metrics via :meth:`stats` and persist them as appropriate.

        :param version: Semantic-version string for this snapshot (e.g. "1.2.0").
        :param label: Optional human-readable label for the snapshot.
        :return: Serialisable snapshot dict.
        """

    # ------------------------------------------------------------------
    # Display helpers
    # ------------------------------------------------------------------

    def display(self) -> str:
        """Return a human-readable one-line summary of this adapter's state.

        The default implementation combines the entry label, availability status,
        and basic graph topology counts.  Adapters may override to include
        domain-specific metrics.

        :return: A single-line string suitable for printing to a terminal.
        """
        available = self.is_available()
        status = "available" if available else "unavailable"
        if available:
            gs = self._graph_stats()
            return (
                f"[{self.entry.kind.value}] {self.entry.name} — {status} "
                f"({gs['node_count']} nodes, {gs['edge_count']} edges)"
            )
        return f"[{self.entry.kind.value}] {self.entry.name} — {status}"

    def __repr__(self) -> str:
        return (
            f"{self.__class__.__name__}("
            f"name={self.entry.name!r}, "
            f"kind={self.entry.kind.value!r}, "
            f"available={self.is_available()!r})"
        )

    # ------------------------------------------------------------------
    # Internal helpers — used by the orchestrator, not part of the public API
    # ------------------------------------------------------------------

    def _graph_stats(self) -> dict[str, int]:
        """Return raw graph topology counts for this KG instance.

        Unlike :meth:`stats`, this method strips all KG-kind-specific or
        semantic fields and always returns a plain ``{node_count, edge_count}``
        mapping with integer values.  Unavailable or non-integer counts are
        normalised to ``0``.

        This is an internal helper called by the orchestrator when it needs to
        aggregate graph-size metrics uniformly across heterogeneous KG kinds
        without being confused by domain-specific keys.

        :return: Dict with integer ``node_count`` and ``edge_count``.
        """
        raw = self.stats()

        def _to_int(val: Any) -> int:
            try:
                return int(val)
            except (TypeError, ValueError):
                return 0

        return {
            "node_count": _to_int(raw.get("node_count")),
            "edge_count": _to_int(raw.get("edge_count")),
        }
