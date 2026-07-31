"""
Calcul des indicateurs techniques (SMA, EMA, RSI, MACD, Bollinger, volatilite,
momentum) a partir de l'historique de prix, et orchestration de l'ingestion.
"""
import uuid
from datetime import date, timedelta

import numpy as np
import pandas as pd
from sqlalchemy.ext.asyncio import AsyncSession

from app.domains.market_data import repository
from app.domains.market_data.providers.base import MarketDataProvider
from app.domains.market_data.providers.binance import BinanceProvider
from app.domains.market_data.providers.yahoo_finance import YahooFinanceProvider

_yahoo_provider = YahooFinanceProvider()
_binance_provider = BinanceProvider()

# Choix du provider (et du libelle "source" trace sur chaque price_bar, voir
# repository.upsert_price_bars) selon le marche de l'actif. "BINANCE" -> API
# publique Binance (crypto, tickers style "BTCUSDT") ; tout le reste ->
# Yahoo Finance (actions/ETF, comportement historique inchange). Point
# d'extension unique si un jour un troisieme fournisseur s'ajoute - jobs/
# ingest_prices_job.py et market_data/router.py passent tous les deux par
# cette fonction, aucune logique de selection dupliquee.
_PROVIDERS_BY_MARKET: dict[str, tuple[MarketDataProvider, str]] = {
    "BINANCE": (_binance_provider, "binance"),
}
_DEFAULT_PROVIDER: tuple[MarketDataProvider, str] = (_yahoo_provider, "yahoo_finance")


def provider_for_market(market: str) -> tuple[MarketDataProvider, str]:
    return _PROVIDERS_BY_MARKET.get(market, _DEFAULT_PROVIDER)


async def ingest_history(
    db: AsyncSession,
    asset_id: uuid.UUID,
    ticker: str,
    provider: MarketDataProvider,
    days_back: int = 400,
    source: str = "yahoo_finance",
) -> int:
    """Recupere l'historique manquant et l'upsert en base. Retourne le nombre de barres inserees.

    `source` doit correspondre au provider passe (ex. "binance" avec
    BinanceProvider) - trace la provenance de chaque price_bar (voir
    jobs/ingest_prices_job.py qui choisit le couple provider/source par
    asset.market)."""
    end = date.today()
    start = end - timedelta(days=days_back)
    bars = await provider.fetch_history(ticker, start, end)
    if not bars:
        return 0
    await repository.upsert_price_bars(db, asset_id, bars, source=source)
    return len(bars)


def _rsi(closes: pd.Series, period: int = 14) -> pd.Series:
    delta = closes.diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)
    avg_gain = gain.rolling(period).mean()
    avg_loss = loss.rolling(period).mean()

    rs = avg_gain / avg_loss.replace(0, np.nan)
    rsi = 100 - (100 / (1 + rs))
    # Cas limites non couverts par la formule generale (division par zero
    # quand il n'y a aucune perte sur la periode) :
    rsi = rsi.mask((avg_loss == 0) & (avg_gain > 0), 100.0)  # aucune perte -> RSI maximal
    rsi = rsi.mask((avg_loss == 0) & (avg_gain == 0), 50.0)  # aucun mouvement de prix -> neutre
    return rsi


def compute_indicators_dataframe(price_history: pd.DataFrame) -> pd.DataFrame:
    """
    Prend un DataFrame indexe par date avec une colonne 'close' et retourne les
    indicateurs techniques calcules, jour par jour. Fonction pure, testable
    independamment de la base de donnees.
    """
    df = price_history.copy()
    df["sma_20"] = df["close"].rolling(20).mean()
    df["sma_50"] = df["close"].rolling(50).mean()
    df["sma_200"] = df["close"].rolling(200).mean()
    df["ema_12"] = df["close"].ewm(span=12, adjust=False).mean()
    df["ema_26"] = df["close"].ewm(span=26, adjust=False).mean()
    df["macd"] = df["ema_12"] - df["ema_26"]
    df["macd_signal"] = df["macd"].ewm(span=9, adjust=False).mean()
    df["rsi_14"] = _rsi(df["close"], 14)

    rolling_std = df["close"].rolling(20).std()
    df["bollinger_upper"] = df["sma_20"] + 2 * rolling_std
    df["bollinger_lower"] = df["sma_20"] - 2 * rolling_std

    daily_returns = df["close"].pct_change()
    df["volatility_20d"] = daily_returns.rolling(20).std()
    df["momentum_roc_20"] = df["close"].pct_change(periods=20)

    return df


async def compute_and_store_indicators(db: AsyncSession, asset_id: uuid.UUID) -> int:
    """Recharge l'historique de prix stocke, recalcule les indicateurs, les persiste."""
    price_rows = await repository.get_price_history(db, asset_id)
    if len(price_rows) < 20:
        return 0  # pas assez d'historique pour un calcul fiable (SMA20 minimum)

    df = (
        pd.DataFrame([{"trade_date": row.trade_date, "close": float(row.close)} for row in price_rows])
        .set_index("trade_date")
        .sort_index()
    )

    indicators_df = compute_indicators_dataframe(df)
    await repository.upsert_indicators(db, asset_id, indicators_df)
    return len(indicators_df)


# Approximation en jours ouvres (pas calendaires) - alignee sur les horizons
# habituels des analystes externes (1/3/6/12 mois), pour donner un point de
# comparaison honnete a la tendance REELLE passee (jamais une prediction).
_TRADING_DAYS_PER_WINDOW = {"return_1m": 21, "return_3m": 63, "return_6m": 126, "return_12m": 252}


def _adjusted_or_close(bar) -> float:
    """
    Etape 19 : le RENDEMENT (pourcentage de variation) doit se baser sur le
    cours ajuste des dividendes/splits, sinon un detachement de dividende
    simule une fausse baisse. `latest_price` affiche, lui, reste le cours
    brut (celui reellement cote aujourd'hui) - seul le calcul du % change.
    """
    return float(bar.adjusted_close) if bar.adjusted_close is not None else float(bar.close)


async def compute_historical_trend(db: AsyncSession, asset_id: uuid.UUID) -> dict:
    """
    Rendement reel sur les fenetres passees 1/3/6/12 mois, calcule a partir
    des price_bars stockes. Retourne None pour une fenetre si l'historique
    disponible est trop court (frequent pour un actif tout juste ajoute).
    """
    bars = await repository.get_price_history(db, asset_id, limit=280)  # ~12 mois de jours ouvres + marge
    if not bars:
        return {"latest_price": None, "latest_date": None, **{k: None for k in _TRADING_DAYS_PER_WINDOW}}

    bars = sorted(bars, key=lambda b: b.trade_date, reverse=True)  # plus recent d'abord
    latest = bars[0]

    result: dict = {"latest_price": float(latest.close), "latest_date": latest.trade_date}
    latest_return_price = _adjusted_or_close(latest)
    for key, days_back in _TRADING_DAYS_PER_WINDOW.items():
        if len(bars) > days_back:
            past_price = _adjusted_or_close(bars[days_back])
            result[key] = (
                round((latest_return_price - past_price) / past_price * 100, 2) if past_price else None
            )
        else:
            result[key] = None
    return result
