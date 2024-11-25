import logging
from functools import lru_cache
from uuid import UUID

from fastapi import Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from db.postgres import get_postgres_session
from models.enums import StatusCardsEnum
from models.models import UserCardsStripe
from services.exceptions import CardNotFoundException, UserNotOwnerOfCardException
from services.payment_process import PaymentProcessorStripe

logger = logging.getLogger("billing")


class CardsManager:
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

    async def _get_is_default_user_card(self, user_id: str) -> UserCardsStripe | None:
        """Для получения активной дефолтной карты юзера."""
        async with self.postgres_session() as session:
            result = await session.execute(
                select(UserCardsStripe).filter_by(user_id=user_id, status=StatusCardsEnum.SUCCESS, is_default=True)
            )

            default_card = result.scalars().first()
            return default_card if default_card else None

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
                user_card.is_default = True  # ставим новую карту по умолчанию дефолтной

                session.add(user_card)

                default_card = await self._get_is_default_user_card(user_id=user_card.user_id)

                # если у юзера была другая активная карта, снимаем с нее флаг дефолтной
                if default_card:
                    logger.info(f"Removing default status from card {default_card.last_numbers_card}")
                    default_card.is_default = False
                    session.add(default_card)

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

    async def set_default_card(self, user_id: str, card_id: str) -> bool:
        """Делает карту юзера дефолтной."""
        async with self.postgres_session() as session:
            result = await session.execute(
                select(UserCardsStripe).filter_by(id=card_id, status=StatusCardsEnum.SUCCESS)
            )
            user_card = result.scalars().first()

            if not user_card:
                raise CardNotFoundException("User card not found")

            if str(user_card.user_id) != user_id:
                raise UserNotOwnerOfCardException("Forbidden")

            # Проверяем, если карта уже дефолтная, то ничего не меняем
            if user_card.is_default:
                return False

            # Получаем текущую дефолтную карту, если есть
            default_card = await self._get_is_default_user_card(user_id=user_id)

            # Снимаем флаг с текущей дефолтной карты
            if default_card and default_card.id != card_id:
                default_card.is_default = False
                session.add(default_card)

            # Делаем новую карту дефолтной
            user_card.is_default = True
            session.add(user_card)

            await session.commit()
            return True

    async def get_all_user_cards(self, user_id: str) -> list | None:
        """Получает все активные карты юзера."""
        async with self.postgres_session() as session:
            result = await session.execute(
                select(UserCardsStripe).filter_by(user_id=user_id, status=StatusCardsEnum.SUCCESS)
            )

            user_cards = result.scalars().all()
            if user_cards:
                list_user_cards = []

                for card in user_cards:
                    card_info = {"id": str(card.id), "last_numbers": card.last_numbers_card, "default": card.is_default}
                    list_user_cards.append(card_info)

                return list_user_cards
            return None


@lru_cache
def get_cards_manager_service(
    postgres_session: AsyncSession = Depends(get_postgres_session),
    payment_processor: PaymentProcessorStripe = Depends(PaymentProcessorStripe),
) -> CardsManager:
    return CardsManager(postgres_session, payment_processor)
