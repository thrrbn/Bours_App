from datetime import date

from pydantic import BaseModel, ConfigDict


class PriceBarRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    trade_date: date
    open: float
    high: float
    low: float
    close: float
    volume: int


class TechnicalIndicatorRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    trade_date: date
    sma_20: float | None
    sma_50: float | None
    sma_200: float | None
    rsi_14: float | None
    macd: float | None
    macd_signal: float | None
    bollinger_upper: float | None
    bollinger_lower: float | None
    volatility_20d: float | None
    momentum_roc_20: float | None


class HistoricalTrendRead(BaseModel):
    """
    Rendement REEL passe (pas une prediction) sur des fenetres calquees sur
    les horizons habituels des analystes externes (1/3/6/12 mois), calcule
    directement a partir des prix connus - jamais une projection future.
    None quand l'historique disponible est trop court pour cette fenetre
    (frequent pour les actifs tout juste ajoutes).
    """

    latest_price: float | None
    latest_date: date | None
    return_1m: float | None
    return_3m: float | None
    return_6m: float | None
    return_12m: float | None
