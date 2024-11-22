import logging
from functools import lru_cache
from uuid import UUID

from fastapi import Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from db.postgres import get_postgres_session
from models.user_cards import StatusCardsEnum, UserCardsStripe
from services.payment_process import PaymentProcessorStripe

logger = logging.getLogger("billing")


class SubscriptionManager:
    def __init__(self, postgres_session: AsyncSession, payment_processor: PaymentProcessorStripe):
        self.postgres_session = postgres_session
        self._payment_processor = payment_processor

    async def get_latest_card_user(self, customer: str) -> UserCardsStripe | None:
        async with self.postgres_session() as session:
            result = await session.execute(
                select(UserCardsStripe)
                .filter_by(stripe_user_id=customer, status=StatusCardsEnum.INIT)
                .order_by(UserCardsStripe.created_at.desc())
            )
            latest_card = result.scalars().first()

            return latest_card if latest_card else None

    async def create_user_card(self, user_id: UUID) -> str:
        async with self.postgres_session() as session:
            user_cards = await session.scalars(select(UserCardsStripe).filter_by(user_id=user_id))
            user_card = user_cards.first()

            if user_card is None:
                # в случае когда юзер привязывает карту первый раз
                customer = await self._payment_processor.create_customer()

            stripe_user_id = user_card.stripe_user_id if user_card else customer.id

            new_user_card = UserCardsStripe(user_id=user_id, stripe_user_id=stripe_user_id)

            session.add(new_user_card)
            await session.commit()

            # возвращаем url на форму Stripe
            url = await self._payment_processor.create_card(customer_id=stripe_user_id, card_id=new_user_card.id)
            return url

    async def handle_webhook(self, event_type: str, data: dict) -> None:
        obj = data.get("object")

        if not obj:
            logger.warning(f"No 'object' found in webhook data for event: {event_type}")
            return

        handlers = {
            "payment_method.attached": self._handle_payment_method_attached,
            "setup_intent.succeeded": self._handle_setup_intent_succeeded,
            "setup_intent.setup_failed": self._handle_setup_intent_failed,
        }

        # вызываем обработчик в зависимости от типа события
        handler = handlers.get(event_type)
        if handler:
            logger.info(f"Handling event: {event_type}")
            await handler(obj)
        else:
            logger.warning(f"No handler found for event: {event_type}")

    async def _handle_payment_method_attached(self, obj: dict) -> None:
        """Для получения последних цифр карты."""
        customer = obj.get("customer")
        last4 = obj.get("card", {}).get("last4")

        if not customer or not last4:
            logger.warning("Missing customer or last4 card info in 'payment_method.attached' event.")
            return

        async with self.postgres_session() as session:
            # Находим свежую запись по добавлению карты юзером
            latest_card = await self.get_latest_card_user(customer=customer)

            if latest_card:
                logger.info(f"Updating last 4 digits for customer {customer}")
                latest_card.last_numbers_card = last4

                session.add(latest_card)
                await session.commit()
                logger.info(f"Last 4 digits updated successfully for customer {customer}")

    async def _handle_setup_intent_succeeded(self, obj: dict) -> None:
        """В случае успешной привязки карты и ее токена."""
        customer = obj.get("customer")
        payment_method = obj.get("payment_method")  # получаем id способа оплаты

        if not customer or not payment_method:
            logger.warning("Missing customer or payment method in 'setup_intent.succeeded' event.")
            return

        async with self.postgres_session() as session:
            user_card = await self.get_latest_card_user(customer=customer)

            if user_card:
                logger.info(f"Updating payment method for customer {customer}")
                user_card.token_card = payment_method
                user_card.status = StatusCardsEnum.SUCCESS

                session.add(user_card)
                logger.info(f"Payment method updated successfully for customer {customer}")
                await session.commit()

    async def _handle_setup_intent_failed(self, obj: dict) -> None:
        """В случае неуспешной привязки проставляем fail статус."""
        customer = obj.get("customer")

        if not customer:
            logger.warning("Missing customer in 'setup_intent.setup_failed' event.")
            return

        async with self.postgres_session() as session:
            user_card = await self.get_latest_card_user(customer=customer)

            if user_card:
                user_card.status = StatusCardsEnum.FAIL

                session.add(user_card)
                await session.commit()
                logger.info(f"Card setup marked as failed successfully for customer {customer}")


@lru_cache
def get_manager_service(
    postgres_session: AsyncSession = Depends(get_postgres_session),
    payment_processor: PaymentProcessorStripe = Depends(PaymentProcessorStripe),
) -> SubscriptionManager:
    return SubscriptionManager(postgres_session, payment_processor)
