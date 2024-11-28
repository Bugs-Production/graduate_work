import logging
from abc import ABC, abstractmethod
from uuid import UUID

import stripe
from stripe.api_resources.abstract.createable_api_resource import CreateableAPIResource

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

    @abstractmethod
    async def process_payment(
        self,
        amount: int,
        currency: str,
        customer_id: str | None = None,
        payment_method: str | None = None,
        description: str | None = None,
    ) -> dict:
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
    ) -> CreateableAPIResource | None:
        """
        Создание платежа.

        :param amount: Сумма платежа в минимальном номинале валюты.
        :param currency: Валюта.
        :param customer_id: ID клиента в Stripe.
        :param payment_method: ID метода оплаты Stripe.
        :param description: Описание платежа.
        """
        try:
            stripe_args = {"amount": amount, "currency": currency, "description": description}

            if customer_id:
                stripe_args["customer"] = customer_id

            if payment_method:
                stripe_args["payment_method"] = payment_method
                stripe_args["off_session"] = True
                stripe_args["confirm"] = True

            return stripe.PaymentIntent.create(**stripe_args)

        except stripe.error.StripeError as e:
            logger.warning(f"Stripe error: {e}")
            return None

    def cancel_payment_intent(self, payment_intent_id: str) -> bool:
        """
        Реализация отмены PaymentIntent.
        """
        try:
            response = stripe.PaymentIntent.cancel(payment_intent_id)
            return bool(hasattr(response, "id"))
        except stripe.error.StripeError as e:
            logger.warning(f"Stripe error: {e}")
            return False
