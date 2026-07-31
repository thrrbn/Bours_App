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
from app.domains.analysis_lab.schemas import (
    DEEP_MODEL_NAMES,
    AssetComparisonRead,
    FeatureSnapshotRead,
    PortfolioComparisonRead,
    TrainingJobCreate,
    TrainingJobRead,
)
from app.domains.assets import repository as assets_repository
from app.jobs.deep_training_job import run_deep_training_job
from app.jobs.scheduler import scheduler

router = APIRouter(prefix="/api/v1/analysis-lab", tags=["analysis_lab"])

HORIZONS = ("short", "medium", "long")


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
