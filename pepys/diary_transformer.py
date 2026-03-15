#!/usr/bin/env python3
"""
Diary Transformer

Transforms diary entries into semantically chunked, contextually rich entries
with topic classification, temporal preservation, and intelligent caching.

This is a general-purpose diary ingestion tool for memory systems like Hindsight.
It processes any diary format and creates structured, searchable memory chunks.

ALGORITHM OVERVIEW
==================

A sophisticated NLP pipeline that converts diary entries into structured,
semantically meaningful memory chunks suitable for modern memory systems.
The process combines supervised topic classification, semantic analysis,
and performance optimization through caching.

CORE ALGORITHM PHASES
=====================

Phase 1: Diverse Entry Selection (Cached)
------------------------------------------
- Analyzes entries using spaCy NLP features (entities, POS tags, length)
- Caches feature extraction results for dramatic speedup on subsequent runs
- Applies k-means clustering on normalized feature vectors to ensure diversity
- Selects representative entries from each cluster to avoid redundancy
- Ensures temporal and thematic coverage across the corpus
- Cache validation based on file modification times with automatic invalidation

Phase 2: Semantic Content Segmentation
--------------------------------------
- Strips legacy temporal preambles from content if present
- Uses sentence-transformers embeddings to analyze semantic similarity
- Identifies semantic boundaries where sentence similarity drops significantly
- Splits content at boundaries while respecting length constraints
- Filters out meaningless fragments
- Temporal data handled via direct database writes to occurred_start/occurred_end

Phase 3: Topic Classification
-----------------------------
- Supervised classification using configurable topics (YAML file)
- Confidence scoring and topic prioritization
- Unsupervised k-means clustering as fallback
- Supports domain-specific vocabularies

Phase 4: Memory Creation
------------------------
- Creates EntryChunk objects with classified categories
- Extracts contextual classifications
- Integrates confidence scores
- Tracks source provenance
- Maintains temporal accuracy

Phase 5: Structured Output Generation
-------------------------------------
- Saves entries in pipe-delimited format with source tracking
- Provides comprehensive provenance tracking
- Includes metadata headers and transformation statistics

CACHING & PERFORMANCE OPTIMIZATION
===================================

Diversity Feature Caching:
- Creates .diary_cache/ directory alongside input files
- Caches normalized diversity feature DataFrames using pickle
- File hash-based cache naming for multiple input file support
- Automatic cache invalidation when input files are modified
- Graceful fallback to recomputation on cache failures

Performance Benefits:
- First run: Standard speed with feature computation and caching
- Subsequent runs: 5-10x faster by skipping expensive NLP analysis
- Progress indicators throughout all phases
- Multiprocessing support for feature extraction

DEPENDENCIES
============

Core NLP & Classification:
- spaCy (en_core_web_sm): Sentence segmentation, NER, POS tagging
- sentence-transformers: Semantic embeddings for similarity analysis
- TopicClassifier: Supervised classification with configurable topics

ML/Analytics:
- scikit-learn: TF-IDF vectorization, k-means clustering
- pandas: Feature analysis and data manipulation
- numpy: Vector operations and similarity calculations

USAGE
=====

Basic execution:
    from personal_agent.tools.diary_transformer import DiaryTransformer

    transformer = DiaryTransformer(
        max_chunk_length=512,
        num_workers=4,  # Parallel processing
        topics_file="path/to/topics.yaml"  # Optional
    )

    transformer.transform_file(
        input_path="diary.txt",
        output_path="transformed.txt",
        batch_size=20
    )

Input format:
    TIMESTAMP | TYPE | CATEGORY | CONTENT
    Example: 2024-01-15T10:30 | raw | DiaryEntry | Today I went to...

The transformer creates semantically chunked, temporally accurate entries
optimized for modern memory systems like Hindsight.
"""

import argparse
import hashlib
import json
import multiprocessing as mp
import pickle
import random
import re
import sys
import warnings

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import numpy as np
import pandas as pd
import spacy
from sentence_transformers import SentenceTransformer
from sklearn.cluster import KMeans
from sklearn.feature_extraction.text import TfidfVectorizer
from tqdm import tqdm

from personal_agent.core.topic_classifier import TopicClassifier


def _extract_entry_features_worker(entry_data: Tuple[int, str]) -> Dict:
    """Worker function to extract features from a single entry.

    This function is called by multiprocessing workers and must be at module level.
    Each worker loads its own spaCy model to avoid serialization issues.

    :param entry_data: Tuple of (index, entry_content)
    :return: Dictionary with features for this entry
    """

    idx, content = entry_data

    # Load spaCy model in worker process (cached per worker)
    if not hasattr(_extract_entry_features_worker, "nlp"):
        try:
            _extract_entry_features_worker.nlp = spacy.load("en_core_web_sm")
        except OSError:
            # Fallback if model not available - return basic features
            return {
                "index": idx,
                "length": len(content),
                "sentences": 1,
                "entities": 0,
                "nouns": 0,
                "verbs": 0,
                "proper_nouns": 0,
            }

    nlp = _extract_entry_features_worker.nlp
    doc = nlp(content)

    # Extract features
    features = {
        "index": idx,
        "length": len(content),
        "sentences": len(list(doc.sents)),
        "entities": len(doc.ents),
        "nouns": len([token for token in doc if token.pos_ == "NOUN"]),
        "verbs": len([token for token in doc if token.pos_ == "VERB"]),
        "proper_nouns": len([token for token in doc if token.pos_ == "PROPN"]),
    }

    return features


@dataclass
class DiaryEntry:
    """Represents a parsed diary entry."""

    timestamp: datetime
    original_type: str
    category: str
    content: str
    index: Optional[int] = None
    chunks: Optional[List[str]] = None


@dataclass
class EntryChunk:
    """Represents a transformed memory chunk."""

    timestamp: datetime
    semantic_category: str
    context_classification: str
    content: str
    confidence: float = 1.0
    phase: str = "immediate"
    source_entry_index: int = -1
    source_entry: Optional[DiaryEntry] = None


class DiaryTransformer:
    """Transforms diary entries into semantic memory chunks.

    A general-purpose diary ingestion tool that processes any diary format
    and creates structured, searchable memory chunks optimized for memory
    systems like Hindsight.
    """

    def __init__(
        self,
        max_chunk_length: int = 512,
        num_workers: int = 1,
        topics_file: Optional[str] = None,
        chunking_strategy: str = "semantic",
        sentences_per_chunk: int = 4,
    ) -> None:
        """Initialize the transformer.

        :param max_chunk_length: Maximum character length per memory chunk
        :param num_workers: Number of parallel workers for feature extraction (1 = sequential)
        :param topics_file: Optional path to custom topics YAML file
        :param chunking_strategy: Chunking strategy - "semantic" (similarity-based), "sentence_group" (N sentences), or "hybrid"
        :param sentences_per_chunk: Number of sentences per chunk when using sentence_group strategy (default: 4)
        """
        self.max_chunk_length = max_chunk_length
        self.chunking_strategy = chunking_strategy
        self.sentences_per_chunk = sentences_per_chunk

        # Validate and cap num_workers
        max_cpus = mp.cpu_count()
        if num_workers < 1:
            print("Warning: num_workers must be >= 1, using 1")
            num_workers = 1
        elif num_workers > max_cpus:
            print(
                f"Warning: num_workers ({num_workers}) exceeds CPU count ({max_cpus}), using {max_cpus}"
            )
            num_workers = max_cpus
        self.num_workers = num_workers

        self.nlp = None
        self.sentence_model = None
        self.topic_classifier = None
        self.topics_file = topics_file
        self.semantic_categories = []
        self.context_patterns = {}

        # State tracking for resumable processing
        self.state_file_path: Optional[str] = None
        self.injected_entry_indices: set = set()
        self.chunk_cache_file: Optional[str] = None
        self.processing_stats = {
            "total_runs": 0,
            "total_entries_injected": 0,
            "last_run": None,
        }

        # Initialize NLP models
        self._init_models()

    def _init_models(self) -> None:
        """Initialize spaCy, sentence transformer, and topic classifier models."""
        print("Loading NLP models...")

        # Load spaCy
        try:
            self.nlp = spacy.load("en_core_web_sm")
        except OSError:
            print("Error: spaCy English model not found. Please install with:")
            print("poetry run python -m spacy download en_core_web_sm")
            sys.exit(1)

        # Load sentence transformer
        try:
            self.sentence_model = SentenceTransformer("all-MiniLM-L6-v2")
        except Exception as e:
            print(f"Error loading sentence transformer: {e}")
            print(
                "Please install sentence-transformers: poetry add sentence-transformers"
            )
            sys.exit(1)

        # Load topic classifier
        try:
            if self.topics_file:
                # Use custom topics file
                self.topic_classifier = TopicClassifier(self.topics_file)
                print(
                    f"✓ Loaded TopicClassifier with custom topics: {self.topics_file}"
                )
            else:
                # Use default general topics
                default_topics_path = (
                    Path(__file__).parent.parent / "core" / "topics.yaml"
                )
                self.topic_classifier = TopicClassifier(str(default_topics_path))
                print("✓ Loaded TopicClassifier with default general topics")
        except Exception as e:
            print(f"Warning: Could not load TopicClassifier: {e}")
            print("Will use unsupervised classification only")

    def _generate_entry_hash(self, entry: DiaryEntry) -> str:
        """Generate a hash for a diary entry to track processing.

        :param entry: Diary entry to hash
        :return: SHA256 hash of entry content and timestamp
        """
        content = f"{entry.timestamp.isoformat()}|{entry.content}"
        return hashlib.sha256(content.encode()).hexdigest()[:16]

    def _migrate_old_state(self, state: dict, input_path: str) -> dict:
        """Migrate old state format to new format if needed.

        :param state: Old state dict
        :param input_path: Path to diary file
        :return: Migrated state dict
        """
        if "processed_entries" not in state or "injected_entry_indices" in state:
            return state  # Already migrated or new format

        print("\n⚠️  Migrating old state format to new format...")
        print(f"   Found {len(state['processed_entries'])} processed entries")

        # Parse diary to get all entries with indices
        all_entries = self.parse_diary_file(input_path)

        # Build mapping from timestamp to index
        timestamp_to_index = {}
        for idx, entry in enumerate(all_entries):
            timestamp_key = entry.timestamp.isoformat()
            timestamp_to_index[timestamp_key] = idx

        # Convert processed_entries timestamps to indices
        injected_indices = set()
        for timestamp_key in state["processed_entries"].keys():
            if timestamp_key in timestamp_to_index:
                injected_indices.add(timestamp_to_index[timestamp_key])
            else:
                print(f"   Warning: Could not find entry for timestamp {timestamp_key}")

        # Create migrated state
        old_stats = state.get("processing_stats", {})
        migrated_state = {
            "output_file": state.get("output_file"),
            "injected_entry_indices": list(injected_indices),
            "chunk_cache_file": None,
            "processing_stats": {
                "total_runs": old_stats.get("total_runs", 0),
                "total_entries_injected": len(injected_indices),
                "last_run": old_stats.get("last_run"),
            },
            "run_parameters": state.get("run_parameters", {}),
            "_migration_note": f"Migrated from old format on {datetime.now().isoformat()}",
            "_original_processed_count": len(state["processed_entries"]),
        }

        # Backup old state
        if self.state_file_path:
            backup_path = Path(self.state_file_path).with_suffix(".json.backup")
            with open(backup_path, "w", encoding="utf-8") as f:
                json.dump(state, f, indent=2)
            print(f"✓ Old state backed up to: {backup_path}")
        else:
            print("⚠ Could not backup old state: state_file_path not set")

        print(f"✓ Migrated {len(injected_indices)} entries to new format")
        print(f"✓ Old state backed up to: {backup_path}")

        return migrated_state

    def _load_state(self, state_file: str, input_path: Optional[str] = None) -> bool:
        """Load processing state from file.

        :param state_file: Path to state file
        :param input_path: Path to diary file (needed for migration)
        :return: True if state loaded successfully
        """
        state_path = Path(state_file)
        if not state_path.exists():
            print(f"No existing state file found at {state_file}")
            return False

        try:
            with open(state_path, "r", encoding="utf-8") as f:
                state = json.load(f)

            # Migrate old format if needed
            if "processed_entries" in state and input_path:
                state = self._migrate_old_state(state, input_path)
                # Save migrated state immediately
                with open(state_path, "w", encoding="utf-8") as f:
                    json.dump(state, f, indent=2)
                print(f"✓ Migrated state saved to {state_file}")

            self.injected_entry_indices = set(state.get("injected_entry_indices", []))
            self.chunk_cache_file = state.get("chunk_cache_file")
            self.processing_stats = state.get(
                "processing_stats",
                {
                    "total_runs": 0,
                    "total_entries_injected": 0,
                    "last_run": None,
                },
            )
            self.state_file_path = state_file

            print(
                f"✓ Loaded state: {len(self.injected_entry_indices)} entries injected"
            )
            if self.processing_stats.get("last_run"):
                print(f"  Last run: {self.processing_stats['last_run']}")
            return True
        except (json.JSONDecodeError, OSError) as e:
            print(f"Warning: Failed to load state file: {e}")
            return False

    def _save_state(self, output_file: str, run_params: Dict) -> None:
        """Save processing state to file.

        :param output_file: Path to output entries file
        :param run_params: Run parameters for this processing session
        """
        if not self.state_file_path:
            return

        state = {
            "output_file": str(output_file),
            "injected_entry_indices": list(self.injected_entry_indices),
            "chunk_cache_file": self.chunk_cache_file,
            "processing_stats": self.processing_stats,
            "run_parameters": run_params,
        }

        try:
            state_path = Path(self.state_file_path)
            state_path.parent.mkdir(parents=True, exist_ok=True)

            with open(state_path, "w", encoding="utf-8") as f:
                json.dump(state, f, indent=2)

            print(f"✓ State saved to {self.state_file_path}")
        except OSError as e:
            print(f"Warning: Failed to save state file: {e}")

    def _filter_uninjected_entries(self, entries: List[DiaryEntry]) -> List[DiaryEntry]:
        """Filter out already-injected entries.

        :param entries: List of all diary entries
        :return: List of uninjected entries
        """
        if not self.injected_entry_indices:
            return entries

        uninjected = []
        for entry in entries:
            if (
                hasattr(entry, "index")
                and entry.index not in self.injected_entry_indices
            ):
                uninjected.append(entry)

        skipped = len(entries) - len(uninjected)
        if skipped > 0:
            print(f"Skipping {skipped} already-injected entries")

        return uninjected

    def _save_chunks_to_json(self, entries: List[DiaryEntry], cache_path: str) -> None:
        """Save chunked entries to pickle cache.

        :param entries: List of diary entries with chunks
        :param cache_path: Path to cache file (will use .pkl extension)
        """
        cache_path_pkl = cache_path.replace(".json", ".pkl")
        print(f"Caching {len(entries)} chunked entries to {cache_path_pkl}")

        cache_data = {
            "version": "1.0",
            "created": datetime.now().isoformat(),
            "total_entries": len(entries),
            "entries": [],
        }

        for idx, entry in enumerate(entries):
            # Chunk the entry with timestamp for explicit preamble
            chunks = self.segment_content(entry.content, timestamp=entry.timestamp)

            cache_data["entries"].append(
                {
                    "index": idx,
                    "timestamp": entry.timestamp.isoformat(),
                    "original_type": entry.original_type,
                    "category": entry.category,
                    "content": entry.content,
                    "chunks": chunks,
                }
            )

        with open(cache_path_pkl, "wb") as f:
            pickle.dump(cache_data, f, protocol=pickle.HIGHEST_PROTOCOL)

        print(f"✓ Cached {len(entries)} entries with chunks")

    def _load_chunks_from_json(self, cache_path: str) -> List[DiaryEntry]:
        """Load chunked entries from pickle cache.

        :param cache_path: Path to cache file
        :return: List of DiaryEntry objects with .chunks attribute
        """
        cache_path_pkl = cache_path.replace(".json", ".pkl")

        if Path(cache_path_pkl).exists():
            print(f"Loading chunked entries from cache: {cache_path_pkl}")
            with open(cache_path_pkl, "rb") as f:
                cache_data = pickle.load(f)
        elif Path(cache_path).exists():
            print(f"Loading chunked entries from legacy JSON cache: {cache_path}")
            with open(cache_path, "r", encoding="utf-8") as f:
                cache_data = json.load(f)
        else:
            raise FileNotFoundError(
                f"Cache not found: {cache_path_pkl} or {cache_path}"
            )

        entries = []
        for entry_data in cache_data["entries"]:
            entry = DiaryEntry(
                timestamp=datetime.fromisoformat(entry_data["timestamp"]),
                original_type=entry_data["original_type"],
                category=entry_data["category"],
                content=entry_data["content"],
            )
            entry.chunks = entry_data["chunks"]
            entry.index = entry_data["index"]
            entries.append(entry)

        print(f"✓ Loaded {len(entries)} entries from cache")
        return entries

    def _mark_entries_injected(self, entries: List[DiaryEntry]) -> None:
        """Mark entry indices as injected in state.

        :param entries: List of injected diary entries
        """
        for entry in entries:
            if hasattr(entry, "index"):
                self.injected_entry_indices.add(entry.index)

    def parse_diary_file(self, file_path: str) -> List[DiaryEntry]:
        """Parse the diary file into structured entries.

        Expected format: TIMESTAMP | TYPE | CATEGORY | CONTENT

        :param file_path: Path to the diary file
        :return: List of DiaryEntry objects
        """
        print(f"Parsing diary file: {file_path}")
        self._current_input_path = file_path
        entries = []

        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()

        # Split by lines and parse each entry
        lines = [line.strip() for line in content.split("\n") if line.strip()]
        total_lines = len(lines)
        print(f"Processing {total_lines} lines...")

        for i, line in enumerate(lines):
            # Show progress every 500 lines
            if i > 0 and i % 500 == 0:
                print(f"  Parsed {i}/{total_lines} lines ({i*100//total_lines}%)")

            # Parse format: TIMESTAMP | TYPE | CATEGORY | CONTENT
            parts = line.split(" | ", 3)
            if len(parts) >= 4:
                try:
                    timestamp = datetime.fromisoformat(parts[0].replace("T", " "))
                    content = parts[3].strip()

                    # Skip entries with meaningless content
                    if self._is_meaningless_fragment(content):
                        continue

                    entry = DiaryEntry(
                        timestamp=timestamp,
                        original_type=parts[1],
                        category=parts[2],
                        content=content,
                    )
                    entries.append(entry)
                except ValueError as e:
                    print(f"Warning: Failed to parse line: {line[:100]}... Error: {e}")

        print(f"Parsed {len(entries)} diary entries")
        return entries

    def _is_meaningless_fragment(self, text: str) -> bool:
        """Check if text is a meaningless fragment that should be filtered out.

        :param text: Text to check
        :return: True if text should be filtered out
        """
        cleaned = text.strip()

        # Filter very short entries
        if len(cleaned) < 10:
            return True

        # Filter ordinal date fragments
        if re.match(r"^\d+(st|nd|rd|th)\.?$", cleaned):
            return True

        # Filter single letters or numbers
        if re.match(r"^[A-Za-z0-9]\.?$", cleaned):
            return True

        return False

    def _get_cache_path(self, input_file_path: str) -> str:
        """Get cache file path for diversity features.

        :param input_file_path: Path to the input diary file
        :return: Path to cache file
        """
        file_hash = hashlib.md5(input_file_path.encode()).hexdigest()[:12]
        cache_dir = Path(input_file_path).parent / ".diary_cache"
        cache_dir.mkdir(exist_ok=True)
        return str(cache_dir / f"diversity_features_{file_hash}.pkl")

    def _is_cache_valid(self, cache_path: str, input_file_path: str) -> bool:
        """Check if cached features are still valid.

        :param cache_path: Path to cache file
        :param input_file_path: Path to input diary file
        :return: True if cache is valid, False otherwise
        """
        if not Path(cache_path).exists():
            return False

        # Check if input file is newer than cache
        try:
            cache_mtime = Path(cache_path).stat().st_mtime
            input_mtime = Path(input_file_path).stat().st_mtime
            return cache_mtime > input_mtime
        except OSError:
            return False

    def select_diverse_sample(
        self,
        entries: List[DiaryEntry],
        target_count: int = 20,
        seed: Optional[int] = None,
    ) -> List[DiaryEntry]:
        """Select a diverse sample of entries for processing.

        :param entries: List of all diary entries
        :param target_count: Target number of entries to select
        :param seed: Random seed for reproducible sampling
        :return: Selected diverse entries
        """
        print(f"Selecting {target_count} diverse entries from {len(entries)} total")

        # Set random seed for reproducible sampling
        if seed is not None:
            print(f"Using random seed: {seed}")
            np.random.seed(seed)
        else:
            run_seed = random.randint(0, 2**32 - 1)
            print(f"Using random seed: {run_seed} (generated)")
            np.random.seed(run_seed)

        # Load or compute diversity features
        df_norm = self._load_or_compute_diversity_features(entries)

        print("Clustering entries for diversity...")
        # Use k-means clustering to find diverse entries
        kmeans = KMeans(
            n_clusters=min(target_count, len(entries)),
            random_state=seed if seed is not None else run_seed,
        )
        clusters = kmeans.fit_predict(df_norm.fillna(0))

        print("Selecting representative entries...")
        # Select one entry from each cluster (closest to centroid)
        selected_entries = []
        for i in range(kmeans.n_clusters):
            cluster_indices = np.where(clusters == i)[0]
            if len(cluster_indices) > 0:
                # Find closest to centroid
                centroid = kmeans.cluster_centers_[i]
                distances = np.linalg.norm(
                    df_norm.fillna(0).iloc[cluster_indices] - centroid, axis=1
                )
                closest_idx = cluster_indices[np.argmin(distances)]
                selected_entries.append(entries[closest_idx])

        print(f"Selected {len(selected_entries)} diverse entries")
        return selected_entries

    def _load_or_compute_diversity_features(
        self, entries: List[DiaryEntry]
    ) -> pd.DataFrame:
        """Load cached diversity features or compute them if cache is invalid.

        :param entries: List of diary entries
        :return: Normalized DataFrame with diversity features
        """
        input_file_path = getattr(self, "_current_input_path", None)

        if input_file_path:
            cache_path = self._get_cache_path(input_file_path)

            # Try to load from cache if valid
            if self._is_cache_valid(cache_path, input_file_path):
                try:
                    print("Loading cached diversity features...")
                    with open(cache_path, "rb") as f:
                        cached_data = pickle.load(f)

                    # Validate cache integrity
                    if len(cached_data) == len(entries):
                        print("✓ Using cached diversity features")
                        return cached_data
                    else:
                        print("⚠ Cache size mismatch, recomputing...")
                except (OSError, pickle.PickleError, KeyError) as e:
                    print(f"⚠ Cache load failed ({e}), recomputing...")

        # Compute features if no valid cache
        return self._compute_and_cache_diversity_features(entries, input_file_path)

    def _compute_and_cache_diversity_features(
        self, entries: List[DiaryEntry], input_file_path: Optional[str] = None
    ) -> pd.DataFrame:
        """Compute diversity features and cache them for future use.

        :param entries: List of diary entries
        :param input_file_path: Path to input file for caching
        :return: Normalized DataFrame with diversity features
        """
        print("Analyzing entry features for diversity...")

        # Choose parallel or sequential processing
        if self.num_workers > 1:
            print(f"  Using {self.num_workers} parallel workers")
            entry_features = self._extract_features_parallel(entries)
        else:
            print("  Using sequential processing")
            entry_features = self._extract_features_sequential(entries)

        print("Building diversity model...")
        # Convert to DataFrame for analysis
        df = pd.DataFrame(entry_features)

        # Add time-based diversity with better temporal resolution
        # Use Unix timestamp for absolute temporal distance
        df["timestamp_days"] = [e.timestamp.timestamp() / 86400 for e in entries]
        df["year"] = [e.timestamp.year for e in entries]
        df["month"] = [e.timestamp.month for e in entries]
        df["day_of_month"] = [e.timestamp.day for e in entries]
        df["hour"] = [e.timestamp.hour for e in entries]

        # Normalize features
        df_norm = (df - df.mean()) / df.std()

        # Cache the normalized features if we have an input file path
        if input_file_path:
            try:
                cache_path = self._get_cache_path(input_file_path)
                with open(cache_path, "wb") as f:
                    pickle.dump(df_norm, f)
                print(f"✓ Cached diversity features to {cache_path}")
            except OSError as e:
                print(f"⚠ Failed to cache features: {e}")

        return df_norm

    def _extract_features_sequential(self, entries: List[DiaryEntry]) -> List[Dict]:
        """Extract features sequentially.

        :param entries: List of diary entries
        :return: List of feature dictionaries
        """
        entry_features = []
        total_entries = len(entries)

        with tqdm(total=total_entries, desc="Analyzing", unit="entry") as pbar:
            for entry in entries:
                doc = self.nlp(entry.content)
                features = {
                    "length": len(entry.content),
                    "sentences": len(list(doc.sents)),
                    "entities": len(doc.ents),
                    "nouns": len([token for token in doc if token.pos_ == "NOUN"]),
                    "verbs": len([token for token in doc if token.pos_ == "VERB"]),
                    "proper_nouns": len(
                        [token for token in doc if token.pos_ == "PROPN"]
                    ),
                }
                entry_features.append(features)
                pbar.update(1)
        return entry_features

    def _extract_features_parallel(self, entries: List[DiaryEntry]) -> List[Dict]:
        """Extract features in parallel using multiprocessing.

        :param entries: List of diary entries
        :return: List of feature dictionaries (ordered by index)
        """
        total_entries = len(entries)

        # Prepare data for workers: (index, content) tuples
        entry_data = [(i, entry.content) for i, entry in enumerate(entries)]

        # Create process pool and map work
        print(f"  Processing {total_entries} entries...")
        results = []
        with mp.Pool(processes=self.num_workers) as pool:
            with tqdm(total=total_entries, desc="Analyzing", unit="entry") as pbar:
                for i, features in enumerate(
                    pool.imap_unordered(
                        _extract_entry_features_worker, entry_data, chunksize=50
                    )
                ):
                    results.append(features)
                    pbar.update(1)

        # Sort results by original index and remove index field
        results.sort(key=lambda x: x["index"])
        entry_features = [{k: v for k, v in r.items() if k != "index"} for r in results]

        print(f"  ✓ Completed {total_entries} entries")
        return entry_features

    def segment_content(
        self,
        content: str,
        max_chunks_per_entry: int = 3,
        timestamp: Optional[datetime] = None,
    ) -> List[str]:
        """Segment content into semantic chunks with limited output per entry.

        Temporal information is now handled via direct database writes to
        occurred_start/occurred_end fields, so no preamble is added to content.

        Supports multiple chunking strategies:
        - semantic: Uses similarity-based boundaries (original behavior)
        - sentence_group: Groups by fixed number of sentences (recommended)
        - hybrid: Sentence groups with max_chunk_length enforcement

        :param content: Full diary entry content
        :param max_chunks_per_entry: Maximum chunks per diary entry
        :param timestamp: Entry timestamp (unused, kept for backward compatibility)
        :return: List of semantic chunks
        """
        # Strip any existing temporal preamble from legacy content
        existing_preamble = self._extract_temporal_preamble(content)
        clean_content = (
            content[len(existing_preamble) :].lstrip() if existing_preamble else content
        )

        doc = self.nlp(clean_content)
        sentences = [sent.text.strip() for sent in doc.sents]

        if not sentences:
            return [content[: self.max_chunk_length]]

        # Route to appropriate chunking strategy
        if self.chunking_strategy == "sentence_group":
            chunks = self._chunk_by_sentence_groups(sentences)
        elif self.chunking_strategy == "hybrid":
            chunks = self._chunk_hybrid(sentences)
        else:  # "semantic" (default)
            chunks = self._chunk_semantic(sentences, clean_content)

        # Filter out meaningless short entries
        filtered_chunks = []
        for chunk in chunks:
            chunk = chunk.strip()
            if chunk and not self._is_meaningless_fragment(chunk):
                filtered_chunks.append(chunk)

        # Limit chunks per entry
        if len(filtered_chunks) > max_chunks_per_entry:
            limited_chunks = [filtered_chunks[0]]  # Keep first chunk
            if len(filtered_chunks) > 1:
                remaining = filtered_chunks[1:]
                remaining.sort(key=len, reverse=True)  # Longer chunks first
                limited_chunks.extend(remaining[: max_chunks_per_entry - 1])
            filtered_chunks = limited_chunks

        return filtered_chunks

    def _chunk_by_sentence_groups(self, sentences: List[str]) -> List[str]:
        """Chunk by grouping N consecutive sentences.

        Respects natural sentence boundaries and creates consistent-sized chunks.
        Recommended strategy based on sentence length analysis.

        :param sentences: List of sentence strings
        :return: List of text chunks
        """
        if len(sentences) <= 1:
            return sentences

        chunks = []
        for i in range(0, len(sentences), self.sentences_per_chunk):
            chunk_sentences = sentences[i : i + self.sentences_per_chunk]
            chunk_text = " ".join(chunk_sentences)
            chunks.append(chunk_text)

        return chunks

    def _chunk_hybrid(self, sentences: List[str]) -> List[str]:
        """Hybrid chunking: Group by sentences but enforce max_chunk_length.

        Tries to group sentences_per_chunk sentences, but splits if it would
        exceed max_chunk_length. Handles very long sentences gracefully.

        :param sentences: List of sentence strings
        :return: List of text chunks
        """
        if len(sentences) <= 1:
            if len(sentences[0]) > self.max_chunk_length:
                return self._split_by_length(sentences[0])
            return sentences

        chunks = []
        current_chunk = []
        current_length = 0

        for sentence in sentences:
            sentence_len = len(sentence)

            # If single sentence exceeds max, split it
            if sentence_len > self.max_chunk_length:
                # Flush current chunk first
                if current_chunk:
                    chunks.append(" ".join(current_chunk))
                    current_chunk = []
                    current_length = 0

                # Split the long sentence
                sub_chunks = self._split_by_length(sentence)
                chunks.extend(sub_chunks)
                continue

            # Check if adding this sentence would exceed limit
            would_exceed = current_length + sentence_len + 1 > self.max_chunk_length

            # Also check if we've reached target sentence count
            at_target = len(current_chunk) >= self.sentences_per_chunk

            if would_exceed or at_target:
                # Flush current chunk
                if current_chunk:
                    chunks.append(" ".join(current_chunk))
                current_chunk = [sentence]
                current_length = sentence_len
            else:
                current_chunk.append(sentence)
                current_length += sentence_len + 1  # +1 for space

        # Flush remaining
        if current_chunk:
            chunks.append(" ".join(current_chunk))

        return chunks

    def _chunk_semantic(self, sentences: List[str], clean_content: str) -> List[str]:
        """Original semantic chunking using similarity-based boundaries.

        Uses sentence embeddings to find semantic boundaries where similarity drops.

        :param sentences: List of sentence strings
        :param clean_content: Full cleaned content text
        :return: List of text chunks
        """
        if len(sentences) <= 1:
            if len(clean_content) > self.max_chunk_length:
                chunks = self._split_by_length(clean_content)
            else:
                chunks = [clean_content]
        else:
            embeddings = self.sentence_model.encode(sentences)

            # Calculate similarity between consecutive sentences
            similarities = []
            for i in range(len(embeddings) - 1):
                sim = np.dot(embeddings[i], embeddings[i + 1]) / (
                    np.linalg.norm(embeddings[i]) * np.linalg.norm(embeddings[i + 1])
                )
                similarities.append(sim)

            # Find break points where similarity drops significantly
            threshold = np.mean(similarities) - np.std(similarities)
            break_points = [0]

            for i, sim in enumerate(similarities):
                if sim < threshold:
                    break_points.append(i + 1)

            break_points.append(len(sentences))

            # Create chunks from break points
            chunks = []
            for i in range(len(break_points) - 1):
                start_idx = break_points[i]
                end_idx = break_points[i + 1]
                chunk_text = " ".join(sentences[start_idx:end_idx])

                if len(chunk_text) > self.max_chunk_length:
                    sub_chunks = self._split_by_length(chunk_text)
                    chunks.extend(sub_chunks)
                else:
                    chunks.append(chunk_text)

        return chunks

    def _extract_temporal_preamble(self, content: str) -> str:
        """Extract temporal preamble from the beginning of diary content.

        :param content: Full diary entry content
        :return: Temporal preamble string or empty string if none found
        """
        pattern = r"^(Today, \d{4}-\d{2}-\d{2}T\d{2}:\d{2},)\s+"
        match = re.match(pattern, content.strip())
        if match:
            return match.group(1) + " "
        return ""

    def _split_by_length(self, text: str) -> List[str]:
        """Split text by length while trying to preserve sentence boundaries.

        :param text: Text to split
        :return: List of text chunks under max length
        """
        if len(text) <= self.max_chunk_length:
            return [text]

        chunks = []
        current_chunk = ""

        sentences = re.split(r"[.!?]+\s+", text)

        for sentence in sentences:
            if sentence != sentences[-1]:
                sentence += "."

            if len(current_chunk + " " + sentence) <= self.max_chunk_length:
                current_chunk = (current_chunk + " " + sentence).strip()
            else:
                if current_chunk:
                    chunks.append(current_chunk)

                if len(sentence) > self.max_chunk_length:
                    words = sentence.split()
                    temp_chunk = ""
                    for word in words:
                        if len(temp_chunk + " " + word) <= self.max_chunk_length:
                            temp_chunk = (temp_chunk + " " + word).strip()
                        else:
                            if temp_chunk:
                                chunks.append(temp_chunk)
                            temp_chunk = word
                    if temp_chunk:
                        current_chunk = temp_chunk
                else:
                    current_chunk = sentence

        if current_chunk:
            chunks.append(current_chunk)

        return chunks

    def discover_semantic_categories(
        self, chunks: List[str], n_categories: int = 10, seed: Optional[int] = None
    ) -> List[str]:
        """Discover semantic categories through unsupervised clustering.

        :param chunks: List of text chunks
        :param n_categories: Number of categories to discover
        :param seed: Random seed for reproducible clustering
        :return: List of discovered category names
        """
        print(
            f"Discovering {n_categories} semantic categories from {len(chunks)} chunks"
        )

        if len(chunks) < n_categories:
            n_categories = max(1, len(chunks) // 2)

        # Vectorize chunks using TF-IDF
        # Adjust min_df based on corpus size to avoid pruning all terms
        min_df = max(1, min(2, len(chunks) // 10))
        vectorizer = TfidfVectorizer(
            max_features=1000, stop_words="english", ngram_range=(1, 2), min_df=min_df
        )

        tfidf_matrix = vectorizer.fit_transform(chunks)

        # Cluster chunks
        kmeans = KMeans(n_clusters=n_categories, random_state=seed)
        kmeans.fit(tfidf_matrix)

        # Generate category names based on top terms in each cluster
        feature_names = vectorizer.get_feature_names_out()
        category_names = []

        for i in range(n_categories):
            cluster_center = kmeans.cluster_centers_[i]
            top_indices = cluster_center.argsort()[-5:][::-1]
            top_terms = [feature_names[idx] for idx in top_indices]

            category_name = self._generate_category_name(top_terms)
            category_names.append(category_name)

        self.semantic_categories = category_names
        print(f"Discovered categories: {category_names}")
        return category_names

    def _generate_category_name(self, top_terms: List[str]) -> str:
        """Generate a category name from top terms.

        :param top_terms: List of top terms for this cluster
        :return: Generated category name
        """
        # Map common patterns to semantic categories
        term_mappings = {
            "work": "work",
            "office": "work",
            "business": "work",
            "dinner": "social",
            "home": "domestic",
            "family": "domestic",
            "money": "finance",
            "health": "health",
            "sick": "health",
            "church": "spiritual",
            "travel": "travel",
            "friend": "social",
        }

        # Check for mapped terms
        for term in top_terms:
            if term.lower() in term_mappings:
                return term_mappings[term.lower()]

        # Fallback to first term, cleaned up
        return top_terms[0].replace(" ", "_").lower()

    def extract_context(self, chunk: str) -> str:
        """Extract context classification from a chunk.

        :param chunk: Text chunk to analyze
        :return: Context classification
        """
        doc = self.nlp(chunk)

        # Extract entities
        entities = [ent.text.lower() for ent in doc.ents]

        # Context patterns
        context_patterns = {
            "work": "Work",
            "office": "Office",
            "home": "Home",
            "family": "Family",
            "money": "Finance",
            "dinner": "Social",
            "sick": "Health",
            "health": "Health",
        }

        chunk_lower = chunk.lower()

        # Check for specific patterns
        for pattern, context in context_patterns.items():
            if pattern in chunk_lower:
                return context

        # Check entities
        for entity in entities:
            if "work" in entity or "office" in entity:
                return "Work"
            elif "home" in entity or "house" in entity:
                return "Home"

        # Default context based on content type
        if any(word in chunk_lower for word in ["think", "believe", "suppose"]):
            return "Reflection"
        elif any(word in chunk_lower for word in ["feel", "angry", "pleased", "fear"]):
            return "Emotion"
        else:
            return "General"

    def classify_chunk_hybrid(
        self, chunk: str, unsupervised_categories: List[str]
    ) -> Tuple[str, Dict[str, float]]:
        """Classify a chunk using both supervised and unsupervised methods.

        :param chunk: Text chunk to classify
        :param unsupervised_categories: List of discovered categories from k-means
        :return: Tuple of (best_category, confidence_scores)
        """
        # Get supervised classification if available
        supervised_topics = {}
        if self.topic_classifier:
            try:
                supervised_topics = self.topic_classifier.classify(
                    chunk, return_list=False
                )
            except Exception as e:
                print(f"Warning: Supervised classification failed: {e}")

        # Get unsupervised classification
        unsupervised_category = self.classify_chunk(chunk, unsupervised_categories)

        # Combine results - prioritize high-confidence supervised topics
        if supervised_topics:
            best_topic = max(supervised_topics.items(), key=lambda x: x[1])
            if best_topic[1] > 0.3:  # Confidence threshold
                return best_topic[0], supervised_topics

        # Fall back to unsupervised
        return unsupervised_category, {unsupervised_category: 1.0}

    def classify_chunk(self, chunk: str, categories: List[str]) -> str:
        """Classify a chunk into one of the discovered semantic categories (unsupervised).

        :param chunk: Text chunk to classify
        :param categories: List of available categories
        :return: Predicted category
        """
        chunk_lower = chunk.lower()

        # Basic classification rules
        if any(word in chunk_lower for word in ["work", "office", "business", "job"]):
            return next((cat for cat in categories if "work" in cat), categories[0])
        elif any(word in chunk_lower for word in ["dinner", "social", "friend"]):
            return next((cat for cat in categories if "social" in cat), categories[0])
        elif any(word in chunk_lower for word in ["home", "family", "house"]):
            return next((cat for cat in categories if "domestic" in cat), categories[0])
        elif any(word in chunk_lower for word in ["money", "paid", "cost"]):
            return next((cat for cat in categories if "finance" in cat), categories[0])
        else:
            return categories[0]

    def transform_entries(
        self,
        entries: List[DiaryEntry],
        seed: Optional[int] = None,
        max_chunks_per_entry: int = 3,
    ) -> List[EntryChunk]:
        """Transform diary entries into memory chunks.

        :param entries: List of diary entries to transform
        :param seed: Random seed for reproducible processing
        :param max_chunks_per_entry: Maximum chunks per entry
        :return: List of memory chunks
        """
        print(f"Transforming {len(entries)} entries into memory chunks")

        all_chunks = []
        chunk_texts = []
        total_entries = len(entries)

        # First pass: segment all entries into chunks
        print("Segmenting content into semantic chunks...")
        for entry_idx, entry in enumerate(entries):
            if entry_idx > 0 and entry_idx % 5 == 0:
                print(
                    f"  Processing entry {entry_idx + 1}/{total_entries} ({(entry_idx + 1)*100//total_entries}%)"
                )

            chunks = self.segment_content(
                entry.content, max_chunks_per_entry, timestamp=entry.timestamp
            )

            for chunk in chunks:
                all_chunks.append((entry_idx, entry, chunk))
                chunk_texts.append(chunk)

        print(f"Created {len(all_chunks)} semantic chunks")

        # Discover semantic categories
        print("Discovering semantic categories...")
        categories = self.discover_semantic_categories(chunk_texts, seed=seed)

        # Second pass: classify chunks and create memory objects
        print("Classifying chunks with hybrid approach...")
        memory_chunks = []
        total_chunks = len(all_chunks)
        for i, (entry_idx, entry, chunk) in enumerate(all_chunks):
            if i > 0 and i % 10 == 0:
                print(
                    f"  Classifying chunk {i + 1}/{total_chunks} ({(i + 1)*100//total_chunks}%)"
                )

            semantic_category, _ = self.classify_chunk_hybrid(chunk, categories)
            context = self.extract_context(chunk)

            memory = EntryChunk(
                timestamp=entry.timestamp,
                semantic_category=semantic_category,
                context_classification=context,
                content=chunk,
                confidence=1.0,
                phase="immediate",
            )
            memory.source_entry_index = entry_idx
            memory.source_entry = entry
            memory_chunks.append(memory)

        print(f"Generated {len(memory_chunks)} memory chunks")
        return memory_chunks

    def save_entries(
        self,
        entries: List[EntryChunk],
        output_path: str,
        run_params: Optional[Dict] = None,
    ) -> None:
        """Save entries to file in the required format with source entry comments.

        :param entries: List of memory chunks to save
        :param output_path: Output file path
        :param run_params: Dictionary of run parameters used for generation
        """
        print(f"Saving {len(entries)} entries to {output_path}")

        with open(output_path, "w", encoding="utf-8") as f:
            # Write run parameters header
            if run_params:
                f.write("# Diary Transformer - Run Parameters\n")
                f.write(f"# Generated: {run_params.get('timestamp', 'Unknown')}\n")
                f.write(f"# Input file: {run_params.get('input_file', 'Unknown')}\n")
                f.write(f"# Batch size: {run_params.get('batch_size', 'Unknown')}\n")
                f.write(f"# Chunk size: {run_params.get('chunk_size', 'Unknown')}\n")
                f.write(
                    f"# Max chunks per entry: {run_params.get('max_chunks_per_entry', 'Unknown')}\n"
                )
                f.write(f"# Random seed: {run_params.get('seed', 'auto-generated')}\n")
                f.write("#\n")

            current_source_entry = None

            # Write entries with source comments
            f.write("# ======== ENTRIES ========\n\n")

            for memory in entries:
                source_entry = getattr(memory, "source_entry", None)
                source_index = getattr(memory, "source_entry_index", None)

                if source_entry and source_entry != current_source_entry:
                    current_source_entry = source_entry

                    # Write comment header for the source entry
                    f.write(
                        f"\n# === Source Entry #{source_index + 1} ({source_entry.timestamp.strftime('%Y-%m-%d %H:%M')}) ===\n"
                    )
                    f.write(
                        f"# Original: {source_entry.original_type} | {source_entry.category}\n"
                    )
                    f.write(
                        f"# Content: {source_entry.content[:100]}{'...' if len(source_entry.content) > 100 else ''}\n"
                    )
                    f.write("# Extracted entries:\n")

                # Format: TIMESTAMP | SEMANTIC_CATEGORY | CONTEXT_CLASSIFICATION | CONTENT
                timestamp_str = memory.timestamp.strftime("%Y-%m-%dT%H:%M")
                line = f"{timestamp_str} | {memory.semantic_category} | {memory.context_classification} | {memory.content}\n"
                f.write(line)

        print(f"Entries saved to {output_path}")

    def transform_file(
        self,
        input_path: str,
        output_path: str,
        batch_size: int = 20,
        seed: Optional[int] = None,
        max_chunks_per_entry: int = 3,
    ) -> None:
        """Transform a diary file into semantic entries.

        :param input_path: Path to input diary file
        :param output_path: Path to output memory file
        :param batch_size: Number of entries to process
        :param seed: Random seed for reproducible sampling
        :param max_chunks_per_entry: Maximum chunks per diary entry
        """
        print(f"Starting transformation: {input_path} -> {output_path}")

        # Determine chunk cache path
        input_dir = Path(input_path).parent
        input_stem = Path(input_path).stem
        chunk_cache_path = input_dir / f"{input_stem}_chunks.json"
        chunk_cache_path_pkl = input_dir / f"{input_stem}_chunks.pkl"

        # Check if chunk cache exists - build it on first run if not
        if chunk_cache_path_pkl.exists() or chunk_cache_path.exists():
            print("✓ Found chunk cache, loading...")
            entries = self._load_chunks_from_json(str(chunk_cache_path))
        else:
            print("No chunk cache found, parsing and chunking all entries...")
            # Parse diary entries
            entries = self.parse_diary_file(input_path)

            # Add indices to entries
            for idx, entry in enumerate(entries):
                entry.index = idx

            # Save chunks to cache for future incremental runs
            self._save_chunks_to_json(entries, str(chunk_cache_path))

            # Reload from cache to ensure consistency
            entries = self._load_chunks_from_json(str(chunk_cache_path))

        # Select diverse sample
        selected_entries = self.select_diverse_sample(entries, batch_size, seed=seed)

        # Transform to memory chunks
        memory_entries = self.transform_entries(
            selected_entries, seed=seed, max_chunks_per_entry=max_chunks_per_entry
        )

        # Sort by timestamp
        memory_entries.sort(key=lambda m: m.timestamp)

        # Collect run parameters
        run_params = {
            "timestamp": datetime.now().isoformat(),
            "input_file": str(input_path),
            "batch_size": batch_size,
            "chunk_size": self.max_chunk_length,
            "max_chunks_per_entry": max_chunks_per_entry,
            "seed": seed,
        }

        # Save to file
        self.save_entries(memory_entries, output_path, run_params)

        print(f"Transformation complete! Generated {len(memory_entries)} entries")

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
        """Transform diary file incrementally, tracking processed entries.

        :param input_path: Path to input diary file
        :param output_path: Path to output memory file
        :param state_file: Path to state tracking file
        :param batch_size: Number of entries to process (ignored in resume mode)
        :param seed: Random seed for reproducible sampling
        :param max_chunks_per_entry: Maximum chunks per diary entry
        :param resume_mode: If True, only process unprocessed entries
        """
        print(f"Starting transformation: {input_path} -> {output_path}")
        print(f"Resume mode: {resume_mode}")

        # Set state file path
        self.state_file_path = state_file

        # Determine chunk cache path
        input_dir = Path(input_path).parent
        input_stem = Path(input_path).stem
        chunk_cache_path = input_dir / f"{input_stem}_chunks.json"
        self.chunk_cache_file = str(chunk_cache_path)

        # Load existing state if resuming
        if resume_mode:
            self._load_state(state_file, input_path)
            print(
                f"Loaded state: {len(self.injected_entry_indices)} entries already injected"
            )

        # Check if chunk cache exists
        chunk_cache_path_pkl = Path(str(chunk_cache_path).replace(".json", ".pkl"))
        if chunk_cache_path_pkl.exists() or chunk_cache_path.exists():
            print("✓ Found chunk cache, loading...")
            entries = self._load_chunks_from_json(str(chunk_cache_path))
        else:
            print("No chunk cache found, parsing and chunking all entries...")
            # Parse diary entries
            entries = self.parse_diary_file(input_path)

            # Add indices to entries
            for idx, entry in enumerate(entries):
                entry.index = idx

            # Save chunks to cache
            self._save_chunks_to_json(entries, str(chunk_cache_path))

            # Reload from cache to ensure consistency
            entries = self._load_chunks_from_json(str(chunk_cache_path))

        # Filter out already-injected entries
        available_entries = self._filter_uninjected_entries(entries)

        if not available_entries:
            print("✓ All entries already injected, nothing to do")
            return

        print(f"Found {len(available_entries)} entries available for injection")

        # Select diverse sample from available entries
        if len(available_entries) > batch_size:
            selected_entries = self.select_diverse_sample(
                available_entries, batch_size, seed=seed
            )
        else:
            selected_entries = available_entries
            print(f"Processing all {len(selected_entries)} available entries")

        # Transform to entries (chunks are already cached in entry.chunks)
        memory_entries = self.transform_entries(
            selected_entries, seed=seed, max_chunks_per_entry=max_chunks_per_entry
        )

        # Sort by timestamp
        memory_entries.sort(key=lambda m: m.timestamp)

        # Update processing stats
        self.processing_stats["total_runs"] += 1
        self.processing_stats["total_entries_injected"] += len(selected_entries)
        self.processing_stats["last_run"] = datetime.now().isoformat()

        # Mark entries as injected
        self._mark_entries_injected(selected_entries)

        # Collect run parameters
        run_params = {
            "timestamp": datetime.now().isoformat(),
            "input_file": str(input_path),
            "batch_size": len(selected_entries),
            "chunk_size": self.max_chunk_length,
            "max_chunks_per_entry": max_chunks_per_entry,
            "seed": seed,
            "mode": "resume" if resume_mode else "incremental",
        }

        # Save entries
        self.save_entries(memory_entries, output_path, run_params)

        # Save state
        self._save_state(output_path, run_params)

        print("\nIncremental transformation complete!")
        print(f"  - {len(memory_entries)} new entries")
        print(f"  - Total runs: {self.processing_stats['total_runs']}")
        print(
            f"  - Total entries injected: {self.processing_stats['total_entries_injected']}"
        )


def main() -> None:
    """Main entry point with command-line argument parsing."""
    warnings.filterwarnings("ignore", category=ResourceWarning, message="unclosed.*")

    parser = argparse.ArgumentParser(
        description="Diary Transformer: Convert diary entries into semantic memory chunks for Personal Agent.\n\nUsage: diary_transformer.py [options] <input_diary_file> <output_transformed_file>\n\nOptions:\n  --input/-i <file>         Input diary file path (alternative to positional)\n  --output/-o <file>        Output transformed file path (alternative to positional)\n  --chunk-size/-c <int>     Maximum character length per memory chunk (default: 512)\n  --batch-size/-b <int>     Number of diverse diary entries to process (default: 20)\n  --max-chunks-per-entry/-m <int>  Maximum chunks per diary entry (default: 3)\n  --workers/-w <int>        Number of parallel workers for feature extraction (default: 1)\n  --topics-file/-t <file>   Custom topics YAML file\n  --clear                   Clear all caches before processing\n  --restart                 Clear injection state and chunk cache for clean processing\n  --resume                  Resume previous run, skip already-processed entries\n  --incremental             Process only new entries (alias for --resume)\n  --state-file <file>       Custom state file path\n  --help                    Show this help message and exit\n\nExample:\n  python diary_transformer.py --input diary.txt --output transformed.txt --batch-size 30 --chunk-size 512\n",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    # File paths
    parser.add_argument(
        "input",
        type=str,
        nargs="?",
        help="Input diary file path (positional argument)",
    )
    parser.add_argument(
        "output",
        type=str,
        nargs="?",
        help="Output transformed file path (positional argument)",
    )
    parser.add_argument(
        "--input",
        "-i",
        dest="input_file",
        type=str,
        help="Input diary file path (alternative to positional)",
    )
    parser.add_argument(
        "--output",
        "-o",
        dest="output_file",
        type=str,
        help="Output transformed file path (alternative to positional)",
    )

    # Processing parameters
    parser.add_argument(
        "--chunk-size",
        "-c",
        type=int,
        default=512,
        help="Maximum character length per memory chunk (default: 512)",
    )
    parser.add_argument(
        "--chunking-strategy",
        type=str,
        choices=["semantic", "sentence_group", "hybrid"],
        default="sentence_group",
        help="Chunking strategy: semantic (similarity-based), sentence_group (fixed N sentences, recommended), hybrid (sentence groups with size limit) (default: sentence_group)",
    )
    parser.add_argument(
        "--sentences-per-chunk",
        type=int,
        default=4,
        help="Number of sentences per chunk for sentence_group strategy (default: 4, based on Pepys analysis)",
    )
    parser.add_argument(
        "--batch-size",
        "-b",
        type=int,
        default=20,
        help="Number of diverse diary entries to process (default: 20)",
    )
    parser.add_argument(
        "--seed",
        type=int,
        help="Random seed for reproducible sampling (default: random)",
    )
    parser.add_argument(
        "--max-chunks-per-entry",
        "-m",
        type=int,
        default=3,
        help="Maximum chunks per diary entry (default: 3)",
    )
    parser.add_argument(
        "--workers",
        "-w",
        type=int,
        default=1,
        help="Number of parallel workers for feature extraction (default: 1 = sequential)",
    )

    # Topic classification
    parser.add_argument(
        "--topics-file",
        "-t",
        type=str,
        help="Custom topics YAML file (default: general topics.yaml)",
    )

    # Cache management
    parser.add_argument(
        "--clear",
        action="store_true",
        help="Clear all caches (feature and chunk) before processing",
    )
    parser.add_argument(
        "--restart",
        action="store_true",
        help="Clear injection state and chunk cache for clean processing (preserves diversity features)",
    )

    # State tracking and resumable processing
    parser.add_argument(
        "--resume",
        action="store_true",
        help="Resume previous run, skip already-processed entries",
    )
    parser.add_argument(
        "--incremental",
        action="store_true",
        help="Process only new entries (alias for --resume)",
    )
    parser.add_argument(
        "--state-file",
        type=str,
        help="Custom state file path (default: .diary_state.json in same directory as output)",
    )

    # Show help if no arguments are provided

    if len(sys.argv) == 1:
        parser.print_help()
        sys.exit(0)

    args = parser.parse_args()

    # Treat incremental as resume mode
    if args.incremental:
        args.resume = True

    # Set up paths (prefer flag arguments over positional)
    input_arg = args.input_file or args.input
    output_arg = args.output_file or args.output

    if not input_arg:
        print(
            "Error: Input file path is required (provide as positional argument or --input)"
        )
        parser.print_help()
        sys.exit(1)

    if not output_arg:
        print(
            "Error: Output file path is required (provide as positional argument or --output)"
        )
        parser.print_help()
        sys.exit(1)

    input_path = Path(input_arg)
    output_path = Path(output_arg)

    # Check input file exists
    if not input_path.exists():
        print(f"Error: Input file not found: {input_path}")
        sys.exit(1)

    # Clear all caches if requested
    if args.clear:
        cache_dir = input_path.parent / ".diary_cache"
        if cache_dir.exists():
            import shutil

            shutil.rmtree(cache_dir)
            print(f"✓ Cleared diversity feature cache: {cache_dir}")
        # Also clear chunk cache
        chunk_cache_path_json = input_path.parent / f"{input_path.stem}_chunks.json"
        chunk_cache_path_pkl = input_path.parent / f"{input_path.stem}_chunks.pkl"
        if chunk_cache_path_pkl.exists():
            chunk_cache_path_pkl.unlink()
            print(f"✓ Cleared chunk cache: {chunk_cache_path_pkl}")
        if chunk_cache_path_json.exists():
            chunk_cache_path_json.unlink()
            print(f"✓ Cleared legacy JSON chunk cache: {chunk_cache_path_json}")

    # Restart: clear state and chunk cache (preserve diversity features)
    if args.restart:
        # Determine state file path
        if args.state_file:
            state_file_path = Path(args.state_file)
        else:
            state_file_path = output_path.parent / ".diary_state.json"

        # Clear state file
        if state_file_path.exists():
            state_file_path.unlink()
            print(f"✓ Restart: Cleared injection state at {state_file_path}")
        else:
            print(f"ℹ️ No injection state found at {state_file_path}")

        # Clear chunk cache
        chunk_cache_path_json = input_path.parent / f"{input_path.stem}_chunks.json"
        chunk_cache_path_pkl = input_path.parent / f"{input_path.stem}_chunks.pkl"

        cleared_cache = False
        if chunk_cache_path_pkl.exists():
            chunk_cache_path_pkl.unlink()
            print(f"✓ Restart: Cleared chunk cache at {chunk_cache_path_pkl}")
            cleared_cache = True
        if chunk_cache_path_json.exists():
            chunk_cache_path_json.unlink()
            print(
                f"✓ Restart: Cleared legacy JSON chunk cache at {chunk_cache_path_json}"
            )
            cleared_cache = True

        if not cleared_cache:
            print("ℹ️ No chunk cache found")

        print(
            "✓ Restart complete: Ready for clean processing (diversity features preserved)"
        )

    # Set up state file path
    if args.state_file:
        state_file_path = Path(args.state_file)
    else:
        state_file_path = output_path.parent / ".diary_state.json"

    print("🔄 Starting Diary Transformation")
    if args.resume:
        print("🔁 Mode: Incremental/Resume (processing new entries only)")
        print(f"💾 State file: {state_file_path}")
    print(f"📖 Input: {input_path}")
    print(f"📝 Output: {output_path}")
    print(f"⚙️ Chunking strategy: {args.chunking_strategy}")
    if args.chunking_strategy == "sentence_group":
        print(f"📏 Sentences per chunk: {args.sentences_per_chunk}")
    print(f"⚙️ Max chunk size: {args.chunk_size} chars")
    print(f"📊 Batch size: {args.batch_size} entries")
    print(f"🎯 Max chunks per entry: {args.max_chunks_per_entry}")
    print(
        f"⚙️ Workers: {args.workers} ({'parallel' if args.workers > 1 else 'sequential'})"
    )
    if args.seed is not None:
        print(f"🎲 Random seed: {args.seed}")
    else:
        print("🎲 Random seed: auto-generated")
    if args.topics_file:
        print(f"📋 Custom topics: {args.topics_file}")

    try:
        # Create transformer
        transformer = DiaryTransformer(
            max_chunk_length=args.chunk_size,
            num_workers=args.workers,
            topics_file=args.topics_file,
            chunking_strategy=args.chunking_strategy,
            sentences_per_chunk=args.sentences_per_chunk,
        )

        # Run transformation (incremental or normal mode)
        if args.resume:
            transformer.transform_file_incremental(
                str(input_path),
                str(output_path),
                str(state_file_path),
                batch_size=args.batch_size,
                seed=args.seed,
                max_chunks_per_entry=args.max_chunks_per_entry,
                resume_mode=True,
            )
        else:
            transformer.transform_file(
                str(input_path),
                str(output_path),
                batch_size=args.batch_size,
                seed=args.seed,
                max_chunks_per_entry=args.max_chunks_per_entry,
            )

        print("\n✅ Transformation completed successfully!")
        print(f"📂 Output saved to: {output_path}")
        if args.resume:
            print(f"💾 State saved to: {state_file_path}")
        print(
            f"🔧 Used {args.chunk_size}-char chunks with max {args.max_chunks_per_entry} per entry"
        )

    except KeyboardInterrupt:
        print("\n⛔ Transformation cancelled by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Error during transformation: {e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
