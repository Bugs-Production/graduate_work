from celery import shared_task
from requests import session

from workers.celery import queue
from asgiref.sync import async_to_sync

from models.models import Subscription
import logging
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from core.config import settings
from services.external import AuthService, NotificationService
from services.payment_process import PaymentManager, get_payment_manager_service
from services.subscription import SubscriptionService
from services.subscription_plan import SubscriptionPlanService
from models.enums import SubscriptionStatus
from sqlalchemy import select
from db import rabbitmq
from db import postgres
from datetime import datetime
from traceback import print_exc

logger = logging.getLogger()


async def main():
    try:
        postgres.engine = create_async_engine(settings.postgres_url, echo=settings.engine_echo, future=True)
        postgres.async_session = async_sessionmaker(bind=postgres.engine, expire_on_commit=False, class_=AsyncSession)  # type: ignore[assignment]
        rabbitmq.connection = await rabbitmq.create_rabbitmq_connection(settings.rabbitmq.url)
        rabbitmq.exchange = await rabbitmq.init_rabbitmq(rabbitmq.connection)

        async with postgres.async_session() as session:
            current_date = datetime.now()
            expired_subscriptions = await session.execute(select(Subscription).filter(
                Subscription.end_date <= current_date,
                Subscription.status == SubscriptionStatus.ACTIVE.value,
            ))
            logger.info(f"expired_subscriptions {expired_subscriptions.all()}")

            subscription_service = SubscriptionService(session,
                                                       subscription_plan_service=SubscriptionPlanService(
                                                           session))
            test = await subscription_service.get_payment_amount(
                "6456dcd2-9092-4825-938b-53d502edb330")
            logger.info(f"RESULT: {test}")

    except Exception as e:
        logger.error(print_exc())
    finally:
        await rabbitmq.close_rabbitmq_connection(rabbitmq.connection)


@shared_task(queue=queue.name)
def check_subscriptions() -> None:
    logger.info("Executing scheduled task")
    async_to_sync(main)()
