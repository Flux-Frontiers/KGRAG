"""
Topic Classifier Module

This module defines a TopicClassifier class that can be used to classify the topic(s) of a given text. The key features of this class are:

1. Configuration Loading:
   - The class loads a configuration file (default is 'topics.yaml') that contains the topic categories and associated keywords/phrases.
   - The configuration data is stored in the 'categories' and 'phrases' attributes.

2. Text Cleaning:
   - The 'clean_text' method preprocesses the input text by converting it to lowercase, removing non-alphabetic characters, and removing stopwords.

3. Topic Classification:
   - The 'classify' method takes in a text input and returns either a list of topic names or a dictionary of topic names and their confidence scores.
   - The classification is done by first checking for matching phrases (with higher weight) and then checking for individual keywords.
   - The final scores are normalized and a confidence threshold is applied to determine the relevant topics.

4. Example Usage:
   - The module includes an example usage section that demonstrates how to use the TopicClassifier class to classify sample text inputs.

The TopicClassifier class provides a convenient way to categorize text data into predefined topics based on keyword and phrase matching. This could be useful in a variety of applications, such as content analysis, customer support, or information retrieval. The module's design allows for easy customization of the topic categories and associated keywords/phrases by modifying the configuration file.
"""

import argparse
import re
from dataclasses import dataclass
from re import Pattern

import yaml


@dataclass
class RuleSet:
    """Basic ruleset"""

    keywords: list[str]
    patterns: list[Pattern]


class TopicClassifier:
    def __init__(self, config_path=None):
        import os

        if config_path is None:
            # Default to topics.yaml in the same directory as this file
            current_dir = os.path.dirname(os.path.abspath(__file__))
            config_path = os.path.join(current_dir, "topics.yaml")

        self.load_config(config_path)
        self.stopwords = set(
            [
                "i",
                "me",
                "my",
                "myself",
                "we",
                "our",
                "ours",
                "ourselves",
                "you",
                "your",
                "yours",
                "yourself",
                "yourselves",
                "he",
                "him",
                "his",
                "himself",
                "she",
                "her",
                "hers",
                "herself",
                "it",
                "its",
                "itself",
                "they",
                "them",
                "their",
                "theirs",
                "themselves",
                "what",
                "which",
                "who",
                "whom",
                "this",
                "that",
                "these",
                "those",
                "am",
                "is",
                "are",
                "was",
                "were",
                "be",
                "been",
                "being",
                "have",
                "has",
                "had",
                "having",
                "do",
                "does",
                "did",
                "doing",
                "a",
                "an",
                "the",
                "and",
                "but",
                "if",
                "or",
                "because",
                "as",
                "until",
                "while",
                "of",
                "at",
                "by",
                "for",
                "with",
                "through",
                "during",
                "before",
                "after",
                "above",
                "below",
                "up",
                "down",
                "in",
                "out",
                "on",
                "off",
                "over",
                "under",
                "again",
                "further",
                "then",
                "once",
            ]
        )
        self.confidence_threshold = 0.1
        self.keyword_weight = 1
        self.phrase_weight = 3

    def load_config(self, config_path):
        with open(config_path) as f:
            config = yaml.safe_load(f)
            self.categories = config.get("categories", {})
            self.phrases = config.get("phrases", {})

    def clean_text(self, text):
        text = text.lower()
        # Expand common contractions
        text = re.sub(r"i'm", "i am", text)
        text = re.sub(r"you're", "you are", text)
        text = re.sub(r"he's", "he is", text)
        text = re.sub(r"she's", "she is", text)
        text = re.sub(r"it's", "it is", text)
        text = re.sub(r"we're", "we are", text)
        text = re.sub(r"they're", "they are", text)
        text = re.sub(r"can't", "cannot", text)
        text = re.sub(r"won't", "will not", text)
        text = re.sub(r"don't", "do not", text)
        text = re.sub(r"doesn't", "does not", text)
        text = re.sub(r"didn't", "did not", text)
        text = re.sub(r"isn't", "is not", text)
        text = re.sub(r"aren't", "are not", text)
        text = re.sub(r"wasn't", "was not", text)
        text = re.sub(r"weren't", "were not", text)
        text = re.sub(r"haven't", "have not", text)
        text = re.sub(r"hasn't", "has not", text)
        text = re.sub(r"hadn't", "had not", text)
        text = re.sub(r"wouldn't", "would not", text)
        text = re.sub(r"shouldn't", "should not", text)
        text = re.sub(r"couldn't", "could not", text)

        # Preserve special characters relevant to programming languages (e.g., C++, C#)
        # and remove other non-alphanumeric characters, but keep spaces.
        text = re.sub(r"[^a-z0-9#+\s]", "", text)
        tokens = text.split()
        tokens = [word for word in tokens if word not in self.stopwords]
        return " ".join(tokens)

    def classify(self, text, return_list=False):
        """
        Classify the topic(s) of a given text.

        Args:
            text (str): Text to classify
            return_list (bool): If True, returns list of topic names only.
                               If False, returns dict with confidence scores.

        Returns:
            Union[List[str], Dict[str, float]]: Topic classification results
        """
        cleaned = self.clean_text(text)
        cleaned_words = cleaned.split()
        # Keep original text for phrase matching (just lowercase, no stopword removal)
        original_lower = text.lower()
        raw_scores = {category: 0 for category in self.categories}

        # Check phrases first (higher weight) - use original text to preserve critical words like "myself"
        for category, phrases in self.phrases.items():
            if category in raw_scores:  # Make sure category exists in raw_scores
                for phrase in phrases:
                    if phrase.lower() in original_lower:
                        raw_scores[category] += self.phrase_weight

        # Check individual keywords with whole word matching
        for category, keywords in self.categories.items():
            for keyword in keywords:
                keyword_lower = keyword.lower()
                # Use whole word matching to avoid partial matches like "ai" in "hiking"
                if keyword_lower in cleaned_words:
                    raw_scores[category] += self.keyword_weight
                # Also check for exact phrase matches for multi-word keywords
                elif " " in keyword_lower and keyword_lower in cleaned:
                    raw_scores[category] += self.keyword_weight

        total_score = sum(raw_scores.values())
        if total_score == 0:
            return ["unknown"] if return_list else {"unknown": 0.0}

        normalized_scores = {
            cat: score / total_score for cat, score in raw_scores.items() if score > 0
        }
        high_confidence = {
            cat: round(score, 3)
            for cat, score in normalized_scores.items()
            if score >= self.confidence_threshold
        }

        if not high_confidence:
            return ["unknown"] if return_list else {"unknown": 0.0}

        if return_list:
            return list(high_confidence.keys())
        else:
            return high_confidence

    def classify_with_confidence(self, text):
        """
        Classify the topic(s) of a given text and return confidence scores.

        Args:
            text (str): Text to classify

        Returns:
            Dict[str, float]: Dictionary mapping topic names to confidence scores
        """
        return self.classify(text, return_list=False)


def demo():
    classifier = TopicClassifier()
    examples = [
        "My name is John and I work at Google.",
        "I love to play the piano and travel.",
        "I am 35 years old and live in Paris.",
        "I studied biology at university.",
        "Married to a wonderful woman with 2 kids.",
        "I prefer coffee over tea.",
        "I plan to climb Mount Everest.",
        "I have a peanut allergy.",
        "I have a dog named Max and love animals.",
        "I enjoy hiking and playing tennis on weekends.",
        "I love to drive my car.",
        "I have four children.",
        "I was a Genius at the Apple Store!",
        "I used to fly RC airplanes",
        "I attended Johns Hopkins Medical School for my PhD.",
        "I love tea",
        "I hate hot weather",
        "I'm feeling a bit stressed today.",
        "I wrote in my journal about my feelings.",
        "Completely unrelated sentence.",
    ]

    print("=== Topic Classification Demo ===")
    for text in examples:
        # Default behavior: returns dict with confidence scores
        topics_with_confidence = classifier.classify(text)
        # Alternative: returns list of topic names only
        topics_list = classifier.classify(text, return_list=True)

        print(f"Input: {text}")
        print(f"Topics with confidence: {topics_with_confidence}")
        print(f"Topics (list only): {topics_list}\n")


def main():
    parser = argparse.ArgumentParser(
        description="Topic Classifier - Classify text into topics with confidence scores"
    )
    parser.add_argument(
        "-d", "--demo", action="store_true", help="Run demo mode with example texts"
    )
    parser.add_argument("text", nargs="*", help="Text to classify (if not using demo mode)")

    args = parser.parse_args()

    if args.demo:
        demo()
    elif args.text:
        # Join all text arguments into a single string
        input_text = " ".join(args.text)
        classifier = TopicClassifier()
        result = classifier.classify(input_text)

        print(f"Input: {input_text}")
        print(f"Topics with confidence: {result}")
    else:
        parser.print_help()
        print("\nExamples:")
        print("  python topic_classifier.py 'I love programming and Python'")
        print("  python topic_classifier.py -d")


if __name__ == "__main__":
    main()

# end of file
