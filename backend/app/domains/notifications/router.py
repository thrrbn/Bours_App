"""Endpoint manuel pour declencher/tester la verification de la watchlist sans
attendre l'execution planifiee (voir jobs/notify_changes_job.py)."""
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.domains.notifications.briefing_service import build_daily_briefing, send_daily_briefing
from app.domains.notifications.schemas import BriefingRead
from app.domains.notifications.service import check_and_notify_watchlist

router = APIRouter(prefix="/api/v1/notifications", tags=["notifications"])


@router.post("/check")
async def trigger_check(db: AsyncSession = Depends(get_db)):
    change_count = await check_and_notify_watchlist(db)
    return {"changes_detected": change_count}


@router.get("/briefing/preview", response_model=BriefingRead)
async def preview_briefing(window_days: int = Query(default=3, ge=1, le=14), db: AsyncSession = Depends(get_db)):
    """
    Apercu du briefing quotidien (portefeuille virtuel + watchlist) SANS
    envoyer d'email ni faire avancer le curseur de suivi des signaux -
    consultable a tout moment, meme avec MAIL_ENABLED=false, pour verifier le
    contenu avant d'activer l'envoi reel (voir jobs/daily_briefing_job.py).
    """
    return await build_daily_briefing(db, window_days=window_days, persist_state=False)


@router.post("/briefing/send", response_model=BriefingRead)
async def send_briefing_now(db: AsyncSession = Depends(get_db)):
    """
    Declenche le briefing quotidien immediatement (meme logique que le job
    planifie, voir jobs/daily_briefing_job.py) - utile pour tester sans
    attendre le cron. N'envoie reellement un email QUE si MAIL_ENABLED=true
    et qu'au moins un titre a quelque chose de neuf a rapporter (voir
    mailer.py et briefing_service.py).
    """
    return await send_daily_briefing(db)
