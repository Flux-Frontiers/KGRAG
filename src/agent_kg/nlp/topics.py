"""topics.py — Topic extraction from Turn text for AgentKG.

Extracts candidate topic labels using spaCy noun chunks (when available)
or TF-IDF-style keyword heuristics as fallback.

Returns a list of topic label strings, deduplicated and ranked by salience.
"""

from __future__ import annotations

import re
from typing import Any

_STOP_TOPICS = frozenset({
    "i", "we", "you", "it", "that", "this", "there", "here",
    "thing", "things", "way", "ways", "time", "times",
    "something", "anything", "nothing", "everything",
    "someone", "anyone", "no one", "everyone",
})

# Patterns that indicate high-salience code topics
_CODE_TOPIC = re.compile(
    r"\b("
    r"(?:class|function|method|module|package|file|repo|codebase|test|endpoint|api|"
    r"schema|database|query|migration|deployment|pipeline|ci|cd|auth|oauth|"
    r"refactor|bug|fix|feature|pr|branch|commit|merge|cache|redis|postgres|"
    r"typescript|python|javascript|docker|kubernetes|aws|performance|memory|"
    r"security|logging|monitoring|error|exception|async|thread|queue|stream)"
    r")\b",
    re.I,
)


def _spacy_topics(text: str) -> list[str]:
    """Extract noun-chunk topics using spaCy."""
    try:
        from agent_kg.nlp.intent import _get_spacy_model  # noqa: PLC0415
        nlp = _get_spacy_model()
        if nlp is None:
            return []
        doc = nlp(text[:1024])
        topics = []
        for chunk in doc.noun_chunks:
            label = chunk.root.lemma_.lower().strip()
            if len(label) < 3 or label in _STOP_TOPICS:
                continue
            # Use full chunk if short enough and meaningful
            full = chunk.text.strip().lower()
            if 3 <= len(full.split()) <= 4 and full not in _STOP_TOPICS:
                topics.append(full)
            else:
                topics.append(label)
        return list(dict.fromkeys(topics))  # preserve order, deduplicate
    except Exception:  # pylint: disable=broad-exception-caught
        return []


def _keyword_topics(text: str) -> list[str]:
    """Heuristic keyword-based topic extraction as fallback."""
    topics = []
    # Prioritize code-domain keywords
    for m in _CODE_TOPIC.finditer(text):
        label = m.group(1).lower()
        if label not in topics:
            topics.append(label)
    # Extract CamelCase identifiers as topics
    for m in re.finditer(r"\b([A-Z][a-z]+(?:[A-Z][a-z]+)+)\b", text):
        label = m.group(1).lower()
        if label not in topics and len(label) >= 4:
            topics.append(label)
    # Multi-word phrases (2-3 consecutive content words)
    words = re.findall(r"\b[a-z][a-z0-9]{2,}\b", text.lower())
    content_words = [w for w in words if w not in _STOP_TOPICS and len(w) >= 4]
    for i in range(len(content_words) - 1):
        bigram = f"{content_words[i]} {content_words[i+1]}"
        if bigram not in topics:
            topics.append(bigram)
    return topics[:10]


def extract_topics(text: str) -> list[str]:
    """Extract topic labels from turn text.

    :param text: Raw turn text.
    :return: List of topic label strings, most salient first.
    """
    if not text or not text.strip():
        return []
    topics = _spacy_topics(text)
    if not topics:
        topics = _keyword_topics(text)
    return [t for t in topics if t not in _STOP_TOPICS][:8]
