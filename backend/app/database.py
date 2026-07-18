"""
Configuration de l'acces base de donnees (SQLAlchemy async).
Fournit la Base declarative dont heritent tous les modeles des domaines,
et la dependance FastAPI get_db() injectee dans les routers.
"""
from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

from app.config import get_settings

settings = get_settings()

engine = create_async_engine(settings.database_url, echo=(settings.environment == "development"))
AsyncSessionLocal = async_sessionmaker(engine, expire_on_commit=False)


class Base(DeclarativeBase):
    """Classe de base declarative commune a tous les modeles ORM du projet."""


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with AsyncSessionLocal() as session:
        yield session
