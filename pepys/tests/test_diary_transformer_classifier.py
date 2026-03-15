"""
test_diary_transformer_classifier.py

Unit tests for diary_transformer.classifier — unsupervised category
discovery, chunk classification, hybrid classification, and context
extraction.
"""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from diary_transformer.classifier import (
    classify_chunk,
    classify_chunk_hybrid,
    discover_semantic_categories,
    extract_context,
)


class TestDiscoverSemanticCategories:
    def test_returns_list_of_strings(self):
        chunks = [
            "Went to the office to do work business.",
            "Had dinner with friends at the social club.",
            "Paid the bills and managed the household money.",
            "Felt sick and stayed home in bed.",
            "Prayed at church this Sunday morning.",
        ] * 4  # repeat to give kmeans enough data
        cats = discover_semantic_categories(chunks, n_categories=3, seed=42)
        assert isinstance(cats, list)
        assert len(cats) > 0
        assert all(isinstance(c, str) for c in cats)

    def test_fewer_categories_than_chunks(self):
        chunks = ["work meeting office"] * 6
        cats = discover_semantic_categories(chunks, n_categories=5, seed=0)
        # Can't have more categories than unique samples
        assert len(cats) <= 5

    def test_single_chunk_returns_one_category(self):
        cats = discover_semantic_categories(["only one chunk here"], n_categories=3, seed=0)
        assert len(cats) == 1

    def test_seed_produces_reproducible_results(self):
        chunks = ["work office meeting"] * 10 + ["home family dinner"] * 10
        a = discover_semantic_categories(chunks, seed=99)
        b = discover_semantic_categories(chunks, seed=99)
        assert a == b


class TestClassifyChunk:
    def test_work_keyword(self):
        categories = ["work", "social", "domestic", "finance"]
        result = classify_chunk("Went to the office for business", categories)
        assert result == "work"

    def test_social_keyword(self):
        categories = ["work", "social", "domestic", "finance"]
        result = classify_chunk("Had dinner with a friend at the club", categories)
        assert result == "social"

    def test_domestic_keyword(self):
        categories = ["work", "social", "domestic", "finance"]
        result = classify_chunk("At home with the family this evening", categories)
        assert result == "domestic"

    def test_finance_keyword(self):
        categories = ["work", "social", "domestic", "finance"]
        result = classify_chunk("Paid the money I owed to the merchant", categories)
        assert result == "finance"

    def test_fallback_to_first_category(self):
        categories = ["misc", "work", "social"]
        result = classify_chunk("Something unrelated entirely", categories)
        assert result == "misc"


class TestClassifyChunkHybrid:
    def test_uses_supervised_when_confident(self):
        mock_tc = MagicMock()
        mock_tc.classify.return_value = {"health": 0.8, "work": 0.1}
        categories = ["work", "social"]
        cat, scores = classify_chunk_hybrid("Felt very ill today", categories, mock_tc)
        assert cat == "health"
        assert scores["health"] == 0.8

    def test_falls_back_when_supervised_below_threshold(self):
        mock_tc = MagicMock()
        mock_tc.classify.return_value = {"health": 0.2, "work": 0.1}
        categories = ["work", "social", "domestic"]
        cat, scores = classify_chunk_hybrid(
            "At home with the family", categories, mock_tc
        )
        # Should fall back to unsupervised — domestic keyword matches
        assert cat == "domestic"

    def test_falls_back_when_no_classifier(self):
        categories = ["work", "social"]
        cat, scores = classify_chunk_hybrid("office work meeting", categories, None)
        assert cat == "work"

    def test_falls_back_on_classifier_exception(self):
        mock_tc = MagicMock()
        mock_tc.classify.side_effect = RuntimeError("model error")
        categories = ["work", "social"]
        # Should not raise — falls back to unsupervised
        cat, scores = classify_chunk_hybrid("office work", categories, mock_tc)
        assert isinstance(cat, str)

    def test_ignores_unknown_only_result(self):
        mock_tc = MagicMock()
        mock_tc.classify.return_value = {"unknown": 0.0}
        categories = ["work", "social"]
        cat, scores = classify_chunk_hybrid("office work", categories, mock_tc)
        assert cat == "work"  # fell back to unsupervised


class TestExtractContext:
    @pytest.fixture
    def nlp(self):
        """Minimal spaCy-like mock."""
        mock = MagicMock()
        doc = MagicMock()
        doc.ents = []
        doc.sents = []
        mock.return_value = doc
        return mock

    def test_work_keyword(self, nlp):
        assert extract_context("Went to work today", nlp) == "Work"

    def test_office_keyword(self, nlp):
        assert extract_context("At the office all morning", nlp) == "Office"

    def test_home_keyword(self, nlp):
        assert extract_context("Stayed at home all day", nlp) == "Home"

    def test_family_keyword(self, nlp):
        assert extract_context("With my family tonight", nlp) == "Family"

    def test_money_keyword(self, nlp):
        assert extract_context("Paid the money owed", nlp) == "Finance"

    def test_dinner_keyword(self, nlp):
        assert extract_context("Had dinner at the club", nlp) == "Social"

    def test_health_keyword(self, nlp):
        assert extract_context("My health is poor today", nlp) == "Health"

    def test_sick_keyword(self, nlp):
        assert extract_context("I am sick and in bed", nlp) == "Health"

    def test_reflection_words(self, nlp):
        # No keyword match — falls through to word set check
        doc = MagicMock()
        doc.ents = []
        nlp.return_value = doc
        result = extract_context("I think this is a problem", nlp)
        assert result == "Reflection"

    def test_emotion_words(self, nlp):
        doc = MagicMock()
        doc.ents = []
        nlp.return_value = doc
        result = extract_context("I feel angry about it", nlp)
        assert result == "Emotion"

    def test_general_fallback(self, nlp):
        doc = MagicMock()
        doc.ents = []
        nlp.return_value = doc
        result = extract_context("The weather was fine today", nlp)
        assert result == "General"
