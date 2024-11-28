import logging
from abc import ABC, abstractmethod
from typing import Any
from uuid import UUID

import stripe
from pydantic import BaseModel, field_validator
from stripe.api_resources.payment_intent import PaymentIntent

from core.config import settings

logger = logging.getLogger("billing")


class PaymentIntentParams(BaseModel):
    amount: int
    currency: str
    customer: str | None
    payment_method: str | None
    description: str | None
    confirm: bool = False
    off_session: bool = False

    @field_validator("amount")
    def check_amount(cls, value):
        if value < 0:
            raise ValueError("The amount cannot be less than zero!")
        return value


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
    ) -> PaymentIntent | None:
        """
        Создание платежа.

        :param amount: Сумма платежа в минимальном номинале валюты.
        :param currency: Валюта.
        :param customer_id: ID клиента в Stripe.
        :param payment_method: ID метода оплаты Stripe.
        :param description: Описание платежа.
        """
        try:
            stripe_args = PaymentIntentParams(
                amount=amount,
                currency=currency,
                description=description,
                customer=customer_id,
                payment_method=payment_method,
            )

            if payment_method:
                stripe_args.off_session = True
                stripe_args.confirm = True

            return await stripe.PaymentIntent.create_async(**stripe_args.model_dump())  # type: ignore[attr-defined]

        except ValueError as e:
            logger.warning(f"Value error: {e}")

        except stripe.error.StripeError as e:
            logger.warning(f"Stripe error: {e}")

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
