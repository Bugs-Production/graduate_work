from contextlib import asynccontextmanager

import uvicorn
from fastapi import FastAPI
from fastapi.responses import ORJSONResponse
from fastapi_pagination import add_pagination
from fastapi_pagination.utils import disable_installed_extensions_check
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from starlette.staticfiles import StaticFiles

from api.v1 import billing, subscription, subscription_plan, transaction
from core.config import settings
from db import postgres, rabbitmq

# Для избежания варнингов для paginator в консоли
disable_installed_extensions_check()


@asynccontextmanager
async def lifespan(app: FastAPI):
    postgres.engine = create_async_engine(postgres.dsn, echo=settings.engine_echo, future=True)
    postgres.async_session = async_sessionmaker(bind=postgres.engine, expire_on_commit=False, class_=AsyncSession)  # type: ignore[assignment]

    rabbitmq.connection = await rabbitmq.create_rabbitmq_connection(settings.rabbitmq.url)
    rabbitmq.exchange = await rabbitmq.init_rabbitmq(rabbitmq.connection)

    yield
    await rabbitmq.close_rabbitmq_connection(rabbitmq.connection)


app = FastAPI(
    lifespan=lifespan,
    title=settings.project_name,
    docs_url="/api/openapi/",
    openapi_url="/api/openapi.json",
    default_response_class=ORJSONResponse,
)

app.include_router(billing.router, prefix="/api/v1/billing", tags=["Billing"])
app.include_router(transaction.router, prefix="/api/v1/billing/transactions", tags=["Transactions"])
app.include_router(subscription_plan.router, prefix="/api/v1/subscription_plans", tags=["Subscription plans"])
app.include_router(subscription.router, prefix="/api/v1/subscriptions", tags=["Subscriptions"])

add_pagination(app)
app.mount("/static", StaticFiles(directory="static"), name="static")

# Для локального запуска
if __name__ == "__main__":
    uvicorn.run("main:app", host="localhost", port=8080, reload=True)
