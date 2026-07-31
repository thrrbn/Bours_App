"""
Tests du module LSTM asynchrone (Phase 3, 31/07/2026 - voir
analysis_lab/deep_models.py et docs/STACK.md).

IMPORTANT : `torch` n'a pas pu etre installe dans le sandbox utilise pour
ecrire ce module (voir le docstring en tete de deep_models.py) - les tests
qui entrainent reellement un LSTM utilisent `pytest.importorskip("torch")`
et seront donc SKIPPED tant que torch n'est pas installe (par exemple avant
le premier `docker compose up -d --build backend` reel de l'utilisateur qui
suit ce Dockerfile). Ils ne sont pas censes rester skip pour toujours -
executer `pytest tests/test_analysis_lab_deep_models.py -v` une fois torch
disponible pour une verification reelle (jamais faite avant livraison de ce
fichier).

`build_sequences()` est en revanche du pur numpy (aucune dependance a torch)
et est donc testee sans condition ci-dessous.
"""
import numpy as np
import pandas as pd
import pytest

from app.domains.analysis_lab.deep_models import SEQUENCE_LENGTH, TORCH_AVAILABLE, build_sequences

# IMPORTANT (bug evite) : `pytest.importorskip("torch")` au niveau du module
# sauterait TOUT le fichier (y compris les tests purs-numpy ci-dessous qui ne
# necessitent pas torch) des la collecte - on utilise donc un
# `skipif(not TORCH_AVAILABLE, ...)` par test, uniquement sur ceux qui
# entrainent reellement un modele.
requires_torch = pytest.mark.skipif(not TORCH_AVAILABLE, reason="torch non installe dans cet environnement")


def test_build_sequences_produces_expected_shape():
    n_rows, n_features = 50, 3
    X = np.arange(n_rows * n_features, dtype=float).reshape(n_rows, n_features)
    y = np.arange(n_rows) % 2
    dates = pd.date_range("2024-01-01", periods=n_rows, freq="D")

    X_seq, y_seq, dates_seq = build_sequences(X, y, dates, sequence_length=10)

    expected_n_sequences = n_rows - 10 + 1
    assert X_seq.shape == (expected_n_sequences, 10, n_features)
    assert y_seq.shape == (expected_n_sequences,)
    assert len(dates_seq) == expected_n_sequences


def test_build_sequences_preserves_chronological_windows():
    n_rows, n_features = 15, 2
    X = np.arange(n_rows * n_features, dtype=float).reshape(n_rows, n_features)
    y = np.arange(n_rows)
    dates = pd.date_range("2024-01-01", periods=n_rows, freq="D")

    X_seq, y_seq, dates_seq = build_sequences(X, y, dates, sequence_length=5)

    # La premiere sequence doit correspondre exactement aux 5 premieres lignes de X.
    assert np.array_equal(X_seq[0], X[0:5])
    # Le label de chaque sequence est celui du DERNIER jour de la fenetre (pas le premier).
    assert y_seq[0] == y[4]
    assert dates_seq[0] == dates[4]
    # Derniere sequence = 5 dernieres lignes.
    assert np.array_equal(X_seq[-1], X[-5:])
    assert y_seq[-1] == y[-1]


def test_build_sequences_returns_empty_when_not_enough_rows():
    X = np.zeros((5, 3))
    y = np.zeros(5)
    dates = pd.date_range("2024-01-01", periods=5, freq="D")

    X_seq, y_seq, dates_seq = build_sequences(X, y, dates, sequence_length=SEQUENCE_LENGTH)

    assert len(X_seq) == 0
    assert len(y_seq) == 0
    assert len(dates_seq) == 0


def test_train_and_predict_lstm_returns_indisponible_when_torch_missing(monkeypatch):
    from app.domains.analysis_lab import deep_models

    monkeypatch.setattr(deep_models, "TORCH_AVAILABLE", False)
    X = np.zeros((100, 3))
    y = np.array([0, 1] * 50)
    dates = pd.date_range("2024-01-01", periods=100, freq="D")
    current_features = np.zeros(3)

    result = deep_models.train_and_predict_lstm(["a", "b", "c"], X, y, dates, current_features)

    assert result.model_status == "indisponible"
    assert result.predicted_direction is None
    assert "PyTorch" in result.explanation


# --- Tests necessitant torch reellement installe (skip sinon, voir docstring) ---


def _separable_sequence_dataset(n_rows: int = 150, n_features: int = 4, seed: int = 0):
    """Meme esprit que test_analysis_lab_models.py::_separable_dataset, mais
    pour des sequences : la feature 0 du DERNIER jour de chaque sequence
    determine le label -> un LSTM correctement cable doit apprendre facilement."""
    rng = np.random.default_rng(seed)
    feature0 = rng.normal(0, 1, n_rows)
    y = (feature0 > 0).astype(int)
    X = np.column_stack([feature0] + [rng.normal(0, 1, n_rows) for _ in range(n_features - 1)])
    dates = pd.date_range("2024-01-01", periods=n_rows, freq="D")
    current_features = np.array([1.0] + [0.0] * (n_features - 1))
    return X, y, dates, current_features


@requires_torch
def test_train_and_predict_lstm_learns_separable_pattern():
    from app.domains.analysis_lab.models import MIN_TRAINING_SAMPLES
    from app.domains.analysis_lab.deep_models import train_and_predict_lstm

    X, y, dates, current_features = _separable_sequence_dataset(n_rows=max(150, MIN_TRAINING_SAMPLES + 30))
    result = train_and_predict_lstm(["f0", "f1", "f2", "f3"], X, y, dates, current_features)

    assert result.model_status == "fiable"
    assert result.predicted_direction in ("hausse", "baisse")
    assert result.probability_up is not None and 0.0 <= result.probability_up <= 1.0
    assert result.validation_status == "ok"
    assert result.validation_accuracy is not None


@requires_torch
def test_train_and_predict_lstm_returns_en_apprentissage_below_min_samples():
    from app.domains.analysis_lab.models import MIN_TRAINING_SAMPLES
    from app.domains.analysis_lab.deep_models import train_and_predict_lstm

    n = MIN_TRAINING_SAMPLES - 1
    X = np.zeros((n, 3))
    y = np.array([0, 1] * (n // 2 + 1))[:n]
    dates = pd.date_range("2024-01-01", periods=n, freq="D")
    current_features = np.zeros(3)

    result = train_and_predict_lstm(["a", "b", "c"], X, y, dates, current_features)

    assert result.model_status == "en_apprentissage"
    assert result.predicted_direction is None
