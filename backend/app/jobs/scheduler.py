"""Configuration du scheduler APScheduler - voir docs/14-jobs-planifies.md."""
import logging

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

from app.jobs.compute_signals_job import compute_signals_job
from app.jobs.credit_dividends_job import credit_dividends_job
from app.jobs.daily_briefing_job import daily_briefing_job
from app.jobs.evaluate_signal_outcomes_job import evaluate_signal_outcomes_job
from app.jobs.evaluate_strategies_job import evaluate_strategies_job
from app.jobs.ingest_news_job import ingest_news_job
from app.jobs.ingest_prices_job import ingest_prices_job
from app.jobs.market_overview_job import market_overview_job
from app.jobs.notify_changes_job import notify_changes_job
from app.jobs.refresh_analyst_ratings_job import refresh_analyst_ratings_job

logger = logging.getLogger(__name__)
scheduler = AsyncIOScheduler()


def register_jobs() -> None:
    scheduler.add_job(ingest_prices_job, CronTrigger(hour=6, minute=0), id="ingest_prices", replace_existing=True)
    scheduler.add_job(ingest_news_job, CronTrigger(minute=0, hour="6-20/2"), id="ingest_news", replace_existing=True)
    scheduler.add_job(
        compute_signals_job, CronTrigger(hour=7, minute=0), id="compute_signals", replace_existing=True
    )
    # 15 minutes apres compute_signals, pour etre sur que les signaux du jour
    # sont deja persistes (voir docs/14).
    scheduler.add_job(
        notify_changes_job, CronTrigger(hour=7, minute=15), id="notify_changes", replace_existing=True
    )
    # Une fois par jour suffit - le consensus d'analystes ne bouge pas d'heure en heure.
    scheduler.add_job(
        refresh_analyst_ratings_job, CronTrigger(hour=6, minute=30), id="refresh_analyst_ratings", replace_existing=True
    )
    # 31/07/2026 : apres ingest_prices (qui ingere aussi les dividendes, voir
    # market_data/service.py:ingest_dividends), pour etre sur que les
    # dividendes du jour sont deja en base avant de tenter de les crediter.
    scheduler.add_job(
        credit_dividends_job, CronTrigger(hour=6, minute=45), id="credit_dividends", replace_existing=True
    )
    # 31/07/2026 : apres compute_signals (7h) ET refresh_analyst_ratings
    # (6h30) - le briefing lit les signaux/consensus du jour, il ne les
    # recalcule jamais lui-meme (voir notifications/briefing_service.py).
    # Reste silencieux tant que MAIL_ENABLED=false (defaut), voir mailer.py.
    scheduler.add_job(
        daily_briefing_job, CronTrigger(hour=7, minute=30), id="daily_briefing", replace_existing=True
    )
    # 01/08/2026 : page "Marche" (indices + top hausses/baisses FR/US) - 3
    # rafraichissements par jour comme demande (7h, 12h, 17h). Decale de 10
    # minutes par rapport aux autres jobs de 7h pour eviter de surcharger le
    # meme instant (voir docs/14-jobs-planifies.md).
    scheduler.add_job(
        market_overview_job,
        CronTrigger(hour="7,12,17", minute=10),
        id="market_overview",
        replace_existing=True,
    )
    # 13/08/2026 : scorecard de fiabilite reelle des signaux - apres
    # ingest_prices (6h, fournit les cours servant a evaluer les signaux
    # murs) et compute_signals (7h, ne devrait pas y avoir de nouveaux
    # signaux non-evalues crees entre 7h et 7h45, mais l'ordre est prudent).
    # Une fois par jour suffit (les signaux mettent des jours a murir).
    scheduler.add_job(
        evaluate_signal_outcomes_job,
        CronTrigger(hour=7, minute=45),
        id="evaluate_signal_outcomes",
        replace_existing=True,
    )
    # 13/08/2026 : evaluation hebdomadaire des strategies de backtest (voir
    # evaluate_strategies_job.py) - plus couteux que les jobs quotidiens
    # (backtest complet x 7 strategies x positions du portefeuille), une fois
    # par semaine suffit largement pour observer une tendance. Lundi matin,
    # apres tous les jobs quotidiens de 6h-7h45.
    scheduler.add_job(
        evaluate_strategies_job,
        CronTrigger(day_of_week="mon", hour=8, minute=0),
        id="evaluate_strategies",
        replace_existing=True,
    )
    logger.info(
        "Jobs planifies enregistres: ingest_prices, ingest_news, compute_signals, notify_changes, "
        "refresh_analyst_ratings, credit_dividends, daily_briefing, market_overview, evaluate_signal_outcomes, "
        "evaluate_strategies"
    )


def start_scheduler() -> None:
    register_jobs()
    scheduler.start()


def shutdown_scheduler() -> None:
    scheduler.shutdown(wait=False)
