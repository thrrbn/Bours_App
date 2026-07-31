"""
Tests du moteur de score V1 (regles ponderees) - domaine le plus sensible du
produit puisqu'il determine le signal final affiche a l'utilisateur.
Voir docs/11-strategie-scoring-hybride.md.
"""
from app.domains.signals.features import SignalFeatures
from app.domains.signals.models_ml.baseline_rules import DecisionParams, classify_signal, compute


def _base_features(**overrides) -> SignalFeatures:
    defaults = dict(
        horizon="short",
        price_history_days=250,
        trend_direction="flat",
        rsi_14=50.0,
        macd_cross="none",
        volatility_20d=0.01,
        news_sentiment=0.0,
        news_article_count=0,
        days_since_last_news=None,
    )
    defaults.update(overrides)
    return SignalFeatures(**defaults)


def test_neutral_features_produce_neutral_or_surveillance_signal():
    features = _base_features()
    result = compute(features)
    assert result.final_signal in ("neutre", "surveillance", "prudence")
    assert 0 <= result.technical_score <= 100
    assert 0 <= result.confidence_score <= 100


def test_bullish_technical_and_news_push_score_up():
    bullish = _base_features(
        trend_direction="up", rsi_14=25.0, macd_cross="bullish", news_sentiment=0.8, news_article_count=3,
        days_since_last_news=0,
    )
    bearish = _base_features(
        trend_direction="down", rsi_14=80.0, macd_cross="bearish", news_sentiment=-0.8, news_article_count=3,
        days_since_last_news=0,
    )
    bullish_result = compute(bullish)
    bearish_result = compute(bearish)
    assert bullish_result.technical_score > bearish_result.technical_score
    assert bullish_result.news_score > bearish_result.news_score


def test_low_confidence_forces_surveillance_regardless_of_scores():
    features = _base_features(
        price_history_days=5,  # tres peu d'historique -> confiance basse
        trend_direction="up", rsi_14=20.0, macd_cross="bullish",
        news_sentiment=0.9, news_article_count=5, days_since_last_news=0,
    )
    result = compute(features)
    assert result.confidence_score < 30
    assert result.final_signal == "surveillance"


def test_every_signal_has_non_empty_explanations():
    result = compute(_base_features())
    assert len(result.components) == 4
    for component in result.components:
        assert component.explanation.strip() != ""


def test_high_volatility_increases_risk_score():
    calm = _base_features(volatility_20d=0.005)
    volatile = _base_features(volatility_20d=0.15)
    assert compute(volatile).risk_score > compute(calm).risk_score


# 31/07/2026 : "laboratoire de parametres" (voir docs/STACK.md et
# backtests/kernc_engine.py) - classify_signal() a ete extrait de compute()
# pour permettre au backtest de tester des variantes de seuils/ponderation
# SANS toucher au moteur reel. Ces tests garantissent que DEFAULT_DECISION_PARAMS
# reproduit exactement l'ancien comportement code en dur, et qu'un parametre
# different change bien la classification.
def test_classify_signal_with_defaults_matches_historical_thresholds():
    # Combined = 0.5*80 + 0.5*60 = 70 -> achat_speculatif si risk < 50
    assert classify_signal(technical=80, news=60, risk=40, confidence=80) == "achat_speculatif"
    # Meme combined (70) mais risk >= 50 -> retombe en surveillance (>= 55)
    assert classify_signal(technical=80, news=60, risk=55, confidence=80) == "surveillance"
    # Combined = 0.5*20 + 0.5*20 = 20 <= 30 et risk >= 60 -> vente_defensive
    assert classify_signal(technical=20, news=20, risk=65, confidence=80) == "vente_defensive"
    # confidence < 30 -> toujours surveillance, quels que soient les autres scores
    assert classify_signal(technical=90, news=90, risk=10, confidence=10) == "surveillance"


def test_classify_signal_with_custom_params_changes_outcome():
    # Avec les seuils par defaut, combined=65 ne declenche pas achat_speculatif
    # (seuil 70) - avec un seuil abaisse a 60, le meme score bascule en achat.
    technical, news, risk, confidence = 70, 60, 40, 80
    default_result = classify_signal(technical, news, risk, confidence)
    lenient_params = DecisionParams(buy_threshold=60.0)
    lenient_result = classify_signal(technical, news, risk, confidence, params=lenient_params)
    assert default_result != "achat_speculatif"
    assert lenient_result == "achat_speculatif"


def test_compute_uses_classify_signal_with_default_params():
    # compute() doit utiliser exactement les memes parametres par defaut que
    # classify_signal() - pas de valeurs dupliquees/divergentes entre les deux.
    features = _base_features(
        trend_direction="up", rsi_14=25.0, macd_cross="bullish", news_sentiment=0.8, news_article_count=3,
        days_since_last_news=0,
    )
    result = compute(features)
    expected = classify_signal(result.technical_score, result.news_score, result.risk_score, result.confidence_score)
    assert result.final_signal == expected
