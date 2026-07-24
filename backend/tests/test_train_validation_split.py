"""
Tests Etape 20 : split train/validation chronologique du modele ML, pour
detecter le surapprentissage plutot que d'entrainer/predire sur 100% des
donnees sans jamais verifier la generalisation (docs/10, docs/11).
"""
from datetime import datetime, timedelta, timezone

from app.domains.signals.models_ml.logistic_model import evaluate_holdout
from app.domains.signals.training import TrainingExample, chronological_split


def _dated_example(days_ago: int, trend_up: int, label: int) -> TrainingExample:
    computed_at = datetime.now(timezone.utc) - timedelta(days=days_ago)
    return TrainingExample(
        trend_up=trend_up,
        trend_down=1 - trend_up,
        rsi_14=25.0 if trend_up else 75.0,
        macd_bullish=trend_up,
        volatility_20d=0.01,
        news_sentiment=0.5 if trend_up else -0.5,
        news_article_count=2,
        label=label,
        computed_at=computed_at,
    )


def test_chronological_split_keeps_oldest_in_train_and_newest_in_validation():
    # days_ago decroissant -> le premier cree est le plus ancien
    examples = [_dated_example(days_ago=100 - i, trend_up=1, label=1) for i in range(20)]
    train, validation = chronological_split(examples, validation_fraction=0.2)
    assert len(train) == 16
    assert len(validation) == 4
    # Le plus ancien (days_ago le plus grand) doit etre en train, pas en validation.
    oldest = examples[0]
    newest = examples[-1]
    assert oldest in train
    assert newest in validation


def test_chronological_split_handles_missing_dates_without_crashing():
    examples = [
        TrainingExample(1, 0, 25.0, 1, 0.01, 0.5, 2, 1),  # computed_at=None par defaut
        TrainingExample(0, 1, 75.0, 0, 0.01, -0.5, 2, 0),
    ]
    train, validation = chronological_split(examples, validation_fraction=0.5)
    assert len(train) + len(validation) == 2


def test_evaluate_holdout_insufficient_when_too_few_examples_per_side():
    examples = [_dated_example(days_ago=30 - i, trend_up=i % 2, label=i % 2) for i in range(10)]
    metrics = evaluate_holdout(examples, validation_fraction=0.2)
    assert metrics.status == "insuffisant"
    assert metrics.train_accuracy is None
    assert metrics.validation_accuracy is None


def test_evaluate_holdout_ok_with_separable_pattern_and_enough_samples():
    # Motif parfaitement separable et stable dans le temps : le modele
    # entraine sur le passe doit aussi bien predire sur la validation
    # recente -> precision train ~ precision validation ~ 100%, pas de gap.
    examples = []
    for i in range(60):
        examples.append(_dated_example(days_ago=200 - i * 2, trend_up=1, label=1))
        examples.append(_dated_example(days_ago=199 - i * 2, trend_up=0, label=0))

    metrics = evaluate_holdout(examples, validation_fraction=0.2)
    assert metrics.status == "ok"
    assert metrics.train_accuracy is not None
    assert metrics.validation_accuracy is not None
    assert metrics.train_accuracy > 0.9
    assert metrics.validation_accuracy > 0.9
    assert abs(metrics.overfitting_gap) < 0.2


def test_evaluate_holdout_insufficient_when_train_side_has_single_class():
    # Le groupe le plus ANCIEN (donc entierement dans le train apres split,
    # puisqu'il est plus nombreux que la taille du train) ne contient qu'une
    # seule classe -> rien d'entrainable sur ce cote, meme si le total est grand.
    old_group = [_dated_example(days_ago=200 - i, trend_up=1, label=1) for i in range(70)]
    recent_group = [_dated_example(days_ago=20 - i, trend_up=0, label=0) for i in range(10)]
    examples = old_group + recent_group  # 80 au total, train = 64 les plus anciens (tous dans old_group)
    metrics = evaluate_holdout(examples, validation_fraction=0.2)
    assert metrics.status == "insuffisant"
