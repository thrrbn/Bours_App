"""Extraction de mots-cles a impact financier - voir docs/09."""
import re
import unicodedata
from dataclasses import dataclass

from app.domains.news.nlp.lexicon import KEYWORD_LEXICON


@dataclass
class KeywordMatch:
    keyword: str
    weight: float
    horizon_impact: str
    occurrences: int


def _normalize(text: str) -> str:
    text = text.lower()
    return unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode("ascii")


def extract_keywords(text: str) -> list[KeywordMatch]:
    normalized = _normalize(text)
    matches: list[KeywordMatch] = []
    for keyword, config in KEYWORD_LEXICON.items():
        pattern = _normalize(keyword)
        occurrences = len(re.findall(re.escape(pattern), normalized))
        if occurrences:
            matches.append(
                KeywordMatch(
                    keyword=keyword,
                    weight=float(config["weight"]),
                    horizon_impact=str(config["horizon"]),
                    occurrences=occurrences,
                )
            )
    return matches
