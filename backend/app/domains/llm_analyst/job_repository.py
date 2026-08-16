"""Requetes pures pour `AnalysisJob` - copie du pattern de
analysis_lab/job_repository.py (Phase 3), voir db_models.py."""
import uuid
from datetime import date, datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domains.llm_analyst.db_models import STATUS_FAILED, STATUS_PENDING, STATUS_RUNNING, AnalysisJob


async def create_job(
    db: AsyncSession,
    asset_id: uuid.UUID,
    strategy_name: str,
    period_start: date,
    period_end: date,
    model_name: str,
) -> AnalysisJob:
    job = AnalysisJob(
        asset_id=asset_id,
        strategy_name=strategy_name,
        period_start=period_start,
        period_end=period_end,
        model_name=model_name,
        status=STATUS_PENDING,
    )
    db.add(job)
    await db.commit()
    await db.refresh(job)
    return job


async def get_job(db: AsyncSession, job_id: uuid.UUID) -> AnalysisJob | None:
    stmt = select(AnalysisJob).where(AnalysisJob.id == job_id)
    result = await db.execute(stmt)
    return result.scalar_one_or_none()


async def mark_running(db: AsyncSession, job: AnalysisJob) -> None:
    job.status = STATUS_RUNNING
    await db.commit()


async def mark_completed(db: AsyncSession, job: AnalysisJob, result: dict) -> None:
    job.status = "completed"
    job.result = result
    job.completed_at = datetime.now(timezone.utc)
    await db.commit()


async def mark_failed(db: AsyncSession, job: AnalysisJob, error_message: str) -> None:
    job.status = STATUS_FAILED
    job.error_message = error_message[:500]
    job.completed_at = datetime.now(timezone.utc)
    await db.commit()
