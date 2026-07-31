"""
Scoring de sentiment - niveau 1 (lexicon-based), voir docs/09-strategie-nlp-sentiment.md.
Fonction pure, testable sans dependance externe.
"""
import re
import unicodedata

from app.domains.news.nlp.lexicon import KEYWORD_LEXICON


def _normalize(text: str) -> str:
    text = text.lower()
    return unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode("ascii")


def score_sentiment(text: str, extra_lexicon: dict[str, dict] | None = None) -> float:
    """
    Retourne un score entre -1.0 (tres negatif) et +1.0 (tres positif).
    Renvoie 0.0 (neutre) si aucun mot-cle du lexique n'est detecte - pas
    d'extrapolation au-dela de ce que le lexique peut justifier.

    `extra_lexicon` : mots-cles personnalises de l'utilisateur (voir
    news/custom_keywords_repository.py::as_lexicon) - un mot-cle perso avec un
    poids de 0.0 (valeur par defaut a la creation) n'influence pas ce score,
    il sert alors uniquement a l'extraction (voir extract_keywords ci-dessus
    dans keywords.py) pour signaler sa presence sans le faire "voter".
    """
    lexicon = {**KEYWORD_LEXICON, **extra_lexicon} if extra_lexicon else KEYWORD_LEXICON
    normalized = _normalize(text)
    matched_weights: list[float] = []
    for keyword, config in lexicon.items():
        pattern = _normalize(keyword)
        occurrences = len(re.findall(re.escape(pattern), normalized))
        if occurrences:
            matched_weights.extend([float(config["weight"])] * min(occurrences, 3))  # plafond anti-repetition

    if not matched_weights:
        return 0.0

    score = sum(matched_weights) / len(matched_weights)
    return max(-1.0, min(1.0, score))
