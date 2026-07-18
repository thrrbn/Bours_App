"""Configuration du scheduler APScheduler - voir docs/14-jobs-planifies.md."""
import logging

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger

from app.jobs.compute_signals_job import compute_signals_job
from app.jobs.ingest_news_job import ingest_news_job
from app.jobs.ingest_prices_job import ingest_prices_job
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
    logger.info(
        "Jobs planifies enregistres: ingest_prices, ingest_news, compute_signals, notify_changes, refresh_analyst_ratings"
    )


def start_scheduler() -> None:
    register_jobs()
    scheduler.start()


def shutdown_scheduler() -> None:
    scheduler.shutdown(wait=False)
