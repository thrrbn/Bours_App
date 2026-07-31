"""Acces aux donnees custom_keywords - requetes SQL/ORM pures."""
import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domains.news.custom_keywords_models import CustomKeyword


async def list_all(db: AsyncSession) -> list[CustomKeyword]:
    stmt = select(CustomKeyword).order_by(CustomKeyword.created_at.desc())
    result = await db.execute(stmt)
    return list(result.scalars().all())


async def get_by_keyword(db: AsyncSession, keyword: str) -> CustomKeyword | None:
    stmt = select(CustomKeyword).where(CustomKeyword.keyword == keyword)
    result = await db.execute(stmt)
    return result.scalar_one_or_none()


async def create(db: AsyncSession, keyword: str, weight: float, horizon_impact: str) -> CustomKeyword:
    row = CustomKeyword(keyword=keyword, weight=weight, horizon_impact=horizon_impact)
    db.add(row)
    await db.commit()
    await db.refresh(row)
    return row


async def delete(db: AsyncSession, row: CustomKeyword) -> None:
    await db.delete(row)
    await db.commit()


async def get_by_id(db: AsyncSession, keyword_id: uuid.UUID) -> CustomKeyword | None:
    return await db.get(CustomKeyword, keyword_id)


async def as_lexicon(db: AsyncSession) -> dict[str, dict[str, float | str]]:
    """Format compatible avec KEYWORD_LEXICON (nlp/lexicon.py) - fusionne
    directement dans extract_keywords()/score_sentiment() via leur parametre
    `extra_lexicon` (voir nlp/keywords.py et nlp/sentiment.py)."""
    rows = await list_all(db)
    return {row.keyword: {"weight": row.weight, "horizon": row.horizon_impact} for row in rows}
