"""chunker.py — Content segmentation strategies.

Three strategies are supported:

``semantic``
    Uses sentence-transformer embeddings to detect topic-shift boundaries.
    Original behaviour; produces variable-length chunks.

``sentence_group``
    Groups exactly *N* consecutive sentences.  Fast, consistent, recommended
    for most diary corpora.

``hybrid``
    Like ``sentence_group`` but also enforces a hard ``max_chunk_length``
    character cap, splitting overlong sentences by word boundary.
"""

from __future__ import annotations

import re
from datetime import datetime
from typing import Any, List, Optional

import numpy as np

from .parser import is_meaningless_fragment


def _extract_temporal_preamble(content: str) -> str:
    """Strip a legacy ``Today, YYYY-MM-DDTHH:MM,`` preamble if present."""
    match = re.match(r"^(Today, \d{4}-\d{2}-\d{2}T\d{2}:\d{2},)\s+", content.strip())
    return (match.group(1) + " ") if match else ""


def _split_by_length(text: str, max_chunk_length: int) -> List[str]:
    """Split text at sentence boundaries to stay within *max_chunk_length*."""
    if len(text) <= max_chunk_length:
        return [text]

    chunks: List[str] = []
    current = ""

    for sentence in re.split(r"[.!?]+\s+", text):
        if sentence and sentence != text.split()[-1]:
            sentence += "."
        candidate = (current + " " + sentence).strip()
        if len(candidate) <= max_chunk_length:
            current = candidate
        else:
            if current:
                chunks.append(current)
            if len(sentence) > max_chunk_length:
                # Word-level fallback
                temp = ""
                for word in sentence.split():
                    trial = (temp + " " + word).strip()
                    if len(trial) <= max_chunk_length:
                        temp = trial
                    else:
                        if temp:
                            chunks.append(temp)
                        temp = word
                current = temp
            else:
                current = sentence

    if current:
        chunks.append(current)
    return chunks


def _chunk_by_sentence_groups(sentences: List[str], n: int) -> List[str]:
    """Group consecutive sentences in batches of *n*."""
    if len(sentences) <= 1:
        return sentences
    return [
        " ".join(sentences[i : i + n])
        for i in range(0, len(sentences), n)
    ]


def _chunk_hybrid(
    sentences: List[str], n: int, max_chunk_length: int
) -> List[str]:
    """Group by *n* sentences but hard-cap at *max_chunk_length* characters."""
    if len(sentences) == 1:
        s = sentences[0]
        return _split_by_length(s, max_chunk_length) if len(s) > max_chunk_length else [s]

    chunks: List[str] = []
    current: List[str] = []
    current_len = 0

    for sentence in sentences:
        slen = len(sentence)
        if slen > max_chunk_length:
            if current:
                chunks.append(" ".join(current))
                current, current_len = [], 0
            chunks.extend(_split_by_length(sentence, max_chunk_length))
            continue

        would_exceed = current_len + slen + 1 > max_chunk_length
        at_target = len(current) >= n

        if would_exceed or at_target:
            if current:
                chunks.append(" ".join(current))
            current, current_len = [sentence], slen
        else:
            current.append(sentence)
            current_len += slen + 1

    if current:
        chunks.append(" ".join(current))
    return chunks


def _chunk_semantic(
    sentences: List[str],
    clean_content: str,
    max_chunk_length: int,
    sentence_model: Any,
) -> List[str]:
    """Split at points of low cosine similarity between adjacent sentences."""
    if len(sentences) <= 1:
        return (
            _split_by_length(clean_content, max_chunk_length)
            if len(clean_content) > max_chunk_length
            else [clean_content]
        )

    embeddings = sentence_model.encode(sentences)
    similarities = [
        float(
            np.dot(embeddings[i], embeddings[i + 1])
            / (np.linalg.norm(embeddings[i]) * np.linalg.norm(embeddings[i + 1]))
        )
        for i in range(len(embeddings) - 1)
    ]

    threshold = float(np.mean(similarities) - np.std(similarities))
    breaks = [0] + [i + 1 for i, s in enumerate(similarities) if s < threshold] + [len(sentences)]

    chunks: List[str] = []
    for a, b in zip(breaks, breaks[1:]):
        chunk_text = " ".join(sentences[a:b])
        if len(chunk_text) > max_chunk_length:
            chunks.extend(_split_by_length(chunk_text, max_chunk_length))
        else:
            chunks.append(chunk_text)
    return chunks


def segment_content(
    content: str,
    nlp: Any,
    sentence_model: Any,
    max_chunk_length: int,
    chunking_strategy: str,
    sentences_per_chunk: int,
    max_chunks_per_entry: int = 3,
    timestamp: Optional[datetime] = None,  # kept for backward-compat; unused
) -> List[str]:
    """Segment diary entry content into one or more chunks.

    :param content: Raw diary entry text.
    :param nlp: Loaded spaCy model.
    :param sentence_model: Loaded SentenceTransformer model.
    :param max_chunk_length: Hard character cap per chunk.
    :param chunking_strategy: ``"semantic"``, ``"sentence_group"``, or ``"hybrid"``.
    :param sentences_per_chunk: Target sentences per chunk (sentence_group / hybrid).
    :param max_chunks_per_entry: Maximum chunks emitted per entry.
    :param timestamp: Unused; retained for API compatibility.
    :return: List of non-trivial chunk strings.
    """
    preamble = _extract_temporal_preamble(content)
    clean = content[len(preamble):].lstrip() if preamble else content

    doc = nlp(clean)
    sentences = [s.text.strip() for s in doc.sents if s.text.strip()]

    if not sentences:
        return [content[:max_chunk_length]]

    if chunking_strategy == "sentence_group":
        chunks = _chunk_by_sentence_groups(sentences, sentences_per_chunk)
    elif chunking_strategy == "hybrid":
        chunks = _chunk_hybrid(sentences, sentences_per_chunk, max_chunk_length)
    else:  # "semantic"
        chunks = _chunk_semantic(sentences, clean, max_chunk_length, sentence_model)

    filtered = [c.strip() for c in chunks if c.strip() and not is_meaningless_fragment(c.strip())]

    if len(filtered) > max_chunks_per_entry:
        # Keep first chunk; fill remaining slots with longest remaining chunks
        rest = sorted(filtered[1:], key=len, reverse=True)
        filtered = [filtered[0]] + rest[: max_chunks_per_entry - 1]

    return filtered
