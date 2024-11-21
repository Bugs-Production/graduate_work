from functools import lru_cache
from uuid import UUID

from fastapi import Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from db.postgres import get_postgres_session
from models.user_cards import StatusCardsEnum, UserCardsStripe
from services.payment_process import PaymentProcessorStripe


class SubscriptionManager:
    def __init__(self, postgres_session: AsyncSession, payment_processor: PaymentProcessorStripe):
        self.postgres_session = postgres_session
        self._payment_processor = payment_processor

    async def get_latest_card_user(self, customer: str) -> UserCardsStripe:
        async with self.postgres_session() as session:
            result = await session.execute(
                select(UserCardsStripe)
                .filter_by(stripe_user_id=customer, status=StatusCardsEnum.INIT)
                .order_by(UserCardsStripe.created_at.desc())
            )
            latest_card = result.scalars().first()

            return latest_card

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

        if event_type == "payment_method.attached" and obj:  # здесь нам прилетают последние 4 цифры карты
            async with self.postgres_session() as session:
                last4 = obj.get("card", {}).get("last4")
                customer = obj.get("customer")

                # находим свежую запись по добавлению карты юзером
                latest_card = await self.get_latest_card_user(customer=customer)

                if latest_card:
                    latest_card.last_numbers_card = last4

                    session.add(latest_card)
                    await session.commit()

        # завершение обработки сохранения карт
        if event_type == "setup_intent.succeeded" and obj:
            payment_method = obj.get("payment_method")  # получаем id способа оплаты
            customer = obj.get("customer")

            if payment_method:
                async with self.postgres_session() as session:
                    user_card = await self.get_latest_card_user(customer=customer)

                    if user_card:
                        user_card.token_card = payment_method
                        user_card.status = StatusCardsEnum.SUCCESS

                        session.add(user_card)
                        await session.commit()

        elif event_type == "setup_intent.setup_failed" and obj:
            customer = obj.get("customer")

            async with self.postgres_session() as session:
                user_card = await self.get_latest_card_user(customer=customer)

                if user_card:
                    user_card.status = StatusCardsEnum.FAIL

                    session.add(user_card)
                    await session.commit()


@lru_cache
def get_manager_service(
    postgres_session: AsyncSession = Depends(get_postgres_session),
    payment_processor: PaymentProcessorStripe = Depends(PaymentProcessorStripe),
) -> SubscriptionManager:
    return SubscriptionManager(postgres_session, payment_processor)
