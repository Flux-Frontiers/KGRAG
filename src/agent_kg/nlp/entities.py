"""entities.py — Named entity extraction for AgentKG Turn nodes.

Uses spaCy NER when available; falls back to regex patterns for
common code-domain entities (file paths, function names, URLs, etc.).

Each entity is returned as:
  {"label": str, "kind": str, "source_text": str}

Entity kinds: file | function | concept | person | project | url | package
"""

from __future__ import annotations

import re
from typing import Any

# Regex patterns for code-domain entities (used as fallback and supplement)
_FILE_PATH = re.compile(r"(?:^|[\s\"'`(])([./~][\w./\-]+\.\w{1,6})(?:\s|[\"'`),]|$)")
_FUNCTION = re.compile(r"\b(\w+)\s*\(")
_PYTHON_IMPORT = re.compile(r"(?:import|from)\s+([\w.]+)")
_CAMEL_CLASS = re.compile(r"\b([A-Z][a-z]+(?:[A-Z][a-z]+)+)\b")
_SNAKE_FUNC = re.compile(r"\b([a-z][a-z0-9]*(?:_[a-z0-9]+){1,})\b")
_URL = re.compile(r"https?://[^\s\"'<>]+")
_GITHUB_REPO = re.compile(r"\b([\w-]+/[\w-]+)\b(?:#\d+)?")

_SPACY_KIND_MAP = {
    "PERSON": "person",
    "ORG": "project",
    "PRODUCT": "project",
    "GPE": "concept",
    "LANGUAGE": "concept",
    "WORK_OF_ART": "concept",
    "EVENT": "concept",
    "LAW": "concept",
    "LOC": "concept",
    "FAC": "concept",
}

_STOP_WORDS = frozenset({
    "i", "we", "you", "it", "is", "was", "are", "were", "be", "been",
    "have", "has", "had", "do", "does", "did", "will", "would", "could",
    "should", "may", "might", "must", "shall", "the", "a", "an", "and",
    "or", "but", "if", "in", "on", "at", "to", "for", "of", "with",
    "as", "by", "from", "that", "this", "these", "those", "not", "no",
})


def _spacy_entities(text: str) -> list[dict[str, Any]]:
    """Extract named entities using spaCy NER."""
    try:
        from agent_kg.nlp.intent import _get_spacy_model  # noqa: PLC0415
        nlp = _get_spacy_model()
        if nlp is None:
            return []
        doc = nlp(text[:1024])
        results = []
        for ent in doc.ents:
            kind = _SPACY_KIND_MAP.get(ent.label_, "concept")
            label = ent.text.strip()
            if len(label) < 2 or label.lower() in _STOP_WORDS:
                continue
            results.append({"label": label, "kind": kind, "source_text": ent.text})
        return results
    except Exception:  # pylint: disable=broad-exception-caught
        return []


def _regex_entities(text: str) -> list[dict[str, Any]]:
    """Extract code-domain entities using regex patterns."""
    results = []
    seen: set[str] = set()

    def _add(label: str, kind: str) -> None:
        key = f"{kind}:{label.lower()}"
        if key not in seen and len(label) >= 2 and label.lower() not in _STOP_WORDS:
            seen.add(key)
            results.append({"label": label, "kind": kind, "source_text": label})

    for m in _FILE_PATH.finditer(text):
        _add(m.group(1), "file")
    for m in _URL.finditer(text):
        _add(m.group(0)[:100], "url")
    for m in _PYTHON_IMPORT.finditer(text):
        _add(m.group(1), "package")
    for m in _CAMEL_CLASS.finditer(text):
        label = m.group(1)
        if len(label) >= 4:
            _add(label, "function")
    return results


def extract_entities(text: str) -> list[dict[str, Any]]:
    """Extract named entities from turn text.

    :param text: Raw turn text.
    :return: List of ``{"label", "kind", "source_text"}`` dicts.
    """
    entities = _spacy_entities(text)
    # Always supplement with regex for code-domain entities
    # (spaCy misses file paths, imports, CamelCase class names)
    regex_ents = _regex_entities(text)
    seen_labels = {e["label"].lower() for e in entities}
    for e in regex_ents:
        if e["label"].lower() not in seen_labels:
            entities.append(e)
    # Deduplicate and limit
    return entities[:20]
