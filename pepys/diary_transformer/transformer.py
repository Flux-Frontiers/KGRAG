"""transformer.py — DiaryTransformer: the main orchestrator class.

``DiaryTransformer`` wires together the parsing, chunking, feature, and
classification modules into two public workflows:

``transform_file``
    One-shot batch: parse → chunk-cache → diverse-sample → classify → save.

``transform_file_incremental``
    Resumable: same pipeline but tracks injected indices in a ``StateManager``
    so repeated runs only process new entries.
"""

from __future__ import annotations

import multiprocessing as mp
import sys
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional

import spacy
from sentence_transformers import SentenceTransformer

from .chunker import segment_content
from .classifier import (
    classify_chunk_hybrid,
    discover_semantic_categories,
    extract_context,
)
from .features import select_diverse_sample
from .models import DiaryEntry, EntryChunk
from .parser import parse_diary_file
from .state import (
    StateManager,
    filter_uninjected,
    load_chunks_from_cache,
    save_chunks_to_cache,
)


class DiaryTransformer:
    """Transform diary entries into semantic memory chunks.

    :param max_chunk_length: Hard character cap per chunk.
    :param num_workers: Parallel workers for feature extraction (1 = sequential).
    :param topics_file: Path to a YAML topics file; defaults to ``topics.yaml``
        bundled with this package.
    :param chunking_strategy: ``"semantic"``, ``"sentence_group"`` (default), or
        ``"hybrid"``.
    :param sentences_per_chunk: Sentences per chunk for ``sentence_group`` /
        ``hybrid`` strategies.
    """

    def __init__(
        self,
        max_chunk_length: int = 512,
        num_workers: int = 1,
        topics_file: Optional[str] = None,
        chunking_strategy: str = "sentence_group",
        sentences_per_chunk: int = 4,
    ) -> None:
        self.max_chunk_length = max_chunk_length
        self.chunking_strategy = chunking_strategy
        self.sentences_per_chunk = sentences_per_chunk
        self.num_workers = max(1, min(num_workers, mp.cpu_count()))
        self.topics_file = topics_file
        self._current_input_path: Optional[str] = None
        self._init_models()

    # ------------------------------------------------------------------
    # Initialisation
    # ------------------------------------------------------------------

    def _init_models(self) -> None:
        print("Loading NLP models...")

        try:
            self.nlp = spacy.load("en_core_web_sm")
        except OSError:
            print("Error: spaCy model not found. Run: python -m spacy download en_core_web_sm")
            sys.exit(1)

        try:
            self.sentence_model = SentenceTransformer("all-MiniLM-L6-v2")
        except Exception as exc:
            print(f"Error loading sentence transformer: {exc}")
            sys.exit(1)

        self.topic_classifier: Optional[Any] = None
        try:
            from .topic_classifier import TopicClassifier
            path = self.topics_file or str(Path(__file__).parent / "topics.yaml")
            self.topic_classifier = TopicClassifier(path)
            print(f"✓ Loaded TopicClassifier: {path}")
        except Exception as exc:
            print(f"Warning: TopicClassifier unavailable ({exc}); using unsupervised only")

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _segment(
        self,
        content: str,
        max_chunks_per_entry: int = 3,
        timestamp: Optional[datetime] = None,
    ) -> List[str]:
        return segment_content(
            content=content,
            nlp=self.nlp,
            sentence_model=self.sentence_model,
            max_chunk_length=self.max_chunk_length,
            chunking_strategy=self.chunking_strategy,
            sentences_per_chunk=self.sentences_per_chunk,
            max_chunks_per_entry=max_chunks_per_entry,
            timestamp=timestamp,
        )

    def _load_or_build_cache(self, input_path: str) -> List[DiaryEntry]:
        """Return entries from chunk cache, building it first if absent."""
        self._current_input_path = input_path
        base = Path(input_path).parent / f"{Path(input_path).stem}_chunks.json"
        pkl = Path(str(base).replace(".json", ".pkl"))

        if pkl.exists() or base.exists():
            print("✓ Found chunk cache, loading...")
            return load_chunks_from_cache(str(base))

        print("No chunk cache found, parsing and chunking all entries...")
        entries = parse_diary_file(input_path)
        for idx, entry in enumerate(entries):
            entry.index = idx
        save_chunks_to_cache(entries, str(base), self._segment)
        return load_chunks_from_cache(str(base))

    # ------------------------------------------------------------------
    # Core transform pipeline
    # ------------------------------------------------------------------

    def transform_entries(
        self,
        entries: List[DiaryEntry],
        seed: Optional[int] = None,
        max_chunks_per_entry: int = 3,
    ) -> List[EntryChunk]:
        """Segment, categorise, and classify a list of diary entries.

        :param entries: Entries to transform.
        :param seed: RNG seed for reproducible category discovery.
        :param max_chunks_per_entry: Max chunks emitted per entry.
        :return: List of ``EntryChunk`` objects.
        """
        print(f"Transforming {len(entries)} entries into memory chunks")

        all_chunks: List[tuple] = []
        chunk_texts: List[str] = []

        print("Segmenting content...")
        for idx, entry in enumerate(entries):
            if idx > 0 and idx % 5 == 0:
                pct = (idx + 1) * 100 // len(entries)
                print(f"  Entry {idx + 1}/{len(entries)} ({pct}%)")
            for chunk in self._segment(entry.content, max_chunks_per_entry, entry.timestamp):
                all_chunks.append((idx, entry, chunk))
                chunk_texts.append(chunk)

        print(f"Created {len(all_chunks)} semantic chunks")

        categories = discover_semantic_categories(chunk_texts, seed=seed)

        print("Classifying chunks...")
        memory_chunks: List[EntryChunk] = []
        for i, (entry_idx, entry, chunk) in enumerate(all_chunks):
            if i > 0 and i % 10 == 0:
                pct = (i + 1) * 100 // len(all_chunks)
                print(f"  Chunk {i + 1}/{len(all_chunks)} ({pct}%)")
            category, _ = classify_chunk_hybrid(chunk, categories, self.topic_classifier)
            context = extract_context(chunk, self.nlp)
            memory_chunks.append(
                EntryChunk(
                    timestamp=entry.timestamp,
                    semantic_category=category,
                    context_classification=context,
                    content=chunk,
                    confidence=1.0,
                    phase="immediate",
                    source_entry_index=entry_idx,
                    source_entry=entry,
                )
            )

        print(f"Generated {len(memory_chunks)} memory chunks")
        return memory_chunks

    def save_entries(
        self,
        entries: List[EntryChunk],
        output_path: str,
        run_params: Optional[Dict] = None,
    ) -> None:
        """Write chunks to a pipe-delimited output file with provenance headers.

        :param entries: Chunks to write.
        :param output_path: Destination file path.
        :param run_params: Run metadata written as comment header lines.
        """
        print(f"Saving {len(entries)} entries to {output_path}")
        with open(output_path, "w", encoding="utf-8") as f:
            if run_params:
                f.write("# Diary Transformer - Run Parameters\n")
                for key in (
                    "timestamp", "input_file", "batch_size",
                    "chunk_size", "max_chunks_per_entry", "seed",
                ):
                    f.write(f"# {key.replace('_', ' ').title()}: {run_params.get(key, 'Unknown')}\n")
                f.write("#\n")

            f.write("# ======== ENTRIES ========\n\n")
            current_source: Optional[DiaryEntry] = None
            for memory in entries:
                source = getattr(memory, "source_entry", None)
                sidx = getattr(memory, "source_entry_index", None)
                if source and source is not current_source:
                    current_source = source
                    ts = source.timestamp.strftime("%Y-%m-%d %H:%M")
                    preview = source.content[:100] + ("..." if len(source.content) > 100 else "")
                    f.write(f"\n# === Source Entry #{sidx + 1} ({ts}) ===\n")
                    f.write(f"# Original: {source.original_type} | {source.category}\n")
                    f.write(f"# Content: {preview}\n")
                    f.write("# Extracted entries:\n")
                ts = memory.timestamp.strftime("%Y-%m-%dT%H:%M")
                f.write(
                    f"{ts} | {memory.semantic_category} | "
                    f"{memory.context_classification} | {memory.content}\n"
                )
        print(f"Entries saved to {output_path}")

    # ------------------------------------------------------------------
    # Public workflows
    # ------------------------------------------------------------------

    def transform_file(
        self,
        input_path: str,
        output_path: str,
        batch_size: int = 20,
        seed: Optional[int] = None,
        max_chunks_per_entry: int = 3,
    ) -> None:
        """One-shot transformation: parse, sample, transform, save.

        :param input_path: Pipe-delimited diary file.
        :param output_path: Output file for transformed chunks.
        :param batch_size: Number of diverse entries to process.
        :param seed: RNG seed.
        :param max_chunks_per_entry: Max chunks per diary entry.
        """
        print(f"Starting transformation: {input_path} -> {output_path}")
        entries = self._load_or_build_cache(input_path)
        selected = select_diverse_sample(
            entries, batch_size, self.nlp, self.num_workers,
            input_file_path=self._current_input_path, seed=seed,
        )
        memory_entries = self.transform_entries(selected, seed=seed, max_chunks_per_entry=max_chunks_per_entry)
        memory_entries.sort(key=lambda m: m.timestamp)
        run_params = {
            "timestamp": datetime.now().isoformat(),
            "input_file": str(input_path),
            "batch_size": batch_size,
            "chunk_size": self.max_chunk_length,
            "max_chunks_per_entry": max_chunks_per_entry,
            "seed": seed,
        }
        self.save_entries(memory_entries, output_path, run_params)
        print(f"Transformation complete! Generated {len(memory_entries)} entries")

    def ingest_to_corpus(
        self,
        input_path: str,
        corpus_dir: str,
        batch_size: int = 20,
        seed: Optional[int] = None,
        max_chunks_per_entry: int = 3,
        source_file: Optional[str] = None,
    ) -> int:
        """Transform diary entries and write DocKG-compatible Markdown files.

        Each chunk is written as a ``.md`` file with YAML frontmatter carrying
        provenance fields that ``DocKG`` can index.  The ``source_file`` value
        surfaces the original source ``.txt`` path — not the generated chunk
        file — so cross-KG queries can cite the real document.

        Directory layout::

            <corpus_dir>/
              entry_0042_chunk_0.md
              entry_0042_chunk_1.md
              ...

        Frontmatter fields per chunk::

            source_file: pepys_diary.txt
            entry_index: 42
            chunk_index: 0
            timestamp: 1667-04-15T22:30
            category: domestic
            context: Home

        :param input_path: Pipe-delimited diary source file.
        :param corpus_dir: Destination directory for generated ``.md`` files.
        :param batch_size: Number of diverse entries to sample (0 = all).
        :param seed: RNG seed for reproducible diversity sampling.
        :param max_chunks_per_entry: Max chunks emitted per entry.
        :param source_file: Override provenance path written into frontmatter.
            Defaults to the basename of *input_path*.
        :return: Number of ``.md`` files written.
        """
        from pathlib import Path as _Path  # pylint: disable=import-outside-toplevel

        out_dir = _Path(corpus_dir)
        out_dir.mkdir(parents=True, exist_ok=True)

        src_label = source_file or _Path(input_path).name

        entries = self._load_or_build_cache(input_path)
        # Stamp source_file on every entry if not already set
        for e in entries:
            if not e.source_file:
                e.source_file = src_label

        if batch_size and len(entries) > batch_size:
            selected = select_diverse_sample(
                entries, batch_size, self.nlp, self.num_workers,
                input_file_path=self._current_input_path, seed=seed,
            )
        else:
            selected = entries

        memory_entries = self.transform_entries(selected, seed=seed, max_chunks_per_entry=max_chunks_per_entry)

        written = 0
        chunk_counter: Dict[int, int] = {}
        for mem in memory_entries:
            eidx = mem.source_entry_index
            cidx = chunk_counter.get(eidx, 0)
            chunk_counter[eidx] = cidx + 1

            src = mem.source_entry
            sf = (src.source_file if src and src.source_file else src_label) if src else src_label

            frontmatter = (
                "---\n"
                f"source_file: {sf}\n"
                f"entry_index: {eidx}\n"
                f"chunk_index: {cidx}\n"
                f"timestamp: {mem.timestamp.strftime('%Y-%m-%dT%H:%M')}\n"
                f"category: {mem.semantic_category}\n"
                f"context: {mem.context_classification}\n"
                "---\n"
            )
            fname = f"entry_{eidx:04d}_chunk_{cidx}.md"
            (out_dir / fname).write_text(frontmatter + "\n" + mem.content + "\n", encoding="utf-8")
            written += 1

        print(f"✓ Wrote {written} chunk files to {corpus_dir}")
        return written

    def transform_file_incremental(
        self,
        input_path: str,
        output_path: str,
        state_file: str,
        batch_size: int = 20,
        seed: Optional[int] = None,
        max_chunks_per_entry: int = 3,
        resume_mode: bool = False,
    ) -> None:
        """Incremental transformation with resumable state.

        :param input_path: Pipe-delimited diary file.
        :param output_path: Output file for transformed chunks.
        :param state_file: JSON file tracking injected entry indices.
        :param batch_size: Max entries per run.
        :param seed: RNG seed.
        :param max_chunks_per_entry: Max chunks per diary entry.
        :param resume_mode: If True, load existing state to skip processed entries.
        """
        print(f"Starting transformation: {input_path} -> {output_path}")
        print(f"Resume mode: {resume_mode}")

        state = StateManager(state_file)
        if resume_mode:
            state.load(input_path)
            print(f"Loaded state: {len(state.injected_entry_indices)} entries already injected")

        entries = self._load_or_build_cache(input_path)
        available = filter_uninjected(entries, state.injected_entry_indices)

        if not available:
            print("✓ All entries already injected, nothing to do")
            return

        print(f"Found {len(available)} entries available for injection")

        if len(available) > batch_size:
            selected = select_diverse_sample(
                available, batch_size, self.nlp, self.num_workers,
                input_file_path=self._current_input_path, seed=seed,
            )
        else:
            selected = available
            print(f"Processing all {len(selected)} available entries")

        memory_entries = self.transform_entries(selected, seed=seed, max_chunks_per_entry=max_chunks_per_entry)
        memory_entries.sort(key=lambda m: m.timestamp)

        state.processing_stats["total_runs"] += 1
        state.processing_stats["total_entries_injected"] += len(selected)
        state.processing_stats["last_run"] = datetime.now().isoformat()
        state.mark_injected(selected)

        run_params = {
            "timestamp": datetime.now().isoformat(),
            "input_file": str(input_path),
            "batch_size": len(selected),
            "chunk_size": self.max_chunk_length,
            "max_chunks_per_entry": max_chunks_per_entry,
            "seed": seed,
            "mode": "resume" if resume_mode else "incremental",
        }
        self.save_entries(memory_entries, output_path, run_params)
        state.save(output_path, run_params)

        print("\nIncremental transformation complete!")
        print(f"  - {len(memory_entries)} new entries")
        print(f"  - Total runs: {state.processing_stats['total_runs']}")
        print(f"  - Total entries injected: {state.processing_stats['total_entries_injected']}")
