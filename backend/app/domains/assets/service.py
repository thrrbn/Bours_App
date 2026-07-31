"""Logique metier du domaine assets : recherche, normalisation, resolution de marche."""
import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import AssetNotFoundError
from app.domains.analyst import repository as analyst_repository
from app.domains.assets import discovery, repository
from app.domains.assets.models import Asset
from app.domains.assets.schemas import AssetCreate
from app.domains.assets.seed_data import BEL20_ASSETS
from app.domains.assets.seed_data_aex import AEX_ASSETS
from app.domains.assets.seed_data_binance import BINANCE_MAJORS_ASSETS
from app.domains.assets.seed_data_cac40 import CAC40_ASSETS
from app.domains.assets.seed_data_dax import DAX40_ASSETS
from app.domains.assets.seed_data_us import US_MAJORS_ASSETS
from app.domains.market_data import repository as market_data_repository
from app.domains.signals import repository as signals_repository


async def get_asset_or_raise(db: AsyncSession, asset_id: uuid.UUID) -> Asset:
    asset = await repository.get_by_id(db, asset_id)
    if asset is None:
        raise AssetNotFoundError(str(asset_id))
    return asset


async def search_assets(db: AsyncSession, query: str) -> list[Asset]:
    normalized = query.strip()
    if not normalized:
        return []
    return await repository.search(db, normalized)


async def list_assets(db: AsyncSession, market: str | None, sector: str | None) -> list[Asset]:
    return await repository.list_all(db, market=market, sector=sector)


async def create_asset(db: AsyncSession, payload: AssetCreate) -> Asset:
    existing = await repository.get_by_ticker(db, payload.ticker, payload.market)
    if existing is not None:
        return existing
    return await repository.create(db, payload)


async def _seed(db: AsyncSession, rows: list[dict]) -> dict:
    """Insertion idempotente commune a tous les seed_xxx ci-dessous - voir
    repository.bulk_upsert (ON CONFLICT DO NOTHING sur ticker+market)."""
    inserted = await repository.bulk_upsert(db, rows)
    return {"total_candidates": len(rows), "inserted": inserted, "already_present": len(rows) - inserted}


async def seed_bel20(db: AsyncSession) -> dict:
    """Insere les 20 composants du BEL20 s'ils n'existent pas deja.
    Idempotent : rejouable sans risque (ex. apres `alembic upgrade head`
    sur une base fraiche, ou pour completer une base partiellement seedee)."""
    return await _seed(db, BEL20_ASSETS)


async def seed_binance_majors(db: AsyncSession) -> dict:
    """Insere un panier de cryptomonnaies (Binance, paires USDT) s'il
    n'existe pas deja. Idempotent, meme principe que seed_bel20. Ces actifs
    sont ensuite ingeres via BinanceProvider (donnees publiques en lecture
    seule, voir market_data/providers/binance.py) - aucun ordre reel."""
    return await _seed(db, BINANCE_MAJORS_ASSETS)


async def seed_us_majors(db: AsyncSession) -> dict:
    """Insere un panier de grandes capitalisations americaines (NASDAQ/NYSE),
    idempotent. Ingere ensuite via Yahoo Finance comme le BEL20."""
    return await _seed(db, US_MAJORS_ASSETS)


async def seed_cac40(db: AsyncSession) -> dict:
    """Insere l'indice CAC 40 (Euronext Paris), idempotent."""
    return await _seed(db, CAC40_ASSETS)


async def seed_dax40(db: AsyncSession) -> dict:
    """Insere l'indice DAX 40 (Xetra / Francfort), idempotent."""
    return await _seed(db, DAX40_ASSETS)


async def seed_aex(db: AsyncSession) -> dict:
    """Insere l'indice AEX (Euronext Amsterdam), idempotent."""
    return await _seed(db, AEX_ASSETS)


async def get_status_overview(db: AsyncSession) -> list[dict]:
    """
    Fraicheur des donnees (prix / signal / consensus analystes) pour tous
    les actifs suivis, en 4 requetes au total (1 pour les actifs + 1 par
    source de fraicheur, chacune groupee par actif) au lieu d'une requete
    par actif x par source - meme principe anti-N+1 que le correctif du
    30/07/2026 sur get_comparison_table (voir docs/STACK.md). Alimente la
    page de suivi des actifs (aucune mise a jour n'est faite ici : purement
    en lecture, voir POST /market-data/{id}/refresh, /signals/{id}/recompute,
    /analyst/{id}/refresh pour forcer une mise a jour titre par titre).
    """
    assets = await repository.list_all(db)
    price_dates = await market_data_repository.get_latest_price_dates(db)
    signal_dates = await signals_repository.get_latest_computed_at_by_asset(db)
    consensus_dates = await analyst_repository.get_latest_fetched_at_by_asset(db)

    return [
        {
            "id": asset.id,
            "ticker": asset.ticker,
            "name": asset.name,
            "market": asset.market,
            "last_price_date": price_dates.get(asset.id),
            "last_signal_computed_at": signal_dates.get(asset.id),
            "last_consensus_fetched_at": consensus_dates.get(asset.id),
        }
        for asset in assets
    ]


async def discover_candidates(db: AsyncSession, limit: int = 10) -> list[dict]:
    """
    Suggestions de titres non suivis, jamais un ajout automatique (voir
    discovery.py pour la justification et les sources). L'utilisateur
    consulte cette liste et decide lui-meme s'il ajoute un candidat via
    POST /api/v1/assets - rien n'est jamais ecrit en base par cette fonction.
    """
    tracked = await repository.get_tracked_tickers(db)
    return await discovery.discover_candidates(tracked, max_candidates=limit)


async def seed_everything(db: AsyncSession) -> dict:
    """Enchaine tous les seed_xxx ci-dessus en une seule requete - pratique
    pour peupler une base fraiche au maximum de la couverture disponible
    (BEL20 + CAC40 + DAX40 + AEX + megacaps US + panier crypto Binance)."""
    return {
        "bel20": await seed_bel20(db),
        "cac40": await seed_cac40(db),
        "dax40": await seed_dax40(db),
        "aex": await seed_aex(db),
        "us_majors": await seed_us_majors(db),
        "binance_majors": await seed_binance_majors(db),
    }
