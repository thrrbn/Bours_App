"""Orchestration du domaine signals : features -> engine -> persistance -> presentation."""
import logging
import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import InsufficientDataError
from app.domains.compliance.guardrails import validate_signal_wording
from app.domains.signals import repository
from app.domains.signals.engine import generate_signal
from app.domains.signals.features import SignalFeatures, build_feature_vector
from app.domains.signals.models_ml import logistic_model
from app.domains.signals.schemas import ExplanationRead, MLPreviewRead, ScoreSet, SignalRead
from app.domains.signals.training import build_training_set

logger = logging.getLogger(__name__)


def _to_signal_read(signal, explanations, ml_preview: MLPreviewRead | None) -> SignalRead:
    return SignalRead(
        horizon=signal.horizon,
        computed_at=signal.computed_at,
        scores=ScoreSet(
            technical=float(signal.technical_score),
            news=float(signal.news_score),
            risk=float(signal.risk_score),
            confidence=float(signal.confidence_score),
        ),
        final_signal=signal.final_signal,
        engine_version=signal.engine_version,
        explanations=[
            ExplanationRead(
                component=exp.component,
                contribution_pct=float(exp.contribution_pct),
                text=exp.text_explanation,
                supporting_data=exp.supporting_data,
            )
            for exp in explanations
        ],
        ml_preview=ml_preview,
    )


async def _compute_ml_preview(db: AsyncSession, features: SignalFeatures) -> MLPreviewRead | None:
    """
    Calcule l'apercu du modele statistique V2, en parallele du signal officiel.
    Ne doit jamais faire echouer le calcul du signal principal : toute erreur
    ici (ex. scikit-learn indisponible, donnees corrompues) est loggee et
    aboutit simplement a l'absence de ml_preview, pas a une erreur HTTP.
    """
    try:
        examples = await build_training_set(db)
        preview = logistic_model.predict(features, examples)
        return MLPreviewRead(
            engine_version=preview.engine_version,
            model_status=preview.model_status,
            sample_count=preview.sample_count,
            min_required_samples=preview.min_required_samples,
            probability_up=preview.probability_up,
            final_signal=preview.final_signal,
            explanation=preview.explanation,
            validation_status=preview.validation_status,
            train_accuracy=preview.train_accuracy,
            validation_accuracy=preview.validation_accuracy,
            validation_sample_count=preview.validation_sample_count,
        )
    except Exception:
        logger.exception("Echec du calcul de l'apercu du modele statistique (ml_preview)")
        return None


async def compute_signal_for_asset(db: AsyncSession, asset_id: uuid.UUID, horizon: str) -> SignalRead:
    features = await build_feature_vector(db, asset_id, horizon)
    if features.price_history_days < 20:
        raise InsufficientDataError(
            f"Historique de prix insuffisant ({features.price_history_days} jours) pour calculer un signal fiable."
        )

    result = generate_signal(features)
    for component in result.components:
        validate_signal_wording(component.explanation)

    signal = await repository.save_signal(db, asset_id, horizon, result)
    explanations = await repository.get_explanations(db, signal.id)
    ml_preview = await _compute_ml_preview(db, features)
    return _to_signal_read(signal, explanations, ml_preview)


async def get_or_compute_signal(db: AsyncSession, asset_id: uuid.UUID, horizon: str) -> SignalRead:
    existing = await repository.get_latest_signal(db, asset_id, horizon)
    if existing is None:
        return await compute_signal_for_asset(db, asset_id, horizon)

    explanations = await repository.get_explanations(db, existing.id)

    # ml_preview reste "vivant" : meme pour un signal deja calcule, on
    # recalcule l'apercu du modele statistique a chaque lecture, car son
    # statut de maturite (nombre d'exemples disponibles) evolue dans le temps
    # independamment du moment ou le signal officiel a ete fige.
    features = await build_feature_vector(db, asset_id, existing.horizon)
    ml_preview = await _compute_ml_preview(db, features)
    return _to_signal_read(existing, explanations, ml_preview)
