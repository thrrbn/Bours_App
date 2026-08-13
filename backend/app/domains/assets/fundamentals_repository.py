"""Acces aux donnees de asset_fundamentals - requetes SQL/ORM pures, meme
decoupage que analyst/repository.py (une table, un fichier)."""
import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domains.assets.fundamentals_models import AssetFundamentals


async def get_by_asset(db: AsyncSession, asset_id: uuid.UUID) -> AssetFundamentals | None:
    stmt = select(AssetFundamentals).where(AssetFundamentals.asset_id == asset_id)
    result = await db.execute(stmt)
    return result.scalar_one_or_none()


async def list_by_sector(db: AsyncSession, sector: str, exclude_asset_id: uuid.UUID) -> list[AssetFundamentals]:
    """Fondamentaux DEJA rafraichis (voir upsert()) pour les autres actifs
    suivis du meme secteur - sert au comparatif secteur/pairs (voir
    service.py::get_sector_comparison). Volontairement pas de nouvel appel
    Yahoo Finance ici : la comparaison ne s'enrichit qu'au fil des
    rafraichissements deja demandes par l'utilisateur sur d'autres titres,
    pas d'appel en cascade a chaque consultation d'une fiche."""
    stmt = select(AssetFundamentals).where(
        AssetFundamentals.sector == sector, AssetFundamentals.asset_id != exclude_asset_id
    )
    result = await db.execute(stmt)
    return list(result.scalars().all())


async def upsert(
    db: AsyncSession,
    asset_id: uuid.UUID,
    sector: str | None,
    industry: str | None,
    market_cap: int | None,
    trailing_pe: float | None,
    forward_pe: float | None,
    dividend_yield: float | None,
    week52_low: float | None,
    week52_high: float | None,
    beta: float | None,
    business_summary: str | None,
    return_on_equity: float | None = None,
    debt_to_equity: float | None = None,
    profit_margin: float | None = None,
    price_to_book: float | None = None,
    ev_to_ebitda: float | None = None,
) -> AssetFundamentals:
    existing = await get_by_asset(db, asset_id)
    if existing is None:
        existing = AssetFundamentals(asset_id=asset_id)
        db.add(existing)

    existing.sector = sector
    existing.industry = industry
    existing.market_cap = market_cap
    existing.trailing_pe = trailing_pe
    existing.forward_pe = forward_pe
    existing.dividend_yield = dividend_yield
    existing.week52_low = week52_low
    existing.week52_high = week52_high
    existing.beta = beta
    existing.return_on_equity = return_on_equity
    existing.debt_to_equity = debt_to_equity
    existing.profit_margin = profit_margin
    existing.price_to_book = price_to_book
    existing.ev_to_ebitda = ev_to_ebitda
    existing.business_summary = business_summary

    await db.commit()
    await db.refresh(existing, attribute_names=["asset"])
    return existing
