"""
Endpoint de maintenance : declenche a la demande, en une seule requete, la
meme sequence que les jobs planifies (prix -> news -> signaux -> consensus
analystes), pour ne pas attendre les horaires cron (06h00/06h30/07h00) quand
on vient d'ajouter plusieurs actifs d'un coup (ex. seed BEL20).

Reutilise directement les fonctions de jobs/ - aucune logique dupliquee, et
le comportement planifie reste strictement identique.
"""
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.domains.assets import service as assets_service
from app.jobs.compute_signals_job import compute_signals_job
from app.jobs.credit_dividends_job import credit_dividends_job
from app.jobs.ingest_news_job import ingest_news_job
from app.jobs.ingest_prices_job import ingest_prices_job
from app.jobs.refresh_analyst_ratings_job import refresh_analyst_ratings_job

router = APIRouter(prefix="/api/v1/maintenance", tags=["maintenance"])


@router.post("/seed-bel20")
async def seed_bel20(db: AsyncSession = Depends(get_db)):
    """
    Insere les 20 composants du BEL20 dans `assets` (idempotent, rejouable).

    Necessaire car `alembic upgrade head` (chemin canonique depuis le
    25/07/2026, voir README.md) ne cree que le schema, jamais de donnees :
    db/migrations/004_bel20_seed.sql n'est joue automatiquement que par
    Postgres au tout premier demarrage d'un volume vide (docker-entrypoint-
    initdb.d). Sans cet appel (ou l'equivalent SQL manuel), la table `assets`
    reste vide et /api/v1/assets, /api/v1/assets/search ne renvoient rien -
    c'est le symptome "l'application ne trouve pas les actifs".
    """
    return await assets_service.seed_bel20(db)


@router.post("/seed-binance-majors")
async def seed_binance_majors(db: AsyncSession = Depends(get_db)):
    """
    Insere un panier de cryptomonnaies majeures (BTC, ETH, BNB, SOL, XRP,
    ADA, DOGE, AVAX - paires USDT) dans `assets` (idempotent, rejouable).
    Donnees ensuite alimentees via l'API publique Binance (/api/v3/klines,
    sans cle API) au meme titre que les actions BEL20 le sont via Yahoo
    Finance - voir market_data/providers/binance.py. Aucun ordre reel n'est
    jamais passe par ce projet.
    """
    return await assets_service.seed_binance_majors(db)


@router.post("/seed-us-majors")
async def seed_us_majors(db: AsyncSession = Depends(get_db)):
    """Insere un panier de grandes capitalisations americaines (~34 valeurs
    NASDAQ/NYSE) dans `assets` (idempotent, rejouable). Ingestion ensuite via
    Yahoo Finance, comme le BEL20."""
    return await assets_service.seed_us_majors(db)


@router.post("/seed-cac40")
async def seed_cac40(db: AsyncSession = Depends(get_db)):
    """Insere l'indice CAC 40 (Euronext Paris, ~39 valeurs) dans `assets`
    (idempotent, rejouable)."""
    return await assets_service.seed_cac40(db)


@router.post("/seed-dax40")
async def seed_dax40(db: AsyncSession = Depends(get_db)):
    """Insere l'indice DAX 40 (Xetra / Francfort, ~39 valeurs) dans `assets`
    (idempotent, rejouable)."""
    return await assets_service.seed_dax40(db)


@router.post("/seed-aex")
async def seed_aex(db: AsyncSession = Depends(get_db)):
    """Insere l'indice AEX (Euronext Amsterdam, 25 valeurs) dans `assets`
    (idempotent, rejouable)."""
    return await assets_service.seed_aex(db)


@router.post("/seed-everything")
async def seed_everything(db: AsyncSession = Depends(get_db)):
    """
    Enchaine tous les seed_xxx en une seule requete : BEL20 + CAC40 + DAX40 +
    AEX + megacaps US + panier crypto Binance (~200 actifs au total).
    Idempotent, rejouable sans risque. Ne fait qu'inserer des lignes `assets`
    - lance ensuite POST /api/v1/market-data/refresh-all pour ingerer les
    prix (peut prendre plusieurs minutes vu le volume et la contrainte de
    debit Yahoo Finance, voir docs/17-limites-legales-techniques.md).
    """
    return await assets_service.seed_everything(db)


@router.post("/refresh-all")
async def refresh_all():
    """
    Sequentiel et volontairement lent (pas de parallelisation) : Yahoo Finance
    bloque les rafales de requetes (429), voir docs/17. Prevoir 30s-1min pour
    20 actifs.
    """
    prices = await ingest_prices_job()
    news = await ingest_news_job()
    signals = await compute_signals_job()
    analyst = await refresh_analyst_ratings_job()
    dividends = await credit_dividends_job()

    return {
        "prices": prices,
        "news": news,
        "signals": signals,
        "analyst": analyst,
        "dividends": dividends,
    }


@router.post("/credit-dividends")
async def credit_dividends():
    """
    Declenche a la demande le credit des dividendes detaches depuis le
    dernier passage (voir jobs/credit_dividends_job.py) - utile pour tester
    sans attendre l'horaire cron (06h45).
    """
    return await credit_dividends_job()
