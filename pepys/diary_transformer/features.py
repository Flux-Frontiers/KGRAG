"""features.py — Diversity feature extraction with disk caching.

Features are computed once per input file and stored in a ``.diary_cache/``
directory as a pickled normalised DataFrame.  Subsequent runs load from cache
(validated by mtime) for a 5-10x speedup on large corpora.

Multiprocessing is supported via the module-level worker function
``_extract_entry_features_worker``, which must live at module scope so that
``multiprocessing.Pool`` can pickle it.
"""

from __future__ import annotations

import hashlib
import multiprocessing as mp
import pickle
import random
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import numpy as np
import pandas as pd
from tqdm import tqdm

from .models import DiaryEntry


# ---------------------------------------------------------------------------
# Module-level worker (must be top-level for pickle / multiprocessing)
# ---------------------------------------------------------------------------

def _extract_entry_features_worker(entry_data: Tuple[int, str]) -> Dict:
    """Extract spaCy features from a single entry (runs in a worker process).

    Each worker process loads its own spaCy model (cached as a function
    attribute to avoid redundant loads within the same worker).

    :param entry_data: ``(index, content)`` tuple.
    :return: Feature dict including the original *index* for re-ordering.
    """
    idx, content = entry_data

    if not hasattr(_extract_entry_features_worker, "nlp"):
        try:
            import spacy
            _extract_entry_features_worker.nlp = spacy.load("en_core_web_sm")
        except OSError:
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
    return {
        "index": idx,
        "length": len(content),
        "sentences": len(list(doc.sents)),
        "entities": len(doc.ents),
        "nouns": sum(1 for t in doc if t.pos_ == "NOUN"),
        "verbs": sum(1 for t in doc if t.pos_ == "VERB"),
        "proper_nouns": sum(1 for t in doc if t.pos_ == "PROPN"),
    }


# ---------------------------------------------------------------------------
# Cache helpers
# ---------------------------------------------------------------------------

def _cache_path(input_file_path: str) -> str:
    """Return the path to the diversity-feature cache file."""
    file_hash = hashlib.md5(input_file_path.encode()).hexdigest()[:12]
    cache_dir = Path(input_file_path).parent / ".diary_cache"
    cache_dir.mkdir(exist_ok=True)
    return str(cache_dir / f"diversity_features_{file_hash}.pkl")


def _cache_valid(cache_path: str, input_file_path: str) -> bool:
    """Return True if the cache file is newer than the input file."""
    if not Path(cache_path).exists():
        return False
    try:
        return Path(cache_path).stat().st_mtime > Path(input_file_path).stat().st_mtime
    except OSError:
        return False


# ---------------------------------------------------------------------------
# Feature extraction (sequential + parallel)
# ---------------------------------------------------------------------------

def _extract_sequential(entries: List[DiaryEntry], nlp: Any) -> List[Dict]:
    features = []
    with tqdm(total=len(entries), desc="Analyzing", unit="entry") as pbar:
        for entry in entries:
            doc = nlp(entry.content)
            features.append(
                {
                    "length": len(entry.content),
                    "sentences": len(list(doc.sents)),
                    "entities": len(doc.ents),
                    "nouns": sum(1 for t in doc if t.pos_ == "NOUN"),
                    "verbs": sum(1 for t in doc if t.pos_ == "VERB"),
                    "proper_nouns": sum(1 for t in doc if t.pos_ == "PROPN"),
                }
            )
            pbar.update(1)
    return features


def _extract_parallel(entries: List[DiaryEntry], num_workers: int) -> List[Dict]:
    entry_data = [(i, e.content) for i, e in enumerate(entries)]
    results: List[Dict] = []
    with mp.Pool(processes=num_workers) as pool:
        with tqdm(total=len(entries), desc="Analyzing", unit="entry") as pbar:
            for feat in pool.imap_unordered(
                _extract_entry_features_worker, entry_data, chunksize=50
            ):
                results.append(feat)
                pbar.update(1)
    results.sort(key=lambda x: x["index"])
    return [{k: v for k, v in r.items() if k != "index"} for r in results]


# ---------------------------------------------------------------------------
# Public: compute / load / select
# ---------------------------------------------------------------------------

def compute_diversity_features(
    entries: List[DiaryEntry],
    nlp: Any,
    num_workers: int,
    input_file_path: Optional[str] = None,
) -> pd.DataFrame:
    """Compute normalised diversity features and cache them to disk.

    :param entries: List of diary entries to analyse.
    :param nlp: Loaded spaCy model (used for sequential extraction).
    :param num_workers: Worker count; > 1 enables multiprocessing.
    :param input_file_path: Source file path used for cache naming.
    :return: Normalised ``DataFrame`` with one row per entry.
    """
    print("Analyzing entry features for diversity...")
    if num_workers > 1:
        print(f"  Using {num_workers} parallel workers")
        raw_features = _extract_parallel(entries, num_workers)
    else:
        print("  Using sequential processing")
        raw_features = _extract_sequential(entries, nlp)

    df = pd.DataFrame(raw_features)
    df["timestamp_days"] = [e.timestamp.timestamp() / 86400 for e in entries]
    df["year"] = [e.timestamp.year for e in entries]
    df["month"] = [e.timestamp.month for e in entries]
    df["day_of_month"] = [e.timestamp.day for e in entries]
    df["hour"] = [e.timestamp.hour for e in entries]

    df_norm = (df - df.mean()) / df.std()

    if input_file_path:
        try:
            cp = _cache_path(input_file_path)
            with open(cp, "wb") as f:
                pickle.dump(df_norm, f)
            print(f"✓ Cached diversity features to {cp}")
        except OSError as exc:
            print(f"⚠ Failed to cache features: {exc}")

    return df_norm


def load_or_compute_diversity_features(
    entries: List[DiaryEntry],
    nlp: Any,
    num_workers: int,
    input_file_path: Optional[str] = None,
) -> pd.DataFrame:
    """Return diversity features, loading from cache when valid.

    :param entries: Diary entries (used when recomputing).
    :param nlp: Loaded spaCy model.
    :param num_workers: Worker count for parallel extraction.
    :param input_file_path: Source file path for cache lookup.
    :return: Normalised ``DataFrame``.
    """
    if input_file_path:
        cp = _cache_path(input_file_path)
        if _cache_valid(cp, input_file_path):
            try:
                print("Loading cached diversity features...")
                with open(cp, "rb") as f:
                    cached = pickle.load(f)
                if len(cached) == len(entries):
                    print("✓ Using cached diversity features")
                    return cached
                print("⚠ Cache size mismatch, recomputing...")
            except (OSError, pickle.PickleError) as exc:
                print(f"⚠ Cache load failed ({exc}), recomputing...")

    return compute_diversity_features(entries, nlp, num_workers, input_file_path)


def select_diverse_sample(
    entries: List[DiaryEntry],
    target_count: int,
    nlp: Any,
    num_workers: int,
    input_file_path: Optional[str] = None,
    seed: Optional[int] = None,
) -> List[DiaryEntry]:
    """Select a diverse subset of entries via k-means clustering.

    Clusters entries in normalised feature space and picks the centroid-nearest
    entry from each cluster, ensuring temporal and thematic coverage.

    :param entries: All available diary entries.
    :param target_count: Desired sample size.
    :param nlp: Loaded spaCy model.
    :param num_workers: Worker count.
    :param input_file_path: Source file path for cache.
    :param seed: RNG seed for reproducibility.
    :return: Selected entries (length ≤ target_count).
    """
    from sklearn.cluster import KMeans

    print(f"Selecting {target_count} diverse entries from {len(entries)} total")

    run_seed = seed if seed is not None else random.randint(0, 2**32 - 1)
    label = "fixed" if seed is not None else "generated"
    print(f"Using random seed: {run_seed} ({label})")
    np.random.seed(run_seed)

    df_norm = load_or_compute_diversity_features(entries, nlp, num_workers, input_file_path)

    print("Clustering entries for diversity...")
    k = min(target_count, len(entries))
    kmeans = KMeans(n_clusters=k, random_state=run_seed)
    clusters = kmeans.fit_predict(df_norm.fillna(0))

    print("Selecting representative entries...")
    selected: List[DiaryEntry] = []
    for i in range(k):
        cluster_idx = np.where(clusters == i)[0]
        if len(cluster_idx) == 0:
            continue
        centroid = kmeans.cluster_centers_[i]
        dists = np.linalg.norm(df_norm.fillna(0).iloc[cluster_idx].values - centroid, axis=1)
        selected.append(entries[cluster_idx[np.argmin(dists)]])

    print(f"Selected {len(selected)} diverse entries")
    return selected
