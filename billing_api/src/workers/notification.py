import logging

from core.config import settings
from workers.base import BaseQueueWorker
from workers.exceptions import PermanentWorkerError

logger = logging.getLogger(__name__)


class NotificationWorker(BaseQueueWorker):
    """Воркер для работы с сервисом Notification."""

    def __init__(self, queue_name: str):
        super().__init__(queue_name)
        self._notifcation_service_url = settings.notification_service_url.rstrip("/")

    async def handle_event(self, message_body: dict) -> None:
        """Обрабатывает сообщения для отпраки нотификации пользователю."""
        user_id = message_body.get("user_id")
        notification_data = message_body.get("notification_data")

        if not all([user_id, notification_data]):
            raise PermanentWorkerError("Неверная структура сообщения для обработки NotificationWorker")

        url = f"{self._notifcation_service_url}/{user_id}/notify/"
        await self.make_post_request(url, payload={"notification_data": notification_data})
