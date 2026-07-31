"""Acces aux donnees de marche - upserts idempotents, aucune logique metier."""
import math
import uuid
from datetime import date
from decimal import Decimal

import pandas as pd
from sqlalchemy import func, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.domains.market_data.models import Dividend, PriceBar, TechnicalIndicator
from app.domains.market_data.providers.base import DividendDTO, PriceBarDTO


def _is_valid_bar(bar: PriceBarDTO) -> bool:
    """Defense en profondeur (voir yahoo_finance.py) : rejette toute barre
    dont l'OHLC contiendrait un NaN, quel que soit le provider - un cours
    invalide ne doit jamais atteindre price_bars (il empoisonnerait ensuite
    irreversiblement le portefeuille virtuel, voir portfolio/service.py)."""
    return not any(math.isnan(v) for v in (bar.open, bar.high, bar.low, bar.close))


async def upsert_price_bars(
    db: AsyncSession, asset_id: uuid.UUID, bars: list[PriceBarDTO], source: str = "yahoo_finance"
) -> None:
    bars = [b for b in bars if _is_valid_bar(b)]
    if not bars:
        return
    values = [
        {
            "asset_id": asset_id,
            "trade_date": bar.trade_date,
            "open": bar.open,
            "high": bar.high,
            "low": bar.low,
            "close": bar.close,
            "adjusted_close": bar.adjusted_close,
            "volume": bar.volume,
            "source": source,
        }
        for bar in bars
    ]
    stmt = insert(PriceBar).values(values)
    stmt = stmt.on_conflict_do_update(
        index_elements=["asset_id", "trade_date"],
        set_={
            "open": stmt.excluded.open,
            "high": stmt.excluded.high,
            "low": stmt.excluded.low,
            "close": stmt.excluded.close,
            "adjusted_close": stmt.excluded.adjusted_close,
            "volume": stmt.excluded.volume,
            "source": stmt.excluded.source,
        },
    )
    await db.execute(stmt)
    await db.commit()


async def get_price_history(db: AsyncSession, asset_id: uuid.UUID, limit: int = 400) -> list[PriceBar]:
    stmt = (
        select(PriceBar)
        .where(PriceBar.asset_id == asset_id)
        .order_by(PriceBar.trade_date.desc())
        .limit(limit)
    )
    result = await db.execute(stmt)
    return list(result.scalars().all())


async def get_latest_bar(db: AsyncSession, asset_id: uuid.UUID) -> PriceBar | None:
    """
    Dernier cours VALIDE connu - utilise par le portefeuille virtuel (Etape 12)
    pour valoriser les positions et executer les achats/ventes simules, et par
    analyst/service.py et market_data/router.py.

    Bug reel trouve le 31/07/2026 (suite du bug NaN du 30/07/2026, voir
    docs/STACK.md) : filtrer le NaN a l'ingestion (yahoo_finance.py,
    _is_valid_bar) empeche un NOUVEAU NaN d'entrer en base, mais une ligne DEJA
    corrompue AVANT ce correctif restait la plus recente par date - un
    rafraichissement ulterieur ne la remplace que si Yahoo Finance renvoie
    entre-temps une valeur non-NaN pour CETTE MEME date (typiquement une fois
    la bougie du jour cloturee) ; en attendant, `_get_latest_price` bloquait
    indefiniment tout achat/vente sur cet actif, meme apres un rafraichissement
    reussi qui avait pourtant bien ingere une barre plus ancienne valide.
    Corrige a la source : on ne considere "le dernier cours" que parmi les
    lignes valides (ni NaN, ni <= 0), une ligne corrompue est simplement
    ignoree au profit de la derniere ligne valide precedente - coherent avec
    l'esprit du garde-fou existant (portfolio/service.py:_get_latest_price)
    mais applique une bonne fois pour toutes ici, pour tous les appelants.

    Attention Postgres : contrairement a IEEE754, `NaN = NaN` est VRAI pour le
    type NUMERIC en Postgres (NaN trie plus grand que toute valeur), donc le
    piege classique `close != close` ne filtre PAS le NaN ici - il faut
    comparer explicitement a la valeur `Decimal('NaN')`.
    """
    stmt = (
        select(PriceBar)
        .where(PriceBar.asset_id == asset_id)
        .where(PriceBar.close != Decimal("NaN"))
        .where(PriceBar.close > 0)
        .order_by(PriceBar.trade_date.desc())
        .limit(1)
    )
    result = await db.execute(stmt)
    return result.scalar_one_or_none()


async def get_latest_price_dates(db: AsyncSession) -> dict[uuid.UUID, date]:
    """Derniere date de cotation connue, groupee par actif (tous actifs en
    UNE requete) - utilise par assets/service.py:get_status_overview() pour
    afficher la fraicheur des prix sans requete N+1."""
    stmt = select(PriceBar.asset_id, func.max(PriceBar.trade_date)).group_by(PriceBar.asset_id)
    result = await db.execute(stmt)
    return {asset_id: trade_date for asset_id, trade_date in result.all()}


async def upsert_dividends(db: AsyncSession, asset_id: uuid.UUID, dividends: list[DividendDTO]) -> int:
    """31/07/2026 - voir models.py::Dividend. Idempotent (ON CONFLICT), rejouable
    sans risque a chaque rafraichissement de prix."""
    if not dividends:
        return 0
    values = [
        {"asset_id": asset_id, "ex_date": d.ex_date, "amount_per_share": d.amount_per_share} for d in dividends
    ]
    stmt = insert(Dividend).values(values)
    stmt = stmt.on_conflict_do_update(
        index_elements=["asset_id", "ex_date"], set_={"amount_per_share": stmt.excluded.amount_per_share}
    )
    await db.execute(stmt)
    await db.commit()
    return len(values)


async def get_dividends_after(db: AsyncSession, asset_id: uuid.UUID, since: date) -> list[Dividend]:
    """Dividendes dont la date de detachement est STRICTEMENT posterieure a
    `since` - utilise par jobs/credit_dividends_job.py pour ne crediter chaque
    dividende qu'une seule fois (voir portfolio/models.py::dividends_credited_until)."""
    stmt = (
        select(Dividend)
        .where(Dividend.asset_id == asset_id, Dividend.ex_date > since)
        .order_by(Dividend.ex_date.asc())
    )
    result = await db.execute(stmt)
    return list(result.scalars().all())


async def get_latest_indicators(db: AsyncSession, asset_id: uuid.UUID) -> TechnicalIndicator | None:
    stmt = (
        select(TechnicalIndicator)
        .where(TechnicalIndicator.asset_id == asset_id)
        .order_by(TechnicalIndicator.trade_date.desc())
        .limit(1)
    )
    result = await db.execute(stmt)
    return result.scalar_one_or_none()


def _safe_float(value) -> float | None:
    if value is None:
        return None
    try:
        f = float(value)
    except (TypeError, ValueError):
        return None
    return f if f == f else None  # exclut NaN


async def upsert_indicators(db: AsyncSession, asset_id: uuid.UUID, indicators_df: pd.DataFrame) -> None:
    values = []
    for trade_date, row in indicators_df.iterrows():
        values.append(
            {
                "asset_id": asset_id,
                "trade_date": trade_date,
                "sma_20": _safe_float(row.get("sma_20")),
                "sma_50": _safe_float(row.get("sma_50")),
                "sma_200": _safe_float(row.get("sma_200")),
                "ema_12": _safe_float(row.get("ema_12")),
                "ema_26": _safe_float(row.get("ema_26")),
                "rsi_14": _safe_float(row.get("rsi_14")),
                "macd": _safe_float(row.get("macd")),
                "macd_signal": _safe_float(row.get("macd_signal")),
                "bollinger_upper": _safe_float(row.get("bollinger_upper")),
                "bollinger_lower": _safe_float(row.get("bollinger_lower")),
                "volatility_20d": _safe_float(row.get("volatility_20d")),
                "momentum_roc_20": _safe_float(row.get("momentum_roc_20")),
            }
        )
    if not values:
        return
    stmt = insert(TechnicalIndicator).values(values)
    update_cols = {c: stmt.excluded[c] for c in values[0] if c not in ("asset_id", "trade_date")}
    stmt = stmt.on_conflict_do_update(index_elements=["asset_id", "trade_date"], set_=update_cols)
    await db.execute(stmt)
    await db.commit()
