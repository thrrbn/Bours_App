"""
Tests du modele statistique V2 (regression logistique) - en particulier le
statut de maturite qui conditionne l'affichage (docs/11, ajout suite a la
demande de flagger visuellement un modele encore en apprentissage).
"""
from app.domains.signals.features import SignalFeatures
from app.domains.signals.models_ml.logistic_model import MIN_TRAINING_SAMPLES, predict
from app.domains.signals.training import TrainingExample


def _features() -> SignalFeatures:
    return SignalFeatures(
        horizon="short",
        price_history_days=250,
        trend_direction="up",
        rsi_14=40.0,
        macd_cross="bullish",
        volatility_20d=0.01,
        news_sentiment=0.2,
        news_article_count=1,
        days_since_last_news=0,
    )


def test_insufficient_examples_returns_en_apprentissage():
    examples = [
        TrainingExample(1, 0, 40.0, 1, 0.01, 0.1, 1, 1) for _ in range(5)
    ]
    preview = predict(_features(), examples)
    assert preview.model_status == "en_apprentissage"
    assert preview.probability_up is None
    assert preview.sample_count == 5


def test_single_class_examples_stay_en_apprentissage_even_above_threshold():
    # Toutes les etiquettes identiques (label=1) -> rien a apprendre, meme
    # avec beaucoup d'exemples.
    examples = [TrainingExample(1, 0, 40.0, 1, 0.01, 0.1, 1, 1) for _ in range(60)]
    preview = predict(_features(), examples)
    assert preview.model_status == "en_apprentissage"
    assert preview.probability_up is None


def test_well_separated_dataset_becomes_fiable_above_threshold():
    # Motif clair et separable : trend_up=1 -> toujours label 1, trend_up=0 -> toujours label 0.
    examples = []
    for _ in range(MIN_TRAINING_SAMPLES + 10):
        examples.append(TrainingExample(1, 0, 25.0, 1, 0.01, 0.5, 2, 1))
        examples.append(TrainingExample(0, 1, 75.0, 0, 0.01, -0.5, 2, 0))

    preview = predict(_features(), examples)
    assert preview.model_status == "fiable"
    assert preview.probability_up is not None
    assert preview.final_signal is not None


def test_below_threshold_but_fittable_still_marked_en_apprentissage():
    # Assez d'exemples pour entrainer (>= 10) mais sous le seuil de fiabilite (50).
    examples = []
    for _ in range(15):
        examples.append(TrainingExample(1, 0, 25.0, 1, 0.01, 0.5, 2, 1))
        examples.append(TrainingExample(0, 1, 75.0, 0, 0.01, -0.5, 2, 0))

    preview = predict(_features(), examples)
    assert preview.sample_count == 30
    assert preview.model_status == "en_apprentissage"
    # Le modele a quand meme pu s'entrainer (motif separable), la prediction existe,
    # seul le STATUT change - c'est precisement le point demande (afficher quand meme,
    # mais coloré differemment).
    assert preview.probability_up is not None
