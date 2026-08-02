"""
Page "Marche" (01/08/2026, revu le meme jour) - photo du marche du moment,
TOUJOURS EN DIRECT depuis des sources externes de reference (Yahoo Finance,
Binance - voir provider.py), jamais limitee aux actifs personnellement
suivis dans cette application. Rafraichie par un job planifie 3x/jour (7h,
12h, 17h - voir jobs/market_overview_job.py et docs/STACK.md). UNE ligne par
rafraichissement (historique conserve, contrairement a asset_fundamentals
qui n'a qu'une ligne par actif) - permet eventuellement de comparer
plusieurs "photos" dans le temps plus tard, sans avoir a re-designer le
schema.

indices/movers en JSONB plutot que des tables normalisees : ce sont des
listes courtes et homogenes (6 indices, ~30 mouvements), recalculees en bloc
a chaque rafraichissement (jamais mises a jour ligne par ligne) - le meme
choix pragmatique que analysis_lab/db_models.py::TrainingJob.result ou
backtests/models.py::BacktestRun.extra_metrics.
"""
import uuid
from datetime import datetime

from sqlalchemy import DateTime, func
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.database import Base


class MarketSnapshot(Base):
    __tablename__ = "market_snapshots"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    captured_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), index=True)
    # Liste de dicts (voir provider.py::fetch_index_quotes) : ticker, label,
    # zone, last_price, change_pct, currency.
    indices: Mapped[list] = mapped_column(JSONB, nullable=False)
    # Dict {"FR": {...}, "US": {...}, "CRYPTO": {...}}, chaque valeur etant
    # {"gainers": [...], "losers": [...]} - chaque ligne inclut une URL vers
    # la fiche de cotation Yahoo Finance/Binance d'origine (voir
    # provider.py::yahoo_quote_url/binance_trade_url). Donnees LIVE (screener
    # Yahoo Finance US, cotations CAC 40 en direct, /ticker/24hr Binance),
    # pas une cloture differee comme dans une version anterieure de cette
    # page - voir provider.py pour le detail complet des sources.
    movers: Mapped[dict] = mapped_column(JSONB, nullable=False)
