"""
Phase 3 (31/07/2026, voir docs/STACK.md) - premier modele sequentiel du
catalogue original de l'utilisateur (LSTM), execute de maniere ASYNCHRONE
(voir jobs/deep_training_job.py + db_models.py::TrainingJob) car
l'entrainement, meme court, est trop long pour un appel HTTP synchrone comme
predict_random_forest/predict_xgboost/predict_arima/predict_prophet
(models.py, Phases 1/2).

IMPORTANT - limite de verification connue : ce fichier utilise PyTorch, une
dependance que le sandbox de developpement utilise pour ecrire ce code n'a
pas pu installer completement (le wheel CPU-only se telecharge depuis un
index separe, injoignable depuis ce sandbox ; le wheel GPU par defaut de PyPI
fait plusieurs centaines de Mo et n'a pas pu etre telecharge dans les
contraintes de temps disponibles). Contrairement a tout le reste de cette
session, ce module n'a donc PAS ete execute reellement avant d'etre livre -
seule la relecture attentive du code et de l'API PyTorch garantit sa
correction. A verifier en priorite avec `pytest backend/tests/test_analysis_lab_deep_models.py`
une fois l'image Docker reconstruite avec `torch` installe (voir
requirements.txt/Dockerfile) - le test est ecrit avec
`pytest.importorskip("torch")` pour ne jamais faire echouer la suite tant que
ce n'est pas fait.

Reutilise volontairement `chronological_split_arrays` de `analysis_lab.models`
(import intra-domaine, pas une exception au principe d'isolation qui ne
concerne que la production - signals/portfolio/backtests).
"""
import logging

import numpy as np
import pandas as pd

from app.domains.analysis_lab.models import MIN_TRAINING_SAMPLES, ModelResult, chronological_split_arrays

logger = logging.getLogger(__name__)

try:
    import torch
    from torch import nn

    TORCH_AVAILABLE = True
except ImportError:  # pragma: no cover - depend de l'installation de torch (voir Dockerfile)
    TORCH_AVAILABLE = False

# Nombre de jours de features consecutifs par sequence d'entrainement - choix
# pragmatique (pas une regle absolue) : assez long pour capturer une
# dynamique de quelques semaines de bourse, assez court pour laisser assez de
# sequences d'entrainement avec seulement ~500 barres d'historique max (voir
# service.py::_load_ohlcv_dataframe).
SEQUENCE_LENGTH = 20
_MIN_FIT_SEQUENCES = 15
_HIDDEN_SIZE = 16
_EPOCHS = 30
_LEARNING_RATE = 1e-3


def build_sequences(
    X: np.ndarray, y: np.ndarray, dates: pd.DatetimeIndex, sequence_length: int = SEQUENCE_LENGTH
) -> tuple[np.ndarray, np.ndarray, pd.DatetimeIndex]:
    """
    Transforme la matrice "une ligne = un jour" (le format deja utilise par
    predict_random_forest/predict_xgboost) en sequences glissantes "sequence_length
    jours consecutifs -> label du dernier jour de la sequence", le format
    attendu par un `nn.LSTM` (batch_first=True : shape (n_sequences,
    sequence_length, n_features)). Suppose X/y/dates deja tries
    chronologiquement (le cas ici, voir service.py::_run_models).
    """
    n_rows = len(X)
    if n_rows < sequence_length:
        return np.empty((0, sequence_length, X.shape[1] if X.ndim > 1 else 0)), np.empty(0), dates[:0]

    n_sequences = n_rows - sequence_length + 1
    X_seq = np.stack([X[i : i + sequence_length] for i in range(n_sequences)])
    y_seq = y[sequence_length - 1 :]
    dates_seq = dates[sequence_length - 1 :]
    return X_seq, y_seq, dates_seq


if TORCH_AVAILABLE:

    class _LSTMClassifier(nn.Module):
        """LSTM -> dernier pas de temps -> couche lineaire -> logit unique
        (hausse/baisse). `BCEWithLogitsLoss` cote entrainement s'occupe du
        sigmoid, pas la peine de l'appliquer ici (logits bruts en sortie)."""

        def __init__(self, n_features: int, hidden_size: int = _HIDDEN_SIZE):
            super().__init__()
            self.lstm = nn.LSTM(input_size=n_features, hidden_size=hidden_size, num_layers=1, batch_first=True)
            self.head = nn.Linear(hidden_size, 1)

        def forward(self, x):
            output, _ = self.lstm(x)
            last_step = output[:, -1, :]
            return self.head(last_step).squeeze(-1)


def _standardize(train_2d: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    """Moyenne/ecart-type calcules UNIQUEMENT sur le train (jamais sur la
    validation ni sur la sequence courante a predire) - evite la fuite de
    donnees classique lors de la normalisation."""
    mean = train_2d.mean(axis=0)
    std = train_2d.std(axis=0)
    std[std == 0] = 1.0
    return mean, std


def _apply_standardize(X_seq: np.ndarray, mean: np.ndarray, std: np.ndarray) -> np.ndarray:
    return (X_seq - mean) / std


def _train_lstm_model(X_train: np.ndarray, y_train: np.ndarray, n_features: int) -> "_LSTMClassifier":
    torch.manual_seed(42)
    model = _LSTMClassifier(n_features=n_features)
    optimizer = torch.optim.Adam(model.parameters(), lr=_LEARNING_RATE)
    loss_fn = nn.BCEWithLogitsLoss()

    X_tensor = torch.tensor(X_train, dtype=torch.float32)
    y_tensor = torch.tensor(y_train, dtype=torch.float32)

    model.train()
    for _ in range(_EPOCHS):
        optimizer.zero_grad()
        logits = model(X_tensor)
        loss = loss_fn(logits, y_tensor)
        loss.backward()
        optimizer.step()
    return model


def _accuracy(model: "_LSTMClassifier", X: np.ndarray, y: np.ndarray) -> float:
    model.eval()
    with torch.no_grad():
        logits = model(torch.tensor(X, dtype=torch.float32))
        predictions = (torch.sigmoid(logits) >= 0.5).float().numpy()
    return float(np.mean(predictions == y))


def _insufficient(reason: str, sample_count: int = 0) -> ModelResult:
    return ModelResult(
        model_name="lstm",
        model_status="en_apprentissage",
        sample_count=sample_count,
        min_required_samples=MIN_TRAINING_SAMPLES,
        probability_up=None,
        predicted_direction=None,
        explanation=reason,
    )


def train_and_predict_lstm(
    feature_names: list[str], X: np.ndarray, y: np.ndarray, dates: pd.DatetimeIndex, current_features: np.ndarray
) -> ModelResult:
    """
    Meme contrat (feature_names, X, y, dates, current_features) que
    predict_random_forest/predict_xgboost (models.py) - permet de reutiliser
    exactement les memes tableaux deja construits par service.py, seule la
    mise en sequence (build_sequences) differe. Execute en tache de fond
    (jobs/deep_training_job.py), jamais dans le thread d'une requete HTTP.
    """
    if not TORCH_AVAILABLE:  # pragma: no cover - depend de l'environnement d'execution
        return ModelResult(
            model_name="lstm",
            model_status="indisponible",
            sample_count=len(y),
            min_required_samples=MIN_TRAINING_SAMPLES,
            probability_up=None,
            predicted_direction=None,
            explanation="PyTorch n'est pas installe dans cet environnement (voir requirements.txt/Dockerfile).",
        )

    sample_count = len(y)
    if sample_count < MIN_TRAINING_SAMPLES:
        return _insufficient(
            f"Pas encore assez de jours d'historique pour un LSTM ({sample_count}/{MIN_TRAINING_SAMPLES}).",
            sample_count,
        )

    X_seq, y_seq, dates_seq = build_sequences(X, y, dates, SEQUENCE_LENGTH)
    if len(y_seq) < _MIN_FIT_SEQUENCES or len(set(y_seq.tolist())) < 2:
        return _insufficient(
            f"Pas encore assez de sequences de {SEQUENCE_LENGTH} jours pour entrainer un LSTM "
            f"({len(y_seq)} sequences disponibles, {_MIN_FIT_SEQUENCES} minimum), ou une seule classe observee.",
            sample_count,
        )

    X_train, y_train, X_val, y_val = chronological_split_arrays(X_seq, y_seq, dates_seq)

    validation_status = "insuffisant"
    train_accuracy = validation_accuracy = None
    if len(y_val) >= 10 and len(y_train) >= 10 and len(set(y_train.tolist())) >= 2:
        train_mean, train_std = _standardize(X_train.reshape(-1, X_train.shape[-1]))
        X_train_scaled = _apply_standardize(X_train, train_mean, train_std)
        X_val_scaled = _apply_standardize(X_val, train_mean, train_std)

        diagnostic_model = _train_lstm_model(X_train_scaled, y_train, n_features=X_train.shape[-1])
        train_accuracy = round(_accuracy(diagnostic_model, X_train_scaled, y_train), 4)
        validation_accuracy = round(_accuracy(diagnostic_model, X_val_scaled, y_val), 4)
        validation_status = "ok"

    # Reentrainement final sur 100% des sequences disponibles (meme
    # philosophie que Random Forest/XGBoost/ARIMA/Prophet : le split ne sert
    # qu'au diagnostic de surapprentissage, jamais a amputer le modele final
    # d'exemples recents).
    final_mean, final_std = _standardize(X_seq.reshape(-1, X_seq.shape[-1]))
    X_seq_scaled = _apply_standardize(X_seq, final_mean, final_std)
    final_model = _train_lstm_model(X_seq_scaled, y_seq, n_features=X_seq.shape[-1])

    # Derniere sequence disponible pour la prediction : les (SEQUENCE_LENGTH-1)
    # derniers jours "valides" de X + le jour courant (current_features, deja
    # impute a 0 pour les NaN par service.py::_run_models - meme convention
    # que pour Random Forest/XGBoost).
    last_window = np.vstack([X[-(SEQUENCE_LENGTH - 1) :], current_features.reshape(1, -1)])
    last_window_scaled = _apply_standardize(last_window[np.newaxis, :, :], final_mean, final_std)
    final_model.eval()
    with torch.no_grad():
        logit = final_model(torch.tensor(last_window_scaled, dtype=torch.float32))
        probability_up = float(torch.sigmoid(logit).item())
    predicted_direction = "hausse" if probability_up >= 0.5 else "baisse"

    model_status = "fiable" if sample_count >= MIN_TRAINING_SAMPLES else "en_apprentissage"
    prefix = (
        f"LSTM (fiabilite suffisante)"
        if model_status == "fiable"
        else f"LSTM (encore en apprentissage, {sample_count}/{MIN_TRAINING_SAMPLES} jours)"
    )
    explanation = (
        f"{prefix} : probabilite de hausse estimee a {probability_up:.0%} sur {len(y_seq)} sequences de "
        f"{SEQUENCE_LENGTH} jours."
    )
    if validation_status == "ok":
        gap = round(train_accuracy - validation_accuracy, 4)
        explanation += (
            f" Train/validation : {train_accuracy:.0%} vs {validation_accuracy:.0%} "
            f"(ecart {gap:+.0%} - un grand ecart positif indiquerait du surapprentissage)."
        )
    else:
        explanation += " Historique de validation insuffisant pour verifier le surapprentissage."

    return ModelResult(
        model_name="lstm",
        model_status=model_status,
        sample_count=sample_count,
        min_required_samples=MIN_TRAINING_SAMPLES,
        probability_up=round(probability_up, 4),
        predicted_direction=predicted_direction,
        explanation=explanation,
        validation_status=validation_status,
        train_accuracy=train_accuracy,
        validation_accuracy=validation_accuracy,
        validation_sample_count=len(y_val) if validation_status == "ok" else 0,
        feature_importance={},  # Pas d'equivalent direct a .feature_importances_ pour un LSTM - hors scope ici.
    )
