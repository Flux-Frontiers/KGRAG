"""
orchestrator.py

KGRAG — cross-KG query orchestrator.

Loads adapters from the registry and executes federated queries across
multiple KG instances (CodeKG, DocKG, MetaKG) simultaneously.
"""
from __future__ import annotations

from pathlib import Path
from typing import Sequence

from kg_rag.adapters import KGAdapter, make_adapter
from kg_rag.primitives import (
    CrossHit,
    CrossQueryResult,
    CrossSnippet,
    CrossSnippetPack,
    KGEntry,
    KGKind,
)
from kg_rag.registry import KGRegistry


class KGRAG:
    """Cross-KG orchestrator: query multiple KG instances as a unified corpus.

    Loads adapters from the registry on demand (lazy initialization).
    Individual KG libraries (code-kg, doc-kg, metakg) are optional — if a
    library is not installed, that KG is silently skipped unless
    ``strict=True``.

    :param registry_path: Path to the registry SQLite file. Defaults to
        ``~/.kgrag/registry.sqlite`` (or KGRAG_REGISTRY env var).
    :param strict: If True, raise ImportError when a required KG library
        is not installed. Default False (skip unavailable KGs).
    """

    def __init__(
        self,
        registry_path: Path | None = None,
        strict: bool = False,
    ) -> None:
        self._registry = KGRegistry(db_path=registry_path)
        self._strict = strict
        self._adapters: dict[str, KGAdapter] = {}  # name → adapter

    @property
    def registry(self) -> KGRegistry:
        """The underlying KGRegistry."""
        return self._registry

    def close(self) -> None:
        """Release all resources."""
        self._registry.close()

    def __enter__(self) -> KGRAG:
        return self

    def __exit__(self, *_) -> None:
        self.close()

    # ------------------------------------------------------------------
    # Adapter management
    # ------------------------------------------------------------------

    def _get_adapter(self, entry: KGEntry) -> KGAdapter | None:
        if entry.name not in self._adapters:
            adapter = make_adapter(entry)
            if not adapter.is_available():
                if self._strict:
                    raise ImportError(
                        f"KG '{entry.name}' ({entry.kind.value}) is not available. "
                        f"Check that the library is installed and the DB is built."
                    )
                return None
            self._adapters[entry.name] = adapter
        return self._adapters[entry.name]

    def _resolve_entries(self, kinds: Sequence[KGKind] | None = None) -> list[KGEntry]:
        """Return all registry entries, optionally filtered by kind.

        :param kinds: Optional sequence of KGKind values to filter by.
        :return: List of matching KGEntry objects.
        """
        if kinds is not None:
            entries = []
            for k in kinds:
                entries.extend(self._registry.list(kind=k))
            return entries
        return self._registry.list()

    # ------------------------------------------------------------------
    # Cross-KG queries
    # ------------------------------------------------------------------

    def query(
        self,
        q: str,
        k: int = 8,
        kinds: Sequence[KGKind] | None = None,
    ) -> CrossQueryResult:
        """Federated query across all (or selected) registered KGs.

        :param q: Natural-language query string.
        :param k: Max hits to return per KG.
        :param kinds: Optional filter: only query KGs of these kinds.
        :return: Aggregated and globally ranked CrossQueryResult.
        """
        all_hits: list[CrossHit] = []
        by_kg: dict[str, list[CrossHit]] = {}
        kgs_queried = 0

        for entry in self._resolve_entries(kinds):
            adapter = self._get_adapter(entry)
            if adapter is None:
                continue
            try:
                hits = adapter.query(q, k=k)
                all_hits.extend(hits)
                by_kg[entry.name] = hits
                kgs_queried += 1
            except Exception:
                if self._strict:
                    raise
                # Silently skip failing KGs in permissive mode

        # Global rank by score descending
        all_hits.sort(key=lambda h: h.score, reverse=True)

        return CrossQueryResult(
            query=q,
            hits=all_hits,
            by_kg=by_kg,
            total_hits=len(all_hits),
            kgs_queried=kgs_queried,
        )

    def pack(
        self,
        q: str,
        k: int = 8,
        context: int = 5,
        kinds: Sequence[KGKind] | None = None,
    ) -> CrossSnippetPack:
        """Federated snippet pack across all (or selected) registered KGs.

        :param q: Natural-language query string.
        :param k: Max snippets per KG.
        :param context: Lines of context for code snippets.
        :param kinds: Optional filter: only query KGs of these kinds.
        :return: CrossSnippetPack with all snippets ranked by score.
        """
        all_snippets: list[CrossSnippet] = []
        kgs_queried = 0

        for entry in self._resolve_entries(kinds):
            adapter = self._get_adapter(entry)
            if adapter is None:
                continue
            try:
                snippets = adapter.pack(q, k=k, context=context)
                all_snippets.extend(snippets)
                kgs_queried += 1
            except Exception:
                if self._strict:
                    raise

        all_snippets.sort(key=lambda s: s.score, reverse=True)
        approx_tokens = sum(len(s.content.split()) * 4 // 3 for s in all_snippets)

        return CrossSnippetPack(
            query=q,
            snippets=all_snippets,
            total_tokens_approx=approx_tokens,
            kgs_queried=kgs_queried,
        )

    def stats(self, kinds: Sequence[KGKind] | None = None) -> dict:
        """Collect statistics from all available KGs.

        :param kinds: Optional filter.
        :return: Dict mapping KG name to stats dict.
        """
        out = {}
        for entry in self._resolve_entries(kinds):
            adapter = self._get_adapter(entry)
            if adapter is None:
                out[entry.name] = {"available": False, "kind": entry.kind.value}
                continue
            try:
                out[entry.name] = {"available": True, **adapter.stats()}
            except Exception as e:
                out[entry.name] = {"available": False, "error": str(e)}
        return out
