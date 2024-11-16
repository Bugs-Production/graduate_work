from typing import Optional

from core.config import settings
from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession
from sqlalchemy.orm import declarative_base

Base = declarative_base()

engine: Optional[AsyncEngine] = None
async_session: Optional[AsyncSession] = None

dsn = settings.postgres_url


async def get_postgres_session() -> AsyncSession:
    return async_session  # type: ignore
