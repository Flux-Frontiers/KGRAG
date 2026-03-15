"""classifier.py — Topic and context classification.

Two classification layers:

1. **Supervised** (optional): ``TopicClassifier`` from ``topic_classifier.py``
   uses keyword/phrase matching against a YAML config.  Returns a confidence
   dict; a hit is used when the top score exceeds 0.3.

2. **Unsupervised fallback**: TF-IDF + k-means discovers categories directly
   from the chunk corpus, then a simple keyword-rule assigns each chunk.

Context classification (Work / Home / Social / …) runs independently via
entity and keyword matching.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple

from sklearn.cluster import KMeans
from sklearn.feature_extraction.text import TfidfVectorizer


# ---------------------------------------------------------------------------
# Unsupervised category discovery
# ---------------------------------------------------------------------------

_TERM_MAPPINGS: Dict[str, str] = {
    "work": "work",
    "office": "work",
    "business": "work",
    "dinner": "social",
    "friend": "social",
    "home": "domestic",
    "family": "domestic",
    "money": "finance",
    "health": "health",
    "sick": "health",
    "church": "spiritual",
    "travel": "travel",
}


def _generate_category_name(top_terms: List[str]) -> str:
    for term in top_terms:
        mapped = _TERM_MAPPINGS.get(term.lower())
        if mapped:
            return mapped
    return top_terms[0].replace(" ", "_").lower()


def discover_semantic_categories(
    chunks: List[str], n_categories: int = 10, seed: Optional[int] = None
) -> List[str]:
    """Discover topic categories from a corpus via TF-IDF k-means.

    :param chunks: All text chunks to cluster.
    :param n_categories: Desired number of categories.
    :param seed: RNG seed for reproducible clustering.
    :return: List of human-readable category name strings.
    """
    print(f"Discovering {n_categories} semantic categories from {len(chunks)} chunks")

    n = min(n_categories, max(1, len(chunks) // 2))
    min_df = max(1, min(2, len(chunks) // 10))

    vectorizer = TfidfVectorizer(
        max_features=1000, stop_words="english", ngram_range=(1, 2), min_df=min_df
    )
    tfidf = vectorizer.fit_transform(chunks)

    kmeans = KMeans(n_clusters=n, random_state=seed)
    kmeans.fit(tfidf)

    feature_names = vectorizer.get_feature_names_out()
    categories = []
    for i in range(n):
        top_idx = kmeans.cluster_centers_[i].argsort()[-5:][::-1]
        categories.append(_generate_category_name([feature_names[j] for j in top_idx]))

    print(f"Discovered categories: {categories}")
    return categories


# ---------------------------------------------------------------------------
# Chunk classification
# ---------------------------------------------------------------------------

def classify_chunk(chunk: str, categories: List[str]) -> str:
    """Assign a chunk to one of the discovered unsupervised categories.

    Uses simple keyword heuristics; falls back to the first category.

    :param chunk: Text chunk.
    :param categories: Categories returned by ``discover_semantic_categories``.
    :return: Matched category string.
    """
    cl = chunk.lower()
    rules = [
        (["work", "office", "business", "job"], "work"),
        (["dinner", "social", "friend"], "social"),
        (["home", "family", "house"], "domestic"),
        (["money", "paid", "cost"], "finance"),
    ]
    for keywords, label in rules:
        if any(kw in cl for kw in keywords):
            match = next((c for c in categories if label in c), None)
            if match:
                return match
    return categories[0]


def classify_chunk_hybrid(
    chunk: str,
    categories: List[str],
    topic_classifier: Optional[Any] = None,
) -> Tuple[str, Dict[str, float]]:
    """Classify using supervised classification with unsupervised fallback.

    If *topic_classifier* is provided and its top prediction exceeds 0.3
    confidence, that result is returned.  Otherwise falls back to the
    unsupervised ``classify_chunk``.

    :param chunk: Text chunk to classify.
    :param categories: Unsupervised category list.
    :param topic_classifier: Optional ``TopicClassifier`` instance.
    :return: ``(category_name, confidence_dict)`` tuple.
    """
    if topic_classifier is not None:
        try:
            scores = topic_classifier.classify(chunk, return_list=False)
            if scores and scores != {"unknown": 0.0}:
                best_cat, best_score = max(scores.items(), key=lambda x: x[1])
                if best_score > 0.3:
                    return best_cat, scores
        except Exception as exc:
            print(f"Warning: Supervised classification failed: {exc}")

    cat = classify_chunk(chunk, categories)
    return cat, {cat: 1.0}


# ---------------------------------------------------------------------------
# Context classification
# ---------------------------------------------------------------------------

_CONTEXT_KEYWORDS: Dict[str, str] = {
    "work": "Work",
    "office": "Office",
    "home": "Home",
    "family": "Family",
    "money": "Finance",
    "dinner": "Social",
    "sick": "Health",
    "health": "Health",
}

_REFLECTION_WORDS = {"think", "believe", "suppose"}
_EMOTION_WORDS = {"feel", "angry", "pleased", "fear"}


def extract_context(chunk: str, nlp: Any) -> str:
    """Return a coarse context label for a chunk.

    :param chunk: Text chunk.
    :param nlp: Loaded spaCy model.
    :return: Context label string (``"Work"``, ``"Home"``, ``"Social"``, etc.).
    """
    cl = chunk.lower()
    for keyword, label in _CONTEXT_KEYWORDS.items():
        if keyword in cl:
            return label

    doc = nlp(chunk)
    for ent in doc.ents:
        et = ent.text.lower()
        if "work" in et or "office" in et:
            return "Work"
        if "home" in et or "house" in et:
            return "Home"

    if _REFLECTION_WORDS & set(cl.split()):
        return "Reflection"
    if _EMOTION_WORDS & set(cl.split()):
        return "Emotion"
    return "General"
