"""Tests du scoring de sentiment et de l'extraction de mots-cles (docs/09)."""
from app.domains.news.nlp.keywords import extract_keywords
from app.domains.news.nlp.sentiment import score_sentiment


def test_neutral_text_scores_zero():
    assert score_sentiment("La societe a publie son rapport trimestriel.") == 0.0


def test_profit_warning_scores_negative():
    score = score_sentiment("La societe emet un profit warning pour le prochain trimestre.")
    assert score < 0


def test_growth_and_positive_guidance_scores_positive():
    score = score_sentiment("La societe annonce une forte croissance et une guidance relevee.")
    assert score > 0


def test_score_is_bounded():
    text = "profit warning " * 20  # repetition volontaire pour tester le plafond
    score = score_sentiment(text)
    assert -1.0 <= score <= 1.0


def test_extract_keywords_finds_expected_matches_with_horizon():
    matches = extract_keywords("Annonce d'une acquisition majeure et d'une dilution du capital.")
    keywords_found = {m.keyword for m in matches}
    assert "acquisition" in keywords_found
    assert "dilution" in keywords_found
    acquisition_match = next(m for m in matches if m.keyword == "acquisition")
    assert acquisition_match.horizon_impact == "long"


def test_extract_keywords_empty_for_irrelevant_text():
    matches = extract_keywords("Le temps est ensoleille a Bruxelles aujourd'hui.")
    assert matches == []
