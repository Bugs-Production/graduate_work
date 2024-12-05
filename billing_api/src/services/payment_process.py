import logging
from abc import ABC, abstractmethod
from functools import lru_cache
from typing import Any
from uuid import UUID

import stripe
from fastapi import Depends
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from stripe.api_resources.payment_intent import PaymentIntent

from core.config import settings
from db.postgres import get_postgres_session
from models.enums import PaymentType, TransactionStatus
from models.models import Transaction, UserCardsStripe
from services.exceptions import CardNotFoundException, CreatePaymentIntentException
from services.transaction import TransactionService, get_admin_transaction_service

logger = logging.getLogger("billing")


class PaymentIntentParams(BaseModel):
    amount: int = Field(gt=0)
    currency: str
    customer: str | None
    payment_method: str | None
    description: str | None
    confirm: bool = False
    off_session: bool = False
    metadata: dict | None


class BasePaymentProcessor(ABC):
    """Базовый класс для реализаций работы с платежками."""

    @abstractmethod
    async def create_card(self, customer_id: str, card_id: UUID) -> str:
        """Создает карту юзера."""
        pass

    @abstractmethod
    async def remove_card(self, token_card: str) -> bool:
        """Удаляет карту юзера."""
        pass

    @abstractmethod
    async def process_payment(
        self,
        amount: int,
        currency: str,
        customer_id: str | None = None,
        payment_method: str | None = None,
        description: str | None = None,
        metadata: dict | None = None,
    ) -> Any:
        """Инициализирует оплату"""
        pass


class PaymentProcessorStripe(BasePaymentProcessor):
    def __init__(self):
        stripe.api_key = settings.stripe_api_key

    async def create_card(self, customer_id: str, card_id: UUID) -> str:
        """Создание запроса на привязку карты."""
        session = await stripe.checkout.Session.create_async(  # type: ignore[attr-defined]
            mode="setup",
            payment_method_types=["card"],
            success_url="http://localhost:80/api/v1/billing/success-card/",  # TODO
            cancel_url="http://localhost:80/api/v1/billing/get-card-form/",  # TODO
            customer=customer_id,
        )
        return session.url

    async def create_customer(self) -> dict:
        """Создание клиента на стороне Stripe."""
        customer = await stripe.Customer.create_async()  # type: ignore[attr-defined]
        return customer

    async def remove_card(self, token_card: str) -> bool:
        """Запрос на удаление карты у юзера."""
        try:
            response = await stripe.PaymentMethod.detach_async(payment_method=token_card)  # type: ignore[attr-defined]
            # если у response есть id карты, считаем, что запрос прошел успешно
            return bool(hasattr(response, "id"))
        except stripe.error.APIError as e:
            logger.warning(f"Stripe API error - {e}")
            return False
        except stripe.error.StripeError as e:
            logger.warning(f"Stripe general error - {e}")
            return False

    async def process_payment(
        self,
        amount: int,
        currency: str,
        customer_id: str | None = None,
        payment_method: str | None = None,
        description: str | None = None,
        metadata: dict | None = None,
    ) -> PaymentIntent | None:
        """
        Создание платежа.

        :param amount: Сумма платежа в минимальном номинале валюты.
        :param currency: Валюта.
        :param customer_id: ID клиента в Stripe.
        :param payment_method: ID метода оплаты Stripe.
        :param description: Описание платежа.
        :param metadata: Метаданные, содержащие детали платежа.
        """
        try:
            stripe_args = PaymentIntentParams(
                amount=amount,
                currency=currency,
                description=description,
                customer=customer_id,
                payment_method=payment_method,
                metadata=metadata,
            )

            if payment_method:
                stripe_args.off_session = True
                stripe_args.confirm = True

            return await stripe.PaymentIntent.create_async(**stripe_args.model_dump())  # type: ignore[attr-defined]

        except ValueError as e:
            logger.warning(f"Value error: {e}\nCustomer_id: {e}\nPayment_method: {e}")

        except stripe.error.StripeError as e:
            logger.warning(f"Stripe error: {e}\nCustomer_id: {e}\nPayment_method: {e}")

        return None

    async def cancel_payment_intent(self, payment_intent_id: str) -> bool:
        """
        Реализация отмены PaymentIntent.
        """
        try:
            payment_intent = await stripe.PaymentIntent.retrieve_async(payment_intent_id)  # type: ignore[attr-defined]
            response = await stripe.PaymentIntent.cancel_async(payment_intent)  # type: ignore[attr-defined]
            return bool(hasattr(response, "id"))
        except stripe.error.StripeError as e:
            logger.warning(f"Stripe error: {e}")
            return False


class PaymentManager:
    def __init__(
        self,
        postgres_session: AsyncSession,
        payment_processor: PaymentProcessorStripe,
        transaction_service: TransactionService,
    ):
        self.postgres_session = postgres_session
        self.payment_processor = payment_processor
        self.transaction_service = transaction_service

    async def _get_stripe_card_data(self, card_id, user_id):
        async with self.postgres_session() as session:
            cards_data = await session.scalars(select(UserCardsStripe).filter_by(id=str(card_id), user_id=str(user_id)))
            stripe_card = cards_data.first()

            if stripe_card is None:
                raise CardNotFoundException("Cards not found")

            return stripe_card

    async def process_payment_with_card(
        self,
        amount: int,
        currency: str,
        subscription_id: UUID,
        user_id: UUID,
        card_id: UUID,
        description: str | None = None,
    ) -> Transaction:
        payment_meta = {
            "subscription_id": subscription_id,
            "user_id": user_id,
        }

        stripe_card = await self._get_stripe_card_data(card_id, user_id)

        transaction = await self.transaction_service.create_transaction(
            subscription_id=subscription_id,
            user_id=user_id,
            amount=amount,
            payment_type=PaymentType.STRIPE,
            user_card_id=card_id,
        )

        payment_intent = await self.payment_processor.process_payment(
            amount=amount,
            currency=currency,
            customer_id=stripe_card.stripe_user_id,
            payment_method=stripe_card.token_card,
            description=description,
            metadata=payment_meta,
        )

        if not payment_intent:
            raise CreatePaymentIntentException("Failure to create a payment intent")

        transaction_updated_data = {"stripe_payment_intent_id": payment_intent["id"]}

        transaction = await self.transaction_service.update_transaction(
            transaction_id=transaction.id, updated_data=transaction_updated_data
        )

        return transaction

    async def _update_transaction_status(self, data: dict, status: TransactionStatus, stripe_payment_intent_id: str):
        logger.info(f"Payment event: {data}")

        filter_data = {"stripe_payment_intent_id": stripe_payment_intent_id}
        transaction_data = await self.transaction_service.get_transactions(filter_data)
        transaction = transaction_data[0]
        await self.transaction_service.update_transaction(transaction.id, {"status": status})

    async def handle_payment_succeeded(self, data):
        stripe_payment_intent_id = data["object"]["id"]
        await self._update_transaction_status(data, TransactionStatus.SUCCESS, stripe_payment_intent_id)

    async def handle_payment_failed(self, data):
        stripe_payment_intent_id = data["object"]["id"]
        await self._update_transaction_status(data, TransactionStatus.FAILED, stripe_payment_intent_id)

    async def handle_payment_refunded(self, data):
        stripe_payment_intent_id = data["object"]["payment_intent"]
        await self._update_transaction_status(data, TransactionStatus.REFUNDED, stripe_payment_intent_id)


@lru_cache
def get_payment_manager_service(
    postgres_session: AsyncSession = Depends(get_postgres_session),
    payment_processor: PaymentProcessorStripe = Depends(PaymentProcessorStripe),
    transaction_service: TransactionService = Depends(get_admin_transaction_service),
) -> PaymentManager:
    return PaymentManager(postgres_session, payment_processor, transaction_service)
