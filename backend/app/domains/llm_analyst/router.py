"""
Endpoints du domaine llm_analyst (16/08/2026, voir docs/20-instance-locale-pc-mac.md).

Feature reservee a une instance locale PC/Mac - `require_enabled()` bloque
TOUT appel a /analyze tant que `settings.enable_llm_analyst` n'est pas
explicitement mis a true (jamais le cas sur le NAS deploye, voir
config.py). GET /status reste toujours accessible (meme desactive) pour que
le frontend puisse decider d'afficher ou non le lien de navigation - voir
docs/20, section "pourquoi un flag runtime plutot qu'un flag de build".
"""
import uuid

from apscheduler.triggers.date import DateTrigger
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.core.exceptions import AssetNotFoundError
from app.database import get_db
from app.domains.assets import repository as assets_repository
from app.domains.backtests.kernc_engine import LLM_ANALYST_SUPPORTED_STRATEGIES
from app.domains.llm_analyst import job_repository
from app.domains.llm_analyst.schemas import AnalysisJobCreate, AnalysisJobRead, AnalysisStatusRead
from app.jobs.llm_analysis_job import run_llm_analysis_job
from app.jobs.scheduler import scheduler

router = APIRouter(prefix="/api/v1/llm-analyst", tags=["llm_analyst"])


def require_enabled() -> None:
    if not get_settings().enable_llm_analyst:
        raise HTTPException(
            403,
            "Analyste IA desactive sur cette instance - reserve a une installation locale PC/Mac avec Ollama "
            "(voir docs/20-instance-locale-pc-mac.md). Jamais active sur le NAS deploye.",
        )


@router.get("/status", response_model=AnalysisStatusRead)
async def get_status():
    settings = get_settings()
    return AnalysisStatusRead(enabled=settings.enable_llm_analyst, ollama_model=settings.ollama_model)


@router.get("/strategies", response_model=list[str])
async def list_strategies():
    """Strategies auto-suffisantes supportees (voir kernc_engine.py::
    LLM_ANALYST_SUPPORTED_STRATEGIES - pas de signal_replay, hors perimetre
    pour l'instant)."""
    return list(LLM_ANALYST_SUPPORTED_STRATEGIES)


@router.post("/analyze", response_model=AnalysisJobRead, status_code=202, dependencies=[Depends(require_enabled)])
async def start_analysis(payload: AnalysisJobCreate, db: AsyncSession = Depends(get_db)):
    """
    Lance une analyse ASYNCHRONE (l'appel au LLM local peut prendre de
    quelques secondes a plusieurs minutes, voir service.py) - meme pattern
    que POST /analysis-lab/{asset_id}/train-deep (Phase 3) : retourne
    immediatement un job en statut 'pending' (202), poller
    GET /jobs/{job_id} pour le resultat.
    """
    if payload.strategy_name not in LLM_ANALYST_SUPPORTED_STRATEGIES:
        raise HTTPException(422, f"strategy_name doit etre l'une de {LLM_ANALYST_SUPPORTED_STRATEGIES}.")
    if payload.period_end <= payload.period_start:
        raise HTTPException(422, "period_end doit etre posterieure a period_start.")

    asset = await assets_repository.get_by_id(db, payload.asset_id)
    if asset is None:
        raise AssetNotFoundError(str(payload.asset_id))

    settings = get_settings()
    job = await job_repository.create_job(
        db,
        payload.asset_id,
        payload.strategy_name,
        payload.period_start,
        payload.period_end,
        payload.model_name or settings.ollama_model,
    )
    scheduler.add_job(
        run_llm_analysis_job,
        trigger=DateTrigger(),
        args=[job.id],
        id=f"llm-analysis-{job.id}",
    )
    return AnalysisJobRead.model_validate(job, from_attributes=True)


@router.get("/jobs/{job_id}", response_model=AnalysisJobRead)
async def get_job(job_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    job = await job_repository.get_job(db, job_id)
    if job is None:
        raise AssetNotFoundError(str(job_id))
    return AnalysisJobRead.model_validate(job, from_attributes=True)
