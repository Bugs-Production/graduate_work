import logging
from abc import ABC, abstractmethod
from uuid import UUID

import stripe

from core.config import settings

logger = logging.getLogger("billing")


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


class PaymentProcessorStripe(BasePaymentProcessor):
    def __init__(self):
        stripe.api_key = settings.stripe_api_key

    async def create_card(self, customer_id: str, card_id: UUID) -> str:
        """Создание запроса на привязку карты."""
        session = await stripe.checkout.Session.create_async(  # type: ignore[attr-defined]
            mode="setup",
            payment_method_types=["card"],
            success_url="http://localhost:80/api/v1/billing/success-card/",
            cancel_url="http://localhost:80/api/v1/billing/get-card-form/",
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
