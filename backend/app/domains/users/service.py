from sqlalchemy.ext.asyncio import AsyncSession

from app.domains.users import repository
from app.domains.users.auth import create_access_token, hash_password, verify_password
from app.domains.users.models import User


async def register_user(db: AsyncSession, email: str, password: str) -> User:
    existing = await repository.get_by_email(db, email)
    if existing is not None:
        return existing
    return await repository.create(db, email, hash_password(password))


async def authenticate(db: AsyncSession, email: str, password: str) -> str | None:
    user = await repository.get_by_email(db, email)
    if user is None or not verify_password(password, user.hashed_password):
        return None
    return create_access_token(subject=str(user.id))
