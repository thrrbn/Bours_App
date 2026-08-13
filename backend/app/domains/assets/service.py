"""Logique metier du domaine assets : recherche, normalisation, resolution de marche."""
import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.exceptions import AssetNotFoundError, ConflictError, DataProviderError
from app.domains.analyst import repository as analyst_repository
from app.domains.assets import discovery, fundamentals_provider, fundamentals_repository, repository
from app.domains.assets.fundamentals_models import AssetFundamentals
from app.domains.assets.models import Asset
from app.domains.assets.schemas import (
    AssetCreate,
    AssetLookupRead,
    SectorComparisonRead,
    SectorPeerAverage,
    SectorPeerRead,
)
from app.domains.assets.seed_data import BEL20_ASSETS
from app.domains.assets.seed_data_aex import AEX_ASSETS
from app.domains.assets.seed_data_binance import BINANCE_MAJORS_ASSETS
from app.domains.assets.seed_data_cac40 import CAC40_ASSETS
from app.domains.assets.seed_data_dax import DAX40_ASSETS
from app.domains.assets.seed_data_us import US_MAJORS_ASSETS
from app.domains.market_data import repository as market_data_repository
from app.domains.portfolio import repository as portfolio_repository
from app.domains.signals import repository as signals_repository
from app.domains.watchlist import repository as watchlist_repository


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
        if not existing.is_active:
            # Reactivation : l'actif avait ete retire (voir delete_asset)
            # mais son historique (prix/signaux/news) est reste en base -
            # on le rend juste de nouveau visible/rafraichi, plutot que de
            # creer un doublon bloque par la contrainte uq_asset_ticker_market.
            return await repository.set_active(db, existing, True)
        return existing
    return await repository.create(db, payload)


async def delete_asset(db: AsyncSession, asset_id: uuid.UUID) -> None:
    """
    Retire un actif de la liste (desactivation, PAS une suppression physique
    - l'historique de prix/signaux/news reste en base, voir repository.py::
    set_active) pour alleger l'univers effectivement traite par les jobs
    planifies (ingest_prices/news, compute_signals, refresh_analyst_ratings,
    daily_briefing - tous filtrent deja sur is_active=True, voir
    repository.list_all). Refuse (409) si l'actif est encore detenu en
    portefeuille virtuel : vendre la position avant de le retirer, pour ne
    pas laisser une position "orpheline" sans plus aucun prix/signal frais.
    """
    asset = await get_asset_or_raise(db, asset_id)

    position = await portfolio_repository.get_position(db, asset_id)
    if position is not None and float(position.quantity) > 0:
        raise ConflictError(
            f"{asset.ticker} est encore detenu en portefeuille virtuel ({position.quantity} unites) - "
            "vends la position avant de retirer ce titre."
        )

    watchlist_item = await watchlist_repository.get_by_asset_id(db, asset_id)
    if watchlist_item is not None:
        await watchlist_repository.remove(db, watchlist_item)

    await repository.set_active(db, asset, False)


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


async def get_fundamentals(db: AsyncSession, asset_id: uuid.UUID) -> AssetFundamentals | None:
    """None si jamais rafraichi pour ce titre (voir POST
    /assets/{id}/fundamentals/refresh) - pas une erreur, juste "pas encore
    consulte"."""
    await get_asset_or_raise(db, asset_id)  # 404 si l'actif lui-meme n'existe pas
    return await fundamentals_repository.get_by_asset(db, asset_id)


async def refresh_fundamentals(db: AsyncSession, asset_id: uuid.UUID) -> AssetFundamentals:
    """Va chercher les fondamentaux actuels sur Yahoo Finance et les
    remplace (upsert) - meme pattern que analyst/service.py::refresh_for_asset,
    a la demande plutot que planifie (pas de cron dedie pour l'instant)."""
    asset = await get_asset_or_raise(db, asset_id)
    dto = fundamentals_provider.fetch_fundamentals(asset.ticker)
    return await fundamentals_repository.upsert(
        db,
        asset_id,
        sector=dto.sector,
        industry=dto.industry,
        market_cap=dto.market_cap,
        trailing_pe=dto.trailing_pe,
        forward_pe=dto.forward_pe,
        dividend_yield=dto.dividend_yield,
        week52_low=dto.week52_low,
        week52_high=dto.week52_high,
        beta=dto.beta,
        business_summary=dto.business_summary,
        return_on_equity=dto.return_on_equity,
        debt_to_equity=dto.debt_to_equity,
        profit_margin=dto.profit_margin,
        price_to_book=dto.price_to_book,
        ev_to_ebitda=dto.ev_to_ebitda,
    )


async def get_sector_comparison(db: AsyncSession, asset_id: uuid.UUID) -> SectorComparisonRead:
    """Compare le PER/rendement/capitalisation de ce titre a la MOYENNE des
    autres actifs suivis du meme secteur DONT les fondamentaux ont deja ete
    rafraichis (voir fundamentals_repository.py::list_by_sector) - aucun
    appel Yahoo Finance supplementaire ici, la comparaison s'enrichit
    seulement au fil des rafraichissements deja demandes par l'utilisateur
    sur d'autres titres."""
    asset = await get_asset_or_raise(db, asset_id)
    fundamentals = await fundamentals_repository.get_by_asset(db, asset_id)
    sector = fundamentals.sector if fundamentals and fundamentals.sector else asset.sector

    if not sector:
        return SectorComparisonRead(
            asset=asset,
            this_trailing_pe=fundamentals.trailing_pe if fundamentals else None,
            this_dividend_yield=fundamentals.dividend_yield if fundamentals else None,
            this_market_cap=fundamentals.market_cap if fundamentals else None,
            peers=None,
            peer_list=[],
            note="Secteur inconnu pour ce titre - rafraichis d'abord ses fondamentaux.",
        )

    peers = await fundamentals_repository.list_by_sector(db, sector, asset_id)
    if not peers:
        peer_avg = None
        peer_list = []
        note = (
            f"Aucun autre actif suivi du secteur « {sector} » n'a encore de fondamentaux rafraichis - "
            "rafraichis-en d'autres pour enrichir la comparaison."
        )
    else:

        def _avg(values: list[float]) -> float | None:
            return round(sum(values) / len(values), 4) if values else None

        pe_values = [p.trailing_pe for p in peers if p.trailing_pe is not None]
        yield_values = [p.dividend_yield for p in peers if p.dividend_yield is not None]
        cap_values = [p.market_cap for p in peers if p.market_cap is not None]
        roe_values = [p.return_on_equity for p in peers if p.return_on_equity is not None]
        de_values = [p.debt_to_equity for p in peers if p.debt_to_equity is not None]
        margin_values = [p.profit_margin for p in peers if p.profit_margin is not None]
        pb_values = [p.price_to_book for p in peers if p.price_to_book is not None]
        ev_ebitda_values = [p.ev_to_ebitda for p in peers if p.ev_to_ebitda is not None]
        peer_avg = SectorPeerAverage(
            sector=sector,
            peer_count=len(peers),
            avg_trailing_pe=_avg(pe_values),
            avg_dividend_yield=_avg(yield_values),
            avg_market_cap=round(sum(cap_values) / len(cap_values), 0) if cap_values else None,
            avg_return_on_equity=_avg(roe_values),
            avg_debt_to_equity=_avg(de_values),
            avg_profit_margin=_avg(margin_values),
            avg_price_to_book=_avg(pb_values),
            avg_ev_to_ebitda=_avg(ev_ebitda_values),
        )
        # 13/08/2026 : liste des pairs INDIVIDUELS (pas seulement la moyenne) -
        # demande explicite de l'utilisateur. `p.asset` deja charge en eager
        # (lazy="joined", voir fundamentals_models.py) - pas de requete
        # supplementaire par pair.
        peer_list = [
            SectorPeerRead(
                asset_id=p.asset_id,
                ticker=p.asset.ticker,
                name=p.asset.name,
                trailing_pe=p.trailing_pe,
                dividend_yield=p.dividend_yield,
                market_cap=p.market_cap,
                return_on_equity=p.return_on_equity,
                debt_to_equity=p.debt_to_equity,
                profit_margin=p.profit_margin,
                price_to_book=p.price_to_book,
                ev_to_ebitda=p.ev_to_ebitda,
            )
            for p in sorted(peers, key=lambda p: p.asset.ticker)
        ]
        note = f"Comparaison basee sur {len(peers)} autre(s) actif(s) suivi(s) du secteur « {sector} » (fondamentaux deja rafraichis)."

    return SectorComparisonRead(
        asset=asset,
        this_trailing_pe=fundamentals.trailing_pe if fundamentals else None,
        this_dividend_yield=fundamentals.dividend_yield if fundamentals else None,
        this_market_cap=fundamentals.market_cap if fundamentals else None,
        peers=peer_avg,
        peer_list=peer_list,
        note=note,
    )


async def lookup_ticker(db: AsyncSession, ticker: str) -> AssetLookupRead:
    """Recherche live sur Yahoo Finance d'un ticker PAS forcement suivi (voir
    router.py: GET /assets/lookup) - contrairement a search_assets() qui ne
    cherche que dans les actifs deja en base. Leve DataProviderError (502) si
    Yahoo ne connait pas ce ticker - a l'utilisateur de corriger l'orthographe
    ou le suffixe de place (.PA, .BR, .DE, .AS...)."""
    normalized = ticker.strip().upper()
    if not normalized:
        raise DataProviderError("Ticker vide.")

    dto = fundamentals_provider.fetch_fundamentals(normalized)
    existing = await repository.get_by_ticker_any_market(db, normalized)

    return AssetLookupRead(
        ticker=normalized,
        name=dto.name,
        market_guess=dto.market_guess,
        currency=dto.currency,
        sector=dto.sector,
        industry=dto.industry,
        last_price=dto.last_price,
        market_cap=dto.market_cap,
        already_tracked_id=existing.id if existing else None,
    )


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
