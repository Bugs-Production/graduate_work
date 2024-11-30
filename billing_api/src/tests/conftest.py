from collections.abc import AsyncGenerator

import pytest_asyncio
from config.settings import settings  # type: ignore[import-not-found]
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from db.postgres import get_postgres_session, get_session
from main import app
from models.models import Base

pytest_plugins = [
    "fixtures.subscription_plan",
]


engine_test = create_async_engine(settings.test_postgres_url, future=True)
test_session_maker = async_sessionmaker(bind=engine_test, expire_on_commit=False, class_=AsyncSession)


async def override_get_session() -> AsyncGenerator[AsyncSession, None]:
    async with test_session_maker() as session:
        try:
            yield session
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


async def override_get_postgres_session() -> async_sessionmaker[AsyncSession]:
    return test_session_maker


app.dependency_overrides[get_session] = override_get_session
app.dependency_overrides[get_postgres_session] = override_get_postgres_session


@pytest_asyncio.fixture(loop_scope="session", autouse=True)
async def prepare_database() -> AsyncGenerator[None, None]:
    async with engine_test.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with engine_test.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)


@pytest_asyncio.fixture(loop_scope="session")
async def api_client() -> AsyncGenerator[AsyncClient, None]:
    async with AsyncClient(transport=ASGITransport(app), base_url="http://test") as async_client:
        yield async_client


@pytest_asyncio.fixture(loop_scope="session")
async def test_session() -> AsyncGenerator[AsyncSession, None]:
    async with test_session_maker() as session:
        yield session