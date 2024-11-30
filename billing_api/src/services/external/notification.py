import enum
from uuid import UUID

from aio_pika.abc import AbstractExchange

from models.enums import StatusCardsEnum, SubscriptionStatus, TransactionStatus
from services.external.base import BaseQueueService


class NotificationTopic(str, enum.Enum):
    SUBSCRIPTION = "subscription"
    CARD = "card"
    TRANSACTION = "transaction"


class NotificationService(BaseQueueService):
    def __init__(self, queue_name: str, exchange: AbstractExchange) -> None:
        super().__init__(queue_name, exchange)

    async def notify_user(self, user_id: UUID, notification_data: dict) -> bool:
        """Отправляет нотификацию пользователю."""
        payload = {"user_id": str(user_id), "notification_data": notification_data}
        return await self.send_message_to_queue(payload)

    async def notify_user_subscription_status(self, user_id: UUID, status: SubscriptionStatus) -> bool:
        """Оповещает пользователя об изменении статуса подписки."""
        data = {"topic": NotificationTopic.SUBSCRIPTION.value, "status": status.value}
        return await self.notify_user(user_id, data)

    async def notify_user_card_status(self, user_id: UUID, status: StatusCardsEnum) -> bool:
        """Оповещает пользователя об изменении статуса платежной карты."""
        data = {"topic": NotificationTopic.CARD.value, "status": status.value}
        return await self.notify_user(user_id, data)

    async def notify_user_transaction_status(self, user_id: UUID, status: TransactionStatus) -> bool:
        """Оповещает пользователя об изменении статуса транзакции."""
        data = {"topic": NotificationTopic.TRANSACTION.value, "status": status.value}
        return await self.notify_user(user_id, data)
