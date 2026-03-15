"""diary_transformer — Plug-and-play diary ingestion package for doc_kg / KGRAG.

Drop this package into any project that needs to ingest diary/journal text into
a structured knowledge graph.  The public surface is intentionally small:

    from diary_transformer import DiaryTransformer, DiaryEntry, EntryChunk

Modules
-------
models      — DiaryEntry, EntryChunk dataclasses
parser      — pipe-delimited diary file parser
chunker     — semantic / sentence-group / hybrid chunking strategies
features    — diversity feature extraction and caching (supports multiprocessing)
classifier  — TF-IDF unsupervised + supervised topic/context classification
state       — resumable processing state management (StateManager)
transformer — DiaryTransformer orchestrator (main public class)
cli         — argparse entry point (``python -m diary_transformer``)
"""

from .models import DiaryEntry, EntryChunk
from .transformer import DiaryTransformer

__all__ = ["DiaryTransformer", "DiaryEntry", "EntryChunk"]
