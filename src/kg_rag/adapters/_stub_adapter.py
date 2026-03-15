"""
_stub_adapter.py

StubKGAdapter — base class for KG adapters whose backing library is not yet
installed or implemented.

Each domain-specific adapter (DiaryKGAdapter, LegalKGAdapter, etc.) subclasses
this and overrides ``_pkg_name``, ``_kind``, and ``_try_load()`` once the
real library becomes available.  Until then, ``is_available()`` returns False
and all query/pack/stats/analyze calls return safe empty results.
"""

from __future__ import annotations

import json
from typing import Any

from kg_rag.adapters.base import KGAdapter
from kg_rag.primitives import CrossHit, CrossSnippet, KGEntry, KGKind


class StubKGAdapter(KGAdapter):
    """Base adapter for domains whose library is not yet installed.

    Subclasses set ``_pkg_name`` (importable package name, or empty string if
    the package does not yet exist) and ``_kind`` (KGKind value).  Override
    ``_try_load()`` to instantiate the real backend when it becomes available.

    :param entry: A KGEntry instance for this KG.
    """

    _pkg_name: str = ""   # set by subclass; empty = library not yet released
    _kind: KGKind = KGKind.CODE  # overridden by subclass

    def __init__(self, entry: KGEntry) -> None:
        super().__init__(entry)
        self._kg: Any = None

    # ------------------------------------------------------------------
    # Subclass extension points
    # ------------------------------------------------------------------

    def _try_load(self) -> None:
        """Override in subclass to instantiate the real backend.

        Raise ImportError if the library is unavailable.
        """
        raise ImportError(
            f"No backing library configured for KGKind.{self._kind.value.upper()}. "
            f"Set _pkg_name and implement _try_load() in the adapter subclass."
        )

    def _load(self) -> None:
        if self._kg is not None:
            return
        self._try_load()

    # ------------------------------------------------------------------
    # KGAdapter interface
    # ------------------------------------------------------------------

    def is_available(self) -> bool:
        """Return True if the backing library is installed and the DB is built.

        :return: False until the domain library is installed.
        """
        if not self._pkg_name:
            return False
        try:
            __import__(self._pkg_name)
            return self.entry.is_built
        except ImportError:
            return False

    def query(self, q: str, k: int = 8) -> list[CrossHit]:
        """Query the KG; returns empty list if library is unavailable.

        :param q: Natural-language query string.
        :param k: Number of results to return.
        :return: List of CrossHit objects, or empty if unavailable.
        """
        if not self.is_available():
            return []
        try:
            self._load()
            raw = self._kg.query(q, k=k)
            hits = []
            for hit in (getattr(raw, "ranked_hits", None) or [])[:k]:
                node = getattr(hit, "node", hit)
                hits.append(CrossHit(
                    kg_name=self.entry.name,
                    kg_kind=self._kind,
                    node_id=getattr(node, "id", str(node)),
                    name=getattr(node, "name", str(node)),
                    kind=getattr(node, "kind", self._kind.value),
                    score=getattr(hit, "score", 0.0),
                    summary=getattr(node, "description", "") or "",
                    source_path=getattr(node, "source", "") or "",
                ))
            return hits
        except Exception:  # pylint: disable=broad-exception-caught
            return []

    def pack(self, q: str, k: int = 8, context: int = 5) -> list[CrossSnippet]:
        """Return source snippets; empty list if library is unavailable.

        :param q: Natural-language query string.
        :param k: Number of snippets to return.
        :param context: Lines of context (may be unused by domain library).
        :return: List of CrossSnippet objects, or empty if unavailable.
        """
        if not self.is_available():
            return []
        try:
            self._load()
            raw = self._kg.pack(q, k=k)
            snippets = []
            for s in getattr(raw, "snippets", []):
                snippets.append(CrossSnippet(
                    kg_name=self.entry.name,
                    kg_kind=self._kind,
                    node_id=getattr(s, "node_id", ""),
                    source_path=getattr(s, "path", ""),
                    content=getattr(s, "text", str(s)),
                    score=getattr(s, "score", 0.0),
                ))
            return snippets
        except Exception:  # pylint: disable=broad-exception-caught
            return []

    def stats(self) -> dict[str, Any]:
        """Return availability and basic stats for this KG instance.

        :return: Dict with kind, status, and optional node/edge counts.
        """
        base: dict[str, Any] = {
            "kind": self._kind.value,
            "status": "available" if self.is_available() else "unavailable",
        }
        if not self.is_available():
            return base
        try:
            self._load()
            raw = self._kg.stats() if callable(getattr(self._kg, "stats", None)) else {}
            if isinstance(raw, dict):
                base["node_count"] = raw.get("node_count") or raw.get("total_nodes", "n/a")
                base["edge_count"] = raw.get("edge_count") or raw.get("total_edges", "n/a")
        except Exception:  # pylint: disable=broad-exception-caught
            pass
        return base

    def analyze(self) -> str:
        """Return a Markdown analysis report for this KG instance.

        :return: Markdown-formatted report, or an unavailability notice.
        """
        kind_label = self._kind.value.capitalize()
        header = (
            f"# {kind_label}KG Analysis Report\n\n"
            f"**KG:** `{self.entry.name}`  |  "
            f"**repo:** `{self.entry.repo_path}`\n"
        )
        if not self.is_available():
            pkg = self._pkg_name or f"{self._kind.value}-kg (not yet released)"
            return (
                header
                + f"\n**Status:** unavailable — `{pkg}` library not installed.\n"
            )
        try:
            self._load()
            if callable(getattr(self._kg, "analyze", None)):
                result = self._kg.analyze()
                if isinstance(result, str):
                    return header + "\n" + result
                if isinstance(result, dict):
                    return header + "\n```json\n" + json.dumps(result, indent=2) + "\n```\n"
            s = self.stats()
            return (
                header
                + "\n## Summary\n\n"
                + f"- **Status:** {s.get('status', 'unknown')}\n"
                + f"- **Node count:** {s.get('node_count', 'n/a')}\n"
                + f"- **Edge count:** {s.get('edge_count', 'n/a')}\n"
            )
        except Exception as exc:  # pylint: disable=broad-exception-caught
            return header + f"\nAnalysis failed: {exc}\n"
