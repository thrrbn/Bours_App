"""Endpoint manuel pour declencher/tester la verification de la watchlist sans
attendre l'execution planifiee (voir jobs/notify_changes_job.py)."""
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.domains.notifications.service import check_and_notify_watchlist

router = APIRouter(prefix="/api/v1/notifications", tags=["notifications"])


@router.post("/check")
async def trigger_check(db: AsyncSession = Depends(get_db)):
    change_count = await check_and_notify_watchlist(db)
    return {"changes_detected": change_count}
