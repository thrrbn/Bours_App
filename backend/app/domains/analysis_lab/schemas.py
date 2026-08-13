import uuid
from datetime import datetime

from pydantic import BaseModel

# Phase 3 (31/07/2026) : modeles deja implementes derriere le job asynchrone
# (voir jobs/deep_training_job.py::_TRAINERS) - un GET /train-deep avec un
# model_name absent de cette liste echoue explicitement (422) plutot que de
# creer un job qui finira de toute facon en statut 'failed'.
DEEP_MODEL_NAMES = ("lstm",)

from app.domains.assets.schemas import AssetRead

DISCLAIMER = (
    "Bac a sable pedagogique - ces predictions (Random Forest, XGBoost, ARIMA) ne sont JAMAIS "
    "utilisees comme signal officiel, ne modifient jamais le portefeuille virtuel, et ne constituent "
    "en aucun cas un conseil d'investissement. Objectif : apprendre l'analyse technique et comparer "
    "des approches classiques au moteur de regles explicable du produit."
)


class FeatureSnapshotRead(BaseModel):
    """Derniere valeur connue de chaque indicateur - vue brute pour comprendre
    'sur quelle base' un modele calcule, sans filtre."""

    asset: AssetRead
    as_of_date: str
    features: dict[str, float | None]
    feature_count: int


class AdjustableIndicatorInfo(BaseModel):
    """
    13/08/2026 (laboratoire d'indicateurs, voir feature_engineering.py::
    ADJUSTABLE_INDICATORS) : decrit un indicateur recalculable a la demande -
    de quoi construire les champs de parametres cote UI sans dupliquer le
    registre en dur dans le frontend.
    """

    key: str
    label: str
    default_params: dict[str, float]


class IndicatorRecomputeRequest(BaseModel):
    """Parametres a appliquer, PARTIELS (voir compute_adjustable_indicator) -
    tout champ omis retombe sur le defaut de l'indicateur."""

    params: dict[str, float] = {}


class IndicatorRecomputeRead(BaseModel):
    indicator: str
    as_of_date: str
    params_used: dict[str, float]
    values: dict[str, float | None]


class ModelResultRead(BaseModel):
    model_name: str
    model_status: str
    sample_count: int
    min_required_samples: int
    probability_up: float | None
    predicted_direction: str | None
    explanation: str
    validation_status: str
    train_accuracy: float | None
    validation_accuracy: float | None
    validation_sample_count: int
    feature_importance: dict[str, float]
    # Comparaison au moteur reel (calcule cote service.py, pas dans le modele
    # lui-meme - c'est un jugement relatif au contexte de comparaison, pas une
    # propriete intrinseque du modele) : None si le moteur reel n'a pas encore
    # de signal calcule pour cet actif/horizon, ou si le modele est encore
    # 'en_apprentissage'/'indisponible'.
    agrees_with_real_signal: bool | None = None


class RealSignalSummaryRead(BaseModel):
    """Resume du signal REEL deja calcule par le moteur de regles (voir
    domaine signals) - jamais recalcule ici, uniquement lu pour comparaison."""

    final_signal: str
    technical_score: float
    news_score: float
    risk_score: float
    confidence_score: float
    computed_at: datetime


class AssetComparisonRead(BaseModel):
    asset: AssetRead
    horizon: str
    real_signal: RealSignalSummaryRead | None
    models: list[ModelResultRead]
    disclaimer: str = DISCLAIMER


class PortfolioComparisonRead(BaseModel):
    horizon: str
    comparisons: list[AssetComparisonRead]
    errors: list[dict]
    disclaimer: str = DISCLAIMER


class TrainingJobCreate(BaseModel):
    """Phase 3 (31/07/2026) - lance un entrainement asynchrone (voir
    jobs/deep_training_job.py). `model_name` doit figurer dans DEEP_MODEL_NAMES
    ('lstm' pour l'instant - gru/transformer a venir)."""

    model_name: str = "lstm"
    horizon: str = "medium"


class TrainingJobRead(BaseModel):
    id: uuid.UUID
    asset_id: uuid.UUID
    model_name: str
    horizon: str
    status: str  # 'pending' | 'running' | 'completed' | 'failed'
    result: ModelResultRead | None = None
    error_message: str | None = None
    created_at: datetime
    completed_at: datetime | None = None
    disclaimer: str = DISCLAIMER
