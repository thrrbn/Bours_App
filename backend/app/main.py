"""Point d'entree FastAPI - montage des routers, lifespan (scheduler), exception handlers."""
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.exceptions import register_exception_handlers
from app.core.logging import configure_logging
from app.domains.analyst.router import router as analyst_router
from app.domains.assets.router import router as assets_router
from app.domains.backtests.router import router as backtests_router
from app.domains.compliance.router import router as compliance_router
from app.domains.maintenance.router import router as maintenance_router
from app.domains.market_data.router import router as market_data_router
from app.domains.news.router import router as news_router
from app.domains.notifications.router import router as notifications_router
from app.domains.portfolio.router import router as portfolio_router
from app.domains.signals.router import router as signals_router
from app.domains.users.router import router as users_router
from app.domains.watchlist.router import router as watchlist_router
from app.jobs.scheduler import shutdown_scheduler, start_scheduler


@asynccontextmanager
async def lifespan(app: FastAPI):
    configure_logging()
    start_scheduler()
    yield
    shutdown_scheduler()


app = FastAPI(title="Bourse Assistant API", version="0.1.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],  # frontend Vite en dev - restreindre en production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

register_exception_handlers(app)

app.include_router(assets_router)
app.include_router(market_data_router)
app.include_router(news_router)
app.include_router(signals_router)
app.include_router(backtests_router)
app.include_router(users_router)
app.include_router(compliance_router)
app.include_router(watchlist_router)
app.include_router(notifications_router)
app.include_router(portfolio_router)
app.include_router(analyst_router)
app.include_router(maintenance_router)


@app.get("/api/v1/health")
async def health():
    return {"status": "ok"}
