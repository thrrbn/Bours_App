"""
Script d'IMPORT manuel (16/08/2026, voir docs/20-instance-locale-pc-mac.md) -
PAS un job planifie recurrent (n'est jamais enregistre dans jobs/scheduler.py),
a executer a la main depuis un terminal sur le PC/Mac de l'utilisateur.

Peuple la base de donnees LOCALE (assets + price_bars) a partir de l'API
publique en LECTURE SEULE du NAS deploye - meme sens de circulation des
donnees que tools/shared/nas_api_client.py (le NAS n'est jamais appele par
autre chose qu'une lecture, jamais l'inverse). Necessaire pour que la page
"Analyste IA" de l'instance locale ait des prix a analyser : sans cet
import, `assets`/`price_bars` restent vides sur une base fraichement migree
(alembic upgrade head cree uniquement le schema, jamais de donnees - meme
avertissement que le README principal pour /maintenance/seed-bel20).

Limite connue (heritee de tools/shared/nas_api_client.py) : l'API publique
n'expose pas le cours ajuste des dividendes/splits (`adjusted_close`) - les
barres importees ont `adjusted_close=None`. `kernc_engine.py::_load_price_dataframe`
retombe alors sur le cours brut pour ces barres (facteur d'ajustement 1.0) -
memes resultats que tools/backtest_analyst/ pour les tickers importes de
cette facon, jusqu'a ce qu'un futur re-telechargement direct (ex. via
ingest_prices_job, qui lui utilise Yahoo Finance et calcule adjusted_close)
ne les remplace.

Usage (depuis backend/, environnement virtuel active) :
    python -m app.jobs.import_from_nas --nas-url http://192.168.88.10:8082
    python -m app.jobs.import_from_nas --nas-url http://192.168.88.10:8082 --market EURONEXT_BRUSSELS
"""
import argparse
import asyncio
import logging
from datetime import date

import httpx

from app.database import AsyncSessionLocal
from app.domains.assets import repository as assets_repository
from app.domains.assets.schemas import AssetCreate
from app.domains.market_data import repository as market_data_repository
from app.domains.market_data.providers.base import PriceBarDTO

logger = logging.getLogger(__name__)


def _fetch_json(nas_url: str, path: str, params: dict | None = None) -> object:
    url = f"{nas_url.rstrip('/')}/api/v1{path}"
    response = httpx.get(url, params=params, timeout=30.0)
    response.raise_for_status()
    return response.json()


def _dto_from_row(row: dict) -> PriceBarDTO | None:
    try:
        return PriceBarDTO(
            trade_date=date.fromisoformat(row["trade_date"]),
            open=float(row["open"]),
            high=float(row["high"]),
            low=float(row["low"]),
            close=float(row["close"]),
            adjusted_close=None,  # non expose par l'API publique, voir docstring de module
            volume=int(row.get("volume") or 0),
        )
    except (KeyError, TypeError, ValueError):
        return None


async def import_from_nas(nas_url: str, market: str | None = None, sector: str | None = None) -> dict:
    params = {k: v for k, v in {"market": market, "sector": sector}.items() if v}
    remote_assets = _fetch_json(nas_url, "/assets", params=params or None)

    assets_created = 0
    assets_seen_bars = 0
    total_bars = 0
    errors: list[str] = []

    async with AsyncSessionLocal() as db:
        for remote in remote_assets:
            ticker = remote.get("ticker", "?")
            try:
                local = await assets_repository.get_by_ticker(db, remote["ticker"], remote["market"])
                if local is None:
                    local = await assets_repository.create(
                        db,
                        AssetCreate(
                            ticker=remote["ticker"],
                            name=remote["name"],
                            market=remote["market"],
                            sector=remote.get("sector"),
                            currency=remote.get("currency") or "EUR",
                            isin=remote.get("isin"),
                        ),
                    )
                    assets_created += 1

                rows = _fetch_json(nas_url, f"/market-data/{remote['id']}/prices")
                bars = [dto for row in rows if (dto := _dto_from_row(row)) is not None]
                await market_data_repository.upsert_price_bars(db, local.id, bars, source="nas_import")
                total_bars += len(bars)
                assets_seen_bars += 1
                logger.info("Importe %s : %d barres.", ticker, len(bars))
            except Exception as exc:
                logger.exception("Echec import pour %s", ticker)
                errors.append(f"{ticker}: {exc}")

    return {
        "assets_seen": len(remote_assets),
        "assets_created": assets_created,
        "assets_with_prices": assets_seen_bars,
        "bars_imported": total_bars,
        "errors": errors,
    }


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Importe assets + prix depuis l'API publique en lecture seule d'un NAS deploye, vers la "
        "base de donnees LOCALE de cette instance PC/Mac (voir docs/20-instance-locale-pc-mac.md)."
    )
    parser.add_argument("--nas-url", required=True, help="Ex: http://192.168.1.50:8082 (port du BACKEND, pas 5174)")
    parser.add_argument("--market", default=None, help="Filtre optionnel (ex: EURONEXT_BRUSSELS)")
    parser.add_argument("--sector", default=None, help="Filtre optionnel")
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(message)s")
    result = asyncio.run(import_from_nas(args.nas_url, args.market, args.sector))

    print(
        f"\n{result['assets_seen']} actif(s) vu(s) sur le NAS - {result['assets_created']} nouveau(x) cree(s) "
        f"en local - {result['bars_imported']} barre(s) de prix importee(s) sur {result['assets_with_prices']} "
        f"actif(s)."
    )
    if result["errors"]:
        print(f"\n{len(result['errors'])} erreur(s) :")
        for err in result["errors"]:
            print(f"  - {err}")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
