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
from app.domains.signals.training import TrainingExample, chronological_split

ENGINE_VERSION = "logistic_v1"

# Seuil de maturite du modele. Volontairement bas pour un MVP (un vrai modele
# de production viserait plutot plusieurs centaines d'exemples) - la valeur
# est un parametre ajustable, pas une verite figee (meme philosophie que les
# poids du moteur de regles, docs/11).
MIN_TRAINING_SAMPLES = 50

# Minimum absolu pour meme tenter un entrainement (en dessous, sklearn produit
# un modele instable/non significatif, autant ne pas essayer).
_MIN_FIT_SAMPLES = 10

# Etape 20 : minimum absolu par cote (train ET validation) pour qu'un
# split train/validation ait un sens statistique - en dessous, l'ecart
# train/validation observe serait du bruit, pas un vrai signal de
# surapprentissage.
_MIN_SPLIT_SAMPLES_PER_SIDE = 10
_VALIDATION_FRACTION = 0.2

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
    # Etape 20 : diagnostic de surapprentissage (train/validation). None tant
    # que l'historique est trop court pour un split fiable des deux cotes.
    validation_status: str = "insuffisant"  # 'insuffisant' | 'ok'
    train_accuracy: float | None = None
    validation_accuracy: float | None = None
    validation_sample_count: int = 0


@dataclass
class ValidationMetrics:
    status: str  # 'insuffisant' | 'ok'
    train_accuracy: float | None
    validation_accuracy: float | None
    train_sample_count: int
    validation_sample_count: int

    @property
    def overfitting_gap(self) -> float | None:
        """Ecart precision train - precision validation. Positif et grand = signe de surapprentissage."""
        if self.train_accuracy is None or self.validation_accuracy is None:
            return None
        return round(self.train_accuracy - self.validation_accuracy, 4)


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


def _accuracy(model: LogisticRegression, examples: list[TrainingExample]) -> float:
    X = np.array([_example_to_vector(e) for e in examples])
    y = np.array([e.label for e in examples])
    predictions = model.predict(X)
    return float(np.mean(predictions == y))


def evaluate_holdout(
    examples: list[TrainingExample], validation_fraction: float = _VALIDATION_FRACTION
) -> ValidationMetrics:
    """
    Etape 20 : entraine un modele UNIQUEMENT sur la portion "train" (passe)
    et mesure sa precision sur la portion "validation" (plus recente),
    jamais vue pendant l'entrainement. Un grand ecart train/validation
    (voir ValidationMetrics.overfitting_gap) signale un modele qui
    memorise le passe au lieu de generaliser - c'est la verification de
    fiabilite demandee en plus du simple comptage d'exemples.

    Ce split est purement diagnostique : le modele reellement utilise pour
    predire (voir predict() ci-dessous) est toujours reentraine sur 100% des
    donnees disponibles ensuite, pour ne pas gaspiller de signal en
    production - pratique standard (le split ne sert qu'a l'evaluation).
    """
    train_examples, validation_examples = chronological_split(examples, validation_fraction)

    if len(train_examples) < _MIN_SPLIT_SAMPLES_PER_SIDE or len(validation_examples) < _MIN_SPLIT_SAMPLES_PER_SIDE:
        return ValidationMetrics(
            status="insuffisant",
            train_accuracy=None,
            validation_accuracy=None,
            train_sample_count=len(train_examples),
            validation_sample_count=len(validation_examples),
        )

    model = train_model(train_examples)
    if model is None:
        # une seule classe dans le train -> rien d'entrainable, meme diagnostic
        return ValidationMetrics(
            status="insuffisant",
            train_accuracy=None,
            validation_accuracy=None,
            train_sample_count=len(train_examples),
            validation_sample_count=len(validation_examples),
        )

    train_accuracy = round(_accuracy(model, train_examples), 4)
    validation_accuracy = round(_accuracy(model, validation_examples), 4)

    return ValidationMetrics(
        status="ok",
        train_accuracy=train_accuracy,
        validation_accuracy=validation_accuracy,
        train_sample_count=len(train_examples),
        validation_sample_count=len(validation_examples),
    )


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

    validation = evaluate_holdout(examples)
    if validation.status == "ok":
        gap = validation.overfitting_gap
        explanation += (
            f" Verification train/validation : {validation.train_accuracy:.0%} de precision sur "
            f"l'entrainement vs {validation.validation_accuracy:.0%} sur les donnees les plus "
            f"recentes jamais vues (ecart {gap:+.0%} - un grand ecart positif indiquerait du "
            f"surapprentissage)."
        )
    else:
        explanation += " Historique encore trop court pour verifier le surapprentissage (train/validation)."

    return MLPreview(
        engine_version=ENGINE_VERSION,
        model_status=model_status,
        sample_count=sample_count,
        min_required_samples=MIN_TRAINING_SAMPLES,
        probability_up=probability_up,
        final_signal=final_signal,
        explanation=explanation,
        validation_status=validation.status,
        train_accuracy=validation.train_accuracy,
        validation_accuracy=validation.validation_accuracy,
        validation_sample_count=validation.validation_sample_count,
    )
