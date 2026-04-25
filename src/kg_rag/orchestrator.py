"""
orchestrator.py

KGRAG — cross-KG query orchestrator.

Loads adapters from the registry and executes federated queries across
multiple KG instances (PyCodeKG, DocKG, MetaKG) simultaneously.

Author: Eric G. Suchanek, PhD
Last Revision: 2026-04-22 19:27:45
License: Elastic 2.0
"""

from __future__ import annotations

from collections.abc import Sequence
from pathlib import Path

from kg_rag.adapters import KGAdapter, make_adapter
from kg_rag.config import load_kgrag_config
from kg_rag.corpus_registry import CorpusRegistry
from kg_rag.embed import Embedder, make_embedder
from kg_rag.person_registry import PersonCorpusRegistry
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

    **Embedding backend**

    By default each KG library uses its own built-in embedder
    (``SentenceTransformerEmbedder``).  Pass an explicit ``embedder`` or
    configure ``embed_backend`` in ``[tool.kgrag]`` to override this for all
    KGs at once.  A single shared embedder instance is used across every
    adapter so the GGUF model is loaded only once.

    Example ``pyproject.toml`` configuration for Raspberry Pi / ARM:

    .. code-block:: toml

        [tool.kgrag]
        embed_backend    = "llama"
        llama_model_path = "~/.kgrag/bge-small-en-v1.5-Q8_0.gguf"

    :param registry_path: Path to the registry SQLite file. Defaults to
        ``~/.kgrag/registry.sqlite`` (or KGRAG_REGISTRY env var).
    :param strict: If True, raise ImportError when a required KG library
        is not installed. Default False (skip unavailable KGs).
    :param embedder: Explicit :class:`~kg_rag.embed.Embedder` instance to use
        for all KG adapters.  When ``None`` (default), the embedder is
        auto-created from ``[tool.kgrag]`` config, or each KG uses its own
        default if no ``embed_backend`` is configured.
    :param project_root: Root directory to search for ``pyproject.toml`` when
        auto-creating the embedder from config.  Defaults to ``Path.cwd()``.
    """

    def __init__(
        self,
        registry_path: Path | None = None,
        strict: bool = False,
        embedder: "Embedder | None" = None,
        project_root: Path | None = None,
    ) -> None:
        self._registry = KGRegistry(db_path=registry_path)
        self._corpus_registry = CorpusRegistry(db_path=registry_path)
        self._person_registry = PersonCorpusRegistry(db_path=registry_path)
        self._strict = strict
        self._adapters: dict[str, KGAdapter] = {}  # name → adapter

        if embedder is not None:
            self._embedder: Embedder | None = embedder
        else:
            cfg = load_kgrag_config(project_root)
            self._embedder = make_embedder(cfg)

    @property
    def registry(self) -> KGRegistry:
        """The underlying KGRegistry."""
        return self._registry

    @property
    def corpus_registry(self) -> CorpusRegistry:
        """The underlying CorpusRegistry."""
        return self._corpus_registry

    @property
    def person_registry(self) -> PersonCorpusRegistry:
        """The underlying PersonCorpusRegistry."""
        return self._person_registry

    def close(self) -> None:
        """Release all resources."""
        self._registry.close()
        self._corpus_registry.close()
        self._person_registry.close()

    def __enter__(self) -> KGRAG:
        return self

    def __exit__(self, *_) -> None:
        self.close()

    # ------------------------------------------------------------------
    # Adapter management
    # ------------------------------------------------------------------

    def _get_adapter(self, entry: KGEntry) -> KGAdapter | None:
        if entry.name not in self._adapters:
            adapter = make_adapter(entry, embedder=self._embedder)
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
        min_score: float = 0.0,
        semantic_floor: float = 0.0,
    ) -> CrossQueryResult:
        """Federated query across all (or selected) registered KGs.

        :param q: Natural-language query string.
        :param k: Max hits to return per KG.
        :param kinds: Optional filter: only query KGs of these kinds.
        :param min_score: Minimum relevance score; hits below this are dropped
            across all KGs.  Set to e.g. ``0.35`` to suppress low-confidence
            hits from KGs whose domain does not match the query.
        :param semantic_floor: Per-KG gate: if the best hit from a KG is below
            this value, that KG's entire result set is discarded.  Use to
            silence KGs that return k near-neighbor hits with no real relevance.
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
                hits = adapter.query(q, k=k, min_score=min_score, semantic_floor=semantic_floor)
                all_hits.extend(hits)
                by_kg[entry.name] = hits
                kgs_queried += 1
            except Exception:  # pylint: disable=broad-exception-caught
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
        semantic_floor: float = 0.0,
    ) -> CrossSnippetPack:
        """Federated snippet pack across all (or selected) registered KGs.

        :param q: Natural-language query string.
        :param k: Max snippets per KG.
        :param context: Lines of context for code snippets.
        :param kinds: Optional filter: only query KGs of these kinds.
        :param semantic_floor: Per-KG gate: if the best snippet from a KG is
            below this value, that KG's entire result set is discarded.
        :return: CrossSnippetPack with all snippets ranked by score.
        """
        all_snippets: list[CrossSnippet] = []
        kgs_queried = 0

        for entry in self._resolve_entries(kinds):
            adapter = self._get_adapter(entry)
            if adapter is None:
                continue
            try:
                snippets = adapter.pack(q, k=k, context=context, semantic_floor=semantic_floor)
                all_snippets.extend(snippets)
                kgs_queried += 1
            except Exception:  # pylint: disable=broad-exception-caught
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
            except Exception as e:  # pylint: disable=broad-exception-caught
                out[entry.name] = {"available": False, "error": str(e)}
        return out

    def analyze(self, kg_name: str) -> str:
        """Run architectural analysis on a specific KG.

        :param kg_name: Name of the registered KG to analyze.
        :return: Markdown-formatted analysis report.
        """
        entry = self._registry.find_by_name(kg_name)
        if entry is None:
            return f"KG '{kg_name}' not found in registry."
        adapter = self._get_adapter(entry)
        if adapter is None:
            return f"KG '{kg_name}' is not available (library not installed or DB not built)."
        return adapter.analyze()

    # ------------------------------------------------------------------
    # Corpus-scoped operations
    # ------------------------------------------------------------------

    def _resolve_corpus_entries(self, corpus_name: str) -> list[KGEntry]:
        """Resolve a corpus name to its constituent KGEntry objects.

        :param corpus_name: Name or UUID of the corpus.
        :return: List of KGEntry objects in the corpus (missing ones skipped).
        :raises KeyError: If corpus not found in registry.
        """
        corpus = self._corpus_registry.get(corpus_name)
        if corpus is None:
            raise KeyError(f"Corpus '{corpus_name}' not found.")
        return self._corpus_registry.resolve_kg_entries(corpus_name, self._registry)

    def query_corpus(
        self,
        corpus_name: str,
        q: str,
        k: int = 8,
        min_score: float = 0.0,
        semantic_floor: float = 0.0,
    ) -> CrossQueryResult:
        """Federated query scoped to a named corpus.

        :param corpus_name: Name or UUID of the corpus to query.
        :param q: Natural-language query string.
        :param k: Max hits to return per KG.
        :param min_score: Minimum relevance score; hits below this are dropped.
        :param semantic_floor: Per-KG gate: if the best hit from a KG is below
            this value, that KG's entire result set is discarded.
        :return: Aggregated and globally ranked CrossQueryResult.
        :raises KeyError: If corpus not found.
        """
        entries = self._resolve_corpus_entries(corpus_name)
        all_hits: list[CrossHit] = []
        by_kg: dict[str, list[CrossHit]] = {}
        kgs_queried = 0

        for entry in entries:
            adapter = self._get_adapter(entry)
            if adapter is None:
                continue
            try:
                hits = adapter.query(q, k=k, min_score=min_score, semantic_floor=semantic_floor)
                all_hits.extend(hits)
                by_kg[entry.name] = hits
                kgs_queried += 1
            except Exception:  # pylint: disable=broad-exception-caught
                if self._strict:
                    raise

        all_hits.sort(key=lambda h: h.score, reverse=True)
        return CrossQueryResult(
            query=q,
            hits=all_hits,
            by_kg=by_kg,
            total_hits=len(all_hits),
            kgs_queried=kgs_queried,
        )

    def pack_corpus(
        self,
        corpus_name: str,
        q: str,
        k: int = 8,
        context: int = 5,
        semantic_floor: float = 0.0,
    ) -> CrossSnippetPack:
        """Federated snippet pack scoped to a named corpus.

        :param corpus_name: Name or UUID of the corpus.
        :param q: Natural-language query string.
        :param k: Max snippets per KG.
        :param context: Lines of context for code snippets.
        :param semantic_floor: Per-KG gate: if the best snippet from a KG is
            below this value, that KG's entire result set is discarded.
        :return: CrossSnippetPack with all snippets ranked by score.
        :raises KeyError: If corpus not found.
        """
        entries = self._resolve_corpus_entries(corpus_name)
        all_snippets: list[CrossSnippet] = []
        kgs_queried = 0

        for entry in entries:
            adapter = self._get_adapter(entry)
            if adapter is None:
                continue
            try:
                snippets = adapter.pack(q, k=k, context=context, semantic_floor=semantic_floor)
                all_snippets.extend(snippets)
                kgs_queried += 1
            except Exception:  # pylint: disable=broad-exception-caught
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

    def stats_corpus(self, corpus_name: str) -> dict:
        """Collect statistics from all KGs in a named corpus.

        :param corpus_name: Name or UUID of the corpus.
        :return: Dict mapping KG name to stats dict.
        :raises KeyError: If corpus not found.
        """
        entries = self._resolve_corpus_entries(corpus_name)
        out: dict = {}
        for entry in entries:
            adapter = self._get_adapter(entry)
            if adapter is None:
                out[entry.name] = {"available": False, "kind": entry.kind.value}
                continue
            try:
                out[entry.name] = {"available": True, **adapter.stats()}
            except Exception as e:  # pylint: disable=broad-exception-caught
                out[entry.name] = {"available": False, "error": str(e)}
        return out

    # ------------------------------------------------------------------
    # Person corpus-scoped operations
    # ------------------------------------------------------------------

    def _resolve_person_entries(self, person_name: str) -> list[KGEntry]:
        """Resolve a person corpus name to its constituent KGEntry objects.

        :param person_name: Name or UUID of the person corpus.
        :return: List of KGEntry objects for the person's KGs (missing ones skipped).
        :raises KeyError: If person corpus not found in registry.
        """
        person = self._person_registry.get(person_name)
        if person is None:
            raise KeyError(f"Person corpus '{person_name}' not found.")
        return self._person_registry.resolve_kg_entries(person_name, self._registry)

    def query_person(
        self,
        person_name: str,
        q: str,
        k: int = 8,
        min_score: float = 0.0,
        semantic_floor: float = 0.0,
    ) -> CrossQueryResult:
        """Federated query scoped to a person corpus.

        :param person_name: Name or UUID of the person corpus.
        :param q: Natural-language query string.
        :param k: Max hits to return per KG.
        :param min_score: Minimum relevance score; hits below this are dropped.
        :param semantic_floor: Per-KG gate: if the best hit from a KG is below
            this value, that KG's entire result set is discarded.
        :return: Aggregated and globally ranked CrossQueryResult.
        :raises KeyError: If person corpus not found.
        """
        entries = self._resolve_person_entries(person_name)
        all_hits: list[CrossHit] = []
        by_kg: dict[str, list[CrossHit]] = {}
        kgs_queried = 0

        for entry in entries:
            adapter = self._get_adapter(entry)
            if adapter is None:
                continue
            try:
                hits = adapter.query(q, k=k, min_score=min_score, semantic_floor=semantic_floor)
                all_hits.extend(hits)
                by_kg[entry.name] = hits
                kgs_queried += 1
            except Exception:  # pylint: disable=broad-exception-caught
                if self._strict:
                    raise

        all_hits.sort(key=lambda h: h.score, reverse=True)
        return CrossQueryResult(
            query=q,
            hits=all_hits,
            by_kg=by_kg,
            total_hits=len(all_hits),
            kgs_queried=kgs_queried,
        )

    def pack_person(
        self,
        person_name: str,
        q: str,
        k: int = 8,
        context: int = 5,
        semantic_floor: float = 0.0,
    ) -> CrossSnippetPack:
        """Federated snippet pack scoped to a person corpus.

        :param person_name: Name or UUID of the person corpus.
        :param q: Natural-language query string.
        :param k: Max snippets per KG.
        :param context: Lines of context for code snippets.
        :param semantic_floor: Per-KG gate: if the best snippet from a KG is
            below this value, that KG's entire result set is discarded.
        :return: CrossSnippetPack with all snippets ranked by score.
        :raises KeyError: If person corpus not found.
        """
        entries = self._resolve_person_entries(person_name)
        all_snippets: list[CrossSnippet] = []
        kgs_queried = 0

        for entry in entries:
            adapter = self._get_adapter(entry)
            if adapter is None:
                continue
            try:
                snippets = adapter.pack(q, k=k, context=context, semantic_floor=semantic_floor)
                all_snippets.extend(snippets)
                kgs_queried += 1
            except Exception:  # pylint: disable=broad-exception-caught
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

    def stats_person(self, person_name: str) -> dict:
        """Collect statistics from all KGs in a person corpus.

        :param person_name: Name or UUID of the person corpus.
        :return: Dict mapping KG name to stats dict.
        :raises KeyError: If person corpus not found.
        """
        entries = self._resolve_person_entries(person_name)
        out: dict = {}
        for entry in entries:
            adapter = self._get_adapter(entry)
            if adapter is None:
                out[entry.name] = {"available": False, "kind": entry.kind.value}
                continue
            try:
                out[entry.name] = {"available": True, **adapter.stats()}
            except Exception as e:  # pylint: disable=broad-exception-caught
                out[entry.name] = {"available": False, "error": str(e)}
        return out
