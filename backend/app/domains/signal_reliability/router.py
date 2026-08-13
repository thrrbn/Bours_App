from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.domains.signal_reliability import service
from app.domains.signal_reliability.schemas import ScorecardRead

router = APIRouter(prefix="/api/v1/signal-reliability", tags=["signal_reliability"])


@router.get("/scorecard", response_model=ScorecardRead)
async def get_scorecard(db: AsyncSession = Depends(get_db)):
    """
    13/08/2026 : precision REELLE du moteur de signal, par horizon et par
    fenetre glissante (30/90/365 jours + tout l'historique) - alimente par le
    job quotidien evaluate_signal_outcomes_job (voir service.py), pas par un
    calcul a la demande. `count=0`/`precision=None` pour une fenetre sans
    aucun signal encore evalue (normal les premiers jours apres le
    deploiement de cette fonctionnalite - aucun signal n'a encore atteint la
    maturite necessaire).
    """
    result = await service.get_scorecard(db)
    return ScorecardRead(**result)
