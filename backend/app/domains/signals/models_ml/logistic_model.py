"""
Modele statistique V2 : regression logistique, comparee a la baseline de
regles (docs/10, docs/11).

Regle de gouvernance non negociable : ce modele n'est JAMAIS utilise pour
produire le signal officiel tant qu'il n'a pas ete prouve superieur a la
baseline par backtesting (docs/11). Il est expose en parallele, sous forme
d'"apercu" (`ml_preview`), avec un statut explicite :
- 'en_apprentissage' : moins de MIN_TRAINING_SAMPLES exemples disponibles -
  le resultat est affiche a titre indicatif seulement (a colorer differemment
  cote frontend), jamais comme un signal fiable.
- 'fiable' : le seuil est atteint - toujours pas le signal officiel, mais un
  second avis dont la fiabilite statistique minimale est desormais plausible.

Entrainement a la volee (pas de modele serialise sur disque) : au volume de
donnees actuel, reentrainer a chaque appel est instantane. A revisiter
seulement si ca devient mesurablement lent (meme principe de simplicite que
le reste du projet, docs/03).
"""
from dataclasses import dataclass

import numpy as np
from sklearn.linear_model import LogisticRegression

from app.domains.signals.features import SignalFeatures
from app.domains.signals.training import TrainingExample

ENGINE_VERSION = "logistic_v1"

# Seuil de maturite du modele. Volontairement bas pour un MVP (un vrai modele
# de production viserait plutot plusieurs centaines d'exemples) - la valeur
# est un parametre ajustable, pas une verite figee (meme philosophie que les
# poids du moteur de regles, docs/11).
MIN_TRAINING_SAMPLES = 50

# Minimum absolu pour meme tenter un entrainement (en dessous, sklearn produit
# un modele instable/non significatif, autant ne pas essayer).
_MIN_FIT_SAMPLES = 10

_FEATURE_NAMES = [
    "trend_up",
    "trend_down",
    "rsi_14",
    "macd_bullish",
    "volatility_20d",
    "news_sentiment",
    "news_article_count",
]


@dataclass
class MLPreview:
    engine_version: str
    model_status: str  # 'en_apprentissage' | 'fiable'
    sample_count: int
    min_required_samples: int
    probability_up: float | None
    final_signal: str | None
    explanation: str


def _example_to_vector(example: TrainingExample) -> list[float]:
    return [
        example.trend_up,
        example.trend_down,
        example.rsi_14,
        example.macd_bullish,
        example.volatility_20d,
        example.news_sentiment,
        example.news_article_count,
    ]


def _signal_features_to_vector(features: SignalFeatures) -> list[float]:
    return [
        1 if features.trend_direction == "up" else 0,
        1 if features.trend_direction == "down" else 0,
        features.rsi_14 if features.rsi_14 is not None else 50.0,
        1 if features.macd_cross == "bullish" else 0,
        features.volatility_20d if features.volatility_20d is not None else 0.0,
        features.news_sentiment,
        float(features.news_article_count),
    ]


def train_model(examples: list[TrainingExample]) -> LogisticRegression | None:
    if len(examples) < _MIN_FIT_SAMPLES:
        return None
    X = np.array([_example_to_vector(e) for e in examples])
    y = np.array([e.label for e in examples])
    if len(set(y.tolist())) < 2:
        return None  # une seule classe observee -> rien a apprendre de fiable
    model = LogisticRegression(max_iter=1000)
    model.fit(X, y)
    return model


def _insufficient_data_preview(sample_count: int) -> MLPreview:
    return MLPreview(
        engine_version=ENGINE_VERSION,
        model_status="en_apprentissage",
        sample_count=sample_count,
        min_required_samples=MIN_TRAINING_SAMPLES,
        probability_up=None,
        final_signal=None,
        explanation=(
            f"Pas encore assez de donnees pour entrainer un modele fiable "
            f"({sample_count}/{MIN_TRAINING_SAMPLES} exemples). Ce resultat est indicatif "
            f"uniquement et ne doit pas etre interprete comme un signal."
        ),
    )


def predict(features: SignalFeatures, examples: list[TrainingExample]) -> MLPreview:
    sample_count = len(examples)
    model = train_model(examples)
    if model is None:
        return _insufficient_data_preview(sample_count)

    vector = np.array([_signal_features_to_vector(features)])
    probability_up = float(model.predict_proba(vector)[0][1])

    if probability_up >= 0.6:
        final_signal = "achat_speculatif"
    elif probability_up >= 0.5:
        final_signal = "surveillance"
    elif probability_up <= 0.4:
        final_signal = "prudence"
    else:
        final_signal = "neutre"

    coefficients = dict(zip(_FEATURE_NAMES, model.coef_[0].tolist()))
    dominant_feature = max(coefficients, key=lambda k: abs(coefficients[k]))
    model_status = "fiable" if sample_count >= MIN_TRAINING_SAMPLES else "en_apprentissage"

    prefix = (
        "Modele statistique (fiabilite suffisante)"
        if model_status == "fiable"
        else f"Modele statistique (encore en apprentissage, {sample_count}/{MIN_TRAINING_SAMPLES} exemples)"
    )
    explanation = (
        f"{prefix} : probabilite de rendement positif estimee a {probability_up:.0%} "
        f"sur {sample_count} exemples d'entrainement. Facteur le plus influent : '{dominant_feature}'."
    )

    return MLPreview(
        engine_version=ENGINE_VERSION,
        model_status=model_status,
        sample_count=sample_count,
        min_required_samples=MIN_TRAINING_SAMPLES,
        probability_up=probability_up,
        final_signal=final_signal,
        explanation=explanation,
    )
