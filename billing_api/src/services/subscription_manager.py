from collections.abc import Sequence
from functools import lru_cache
from uuid import UUID

from aio_pika.abc import AbstractExchange
from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from db.postgres import get_session
from db.rabbitmq import QueueName, get_rabbitmq_exchange
from models.enums import SubscriptionStatus, TransactionStatus
from models.models import Subscription
from schemas.subscription import SubscriptionCreate, SubscriptionRenew
from services.external import AuthService, NotificationService
from services.payment_process import PaymentProcessorStripe
from services.subscription import SubscriptionService
from services.subscription_plan import SubscriptionPlanService
from services.transaction import TransactionService


class SubscriptionManager:
    def __init__(
        self,
        subscription_service: SubscriptionService,
        payment_processor: PaymentProcessorStripe,
        transaction_service: TransactionService,
        auth_service: AuthService,
        notification_service: NotificationService,
    ):
        self._subscription_service = subscription_service
        self._payment_processor = payment_processor
        self._transaction_service = transaction_service
        self._auth_service = auth_service
        self._notification_service = notification_service

    async def create_subscription(self, user_id: UUID, subscription_data: SubscriptionCreate) -> Subscription:
        """Создаёт новую подписку для пользователя."""
        subscription = await self._subscription_service.create_subscription(user_id, subscription_data)
        await self._notification_service.notify_user_subscription_status(user_id, SubscriptionStatus.PENDING)
        return subscription

    async def initate_subscription_payment(self, subscription_id: UUID):
        # TODO: логика инициации оплаты по подписке:
        # - создание payment-intent
        # - создание транзакции
        # например
        # payment_intent = await self._payment_processor.create_payment_intent(subscription_data?)
        # transaction = await self._transaction_service.create(payment_intent_data?)
        pass

    async def activate_subscription(self):
        # TODO: логика обработки вебхука успешного платежа:
        # - обновление статуса транзакции
        # - обновление статуса подписки
        # - обновление роли пользователя
        # - нотификация пользователя
        # transaction = await self._transaction_service.change_status(transaction_id, TransactionStatus.SUCCESS)
        # subscription = await self._subscription_service.change_status(transaction.subscription_id, SubscriptionStatus.ACTIVE)
        # await self._auth_service.upgrade_user_to_subscriber(subscription.user_id)
        # await self._notification_service.notify_user_subscription_status(subscription.user_id, SubscriptionStatus.ACTIVE)
        pass

    async def handle_failed_subscription_payment(self):
        # TODO: логика обработки вебхука НЕ успешного платежа:
        # - обновление статуса транзакции
        # - нотификация пользователя
        # transaction = await self._transaction_service.change_status(transaction_id, TransactionStatus.FAILED)
        # await self._notification_service.notify_user_transaction_status(transaction.user_id, TransactionStatus.FAILED)
        pass

    async def cancel_subscription(self, user_id: UUID, subscription_id: UUID) -> Subscription:
        """Отменяет подписку пользователя."""
        # TODO: логика отмены подписки
        # - обновление статуса подписки
        # - обновление статуса транзакции
        # - обновление роли пользователя
        # - нотификация пользователя
        # subscription = await self._subscription_service.cancel_subscription(user_id, subscription_id)
        # await self._transaction_service.refund_transaction(subscription.id)  # найти и отменить успешную транзакцию по subscription_id
        # await self._auth_service.downgrade_user_to_basic(user_id)
        # await self._notification_service.notify_user_subscription_status(user_id, SubscriptionStatus.CANCELLED)
        # return subscription
        pass

    async def renew_subscription(
        self, user_id: UUID, subscription_id: UUID, renew_data: SubscriptionRenew
    ) -> Subscription:
        """Продляет подписку.

        Под продлением понимается смещение даты завершения подписки на количество дней, указанных в плане подписки.
        """
        # TODO: логика обработки вебхука успешного платежа для обновления подписки.
        pass

    async def get_subscription_by_id(self, subscription_id: UUID) -> Subscription:
        return await self._subscription_service.get(subscription_id)

    async def get_user_subscription(self, user_id: UUID, subscription_id: UUID) -> Subscription:
        return await self._subscription_service.get_user_subscription(user_id, subscription_id)

    async def get_subscriptions(self, filters: dict | None) -> Sequence[Subscription]:
        return await self._subscription_service.get_many(filters)

    async def toggle_subscription_auto_renewal(self, user_id: UUID, subscription_id: UUID) -> Subscription:
        return await self._subscription_service.toggle_auto_renewal(user_id, subscription_id)


@lru_cache
def get_subscription_manager(
    session: AsyncSession = Depends(get_session), exchange: AbstractExchange = Depends(get_rabbitmq_exchange)
):
    subscription_service = SubscriptionService(session, subscription_plan_service=SubscriptionPlanService(session))
    payment_processor = PaymentProcessorStripe()
    transaction_service = TransactionService(session)
    auth_service = AuthService(QueueName.AUTH, exchange)
    notification_service = NotificationService(QueueName.NOTIFICATION, exchange)
    return SubscriptionManager(
        subscription_service=subscription_service,
        payment_processor=payment_processor,
        transaction_service=transaction_service,
        auth_service=auth_service,
        notification_service=notification_service,
    )
