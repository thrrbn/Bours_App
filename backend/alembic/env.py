"""Configuration Alembic - utilise la meme Base et les memes settings que l'application."""
import asyncio
import os
import sys
from logging.config import fileConfig

from alembic import context
from sqlalchemy import pool
from sqlalchemy.ext.asyncio import async_engine_from_config

# Bug reel trouve le 31/07/2026 : `alembic` est invoque via son script console
# (/usr/local/bin/alembic dans le conteneur, ou l'executable Windows en local),
# qui n'ajoute PAS automatiquement le repertoire courant a sys.path - contrairement
# a `python -m alembic` ou a pytest. Sans ce correctif, `from app.config import
# get_settings` echoue avec `ModuleNotFoundError: No module named 'app'`, meme
# en executant la commande depuis le bon dossier (backend/, ou /app dans le
# conteneur - WORKDIR du Dockerfile). On force explicitement le dossier parent
# de alembic/ (= backend/, = /app dans le conteneur, la ou vit le package
# `app`) en tete de sys.path, quel que soit le repertoire courant d'appel.
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.config import get_settings
from app.database import Base

# Import de tous les modeles pour qu'Alembic les detecte via Base.metadata
# ATTENTION : cette liste doit rester synchronisee avec app/domains/*/models.py
# a chaque ajout de domaine - sinon `alembic revision --autogenerate` genere
# une migration incomplete sans avertissement (bug reel trouve et corrige ici :
# analyst, notifications, portfolio et watchlist manquaient).
from app.domains.analysis_lab.db_models import TrainingJob  # noqa: F401
from app.domains.analyst.models import AnalystConsensus  # noqa: F401
from app.domains.assets.models import Asset  # noqa: F401
from app.domains.backtests.models import BacktestResult, BacktestRun  # noqa: F401
from app.domains.llm_analyst.db_models import AnalysisJob  # noqa: F401
from app.domains.market_data.models import Dividend, PriceBar, TechnicalIndicator  # noqa: F401
from app.domains.market_overview.models import MarketSnapshot  # noqa: F401
from app.domains.news.models import NewsArticle, NewsKeywordMatch  # noqa: F401
from app.domains.notifications.models import NotificationState  # noqa: F401
from app.domains.portfolio.models import (  # noqa: F401
    PortfolioPosition,
    PortfolioState,
    PortfolioTransaction,
)
from app.domains.signal_reliability.models import SignalOutcome  # noqa: F401
from app.domains.signals.models import Signal, SignalExplanation  # noqa: F401
from app.domains.users.models import User  # noqa: F401
from app.domains.watchlist.models import WatchlistItem  # noqa: F401

config = context.config
settings = get_settings()
config.set_main_option("sqlalchemy.url", settings.database_url)

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


def run_migrations_offline() -> None:
    url = config.get_main_option("sqlalchemy.url")
    context.configure(url=url, target_metadata=target_metadata, literal_binds=True)
    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection) -> None:
    context.configure(connection=connection, target_metadata=target_metadata)
    with context.begin_transaction():
        context.run_migrations()


async def run_migrations_online() -> None:
    connectable = async_engine_from_config(
        config.get_section(config.config_ini_section), prefix="sqlalchemy.", poolclass=pool.NullPool
    )
    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)
    await connectable.dispose()


if context.is_offline_mode():
    run_migrations_offline()
else:
    asyncio.run(run_migrations_online())
