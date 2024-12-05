from collections.abc import Sequence
from functools import lru_cache
from uuid import UUID

from aio_pika.abc import AbstractExchange
from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from db.postgres import get_session
from db.rabbitmq import QueueName, get_rabbitmq_exchange
from models.enums import SubscriptionStatus
from models.models import Subscription, Transaction
from schemas.subscription import SubscriptionCreate, SubscriptionRenew
from services.external import AuthService, NotificationService
from services.payment_process import PaymentManager, get_payment_manager_service
from services.subscription import SubscriptionService
from services.subscription_plan import SubscriptionPlanService


class SubscriptionManager:
    def __init__(
        self,
        subscription_service: SubscriptionService,
        payment_manager: PaymentManager,
        auth_service: AuthService,
        notification_service: NotificationService,
    ):
        self._subscription_service = subscription_service
        self._payment_manager = payment_manager
        self._auth_service = auth_service
        self._notification_service = notification_service

    async def create_subscription(self, user_id: UUID, subscription_data: SubscriptionCreate) -> Subscription:
        """Создаёт новую подписку для пользователя."""
        subscription = await self._subscription_service.create_subscription(user_id, subscription_data)
        await self._notification_service.notify_user_subscription_status(user_id, SubscriptionStatus.PENDING)
        return subscription

    async def initate_subscription_payment(self, user_id: UUID, card_id: UUID, subscription_id: UUID) -> Transaction:
        """Инициирует оплату по подписке."""
        amount = await self._subscription_service.get_payment_amount(subscription_id)
        transaction = await self._payment_manager.process_payment_with_card(
            amount=amount, subscription_id=subscription_id, user_id=user_id, card_id=card_id
        )
        return transaction

    async def activate_subscription(self, subscription_id: UUID) -> Subscription:
        """Активирует подписку, изменяет роль пользователя и отправляет уведомление пользователю."""
        subscription = await self._subscription_service.change_status(subscription_id, SubscriptionStatus.ACTIVE)
        await self._auth_service.upgrade_user_to_subscriber(subscription.user_id)
        await self._notification_service.notify_user_subscription_status(
            subscription.user_id, SubscriptionStatus.ACTIVE
        )
        return subscription

    async def cancel_subscription(self, user_id: UUID, subscription_id: UUID) -> Subscription:
        """Отменяет подписку пользователя, изменяет роль пользователя и отправляет уведомление пользователю."""
        subscription = await self._subscription_service.cancel_subscription(user_id, subscription_id)
        await self._auth_service.downgrade_user_to_basic(user_id)
        await self._notification_service.notify_user_subscription_status(user_id, SubscriptionStatus.CANCELLED)
        return subscription

    async def renew_subscription(
        self, user_id: UUID, subscription_id: UUID, renew_data: SubscriptionRenew
    ) -> Subscription:
        """Продляет подписку и инициирует оплату подписки дефолтной картой пользователя.

        Под продлением понимается создание новой подписки.
        """
        current_subscription = await self.get_user_subscription(user_id, subscription_id)
        new_subscription = await self._subscription_service.renew_subscription(
            user_id, current_subscription.id, renew_data
        )
        default_user_card = await self._payment_manager.get_user_default_card_id(user_id)
        await self.initate_subscription_payment(user_id, card_id=default_user_card, subscription_id=new_subscription.id)
        return new_subscription

    async def get_subscription_by_id(self, subscription_id: UUID) -> Subscription:
        """Получает подписку по id."""
        return await self._subscription_service.get(subscription_id)

    async def get_user_subscription(self, user_id: UUID, subscription_id: UUID) -> Subscription:
        """Получает подписку пользователя по id."""
        return await self._subscription_service.get_user_subscription(user_id, subscription_id)

    async def get_subscriptions(self, filters: dict | None) -> Sequence[Subscription]:
        """Выгружает список подписок."""
        return await self._subscription_service.get_many(filters)

    async def toggle_subscription_auto_renewal(self, user_id: UUID, subscription_id: UUID) -> Subscription:
        """Включает/отключает автоматическое продление подписки."""
        return await self._subscription_service.toggle_auto_renewal(user_id, subscription_id)

    async def handle_payment_webhook(self, payment_gateway_response: dict) -> None:
        """Обрабатывает ответ от платёжной системы."""
        pass

    async def _handle_succefull_subscription_payment(self, payment_gateway_response: dict) -> None:
        """Обработка события успешного платежа по подписке."""
        transaction = await self._payment_manager.handle_payment_succeeded(payment_gateway_response)
        await self.activate_subscription(transaction.subscription_id)

    async def _handle_failed_subscription_payment(self, payment_gateway_response: dict) -> None:
        """Обработка события неуспешного платеджа по подписке."""
        await self._payment_manager.handle_payment_failed(payment_gateway_response)

    async def _handle_refund_subscription_payment(self, payment_gateway_response: dict) -> None:
        """Обработка события возврата платежа по подписке."""
        transaction = await self._payment_manager.handle_payment_refunded(payment_gateway_response)
        subscription = await self._subscription_service.get(transaction.subscription_id)
        await self.cancel_subscription(user_id=subscription.user_id, subscription_id=subscription.id)


@lru_cache
def get_subscription_manager(
    session: AsyncSession = Depends(get_session),
    exchange: AbstractExchange = Depends(get_rabbitmq_exchange),
    payment_manager: PaymentManager = Depends(get_payment_manager_service),
):
    subscription_service = SubscriptionService(session, subscription_plan_service=SubscriptionPlanService(session))
    auth_service = AuthService(QueueName.AUTH, exchange)
    notification_service = NotificationService(QueueName.NOTIFICATION, exchange)
    return SubscriptionManager(
        subscription_service=subscription_service,
        payment_manager=payment_manager,
        auth_service=auth_service,
        notification_service=notification_service,
    )
