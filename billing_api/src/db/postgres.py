from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker

from core.config import settings

engine: AsyncEngine | None = None
async_session: async_sessionmaker[AsyncSession] | None = None

dsn = settings.postgres_url


async def get_postgres_session() -> async_sessionmaker[AsyncSession]:
    return async_session


async def get_session() -> AsyncGenerator[AsyncSession, None]:
    async with async_session() as session:  # type: ignore[misc]
        try:
            yield session
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()
