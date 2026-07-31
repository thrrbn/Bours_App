"""
Tests des wrappers de modeles legers du bac a sable pedagogique
(analysis_lab/models.py, 31/07/2026 - voir docs/STACK.md).

Aucun acces DB : donnees synthetiques en memoire, meme convention que
test_analysis_lab_features.py et tests/test_signals_engine.py (tests purs sur
signals/models_ml/logistic_model.py, dont ce module reprend le style).
"""
import numpy as np
import pandas as pd
import pytest

from app.domains.analysis_lab.models import (
    MIN_TRAINING_SAMPLES,
    ModelResult,
    _MIN_FIT_SAMPLES,
    chronological_split_arrays,
    predict_arima,
    predict_ensemble,
    predict_prophet,
    predict_random_forest,
    predict_xgboost,
)


def _separable_dataset(n: int = 200, seed: int = 0):
    """Dataset synthetique ou la feature 0 determine presque parfaitement le
    label -> les modeles doivent apprendre facilement (haute accuracy)."""
    rng = np.random.default_rng(seed)
    dates = pd.date_range("2024-01-01", periods=n, freq="D")
    feature0 = rng.normal(0, 1, n)
    noise = rng.normal(0, 0.1, n)
    y = (feature0 + noise > 0).astype(int)
    X = np.column_stack([feature0, rng.normal(0, 1, n)])
    current_features = np.array([1.0, 0.0])  # feature0 fortement positive -> devrait predire "hausse"
    return X, y, dates, current_features


def test_chronological_split_preserves_order_and_fraction():
    dates = pd.to_datetime([f"2024-01-{d:02d}" for d in range(1, 21)])
    # Melange volontaire l'ordre d'entree pour verifier que le tri par date est bien applique.
    shuffle = np.random.default_rng(1).permutation(20)
    X = np.arange(20).reshape(-1, 1)[shuffle]
    y = np.arange(20)[shuffle]
    shuffled_dates = dates[shuffle]

    X_train, y_train, X_val, y_val = chronological_split_arrays(X, y, shuffled_dates, validation_fraction=0.2)

    assert len(X_train) == 16
    assert len(X_val) == 4
    # Une fois retries par date, y doit etre strictement croissant (0..19 dans l'ordre).
    assert list(y_train) == list(range(16))
    assert list(y_val) == list(range(16, 20))


def test_random_forest_learns_separable_pattern_with_high_validation_accuracy():
    feature_names = ["feature0", "feature1"]
    X, y, dates, current_features = _separable_dataset()
    result = predict_random_forest(feature_names, X, y, dates, current_features)

    assert result.model_status == "fiable"
    assert result.sample_count == 200
    assert result.validation_status == "ok"
    assert result.validation_accuracy > 0.8
    assert result.predicted_direction in ("hausse", "baisse")
    assert result.probability_up is not None and 0.0 <= result.probability_up <= 1.0
    assert "feature0" in result.feature_importance


def test_xgboost_learns_separable_pattern_with_high_validation_accuracy():
    feature_names = ["feature0", "feature1"]
    X, y, dates, current_features = _separable_dataset()
    result = predict_xgboost(feature_names, X, y, dates, current_features)

    assert result.model_status == "fiable"
    assert result.validation_status == "ok"
    assert result.validation_accuracy > 0.8
    assert result.predicted_direction in ("hausse", "baisse")


def test_random_forest_returns_en_apprentissage_below_min_fit_samples():
    feature_names = ["feature0"]
    X = np.arange(_MIN_FIT_SAMPLES - 1).reshape(-1, 1).astype(float)
    y = np.array([0, 1] * ((_MIN_FIT_SAMPLES - 1) // 2 + 1))[: _MIN_FIT_SAMPLES - 1]
    dates = pd.date_range("2024-01-01", periods=_MIN_FIT_SAMPLES - 1, freq="D")
    current_features = np.array([0.0])

    result = predict_random_forest(feature_names, X, y, dates, current_features)

    assert result.model_status == "en_apprentissage"
    assert result.probability_up is None
    assert result.predicted_direction is None


def test_random_forest_returns_en_apprentissage_with_single_class():
    # Assez d'echantillons mais une seule classe observee -> impossible a entrainer.
    feature_names = ["feature0"]
    n = 60
    X = np.arange(n).reshape(-1, 1).astype(float)
    y = np.zeros(n, dtype=int)  # une seule classe
    dates = pd.date_range("2024-01-01", periods=n, freq="D")
    current_features = np.array([0.0])

    result = predict_random_forest(feature_names, X, y, dates, current_features)

    assert result.model_status == "en_apprentissage"


def test_random_forest_marked_en_apprentissage_below_min_training_samples_even_if_fittable():
    # Entre _MIN_FIT_SAMPLES (10) et MIN_TRAINING_SAMPLES (50) : le modele
    # s'entraine (assez pour fit) mais reste marque "en_apprentissage" (pas
    # encore "fiable") - verifie la distinction entre les deux seuils.
    feature_names = ["feature0", "feature1"]
    X, y, dates, current_features = _separable_dataset(n=30)
    result = predict_random_forest(feature_names, X, y, dates, current_features)

    assert result.sample_count == 30
    assert result.sample_count < MIN_TRAINING_SAMPLES
    assert result.model_status == "en_apprentissage"
    # Contrairement au cas "pas assez pour fit", ici une prediction existe bel et bien.
    assert result.predicted_direction is not None


def test_predict_arima_returns_en_apprentissage_below_min_training_samples():
    close = pd.Series(np.linspace(100, 110, MIN_TRAINING_SAMPLES - 1))
    result = predict_arima(close, forward_days=5)

    assert result.model_status == "en_apprentissage"
    assert result.predicted_direction is None
    assert result.sample_count == MIN_TRAINING_SAMPLES - 1


def test_predict_arima_predicts_hausse_on_clear_uptrend():
    # Serie fortement et regulierement croissante -> ARIMA(5,1,0) devrait
    # raisonnablement prolonger la tendance a la hausse.
    n = 150
    close = pd.Series(100 + np.arange(n) * 0.5 + np.random.default_rng(2).normal(0, 0.05, n))
    result = predict_arima(close, forward_days=5)

    assert result.model_status == "fiable"
    assert result.predicted_direction == "hausse"
    assert result.probability_up is None  # ARIMA ne produit pas de probabilite (regression, pas classification)
    assert result.validation_status == "ok"
    assert result.validation_accuracy is not None


# --- Prophet (Phase 2, 31/07/2026) ---------------------------------------


def test_predict_prophet_returns_en_apprentissage_below_min_training_samples():
    close = pd.Series(
        np.linspace(100, 110, MIN_TRAINING_SAMPLES - 1),
        index=pd.date_range("2024-01-01", periods=MIN_TRAINING_SAMPLES - 1, freq="D"),
    )
    result = predict_prophet(close, forward_days=5)

    assert result.model_status == "en_apprentissage"
    assert result.predicted_direction is None
    assert result.sample_count == MIN_TRAINING_SAMPLES - 1


def test_predict_prophet_predicts_hausse_on_clear_uptrend_and_needs_dated_index():
    n = 150
    close = pd.Series(
        100 + np.arange(n) * 0.5 + np.random.default_rng(4).normal(0, 0.05, n),
        index=pd.date_range("2024-01-01", periods=n, freq="D"),
    )
    result = predict_prophet(close, forward_days=5)

    assert result.model_status == "fiable"
    assert result.predicted_direction == "hausse"
    assert result.probability_up is None  # Prophet ne produit pas de probabilite (regression, pas classification)
    assert result.validation_status == "ok"
    assert result.validation_accuracy is not None
    assert 0.0 <= result.validation_accuracy <= 1.0


# --- Ensemble (Phase 2, 31/07/2026) --------------------------------------


def _model(name, status="fiable", direction="hausse", prob=None):
    return ModelResult(
        model_name=name,
        model_status=status,
        sample_count=100,
        min_required_samples=MIN_TRAINING_SAMPLES,
        probability_up=prob,
        predicted_direction=direction,
        explanation="x",
    )


def test_predict_ensemble_majority_vote_wins():
    models = [
        _model("random_forest", direction="hausse", prob=0.7),
        _model("xgboost", direction="hausse", prob=0.65),
        _model("arima", direction="hausse"),
        _model("prophet", direction="baisse"),
    ]
    result = predict_ensemble(models)

    assert result.predicted_direction == "hausse"
    assert result.model_status == "fiable"


def test_predict_ensemble_tie_broken_by_average_probability():
    # 2 votes hausse (avec probabilites), 2 votes baisse (sans probabilite,
    # ARIMA/Prophet) - egalite de voix, tranchee par la moyenne des
    # probabilites disponibles (0.675 >= 0.5 -> hausse).
    models = [
        _model("random_forest", direction="hausse", prob=0.7),
        _model("xgboost", direction="hausse", prob=0.65),
        _model("arima", direction="baisse"),
        _model("prophet", direction="baisse"),
    ]
    result = predict_ensemble(models)

    assert result.predicted_direction == "hausse"
    assert result.probability_up == pytest.approx(0.675)


def test_predict_ensemble_status_reflects_reliable_majority():
    models = [
        _model("random_forest", status="en_apprentissage", direction="hausse"),
        _model("xgboost", status="en_apprentissage", direction="hausse"),
        _model("arima", status="fiable", direction="baisse"),
    ]
    result = predict_ensemble(models)

    # Seul 1/3 des votants est "fiable" -> l'ensemble reste "en_apprentissage".
    assert result.model_status == "en_apprentissage"


def test_predict_ensemble_returns_en_apprentissage_when_no_model_has_a_prediction():
    models = [
        _model("random_forest", status="en_apprentissage", direction=None),
        _model("arima", status="en_apprentissage", direction=None),
    ]
    result = predict_ensemble(models)

    assert result.model_status == "en_apprentissage"
    assert result.predicted_direction is None
