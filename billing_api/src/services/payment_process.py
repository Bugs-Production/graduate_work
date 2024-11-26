import logging
from abc import ABC, abstractmethod
from uuid import UUID

import stripe

from core.config import settings

logger = logging.getLogger(__name__)


class BasePaymentProcessor(ABC):
    """Базовый класс для реализаций работы с платежками."""

    @abstractmethod
    async def create_card(self, customer_id: str, card_id: UUID) -> str:
        """Создает карту юзера."""
        pass

    @abstractmethod
    async def process_payment(self, amount: int, currency: str, customer_id: str, payment_id: str) -> dict:
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
            success_url="http://localhost:80/success/",
            cancel_url="http://localhost:80/api/v1/billing/get-card-form/",
            customer=customer_id,
        )
        return session.url

    async def create_customer(self) -> dict:
        """Создание клиента на стороне Stripe."""
        customer = await stripe.Customer.create_async()  # type: ignore[attr-defined]
        return customer

    async def process_payment(
        self, amount: int, currency: str, customer_id: str, payment_id: str
    ) -> dict:
        """Создание платежного намерения"""
        try:
            payment_intent = stripe.PaymentIntent.create(
                amount=amount,
                currency=currency,
                customer=customer_id,
                confirm=True,
                payment_method=payment_id,
                off_session=True,
            )
            return {"client_secret": payment_intent["client_secret"]}
        except stripe.error.StripeError as e:
            logger.warning(f"Stripe error: {e}")
