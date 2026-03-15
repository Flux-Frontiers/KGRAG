"""state.py — Resumable processing state management.

``StateManager`` persists which diary entries have already been injected so
that incremental / resume runs only process new material.  State is stored as
a JSON file alongside the output.

Chunk caching (pickle) is handled separately by ``save_chunks_to_cache`` /
``load_chunks_from_cache``.
"""

from __future__ import annotations

import json
import pickle
from datetime import datetime
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Set

from .models import DiaryEntry


# ---------------------------------------------------------------------------
# Chunk cache I/O
# ---------------------------------------------------------------------------

def save_chunks_to_cache(
    entries: List[DiaryEntry],
    cache_path: str,
    segment_fn: Callable[..., List[str]],
) -> None:
    """Segment all entries and persist to a pickle cache.

    :param entries: Diary entries to chunk and cache.
    :param cache_path: Desired cache path (extension swapped to ``.pkl``).
    :param segment_fn: ``segment_content`` callable with signature
        ``(content, timestamp=None) -> List[str]``.
    """
    pkl_path = cache_path.replace(".json", ".pkl")
    print(f"Caching {len(entries)} chunked entries to {pkl_path}")

    cache_data: Dict[str, Any] = {
        "version": "1.0",
        "created": datetime.now().isoformat(),
        "total_entries": len(entries),
        "entries": [],
    }
    for idx, entry in enumerate(entries):
        cache_data["entries"].append(
            {
                "index": idx,
                "timestamp": entry.timestamp.isoformat(),
                "original_type": entry.original_type,
                "category": entry.category,
                "content": entry.content,
                "chunks": segment_fn(entry.content, timestamp=entry.timestamp),
            }
        )

    with open(pkl_path, "wb") as f:
        pickle.dump(cache_data, f, protocol=pickle.HIGHEST_PROTOCOL)
    print(f"✓ Cached {len(entries)} entries with chunks")


def load_chunks_from_cache(cache_path: str) -> List[DiaryEntry]:
    """Load chunked diary entries from pickle (or legacy JSON) cache.

    :param cache_path: Base cache path (``.json`` or ``.pkl``).
    :return: List of ``DiaryEntry`` objects with ``.chunks`` and ``.index`` set.
    :raises FileNotFoundError: If neither ``.pkl`` nor ``.json`` cache exists.
    """
    pkl_path = cache_path.replace(".json", ".pkl")

    if Path(pkl_path).exists():
        print(f"Loading chunked entries from cache: {pkl_path}")
        with open(pkl_path, "rb") as f:
            data = pickle.load(f)
    elif Path(cache_path).exists():
        print(f"Loading chunked entries from legacy JSON cache: {cache_path}")
        with open(cache_path, "r", encoding="utf-8") as f:
            data = json.load(f)
    else:
        raise FileNotFoundError(f"Cache not found: {pkl_path} or {cache_path}")

    entries: List[DiaryEntry] = []
    for ed in data["entries"]:
        entry = DiaryEntry(
            timestamp=datetime.fromisoformat(ed["timestamp"]),
            original_type=ed["original_type"],
            category=ed["category"],
            content=ed["content"],
        )
        entry.chunks = ed["chunks"]
        entry.index = ed["index"]
        entries.append(entry)

    print(f"✓ Loaded {len(entries)} entries from cache")
    return entries


# ---------------------------------------------------------------------------
# Entry filtering
# ---------------------------------------------------------------------------

def filter_uninjected(
    entries: List[DiaryEntry], injected_indices: Set[int]
) -> List[DiaryEntry]:
    """Return entries whose index has not yet been injected.

    :param entries: All available entries.
    :param injected_indices: Set of already-processed entry indices.
    :return: Filtered list.
    """
    if not injected_indices:
        return entries
    result = [e for e in entries if not (hasattr(e, "index") and e.index in injected_indices)]
    skipped = len(entries) - len(result)
    if skipped:
        print(f"Skipping {skipped} already-injected entries")
    return result


# ---------------------------------------------------------------------------
# StateManager
# ---------------------------------------------------------------------------

class StateManager:
    """Persist and restore incremental-processing state.

    State is written to a JSON file with the structure::

        {
            "output_file": "...",
            "injected_entry_indices": [0, 3, 7, ...],
            "chunk_cache_file": "...",
            "processing_stats": { "total_runs": N, ... },
            "run_parameters": { ... }
        }

    :param state_file: Path to the JSON state file.
    """

    def __init__(self, state_file: str) -> None:
        self.state_file = state_file
        self.injected_entry_indices: Set[int] = set()
        self.chunk_cache_file: Optional[str] = None
        self.processing_stats: Dict[str, Any] = {
            "total_runs": 0,
            "total_entries_injected": 0,
            "last_run": None,
        }

    def load(self, input_path: Optional[str] = None) -> bool:
        """Load state from disk.

        :param input_path: Unused; retained for API compatibility.
        :return: True if state was loaded successfully.
        """
        state_path = Path(self.state_file)
        if not state_path.exists():
            print(f"No existing state file found at {self.state_file}")
            return False
        try:
            with open(state_path, "r", encoding="utf-8") as f:
                state = json.load(f)
            self.injected_entry_indices = set(state.get("injected_entry_indices", []))
            self.chunk_cache_file = state.get("chunk_cache_file")
            self.processing_stats = state.get("processing_stats", self.processing_stats)
            print(f"✓ Loaded state: {len(self.injected_entry_indices)} entries injected")
            if self.processing_stats.get("last_run"):
                print(f"  Last run: {self.processing_stats['last_run']}")
            return True
        except (json.JSONDecodeError, OSError) as exc:
            print(f"Warning: Failed to load state file: {exc}")
            return False

    def save(self, output_file: str, run_params: Dict) -> None:
        """Persist state to disk.

        :param output_file: Path to the output entries file.
        :param run_params: Run parameters dict to store alongside state.
        """
        state = {
            "output_file": str(output_file),
            "injected_entry_indices": sorted(self.injected_entry_indices),
            "chunk_cache_file": self.chunk_cache_file,
            "processing_stats": self.processing_stats,
            "run_parameters": run_params,
        }
        try:
            Path(self.state_file).parent.mkdir(parents=True, exist_ok=True)
            with open(self.state_file, "w", encoding="utf-8") as f:
                json.dump(state, f, indent=2)
            print(f"✓ State saved to {self.state_file}")
        except OSError as exc:
            print(f"Warning: Failed to save state file: {exc}")

    def mark_injected(self, entries: List[DiaryEntry]) -> None:
        """Record entry indices as injected.

        :param entries: Entries that were processed in this run.
        """
        for entry in entries:
            if hasattr(entry, "index") and entry.index is not None:
                self.injected_entry_indices.add(entry.index)
