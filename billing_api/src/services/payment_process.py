from abc import ABC, abstractmethod
from uuid import UUID

import stripe

from core.config import settings


class BasePaymentProcessor(ABC):
    """Базовый класс для реализаций работы с платежками."""

    @abstractmethod
    async def create_card(self, customer_id: str, card_id: UUID) -> str:
        """Создает карту юзера."""
        pass


class PaymentProcessorStripe(BasePaymentProcessor):
    def __init__(self):
        stripe.api_key = settings.stripe_api_key

    async def create_card(self, customer_id: str, card_id: UUID) -> str:
        """Создание запроса на привязку карты."""
        session = stripe.checkout.Session.create(
            mode="setup",
            payment_method_types=["card"],
            success_url="http://localhost:80/success/",
            cancel_url="http://localhost:80/cancel/",
            customer=customer_id,
        )
        return session.url

    async def create_customer(self) -> dict:
        """Создание клиента на стороне Stripe."""
        return stripe.Customer.create()
