import logging
from functools import lru_cache

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession
from db.postgres import get_postgres_session
from sqlalchemy import select
from services.payment_process import PaymentProcessorStripe
from models.models import Transaction

logger = logging.getLogger("payment_webhook_manager")


class PaymentWebhookManager:
    def __init__(self, postgres_session: AsyncSession, payment_processor: PaymentProcessorStripe):
        self.postgres_session = postgres_session
        self._payment_processor = payment_processor

    async def handle_payment_succeeded(self, data):
        logger.info(f"Payment event: {data}")
        stripe_obj = data["object"]
        order_id = stripe_obj["metadata"].get("order_id")
        product_type = stripe_obj["metadata"].get("product_type")
        if order_id:
            async with self.postgres_session() as session:
                stmt = await session.execute(select(Transaction).filter_by(subscription_id=order_id))
                transaction = stmt.scalar()

    async def handle_payment_failed(self, data):
        logger.info(f"Payment event: {data}")


@lru_cache
def get_payment_manager_service(
    postgres_session: AsyncSession = Depends(get_postgres_session),
    payment_processor: PaymentProcessorStripe = Depends(PaymentProcessorStripe),
) -> PaymentWebhookManager:
    return PaymentWebhookManager(postgres_session, payment_processor)
