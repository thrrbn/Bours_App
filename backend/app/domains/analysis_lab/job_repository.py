"""
Requetes pures pour `TrainingJob` (Phase 3, 31/07/2026 - voir db_models.py
pour le contexte complet de cette exception au principe "lecture seule"
d'analysis_lab).
"""
import uuid
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domains.analysis_lab.db_models import STATUS_FAILED, STATUS_PENDING, STATUS_RUNNING, TrainingJob


async def create_job(db: AsyncSession, asset_id: uuid.UUID, model_name: str, horizon: str) -> TrainingJob:
    job = TrainingJob(asset_id=asset_id, model_name=model_name, horizon=horizon, status=STATUS_PENDING)
    db.add(job)
    await db.commit()
    await db.refresh(job)
    return job


async def get_job(db: AsyncSession, job_id: uuid.UUID) -> TrainingJob | None:
    stmt = select(TrainingJob).where(TrainingJob.id == job_id)
    result = await db.execute(stmt)
    return result.scalar_one_or_none()


async def mark_running(db: AsyncSession, job: TrainingJob) -> None:
    job.status = STATUS_RUNNING
    await db.commit()


async def mark_completed(db: AsyncSession, job: TrainingJob, result: dict) -> None:
    job.status = "completed"
    job.result = result
    job.completed_at = datetime.now(timezone.utc)
    await db.commit()


async def mark_failed(db: AsyncSession, job: TrainingJob, error_message: str) -> None:
    job.status = STATUS_FAILED
    job.error_message = error_message[:500]
    job.completed_at = datetime.now(timezone.utc)
    await db.commit()
