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


def extract_keywords(text: str, extra_lexicon: dict[str, dict] | None = None) -> list[KeywordMatch]:
    """`extra_lexicon` : mots-cles personnalises de l'utilisateur (voir
    custom_keywords_repository.py::as_lexicon), meme format que
    KEYWORD_LEXICON - fusionnes ici, les mots-cles perso l'emportent en cas de
    collision de nom (permet de surcharger le poids d'un terme existant)."""
    lexicon = {**KEYWORD_LEXICON, **extra_lexicon} if extra_lexicon else KEYWORD_LEXICON
    normalized = _normalize(text)
    matches: list[KeywordMatch] = []
    for keyword, config in lexicon.items():
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
