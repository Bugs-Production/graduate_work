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

    async def _get_card_user(
        self,
        card_id: str | None = None,
        customer: str | None = None,
        user_id: str | None = None,
        status: StatusCardsEnum | None = None,
        is_default: bool | None = None,
        order_by: str = "desc",
    ) -> UserCardsStripe | None:
        """Метод для поиска карты юзера в зависимости от параметров."""
        async with self.postgres_session() as session:
            query = select(UserCardsStripe)

            if card_id:
                query = query.filter_by(id=card_id)
            if customer:
                query = query.filter_by(stripe_user_id=customer)
            if user_id:
                query = query.filter_by(user_id=user_id)
            if status:
                query = query.filter_by(status=status)
            if is_default is not None:
                query = query.filter_by(is_default=is_default)

            if order_by == "desc":
                query = query.order_by(UserCardsStripe.created_at.desc())
            else:
                query = query.order_by(UserCardsStripe.created_at.asc())

            result = await session.execute(query)
            card = result.scalars().first()

            return card if card else None

    async def create_user_card(self, user_id: UUID) -> str:
        async with self.postgres_session() as session:
            user_card = await self._get_card_user(user_id=str(user_id))

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
            latest_card = await self._get_card_user(customer=customer, status=StatusCardsEnum.INIT)

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
            user_card = await self._get_card_user(customer=customer, status=StatusCardsEnum.INIT)

            if user_card:
                logger.info(f"Updating payment method for customer {customer}")
                user_card.token_card = payment_method
                user_card.status = StatusCardsEnum.SUCCESS
                user_card.is_default = True  # ставим новую карту по умолчанию дефолтной

                session.add(user_card)

                default_card = await self._get_card_user(
                    user_id=user_card.user_id,
                    status=StatusCardsEnum.SUCCESS,
                    is_default=True,
                )

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
            user_card = await self._get_card_user(customer=customer, status=StatusCardsEnum.INIT)

            if user_card:
                user_card.status = StatusCardsEnum.FAIL

                session.add(user_card)
                await session.commit()
                logger.info(f"Card setup marked as failed successfully for customer {customer}")

    async def set_default_card(self, user_id: str, card_id: str) -> bool:
        """Делает карту юзера дефолтной."""
        async with self.postgres_session() as session:
            user_card = await self._get_card_user(card_id=card_id, status=StatusCardsEnum.SUCCESS)

            if not user_card:
                raise CardNotFoundException("User card not found")

            if str(user_card.user_id) != user_id:
                raise UserNotOwnerOfCardException("Forbidden")

            # Проверяем, если карта уже дефолтная, то ничего не меняем
            if user_card.is_default:
                return False

            # Получаем текущую дефолтную карту, если есть
            default_card = await self._get_card_user(user_id=user_id, status=StatusCardsEnum.SUCCESS, is_default=True)

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

    async def remove_card_from_user(self, card_id: str, user_id: str) -> bool:
        """Удаляет карту юзера."""
        async with self.postgres_session() as session:
            user_card = await self._get_card_user(card_id=card_id)

            if not user_card:
                raise CardNotFoundException("User card not found")

            if str(user_card.user_id) != user_id:
                raise UserNotOwnerOfCardException("Forbidden")

            response = await self._payment_processor.remove_card(token_card=user_card.token_card)

            if not response:
                return False

            # удаляем карту на нашей стороне
            await session.delete(user_card)
            await session.commit()

            # проверяем была ли она дефолтной
            if user_card.is_default:
                # если да, то пытаемся найти другую и сделать ее дефолтной
                last_active_card = await self._get_card_user(user_id=user_id, status=StatusCardsEnum.SUCCESS)

                if last_active_card:
                    last_active_card.is_default = True
                    session.add(last_active_card)
                    await session.commit()

            return True


@lru_cache
def get_cards_manager_service(
    postgres_session: AsyncSession = Depends(get_postgres_session),
    payment_processor: PaymentProcessorStripe = Depends(PaymentProcessorStripe),
) -> CardsManager:
    return CardsManager(postgres_session, payment_processor)
