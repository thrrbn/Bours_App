"""Interface abstraite d'un fournisseur de donnees de marche.

Toute nouvelle source (Yahoo Finance, Stooq, un futur fournisseur payant...)
implemente ce contrat unique, ce qui permet de changer de fournisseur sans
modifier le reste du domaine market_data (service, repository, router).
"""
from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import date


@dataclass
class PriceBarDTO:
    trade_date: date
    open: float
    high: float
    low: float
    close: float
    adjusted_close: float | None
    volume: int


class MarketDataProvider(ABC):
    @abstractmethod
    async def fetch_history(self, ticker: str, start: date, end: date) -> list[PriceBarDTO]:
        """Retourne l'historique de prix pour un ticker sur la periode demandee."""
