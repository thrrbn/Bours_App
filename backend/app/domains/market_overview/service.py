"""Orchestration de la page Marche - voir provider.py pour le detail des sources (toutes externes, en direct)."""
from sqlalchemy.ext.asyncio import AsyncSession

from app.domains.market_overview import provider, repository
from app.domains.market_overview.models import MarketSnapshot


async def refresh_snapshot(db: AsyncSession) -> MarketSnapshot:
    """
    01/08/2026 (revu) : toutes les donnees viennent desormais de sources
    externes en direct (Yahoo Finance, Binance - voir provider.py) plutot que
    des actifs personnellement suivis dans cette application. Consequence
    directe : plus aucune dependance a assets_repository/market_data_repository
    ici - la page "Marche" est totalement independante de ce que l'utilisateur
    suit par ailleurs (portefeuille/watchlist), comme demande explicitement.
    """
    indices = provider.fetch_index_quotes()
    movers = {
        "FR": provider.fetch_fr_movers(),
        "US": provider.fetch_us_movers(),
        "CRYPTO": await provider.fetch_crypto_movers(),
    }
    return await repository.save_snapshot(db, indices=indices, movers=movers)


async def get_latest(db: AsyncSession) -> MarketSnapshot | None:
    return await repository.get_latest_snapshot(db)
