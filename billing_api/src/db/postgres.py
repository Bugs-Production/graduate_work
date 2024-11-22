from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession

from core.config import settings

engine: AsyncEngine | None = None
async_session: AsyncSession | None = None

dsn = settings.postgres_url


async def get_postgres_session() -> AsyncSession | None:
    return async_session
