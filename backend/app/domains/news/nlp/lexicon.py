"""
Dictionnaire de mots-cles financiers pondere, utilise pour le scoring de
sentiment (niveau 1, lexicon-based) et l'extraction de mots-cles (docs/09).

Chaque entree : poids de polarite (-1 a +1) et horizon d'impact dominant
('short', 'medium', 'long'). Ce fichier est LE point de configuration a
ajuster par calibration (backtesting), pas le code du moteur NLP lui-meme.
"""

KEYWORD_LEXICON: dict[str, dict[str, float | str]] = {
    "achat": {"weight": 0.3, "horizon": "short"},
    "acquisition": {"weight": 0.3, "horizon": "long"},
    "restructuration": {"weight": -0.3, "horizon": "medium"},
    "licenciement": {"weight": -0.4, "horizon": "medium"},
    "guidance relevee": {"weight": 0.6, "horizon": "medium"},
    "guidance abaissee": {"weight": -0.6, "horizon": "medium"},
    "profit warning": {"weight": -0.8, "horizon": "short"},
    "croissance": {"weight": 0.4, "horizon": "long"},
    "dette": {"weight": -0.3, "horizon": "long"},
    "fusion": {"weight": 0.2, "horizon": "long"},
    "dilution": {"weight": -0.5, "horizon": "short"},
    "rachat d'actions": {"weight": 0.4, "horizon": "medium"},
    "dividende": {"weight": 0.2, "horizon": "medium"},
    "litige": {"weight": -0.3, "horizon": "medium"},
    "amende": {"weight": -0.4, "horizon": "short"},
    "record de resultat": {"weight": 0.7, "horizon": "short"},
}
