from core.config import settings
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession
from sqlalchemy.orm import declarative_base

Base = declarative_base()

engine: AsyncEngine | None = None
async_session: AsyncSession | None = None

dsn = settings.postgres_url


async def get_postgres_session() -> AsyncSession | None:
    return async_session
