"""nlp — lightweight NLP pipeline for AgentKG ingest.

Components:
  intent     — intent classification (question/request/correction/…)
  entities   — named entity extraction and deduplication
  topics     — topic extraction from noun chunks
  preferences — preference/commitment/expertise detection
"""

from agent_kg.nlp.entities import extract_entities
from agent_kg.nlp.intent import classify_intent
from agent_kg.nlp.preferences import extract_preferences
from agent_kg.nlp.topics import extract_topics

__all__ = ["classify_intent", "extract_entities", "extract_topics", "extract_preferences"]
