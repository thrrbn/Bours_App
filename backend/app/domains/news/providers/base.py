"""Interface abstraite d'un fournisseur d'actualites financieres."""
from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime


@dataclass
class NewsArticleDTO:
    source: str
    title: str
    url: str
    published_at: datetime
    raw_content: str | None = None


class NewsProvider(ABC):
    @abstractmethod
    async def fetch_articles(self, ticker: str, company_name: str) -> list[NewsArticleDTO]:
        """Retourne les articles recents mentionnant le ticker/l'entreprise."""
