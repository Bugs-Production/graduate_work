import logging
from datetime import datetime

from asgiref.sync import async_to_sync
from celery import shared_task
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from core.config import settings
from db import postgres
from models.enums import SubscriptionStatus
from models.models import Subscription
from schemas.subscription import SubscriptionRenew
from services.subscription import SubscriptionService
from services.subscription_plan import SubscriptionPlanService
from workers.celery import queue

logger = logging.getLogger()


async def main():
    try:
        postgres.engine = create_async_engine(settings.postgres_url, echo=settings.engine_echo, future=True)
        postgres.async_session = async_sessionmaker(bind=postgres.engine, expire_on_commit=False, class_=AsyncSession)  # type: ignore[assignment]

        async with postgres.async_session() as session:
            subscription_service = SubscriptionService(
                session, subscription_plan_service=SubscriptionPlanService(session)
            )
            current_date = datetime.now()
            result = await session.execute(
                select(Subscription).filter(
                    Subscription.end_date <= current_date,
                    Subscription.status == SubscriptionStatus.ACTIVE.value,
                )
            )
            expired_subscriptions = result.scalars().all()

            for subscription in expired_subscriptions:
                await subscription_service.change_status(
                    subscription_id=subscription.id, new_status=SubscriptionStatus.EXPIRED
                )
                logger.info(f"Subscription {subscription.id} is expired")

                if subscription.auto_renewal:
                    renew_data = SubscriptionRenew(plan_id=subscription.plan_id)
                    new_subscription = await subscription_service.renew_subscription(
                        user_id=subscription.user_id, subscription_id=subscription.id, renew_data=renew_data
                    )
                    if hasattr(new_subscription, "id"):
                        logger.info(f"Subscription {subscription.id} is renewed")
    except Exception:
        logger.exception("An error occurred during subscription check process")


@shared_task(queue=queue.name)
def check_subscriptions() -> None:
    logger.info("Executing scheduled task")
    async_to_sync(main)()
