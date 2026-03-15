"""diary_adapter.py — KGAdapter for DiaryKG."""

from __future__ import annotations

from typing import Any

from kg_rag.adapters.base import KGAdapter
from kg_rag.primitives import CrossHit, CrossSnippet, KGEntry, KGKind


class DiaryKGAdapter(KGAdapter):
    """Adapter wrapping the ``diary_kg.DiaryKG`` class.

    ``KGEntry.repo_path`` must point to the project root that contains
    ``.diarykg/``.  The original source file is read from
    ``KGEntry.metadata["source_file"]`` (set at registration time) and passed
    to ``DiaryKG`` as the provenance anchor.

    :param entry: KGEntry with ``kind=KGKind.DIARY``.
    """

    def __init__(self, entry: KGEntry) -> None:
        super().__init__(entry)
        self._kg: Any = None

    def _load(self) -> None:
        if self._kg is not None:
            return
        try:
            from diary_kg.kg import DiaryKG  # pylint: disable=import-outside-toplevel
        except ImportError as exc:
            raise ImportError(
                "diary-kg is not installed. It lives in pepys/diary_kg/ — "
                "ensure the pepys packages are on sys.path or installed."
            ) from exc
        source_file = self.entry.metadata.get("source_file")
        self._kg = DiaryKG(self.entry.repo_path, source_file=source_file)

    def is_available(self) -> bool:
        """Return True if diary_kg is importable and the KG is built.

        :return: True if this adapter can serve queries.
        """
        try:
            import diary_kg  # noqa: F401  # pylint: disable=import-outside-toplevel
            return self.entry.is_built
        except ImportError:
            return False

    def query(self, q: str, k: int = 8) -> list[CrossHit]:
        """Semantic search over the diary corpus.

        ``CrossHit.source_path`` is set to the original diary ``.txt`` file
        (not the generated chunk path), sourced from chunk frontmatter.

        :param q: Natural-language query string.
        :param k: Number of results to return.
        :return: Ranked list of CrossHit objects.
        """
        self._load()
        hits = []
        for h in self._kg.query(q, k=k):
            hits.append(
                CrossHit(
                    kg_name=self.entry.name,
                    kg_kind=KGKind.DIARY,
                    node_id=h.get("node_id", ""),
                    name=h.get("timestamp") or h.get("source_file", ""),
                    kind="chunk",
                    score=h.get("score", 0.0),
                    summary=h.get("summary", ""),
                    source_path=h.get("source_file", ""),
                )
            )
        return hits

    def pack(self, q: str, k: int = 8, context: int = 5) -> list[CrossSnippet]:
        """Return diary snippets for LLM ingestion.

        :param q: Natural-language query string.
        :param k: Number of snippets to return.
        :param context: Unused for diary KGs (no line-number semantics).
        :return: List of CrossSnippet objects.
        """
        self._load()
        snippets = []
        for s in self._kg.pack(q, k=k):
            snippets.append(
                CrossSnippet(
                    kg_name=self.entry.name,
                    kg_kind=KGKind.DIARY,
                    node_id=s.get("node_id", ""),
                    source_path=s.get("source_file", ""),
                    content=s.get("content", ""),
                    score=s.get("score", 0.0),
                )
            )
        return snippets

    def stats(self) -> dict[str, Any]:
        """Return corpus statistics.

        :return: Dict with chunk_count, entry_count, temporal_span, kind.
        """
        self._load()
        return self._kg.stats()

    def analyze(self) -> str:
        """Return a Markdown analysis report for this diary corpus.

        :return: Markdown-formatted report string.
        """
        self._load()
        return self._kg.analyze()
