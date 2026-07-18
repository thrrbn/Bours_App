"""
Recuperation du consensus d'analystes via yfinance (Ticker.recommendations).
Comme yahoo_finance.py (market_data), ceci consomme un endpoint Yahoo non
contractuel - isole ici pour absorber un eventuel changement de format sans
toucher au reste du domaine (voir docs/17).
"""
import yfinance as yf

from app.core.exceptions import DataProviderError


class ConsensusDTO:
    def __init__(self, strong_buy: int, buy: int, hold: int, sell: int, strong_sell: int):
        self.strong_buy = strong_buy
        self.buy = buy
        self.hold = hold
        self.sell = sell
        self.strong_sell = strong_sell


def fetch_consensus(ticker: str) -> ConsensusDTO | None:
    """Retourne le consensus le plus recent (periode '0m') ou None si Yahoo
    n'a aucune couverture analyste pour ce titre (frequent sur les valeurs
    europeennes de taille moyenne - voir docs/17)."""
    try:
        recommendations = yf.Ticker(ticker).recommendations
    except Exception as exc:
        raise DataProviderError(f"Echec de recuperation du consensus analystes pour {ticker}: {exc}") from exc

    if recommendations is None or recommendations.empty:
        return None

    current = recommendations[recommendations["period"] == "0m"]
    if current.empty:
        current = recommendations.iloc[[0]]  # a defaut de '0m', on prend la ligne la plus recente disponible

    row = current.iloc[0]
    return ConsensusDTO(
        strong_buy=int(row["strongBuy"]),
        buy=int(row["buy"]),
        hold=int(row["hold"]),
        sell=int(row["sell"]),
        strong_sell=int(row["strongSell"]),
    )
