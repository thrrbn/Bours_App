"""
Job asynchrone de la Phase 3 du bac a sable pedagogique (31/07/2026, voir
docs/STACK.md) : entraine un modele sequentiel (LSTM pour l'instant, voir
domains/analysis_lab/deep_models.py) en tache de fond, hors du cycle de
requete HTTP - contrairement a Random Forest/XGBoost/ARIMA/Prophet (Phases
1/2, synchrones dans GET /compare), un LSTM prend trop longtemps a entrainer
pour un appel bloquant.

Declenche a la demande (POST /analysis-lab/{asset_id}/train-deep, voir
router.py) via `scheduler.add_job(..., trigger=DateTrigger(run_date=now))` -
PAS un job planifie recurrent comme ingest_prices_job/credit_dividends_job.
Meme pattern d'acces DB que les jobs existants (ouvre sa propre session,
AsyncSessionLocal) puisqu'il tourne hors du cycle de requete FastAPI.
"""
import logging
import uuid

from app.database import AsyncSessionLocal
from app.domains.analysis_lab import deep_models, job_repository, service
from app.domains.analysis_lab.models import ModelResult

logger = logging.getLogger(__name__)

_TRAINERS = {
    "lstm": deep_models.train_and_predict_lstm,
    # gru/transformer (Phase 3, suite) : a ajouter ici une fois valides sur le LSTM.
}


def _model_result_to_dict(result: ModelResult) -> dict:
    return {
        "model_name": result.model_name,
        "model_status": result.model_status,
        "sample_count": result.sample_count,
        "min_required_samples": result.min_required_samples,
        "probability_up": result.probability_up,
        "predicted_direction": result.predicted_direction,
        "explanation": result.explanation,
        "validation_status": result.validation_status,
        "train_accuracy": result.train_accuracy,
        "validation_accuracy": result.validation_accuracy,
        "validation_sample_count": result.validation_sample_count,
        "feature_importance": result.feature_importance,
    }


async def run_deep_training_job(job_id: uuid.UUID) -> None:
    async with AsyncSessionLocal() as db:
        job = await job_repository.get_job(db, job_id)
        if job is None:
            logger.error("deep_training_job: job introuvable (id=%s)", job_id)
            return

        await job_repository.mark_running(db, job)
        try:
            trainer = _TRAINERS.get(job.model_name)
            if trainer is None:
                raise ValueError(f"Modele inconnu ou pas encore implemente: {job.model_name}")

            arrays = await service.get_training_arrays_for_asset(db, job.asset_id, job.horizon)
            if arrays is None:
                raise ValueError("Historique de prix insuffisant pour cet actif (30 barres minimum).")

            feature_names, X, y, dates, current_features = arrays
            result = trainer(feature_names, X, y, dates, current_features)
            await job_repository.mark_completed(db, job, _model_result_to_dict(result))
            logger.info(
                "deep_training_job termine: job=%s modele=%s statut=%s",
                job_id,
                job.model_name,
                result.model_status,
            )
        except Exception as exc:
            logger.exception("deep_training_job: echec (job=%s)", job_id)
            await job_repository.mark_failed(db, job, str(exc))
