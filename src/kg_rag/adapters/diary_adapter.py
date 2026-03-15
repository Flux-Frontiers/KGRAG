"""diary_adapter.py — KGAdapter for DiaryKG backed by DocKG."""

from __future__ import annotations

from typing import Any

from kg_rag.adapters.base import KGAdapter
from kg_rag.primitives import CrossHit, CrossSnippet, KGEntry, KGKind


class DiaryKGAdapter(KGAdapter):
    """Adapter for a diary knowledge graph stored as a DocKG corpus.

    The diary ingestion pipeline (``DiaryTransformer.ingest_to_corpus``) writes
    one ``.md`` file per chunk with YAML frontmatter that carries the original
    source file path and entry timestamp.  This adapter indexes that corpus via
    ``DocKG`` and surfaces the ``source_file`` frontmatter field — not the
    generated chunk path — as ``CrossHit.source_path`` so callers always see the
    provenance back to the original diary ``.txt``.

    :param entry: KGEntry with ``kind=KGKind.DIARY``.  ``repo_path`` must point
        to the corpus directory produced by ``ingest_to_corpus()``.
    """

    def __init__(self, entry: KGEntry) -> None:
        super().__init__(entry)
        self._kg: Any = None

    # ------------------------------------------------------------------
    # Lazy loading
    # ------------------------------------------------------------------

    def _load(self) -> None:
        if self._kg is not None:
            return
        try:
            from doc_kg.kg import DocKG  # pylint: disable=import-outside-toplevel
        except ImportError as exc:
            raise ImportError(
                "doc-kg is not installed. Install it with: pip install doc-kg"
            ) from exc
        entry = self.entry
        sqlite = str(entry.sqlite_path) if entry.sqlite_path else None
        lancedb = str(entry.lancedb_path) if entry.lancedb_path else None
        self._kg = DocKG(
            corpus_root=str(entry.repo_path),
            db_path=sqlite or str(entry.repo_path / ".dockg" / "graph.sqlite"),
            lancedb_dir=lancedb or str(entry.repo_path / ".dockg" / "lancedb"),
        )

    # ------------------------------------------------------------------
    # KGAdapter interface
    # ------------------------------------------------------------------

    def is_available(self) -> bool:
        """Return True if doc_kg is installed and the corpus DB is built.

        :return: True if this adapter can serve queries.
        """
        try:
            import doc_kg  # noqa: F401  # pylint: disable=import-outside-toplevel

            return self.entry.is_built
        except ImportError:
            return False

    def query(self, q: str, k: int = 8) -> list[CrossHit]:
        """Query the diary corpus and return ranked hits.

        The ``source_path`` on each hit is the ``source_file`` value embedded in
        the chunk frontmatter (the original diary ``.txt``), not the generated
        ``.md`` file path.

        :param q: Natural-language query string.
        :param k: Number of results to return.
        :return: List of CrossHit objects ranked by score.
        """
        self._load()
        result = self._kg.query(q, k=k)
        hits = []
        for node in result.nodes[:k]:
            relevance = node.get("relevance") or {}
            # Prefer the original source file stored in frontmatter metadata;
            # fall back to the chunk file path if not present.
            meta = node.get("metadata") or {}
            source = meta.get("source_file") or node.get("file_path") or ""
            hits.append(
                CrossHit(
                    kg_name=self.entry.name,
                    kg_kind=KGKind.DIARY,
                    node_id=node["id"],
                    name=node.get("name") or node.get("title", ""),
                    kind=node.get("kind", "chunk"),
                    score=relevance.get("score", 0.0),
                    summary=node.get("text") or node.get("title", ""),
                    source_path=source,
                )
            )
        return hits

    def pack(self, q: str, k: int = 8, context: int = 5) -> list[CrossSnippet]:
        """Query the diary corpus and return source snippets.

        :param q: Natural-language query string.
        :param k: Number of snippets to return.
        :param context: Unused for diary KGs (no line-number semantics).
        :return: List of CrossSnippet objects.
        """
        self._load()
        pack = self._kg.pack(q, k=k)
        snippets = []
        for node in pack.nodes:
            relevance = node.get("relevance") or {}
            meta = node.get("metadata") or {}
            source = meta.get("source_file") or node.get("file_path") or ""
            snippets.append(
                CrossSnippet(
                    kg_name=self.entry.name,
                    kg_kind=KGKind.DIARY,
                    node_id=node["id"],
                    source_path=source,
                    content=node.get("text") or "",
                    score=relevance.get("score", 0.0),
                )
            )
        return snippets

    def stats(self) -> dict[str, Any]:
        """Return basic statistics about this diary corpus.

        :return: Dict with node_count, edge_count, and kind.
        """
        self._load()
        try:
            s = self._kg.store.stats()
            return {
                "node_count": s.get("total_nodes", "n/a"),
                "edge_count": s.get("total_edges", "n/a"),
                "kind": "diary",
            }
        except Exception:  # pylint: disable=broad-exception-caught
            return {"kind": "diary", "error": "stats unavailable"}

    def analyze(self) -> str:
        """Return a Markdown analysis report for this diary corpus.

        Combines DocKG baseline metrics with diary-specific information
        (temporal span, topic distribution from frontmatter categories).

        :return: Markdown-formatted analysis report.
        """
        self._load()
        try:
            from pathlib import Path  # pylint: disable=import-outside-toplevel

            corpus_root = Path(self.entry.repo_path)
            md_files = list(corpus_root.rglob("*.md"))

            # Parse frontmatter from chunk files for diary-specific metrics
            from collections import Counter  # pylint: disable=import-outside-toplevel
            import re  # pylint: disable=import-outside-toplevel

            timestamps: list[str] = []
            categories: Counter = Counter()
            contexts: Counter = Counter()
            source_files: set[str] = set()

            fm_re = re.compile(r"^---\n(.*?)\n---", re.DOTALL)
            for md in md_files:
                try:
                    text = md.read_text(encoding="utf-8")
                    m = fm_re.match(text)
                    if not m:
                        continue
                    for line in m.group(1).splitlines():
                        if ": " not in line:
                            continue
                        key, _, val = line.partition(": ")
                        key, val = key.strip(), val.strip()
                        if key == "timestamp":
                            timestamps.append(val)
                        elif key == "category":
                            categories[val] += 1
                        elif key == "context":
                            contexts[val] += 1
                        elif key == "source_file":
                            source_files.add(val)
                except OSError:
                    continue

            timestamps.sort()
            span = f"{timestamps[0]} → {timestamps[-1]}" if len(timestamps) >= 2 else (timestamps[0] if timestamps else "n/a")

            lines: list[str] = [
                "# DiaryKG Analysis Report",
                "",
                f"**KG:** `{self.entry.name}`  |  **corpus:** `{self.entry.repo_path}`",
                "",
                "## Corpus Overview",
                "",
                f"- Chunk files: **{len(md_files)}**",
                f"- Source files: **{len(source_files)}**  ({', '.join(sorted(source_files)[:5])})",
                f"- Temporal span: **{span}**",
                "",
                "## Topic Distribution",
                "",
                "| Category | Chunks |",
                "|---|---:|",
            ]
            for cat, cnt in categories.most_common(15):
                lines.append(f"| {cat} | {cnt} |")

            lines += [
                "",
                "## Context Distribution",
                "",
                "| Context | Chunks |",
                "|---|---:|",
            ]
            for ctx, cnt in contexts.most_common(10):
                lines.append(f"| {ctx} | {cnt} |")
            lines.append("")

            # DocKG baseline stats
            try:
                s = self._kg.store.stats()
                lines += [
                    "## DocKG Baseline",
                    "",
                    f"- Total nodes: **{s.get('total_nodes', 'n/a')}**",
                    f"- Total edges: **{s.get('total_edges', 'n/a')}**",
                    "",
                ]
            except Exception:  # pylint: disable=broad-exception-caught
                pass

            return "\n".join(lines)

        except Exception as exc:  # pylint: disable=broad-exception-caught
            return f"# DiaryKG Analysis\n\nAnalysis failed: {exc}\n"
