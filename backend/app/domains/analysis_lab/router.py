"""
Bac a sable pedagogique (31/07/2026, voir feature_engineering.py/models.py/
service.py) - endpoints en LECTURE SEULE : ne modifient jamais un signal, une
position de portefeuille ou un run de backtest. Objectif explicite :
apprendre l'analyse technique classique (50+ indicateurs) et comparer des
modeles legers (Random Forest, XGBoost, ARIMA) au moteur de regles reel, sur
les memes actifs que ceux deja suivis/detenus.
"""
import uuid

from apscheduler.triggers.date import DateTrigger
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import AssetNotFoundError, InsufficientDataError
from app.database import get_db
from app.domains.analysis_lab import job_repository, service
from app.domains.analysis_lab.feature_engineering import ADJUSTABLE_INDICATORS
from app.domains.analysis_lab.schemas import (
    DEEP_MODEL_NAMES,
    AdjustableIndicatorInfo,
    AssetComparisonRead,
    FeatureSnapshotRead,
    IndicatorRecomputeRead,
    IndicatorRecomputeRequest,
    PortfolioComparisonRead,
    TrainingJobCreate,
    TrainingJobRead,
)
from app.domains.assets import repository as assets_repository
from app.jobs.deep_training_job import run_deep_training_job
from app.jobs.scheduler import scheduler

router = APIRouter(prefix="/api/v1/analysis-lab", tags=["analysis_lab"])

HORIZONS = ("short", "medium", "long")


@router.get("/indicators/adjustable", response_model=list[AdjustableIndicatorInfo])
async def list_adjustable_indicators():
    """
    13/08/2026 (laboratoire d'indicateurs) : liste les indicateurs qui
    acceptent des parametres personnalisables (voir feature_engineering.py::
    ADJUSTABLE_INDICATORS) - route LITTERALE declaree avant les routes
    parametrees ci-dessous (convention du projet, voir docs/STACK.md), pour
    eviter toute ambiguite de matching FastAPI avec /{asset_id}/... .
    """
    return service.list_adjustable_indicators()


@router.get("/training-jobs/{job_id}", response_model=TrainingJobRead)
async def get_training_job(job_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    """
    Phase 3 (31/07/2026) - poll du statut/resultat d'un entrainement LSTM
    lance via POST /{asset_id}/train-deep. `result` reste null tant que
    `status` n'est pas 'completed'.
    """
    job = await job_repository.get_job(db, job_id)
    if job is None:
        raise AssetNotFoundError(str(job_id))
    return TrainingJobRead.model_validate(job, from_attributes=True)


@router.post("/{asset_id}/train-deep", response_model=TrainingJobRead, status_code=202)
async def train_deep_model(asset_id: uuid.UUID, payload: TrainingJobCreate, db: AsyncSession = Depends(get_db)):
    """
    Lance un entrainement ASYNCHRONE (LSTM pour l'instant - Phase 3, voir
    deep_models.py) : contrairement a /compare (Random Forest/XGBoost/ARIMA/
    Prophet, synchrones), un modele sequentiel prend trop longtemps a
    entrainer pour un appel HTTP bloquant. Retourne immediatement un job en
    statut 'pending' (202 Accepted) - poller GET /training-jobs/{job_id}
    pour le resultat. Le job tourne en tache de fond via le scheduler
    APScheduler deja utilise pour les jobs planifies (execution unique,
    immediate - pas un cron recurrent).
    """
    if payload.model_name not in DEEP_MODEL_NAMES:
        raise HTTPException(422, f"model_name doit etre l'un de {DEEP_MODEL_NAMES}.")
    if payload.horizon not in HORIZONS:
        raise HTTPException(422, f"horizon doit etre l'un de {HORIZONS}.")

    asset = await assets_repository.get_by_id(db, asset_id)
    if asset is None:
        raise AssetNotFoundError(str(asset_id))

    job = await job_repository.create_job(db, asset_id, payload.model_name, payload.horizon)
    scheduler.add_job(
        run_deep_training_job,
        trigger=DateTrigger(),
        args=[job.id],
        id=f"deep-train-{job.id}",
    )
    return TrainingJobRead.model_validate(job, from_attributes=True)


@router.get("/{asset_id}/features", response_model=FeatureSnapshotRead)
async def get_feature_snapshot(asset_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    """Derniere valeur connue des 70+ indicateurs techniques (feature_engineering.py)
    pour cet actif - reponse a 'sur quelle base calcule-t-on ?', sans modele."""
    asset = await assets_repository.get_by_id(db, asset_id)
    if asset is None:
        raise AssetNotFoundError(str(asset_id))
    snapshot = await service.get_feature_snapshot(db, asset)
    if snapshot is None:
        raise InsufficientDataError(
            f"Aucun historique de prix pour cet actif - lance d'abord un rafraichissement "
            "(POST /api/v1/market-data/{asset_id}/refresh)."
        )
    return snapshot


@router.post("/{asset_id}/indicators/{indicator_key}/recompute", response_model=IndicatorRecomputeRead)
async def recompute_indicator(
    asset_id: uuid.UUID, indicator_key: str, payload: IndicatorRecomputeRequest, db: AsyncSession = Depends(get_db)
):
    """
    13/08/2026 (laboratoire d'indicateurs) : recalcule UN indicateur avec des
    parametres personnalises (periode, ecart-type...) - voir
    feature_engineering.py::compute_adjustable_indicator. N'affecte jamais le
    tableau des 70+ indicateurs (toujours calcules avec les parametres par
    defaut, voir /{asset_id}/features), ni un signal, ni le portefeuille -
    lecture/calcul a la demande uniquement, rien n'est sauvegarde.
    """
    if indicator_key not in ADJUSTABLE_INDICATORS:
        raise HTTPException(404, f"Indicateur inconnu ou non ajustable: {indicator_key}")
    asset = await assets_repository.get_by_id(db, asset_id)
    if asset is None:
        raise AssetNotFoundError(str(asset_id))
    result = await service.recompute_indicator(db, asset, indicator_key, payload.params)
    if result is None:
        raise InsufficientDataError(
            f"Aucun historique de prix pour cet actif - lance d'abord un rafraichissement "
            "(POST /api/v1/market-data/{asset_id}/refresh)."
        )
    return IndicatorRecomputeRead(indicator=indicator_key, **result)


@router.get("/{asset_id}/compare", response_model=AssetComparisonRead)
async def compare_asset(
    asset_id: uuid.UUID, horizon: str = Query(default="medium"), db: AsyncSession = Depends(get_db)
):
    """
    Entraine Random Forest / XGBoost / ARIMA sur l'historique de cet actif et
    compare leurs predictions au signal REEL deja calcule par le moteur de
    regles (domaine signals, lu mais jamais modifie). Rien n'est sauvegarde -
    chaque appel reentraine a la volee (rapide, voir models.py).
    """
    if horizon not in HORIZONS:
        horizon = "medium"
    result = await service.compare_asset_by_id(db, asset_id, horizon)
    if result is None:
        raise AssetNotFoundError(str(asset_id))
    return result


@router.get("/portfolio-compare", response_model=PortfolioComparisonRead)
async def compare_portfolio(horizon: str = Query(default="medium"), db: AsyncSession = Depends(get_db)):
    """
    Meme comparaison que /compare, mais pour TOUS les actifs actuellement
    detenus dans le portefeuille virtuel (demande explicite : reutiliser les
    actifs deja suivis en simulation comme jeu de test "reel", plutot qu'un
    jeu de donnees separe) - lecture seule des positions, aucune influence
    sur le portefeuille.
    """
    if horizon not in HORIZONS:
        horizon = "medium"
    return await service.compare_portfolio(db, horizon)
