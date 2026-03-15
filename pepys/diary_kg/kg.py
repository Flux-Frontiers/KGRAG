"""kg.py — DiaryKG: knowledge graph for diary and journal sources.

``DiaryKG`` orchestrates the full diary-to-KG pipeline:

1. **Build**: ``DiaryTransformer.ingest_to_corpus()`` segments the source diary
   into ``.md`` chunk files under ``.diarykg/corpus/``, then ``DocKG`` indexes
   the corpus into SQLite + LanceDB.

2. **Query / Pack**: ``DocKG`` provides semantic search; provenance is surfaced
   as the original source ``.txt`` (not the generated chunk file).

3. **Snapshots**: Point-in-time captures of corpus metrics stored under
   ``.diarykg/snapshots/`` with manifest and per-snapshot JSON files.
"""

from __future__ import annotations

import json
import re
import subprocess
from collections import Counter
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Dict, List, Optional


_FM_RE = re.compile(r"^---\n(.*?)\n---", re.DOTALL)


def _parse_frontmatter(text: str) -> Dict[str, str]:
    """Return frontmatter key-value dict from a Markdown chunk file."""
    m = _FM_RE.match(text)
    if not m:
        return {}
    result: Dict[str, str] = {}
    for line in m.group(1).splitlines():
        if ": " in line:
            k, _, v = line.partition(": ")
            result[k.strip()] = v.strip()
    return result


def _git_commit_hash(path: Path) -> Optional[str]:
    """Return the current HEAD commit hash for *path*, or None."""
    try:
        out = subprocess.check_output(
            ["git", "-C", str(path), "rev-parse", "HEAD"],
            stderr=subprocess.DEVNULL,
        )
        return out.decode().strip()
    except (subprocess.CalledProcessError, FileNotFoundError):
        return None


def _git_branch(path: Path) -> str:
    """Return current branch name, or 'unknown'."""
    try:
        out = subprocess.check_output(
            ["git", "-C", str(path), "rev-parse", "--abbrev-ref", "HEAD"],
            stderr=subprocess.DEVNULL,
        )
        return out.decode().strip()
    except (subprocess.CalledProcessError, FileNotFoundError):
        return "unknown"


class DiaryKG:
    """Knowledge graph for a diary or journal corpus.

    :param root: Project root directory.  The ``.diarykg/`` storage directory
        is created here.
    :param source_file: Relative path to the diary ``.txt`` source inside
        *root*.  Required for the first ``build()``; subsequent calls read it
        from ``config.json`` when omitted.
    """

    KG_DIR = ".diarykg"

    def __init__(self, root: str | Path, source_file: Optional[str] = None) -> None:
        self.root = Path(root).resolve()
        self._source_file_override = source_file

        self._kg_dir = self.root / self.KG_DIR
        self._corpus_dir = self._kg_dir / "corpus"
        self._db_path = self._kg_dir / "graph.sqlite"
        self._lancedb_dir = self._kg_dir / "lancedb"
        self._config_path = self._kg_dir / "config.json"
        self._snapshot_dir = self._kg_dir / "snapshots"

        self._dockg: Any = None  # lazy-loaded

    # ------------------------------------------------------------------
    # Properties
    # ------------------------------------------------------------------

    @property
    def source_path(self) -> Optional[Path]:
        """Absolute path to the source diary file (if set / resolvable)."""
        sf = self._source_file_override or self._read_config().get("source_file")
        if sf:
            p = self.root / sf
            return p if p.exists() else Path(sf).resolve()
        return None

    @property
    def source_file(self) -> Optional[str]:
        """Relative source file label (used in frontmatter + provenance)."""
        return self._source_file_override or self._read_config().get("source_file")

    def is_built(self) -> bool:
        """True if at least one database exists."""
        return self._db_path.exists() or self._lancedb_dir.exists()

    # ------------------------------------------------------------------
    # Config helpers
    # ------------------------------------------------------------------

    def _read_config(self) -> Dict[str, Any]:
        if self._config_path.exists():
            try:
                return json.loads(self._config_path.read_text(encoding="utf-8"))
            except (json.JSONDecodeError, OSError):
                pass
        return {}

    def _write_config(self, data: Dict[str, Any]) -> None:
        self._kg_dir.mkdir(parents=True, exist_ok=True)
        existing = self._read_config()
        existing.update(data)
        self._config_path.write_text(json.dumps(existing, indent=2), encoding="utf-8")

    # ------------------------------------------------------------------
    # Lazy DocKG loader
    # ------------------------------------------------------------------

    def _load_dockg(self) -> Any:
        if self._dockg is not None:
            return self._dockg
        try:
            from doc_kg.kg import DocKG  # pylint: disable=import-outside-toplevel
        except ImportError as exc:
            raise ImportError(
                "doc-kg is not installed. Install it with: pip install doc-kg"
            ) from exc
        if not self.is_built():
            raise RuntimeError(
                f"DiaryKG is not built yet. Run DiaryKG.build() first."
            )
        self._dockg = DocKG(
            corpus_root=str(self._corpus_dir),
            db_path=str(self._db_path),
            lancedb_dir=str(self._lancedb_dir),
        )
        return self._dockg

    @staticmethod
    def _source_from_node(node: Dict[str, Any], fallback_sf: Optional[str]) -> str:
        """Extract original source file label from a DocKG result node."""
        meta = node.get("metadata") or {}
        return meta.get("source_file") or fallback_sf or node.get("file_path") or ""

    @staticmethod
    def _timestamp_from_node(node: Dict[str, Any]) -> Optional[str]:
        meta = node.get("metadata") or {}
        return meta.get("timestamp")

    # ------------------------------------------------------------------
    # Build
    # ------------------------------------------------------------------

    def build(
        self,
        batch_size: int = 0,
        seed: Optional[int] = None,
        max_chunks_per_entry: int = 3,
        chunking_strategy: str = "sentence_group",
        chunk_size: int = 512,
        sentences_per_chunk: int = 4,
        workers: int = 1,
        topics_file: Optional[str] = None,
        wipe: bool = False,
    ) -> int:
        """Run the full build pipeline: ingest → index.

        1. ``DiaryTransformer.ingest_to_corpus()`` → ``.diarykg/corpus/*.md``
        2. ``dockg build`` → ``.diarykg/graph.sqlite`` + ``.diarykg/lancedb/``

        :param batch_size: Entries to sample (``0`` = all).
        :param seed: RNG seed for reproducible sampling.
        :param max_chunks_per_entry: Max chunks emitted per diary entry.
        :param chunking_strategy: ``sentence_group`` | ``semantic`` | ``hybrid``.
        :param chunk_size: Max characters per chunk.
        :param sentences_per_chunk: Sentences per chunk for sentence_group/hybrid.
        :param workers: Parallel workers for feature extraction.
        :param topics_file: Path to YAML topics override.
        :param wipe: Delete existing corpus + DBs before rebuilding.
        :return: Number of ``.md`` chunk files written.
        :raises ValueError: If no source file is configured.
        """
        sf = self.source_file
        if not sf:
            raise ValueError(
                "source_file is required for build(). Pass it to DiaryKG() or --source."
            )

        src_path = self.root / sf
        if not src_path.exists():
            src_path = Path(sf)
        if not src_path.exists():
            raise FileNotFoundError(f"Source file not found: {sf}")

        if wipe:
            import shutil  # pylint: disable=import-outside-toplevel
            for target in (self._corpus_dir, self._lancedb_dir):
                if target.exists():
                    shutil.rmtree(target)
            if self._db_path.exists():
                self._db_path.unlink()
            self._dockg = None
            print(f"Wiped existing corpus + databases.")

        self._corpus_dir.mkdir(parents=True, exist_ok=True)

        # Step 1 — ingest via DiaryTransformer
        from diary_transformer import DiaryTransformer  # pylint: disable=import-outside-toplevel

        dt = DiaryTransformer(
            max_chunk_length=chunk_size,
            num_workers=workers,
            topics_file=topics_file,
            chunking_strategy=chunking_strategy,
            sentences_per_chunk=sentences_per_chunk,
        )
        n = dt.ingest_to_corpus(
            str(src_path),
            str(self._corpus_dir),
            batch_size=batch_size,
            seed=seed,
            max_chunks_per_entry=max_chunks_per_entry,
            source_file=sf,
        )

        # Step 2 — build DocKG index
        print(f"Building DocKG index for {self._corpus_dir}...")
        try:
            from doc_kg.kg import DocKG  # pylint: disable=import-outside-toplevel
            dockg = DocKG(
                corpus_root=str(self._corpus_dir),
                db_path=str(self._db_path),
                lancedb_dir=str(self._lancedb_dir),
            )
            dockg.build()
            self._dockg = dockg
        except ImportError:
            # Fallback: invoke dockg CLI
            result = subprocess.run(
                ["dockg", "build", "--repo", str(self._corpus_dir),
                 "--db", str(self._db_path),
                 "--lancedb", str(self._lancedb_dir)],
                check=True,
            )

        # Persist config
        self._write_config({
            "source_file": sf,
            "built_at": datetime.now(UTC).isoformat(),
            "chunk_count": n,
            "batch_size": batch_size,
            "chunking_strategy": chunking_strategy,
            "chunk_size": chunk_size,
        })

        print(f"DiaryKG build complete: {n} chunks indexed.")
        return n

    # ------------------------------------------------------------------
    # Query / Pack
    # ------------------------------------------------------------------

    def query(self, q: str, k: int = 8) -> List[Dict[str, Any]]:
        """Semantic search over the diary corpus.

        :param q: Natural-language query string.
        :param k: Number of results to return.
        :return: List of result dicts with keys: ``score``, ``summary``,
            ``source_file``, ``timestamp``, ``category``, ``context``,
            ``node_id``.
        """
        dockg = self._load_dockg()
        result = dockg.query(q, k=k)
        sf = self.source_file
        hits = []
        for node in result.nodes[:k]:
            relevance = node.get("relevance") or {}
            hits.append({
                "node_id": node.get("id", ""),
                "score": relevance.get("score", 0.0),
                "summary": node.get("text") or node.get("title", ""),
                "source_file": self._source_from_node(node, sf),
                "timestamp": self._timestamp_from_node(node),
                "category": (node.get("metadata") or {}).get("category", ""),
                "context": (node.get("metadata") or {}).get("context", ""),
            })
        return hits

    def pack(self, q: str, k: int = 8) -> List[Dict[str, Any]]:
        """Return source snippets for LLM ingestion.

        :param q: Natural-language query string.
        :param k: Number of snippets.
        :return: List of snippet dicts with keys: ``content``, ``source_file``,
            ``timestamp``, ``score``, ``node_id``.
        """
        dockg = self._load_dockg()
        pack_result = dockg.pack(q, k=k)
        sf = self.source_file
        snippets = []
        for node in pack_result.nodes:
            relevance = node.get("relevance") or {}
            snippets.append({
                "node_id": node.get("id", ""),
                "score": relevance.get("score", 0.0),
                "content": node.get("text") or "",
                "source_file": self._source_from_node(node, sf),
                "timestamp": self._timestamp_from_node(node),
            })
        return snippets

    # ------------------------------------------------------------------
    # Stats / Analyze
    # ------------------------------------------------------------------

    def stats(self) -> Dict[str, Any]:
        """Return corpus statistics.

        Reads config + corpus frontmatter without loading the full DocKG.

        :return: Dict with chunk_count, entry_count, source_file, built_at,
            temporal_span, topic_counts, context_counts.
        """
        config = self._read_config()
        md_files = list(self._corpus_dir.rglob("*.md")) if self._corpus_dir.exists() else []

        timestamps: List[str] = []
        categories: Counter = Counter()
        contexts: Counter = Counter()
        entry_indices: set = set()

        for md in md_files:
            try:
                fm = _parse_frontmatter(md.read_text(encoding="utf-8"))
                if fm.get("timestamp"):
                    timestamps.append(fm["timestamp"])
                if fm.get("category"):
                    categories[fm["category"]] += 1
                if fm.get("context"):
                    contexts[fm["context"]] += 1
                if fm.get("entry_index"):
                    entry_indices.add(fm["entry_index"])
            except OSError:
                continue

        timestamps.sort()
        span: Optional[Dict[str, str]] = None
        if len(timestamps) >= 2:
            span = {"start": timestamps[0], "end": timestamps[-1]}
        elif timestamps:
            span = {"start": timestamps[0], "end": timestamps[0]}

        # DocKG node/edge counts (only if built and loaded)
        node_count: Any = "n/a"
        edge_count: Any = "n/a"
        if self.is_built():
            try:
                dockg = self._load_dockg()
                s = dockg.store.stats()
                node_count = s.get("total_nodes", "n/a")
                edge_count = s.get("total_edges", "n/a")
            except Exception:  # pylint: disable=broad-exception-caught
                pass

        return {
            "source_file": config.get("source_file", self._source_file_override),
            "built_at": config.get("built_at"),
            "chunk_count": len(md_files),
            "entry_count": len(entry_indices),
            "temporal_span": span,
            "topic_counts": dict(categories.most_common()),
            "context_counts": dict(contexts.most_common()),
            "node_count": node_count,
            "edge_count": edge_count,
            "kind": "diary",
        }

    def analyze(self) -> str:
        """Return a Markdown analysis report.

        :return: Markdown string covering corpus overview, topic distribution,
            context distribution, temporal span, and DocKG baseline stats.
        """
        s = self.stats()
        span = s.get("temporal_span") or {}
        span_str = f"{span.get('start', '?')} → {span.get('end', '?')}" if span else "n/a"

        lines: List[str] = [
            "# DiaryKG Analysis Report",
            "",
            f"**Root:** `{self.root}`  |  **Source:** `{s.get('source_file', 'unknown')}`",
            "",
            "## Corpus Overview",
            "",
            f"- Chunk files   : **{s['chunk_count']}**",
            f"- Diary entries : **{s['entry_count']}**",
            f"- Temporal span : **{span_str}**",
            f"- Built at      : {s.get('built_at', 'n/a')}",
            f"- DocKG nodes   : {s['node_count']}",
            f"- DocKG edges   : {s['edge_count']}",
            "",
            "## Topic Distribution",
            "",
            "| Category | Chunks |",
            "|---|---:|",
        ]
        for cat, cnt in (s.get("topic_counts") or {}).items():
            lines.append(f"| {cat} | {cnt} |")

        lines += [
            "",
            "## Context Distribution",
            "",
            "| Context | Chunks |",
            "|---|---:|",
        ]
        for ctx, cnt in (s.get("context_counts") or {}).items():
            lines.append(f"| {ctx} | {cnt} |")
        lines.append("")

        return "\n".join(lines)

    # ------------------------------------------------------------------
    # Snapshots
    # ------------------------------------------------------------------

    def _snapshot_manifest_path(self) -> Path:
        return self._snapshot_dir / "manifest.json"

    def _load_manifest(self) -> Dict[str, Any]:
        mp = self._snapshot_manifest_path()
        if mp.exists():
            try:
                return json.loads(mp.read_text(encoding="utf-8"))
            except (json.JSONDecodeError, OSError):
                pass
        return {"format": "1.0", "last_update": None, "snapshots": []}

    def _save_manifest(self, manifest: Dict[str, Any]) -> None:
        self._snapshot_dir.mkdir(parents=True, exist_ok=True)
        manifest["last_update"] = datetime.now(UTC).isoformat()
        self._snapshot_manifest_path().write_text(
            json.dumps(manifest, indent=2), encoding="utf-8"
        )

    def snapshot_save(self, label: Optional[str] = None) -> Dict[str, Any]:
        """Capture a point-in-time snapshot of corpus metrics.

        The snapshot key is the current git commit hash if available,
        otherwise a UTC timestamp slug.  Metrics include chunk count,
        entry count, temporal span, topic and context distributions.

        :param label: Optional human-readable label for this snapshot.
        :return: The snapshot dict that was saved.
        :raises RuntimeError: If the KG is not built.
        """
        if not self.is_built():
            raise RuntimeError("DiaryKG is not built. Run build() first.")

        key = _git_commit_hash(self.root) or datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
        branch = _git_branch(self.root)

        current = self.stats()
        manifest = self._load_manifest()

        # Delta vs previous snapshot
        vs_previous: Optional[Dict[str, Any]] = None
        vs_baseline: Optional[Dict[str, Any]] = None
        snapshots = manifest.get("snapshots", [])

        if snapshots:
            prev = snapshots[-1].get("metrics", {})
            vs_previous = {
                "chunks": current["chunk_count"] - prev.get("chunk_count", 0),
                "entries": current["entry_count"] - prev.get("entry_count", 0),
            }
            baseline = snapshots[0].get("metrics", {})
            vs_baseline = {
                "chunks": current["chunk_count"] - baseline.get("chunk_count", 0),
                "entries": current["entry_count"] - baseline.get("entry_count", 0),
            }

        config = self._read_config()
        snapshot: Dict[str, Any] = {
            "key": key,
            "branch": branch,
            "timestamp": datetime.now(UTC).isoformat(),
            "label": label,
            "source_file": current.get("source_file"),
            "metrics": {
                "chunk_count": current["chunk_count"],
                "entry_count": current["entry_count"],
                "node_count": current["node_count"],
                "edge_count": current["edge_count"],
                "temporal_span": current.get("temporal_span"),
                "topic_counts": current.get("topic_counts", {}),
                "context_counts": current.get("context_counts", {}),
                "chunking_strategy": config.get("chunking_strategy"),
                "chunk_size": config.get("chunk_size"),
            },
            "vs_previous": vs_previous,
            "vs_baseline": vs_baseline,
        }

        # Write individual snapshot file
        self._snapshot_dir.mkdir(parents=True, exist_ok=True)
        snap_file = self._snapshot_dir / f"{key}.json"
        snap_file.write_text(json.dumps(snapshot, indent=2), encoding="utf-8")

        # Update manifest
        manifest["snapshots"].append({
            "key": key,
            "branch": branch,
            "timestamp": snapshot["timestamp"],
            "label": label,
            "file": f"{key}.json",
            "metrics": {
                "chunk_count": current["chunk_count"],
                "entry_count": current["entry_count"],
            },
        })
        self._save_manifest(manifest)

        return snapshot

    def snapshot_list(self) -> List[Dict[str, Any]]:
        """Return all snapshots from the manifest (newest first).

        :return: List of snapshot summary dicts.
        """
        manifest = self._load_manifest()
        return list(reversed(manifest.get("snapshots", [])))

    def snapshot_show(self, key: str) -> Dict[str, Any]:
        """Load a full snapshot by key.

        :param key: Commit hash or timestamp slug (from ``snapshot_list()``).
        :return: Full snapshot dict.
        :raises FileNotFoundError: If the snapshot does not exist.
        """
        snap_file = self._snapshot_dir / f"{key}.json"
        if not snap_file.exists():
            raise FileNotFoundError(f"Snapshot not found: {key}")
        return json.loads(snap_file.read_text(encoding="utf-8"))

    def snapshot_diff(self, key_a: str, key_b: str) -> Dict[str, Any]:
        """Compare two snapshots and return a delta report.

        :param key_a: Earlier snapshot key.
        :param key_b: Later snapshot key.
        :return: Dict with ``from``, ``to``, and ``delta`` fields.
        """
        a = self.snapshot_show(key_a)
        b = self.snapshot_show(key_b)
        ma = a.get("metrics", {})
        mb = b.get("metrics", {})
        return {
            "from": {"key": key_a, "timestamp": a.get("timestamp"), "label": a.get("label")},
            "to": {"key": key_b, "timestamp": b.get("timestamp"), "label": b.get("label")},
            "delta": {
                "chunks": mb.get("chunk_count", 0) - ma.get("chunk_count", 0),
                "entries": mb.get("entry_count", 0) - ma.get("entry_count", 0),
                "nodes": (mb.get("node_count") or 0) - (ma.get("node_count") or 0)
                if isinstance(mb.get("node_count"), int) and isinstance(ma.get("node_count"), int)
                else "n/a",
            },
        }
