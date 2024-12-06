import logging
from collections.abc import Sequence
from datetime import datetime

from asgiref.sync import async_to_sync
from celery import shared_task  # type: ignore[import-untyped]
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from core.config import settings
from db import postgres, rabbitmq
from db.rabbitmq import QueueName
from models.enums import SubscriptionStatus
from models.models import Subscription
from schemas.subscription import SubscriptionRenew
from services.external.auth import AuthService
from services.external.notification import NotificationService
from services.payment_process import PaymentManager, PaymentProcessorStripe
from services.subscription import SubscriptionService
from services.subscription_manager import SubscriptionManager
from services.subscription_plan import SubscriptionPlanService
from services.transaction import TransactionService
from workers.celery import queue

logger = logging.getLogger(__name__)

async def get_expired_subscriptions(session: AsyncSession) -> Sequence[Subscription]:
    current_date = datetime.now()

    result = await session.execute(
        select(Subscription).filter(
            Subscription.end_date <= current_date,
            Subscription.status == SubscriptionStatus.ACTIVE.value,
        )
    )
    return result.scalars().all()


async def check_subscription(subscription: Subscription, subscription_manager: SubscriptionManager):
    if subscription.auto_renewal:
        renew_data = SubscriptionRenew(plan_id=subscription.plan_id)
        new_subscription = await subscription_manager.renew_subscription(
            user_id=subscription.user_id, subscription_id=subscription.id, renew_data=renew_data
        )
        if hasattr(new_subscription, "id"):
            logger.info(f"Subscription {subscription.id} is renewed")
        await subscription_manager.mark_subscription_expired(
            user_id=subscription.user_id, subscription_id=subscription.id, role_detachment=False
        )
    else:
        await subscription_manager.mark_subscription_expired(
            subscription.user_id, subscription.id, role_detachment=True
        )


async def main():
    try:
        postgres.engine = create_async_engine(settings.postgres_url, echo=settings.engine_echo, future=True)
        postgres.async_session = async_sessionmaker(bind=postgres.engine, expire_on_commit=False, class_=AsyncSession)  # type: ignore[assignment]
        rabbitmq.connection = await rabbitmq.create_rabbitmq_connection(settings.rabbitmq.url)
        rabbitmq.exchange = await rabbitmq.init_rabbitmq(rabbitmq.connection)

        async with postgres.async_session() as session:
            subscription_service = SubscriptionService(
                session, subscription_plan_service=SubscriptionPlanService(postgres.async_session)
            )
            transaction_service = TransactionService(postgres.async_session)
            notification_service = NotificationService(QueueName.NOTIFICATION, rabbitmq.exchange)
            auth_service = AuthService(QueueName.AUTH, rabbitmq.exchange)
            payment_proccessor = PaymentProcessorStripe()
            payment_manager = PaymentManager(
                postgres.async_session, payment_proccessor, transaction_service, notification_service
            )
            subscription_manager = SubscriptionManager(
                subscription_service, payment_manager, auth_service, notification_service
            )

            expired_subscriptions = await get_expired_subscriptions(session)

            for subscription in expired_subscriptions:
                await check_subscription(subscription, subscription_manager)

    except Exception:
        logger.exception("An error occurred during subscription check process")
    finally:
        await rabbitmq.close_rabbitmq_connection(rabbitmq.connection)


@shared_task(queue=queue.name)
def check_subscriptions() -> None:
    logger.info("Executing scheduled task (check_subscripions)")
    async_to_sync(main)()
