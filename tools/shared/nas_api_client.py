"""
Client HTTP en LECTURE SEULE vers l'API publique de Bourse Assistant
(14/08/2026, factorise depuis tools/backtest_analyst/ le meme jour - voir
docs/19-outils-pc-autonomes.md pour le principe general).

Partage entre TOUS les outils autonomes PC/Mac de tools/ - jamais
d'ecriture, jamais d'acces direct a la base Postgres du NAS. Chaque outil
qui a besoin de lire des donnees deja suivies dans l'application (prix,
tickers) doit passer par ce module plutot que de recopier son propre client
HTTP - voir docs/19-outils-pc-autonomes.md, "contrat" section 2.

Limite connue et documentee (a ne jamais oublier en lisant un rapport
genere par un outil qui utilise ce client) : l'endpoint public
GET /market-data/{id}/prices n'expose PAS le cours ajuste des dividendes/
splits (`adjusted_close`, colonne interne uniquement, voir
backend/app/domains/market_data/schemas.py::PriceBarRead) - seul le cours
brut `close` est disponible ici. Le moteur interne de l'application
(kernc_engine.py::_load_price_dataframe) retraite Open/High/Low/Close par
ce facteur d'ajustement avant de lancer backtesting.py ; ce client ne le
fait PAS. Consequence concrete : sur un titre versant des dividendes
reguliers, un backtest local via ce client peut legerement differer de
celui affiche par "tester les parametres" dans l'application - un ecart
de quelques % de rendement sur plusieurs annees n'est pas anormal.
"""
from __future__ import annotations

from datetime import date

import httpx
import pandas as pd


class ApiClientError(Exception):
    pass


class BourseApiClient:
    def __init__(self, base_url: str, timeout: float = 30.0):
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout

    def _get(self, path: str, params: dict | None = None) -> object:
        url = f"{self.base_url}/api/v1{path}"
        try:
            response = httpx.get(url, params=params, timeout=self.timeout)
            response.raise_for_status()
        except httpx.ConnectError as exc:
            raise ApiClientError(
                f"Impossible de joindre l'API sur {self.base_url} - verifie l'URL et que le NAS est accessible "
                f"depuis ce PC (meme reseau local, ou VPN). Rappel : c'est le port du BACKEND (ex: 8082 sur un "
                f"NAS deploye via docker-compose.yml), pas le port du site web (5174)."
            ) from exc
        except httpx.HTTPStatusError as exc:
            raise ApiClientError(f"Erreur HTTP {exc.response.status_code} sur {url}") from exc
        return response.json()

    def resolve_ticker(self, ticker: str) -> dict:
        """Retourne le premier resultat de recherche correspondant a ce
        ticker parmi les actifs deja suivis dans l'application (ne fait PAS
        de recherche live Yahoo Finance - l'actif doit deja etre suivi,
        voir GET /assets/lookup cote backend si un jour un outil a besoin
        de la recherche live plutot que des actifs deja suivis)."""
        results = self._get("/assets/search", params={"q": ticker})
        if not results:
            raise ApiClientError(
                f"Aucun actif suivi ne correspond a '{ticker}' - verifie l'orthographe exacte du ticker "
                f"(ex: MC.PA, SOLB.BR), ou ajoute-le d'abord dans l'application (page Recherche)."
            )
        exact = [r for r in results if r["ticker"].upper() == ticker.upper()]
        return exact[0] if exact else results[0]

    def fetch_price_history(self, asset_id: str, period_start: date, period_end: date) -> pd.DataFrame:
        """DataFrame OHLCV compatible backtesting.py (colonnes Open/High/Low/
        Close/Volume, index datetime croissant), filtre sur la periode
        demandee - l'API ne supporte pas de filtre par date cote serveur
        (voir docstring de module), le filtrage se fait donc ici cote
        client apres recuperation de l'historique complet."""
        rows = self._get(f"/market-data/{asset_id}/prices")
        if not rows:
            raise ApiClientError("Aucun historique de prix disponible pour cet actif.")

        df = pd.DataFrame(rows)
        df["trade_date"] = pd.to_datetime(df["trade_date"])
        df = df.set_index("trade_date").sort_index()
        df = df.loc[str(period_start) : str(period_end)]
        df = df.rename(columns={"open": "Open", "high": "High", "low": "Low", "close": "Close", "volume": "Volume"})
        return df[["Open", "High", "Low", "Close", "Volume"]]

    def list_tracked_assets(self, market: str | None = None, sector: str | None = None) -> list[dict]:
        """Tous les actifs suivis (GET /assets), avec filtres optionnels -
        utile a un futur outil qui doit parcourir tout ou partie de
        l'univers suivi plutot qu'un seul ticker a la fois."""
        params = {k: v for k, v in {"market": market, "sector": sector}.items() if v is not None}
        return self._get("/assets", params=params or None)
