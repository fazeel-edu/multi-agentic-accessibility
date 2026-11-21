"""Readability scorer (Flesch reading ease and Flesch-Kincaid grade). Pure."""

import re
from typing import Any

_WORD = re.compile(r"[A-Za-z]+(?:'[A-Za-z]+)?")
_SENTENCE_END = re.compile(r"[.!?]+(?:\s|$)")
_VOWEL_GROUPS = re.compile(r"[aeiouy]+")


def count_syllables(word: str) -> int:
    w = word.lower().strip("'")
    if len(w) <= 3:
        return 1
    w = re.sub(r"(?:es|ed|e)$", "", w) or w
    return max(1, len(_VOWEL_GROUPS.findall(w)))


def score(text: str) -> dict[str, Any]:
    """Words, sentences, and the two Flesch measures. Empty text scores None."""
    words = _WORD.findall(text)
    sentences = max(1, len(_SENTENCE_END.findall(text.strip() + " "))) if words else 0
    if not words:
        return {"words": 0, "sentences": 0, "reading_ease": None, "grade_level": None}
    syllables = sum(count_syllables(w) for w in words)
    wps = len(words) / sentences
    spw = syllables / len(words)
    return {
        "words": len(words),
        "sentences": sentences,
        "avg_words_per_sentence": round(wps, 1),
        "reading_ease": round(206.835 - 1.015 * wps - 84.6 * spw, 1),
        "grade_level": round(0.39 * wps + 11.8 * spw - 15.59, 1),
    }
