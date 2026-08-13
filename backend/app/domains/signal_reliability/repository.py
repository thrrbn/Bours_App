import uuid
from datetime import datetime, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domains.market_data.models import PriceBar
from app.domains.signal_reliability.models import SignalOutcome
from app.domains.signals.models import Signal


async def get_mature_unevaluated_signals(db: AsyncSession, horizon: str, cutoff: datetime) -> list[Signal]:
    """
    Signaux de cet horizon assez anciens pour que leur fenetre de rendement
    futur (HORIZON_FORWARD_DAYS, voir service.py) soit deja entierement
    ecoulee (computed_at <= cutoff), et pas encore presents dans
    signal_outcomes (idempotence - voir docstring du modele SignalOutcome).
    Sous-requete NOT IN plutot qu'un LEFT JOIN ... IS NULL : plus lisible ici,
    la table signal_outcomes reste petite (une ligne par signal EVALUE, pas
    par signal calcule).
    """
    already_evaluated = select(SignalOutcome.signal_id)
    stmt = (
        select(Signal)
        .where(
            Signal.horizon == horizon,
            Signal.computed_at <= cutoff,
            Signal.final_signal != "neutre",  # jamais evalue, meme regle que evaluate_signals()
            Signal.id.notin_(already_evaluated),
        )
        .order_by(Signal.computed_at.asc())
    )
    result = await db.execute(stmt)
    return list(result.scalars().all())


async def get_forward_bars(db: AsyncSession, asset_id: uuid.UUID, from_date, forward_days: int) -> list[PriceBar]:
    """Meme requete que backtests/service.py::_compute_forward_return (duplique
    volontairement - isolation des domaines, voir docstring de module)."""
    stmt = (
        select(PriceBar)
        .where(PriceBar.asset_id == asset_id, PriceBar.trade_date >= from_date)
        .order_by(PriceBar.trade_date.asc())
        .limit(forward_days + 1)
    )
    result = await db.execute(stmt)
    return list(result.scalars().all())


async def save_outcomes(db: AsyncSession, outcomes: list[dict]) -> int:
    """Insertion en lot - chaque dict : signal_id, asset_id, horizon,
    signal_computed_at, final_signal, forward_return, was_correct."""
    if not outcomes:
        return 0
    for data in outcomes:
        db.add(SignalOutcome(id=uuid.uuid4(), **data))
    await db.commit()
    return len(outcomes)


# Fenetres glissantes usuelles du scorecard (voir service.py::get_scorecard) -
# "all" = tout l'historique disponible, sans limite de date.
SCORECARD_WINDOWS = {"30d": 30, "90d": 90, "365d": 365, "all": None}


async def get_window_stats(db: AsyncSession, horizon: str, window_days: int | None) -> dict:
    """
    Compte/precision des signaux DEJA EVALUES de cet horizon, sur la fenetre
    glissante demandee (base sur signal_computed_at - la date du signal, pas
    la date d'evaluation, pour repondre a "la fiabilite du moteur sur les X
    derniers mois de signaux" plutot que "ce qui a ete evalue cette semaine").
    Agregation en Python plutot qu'un GROUP BY SQL : le volume attendu
    (quelques milliers de lignes max pour un usage personnel) rend ça largement
    suffisant, et evite du SQL agregatif specifique par dialecte.
    """
    stmt = select(SignalOutcome.was_correct).where(SignalOutcome.horizon == horizon)
    if window_days is not None:
        cutoff = datetime.now(timezone.utc) - timedelta(days=window_days)
        stmt = stmt.where(SignalOutcome.signal_computed_at >= cutoff)
    result = await db.execute(stmt)
    outcomes = list(result.scalars().all())
    total = len(outcomes)
    correct = sum(1 for o in outcomes if o)
    return {
        "count": total,
        "precision": round(correct / total, 4) if total > 0 else None,
    }


async def get_last_evaluated_at(db: AsyncSession) -> datetime | None:
    stmt = select(SignalOutcome.evaluated_at).order_by(SignalOutcome.evaluated_at.desc()).limit(1)
    result = await db.execute(stmt)
    return result.scalar_one_or_none()
