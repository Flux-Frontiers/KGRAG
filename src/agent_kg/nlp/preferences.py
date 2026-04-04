"""preferences.py — Preference, commitment, and expertise extraction.

Detects when a user is expressing a standing rule, personal preference,
area of expertise, or interest. Returns typed records for storage in the
UserProfile tree.

Each result is: {"kind": "preference"|"commitment"|"expertise"|"interest", "label": str, "text": str}
"""

from __future__ import annotations

import re
from typing import Any

# --- Commitment patterns ("always do X", "never do Y", "always run Z") ------
_COMMITMENT_ALWAYS = re.compile(
    r"\b(always|every\s+time|each\s+time|make\s+sure\s+to|remember\s+to)\b.{3,80}",
    re.I,
)
_COMMITMENT_NEVER = re.compile(
    r"\b(never|don'?t\s+ever|stop\s+doing|avoid|don'?t\s+use|refrain\s+from)\b.{3,80}",
    re.I,
)
_COMMITMENT_RULE = re.compile(
    r"\b(rule:|my\s+rule\s+is|policy:|from\s+now\s+on|going\s+forward)\b.{3,80}",
    re.I,
)

# --- Preference patterns ("I prefer X", "I like X", "I want X") -------------
_PREF_LIKE = re.compile(
    r"\b(i\s+(?:prefer|like|love|want|use|tend\s+to\s+use|usually\s+use))\s+(.{3,60}?)(?:\.|,|$)",
    re.I,
)
_PREF_HATE = re.compile(
    r"\b(i\s+(?:hate|dislike|don'?t\s+like|avoid|can'?t\s+stand))\s+(.{3,60}?)(?:\.|,|$)",
    re.I,
)
_PREF_STYLE = re.compile(
    r"\b((?:use|prefer)\s+(?:google|numpy|sphinx)\s+(?:docstrings?|style))\b",
    re.I,
)
_PREF_CONCISE = re.compile(
    r"\b((?:be\s+)?(?:concise|brief|short|terse|detailed|verbose|comprehensive))\b",
    re.I,
)

# --- Expertise patterns ("I know X well", "I'm an expert in X") -------------
_EXPERTISE = re.compile(
    r"\b(i(?:'m|'ve|\s+am|\s+have)\s+(?:been\s+)?(?:working\s+(?:with|in|on)|"
    r"expert\s+in|experienced\s+(?:with|in)|good\s+(?:with|at)|know(?:ing)?)\s+)"
    r"(.{3,50}?)(?:\.|,|$)",
    re.I,
)
_EXPERTISE_YEARS = re.compile(
    r"(\d+)\s+years?\s+(?:of\s+)?(?:experience|working\s+(?:with|in))\s+(.{3,50}?)(?:\.|,|$)",
    re.I,
)

# --- Interest patterns ("I'm interested in X", "I enjoy X") -----------------
_INTEREST = re.compile(
    r"\b(i(?:'m|'ve|\s+am|\s+have)\s+(?:interested\s+in|into|enjoy(?:ing)?|"
    r"passionate\s+about|a\s+fan\s+of|working\s+on\s+(?:a\s+)?(?:hobby|side)?))\s+"
    r"(.{3,60}?)(?:\.|,|$)",
    re.I,
)


def _extract_commitments(text: str) -> list[dict[str, Any]]:
    results = []
    for pattern in (_COMMITMENT_ALWAYS, _COMMITMENT_NEVER, _COMMITMENT_RULE):
        for m in pattern.finditer(text):
            snippet = m.group(0).strip().rstrip(".,;")
            if len(snippet) >= 8:
                results.append({"kind": "commitment", "label": snippet[:80], "text": snippet})
    return results


def _extract_preferences(text: str) -> list[dict[str, Any]]:
    results = []
    for pattern in (_PREF_LIKE, _PREF_HATE):
        for m in pattern.finditer(text):
            label = m.group(2).strip().rstrip(".,;")
            if len(label) >= 3:
                results.append({"kind": "preference", "label": label[:80], "text": m.group(0).strip()})
    for pattern in (_PREF_STYLE, _PREF_CONCISE):
        for m in pattern.finditer(text):
            label = m.group(1).strip()
            results.append({"kind": "style", "label": label[:80], "text": label})
    return results


def _extract_expertise(text: str) -> list[dict[str, Any]]:
    results = []
    for m in _EXPERTISE.finditer(text):
        label = m.group(2).strip().rstrip(".,;")
        if len(label) >= 3:
            results.append({"kind": "expertise", "label": label[:80], "text": m.group(0).strip()})
    for m in _EXPERTISE_YEARS.finditer(text):
        label = f"{m.group(2).strip()} ({m.group(1)}y)"
        results.append({"kind": "expertise", "label": label[:80], "text": m.group(0).strip()})
    return results


def _extract_interests(text: str) -> list[dict[str, Any]]:
    results = []
    for m in _INTEREST.finditer(text):
        label = m.group(2).strip().rstrip(".,;")
        if len(label) >= 3:
            results.append({"kind": "interest", "label": label[:80], "text": m.group(0).strip()})
    return results


def extract_preferences(text: str) -> list[dict[str, Any]]:
    """Detect preferences, commitments, expertise, and interests in ``text``.

    Only meaningful for user-role turns (assistant text rarely expresses preferences).

    :param text: Raw turn text.
    :return: List of ``{"kind", "label", "text"}`` dicts.
    """
    if not text or not text.strip():
        return []
    results = []
    results.extend(_extract_commitments(text))
    results.extend(_extract_preferences(text))
    results.extend(_extract_expertise(text))
    results.extend(_extract_interests(text))
    # Deduplicate by label
    seen: set[str] = set()
    unique = []
    for r in results:
        key = r["label"].lower()
        if key not in seen:
            seen.add(key)
            unique.append(r)
    return unique[:10]
