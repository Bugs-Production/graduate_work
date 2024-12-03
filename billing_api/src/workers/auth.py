import logging

from core.config import settings
from workers.base import BaseQueueWorker
from workers.exceptions import PermanentWorkerError

logger = logging.getLogger(__name__)


class AuthWorker(BaseQueueWorker):
    """Воркер для работы с сервисом Auth."""

    def __init__(self, queue_name: str):
        super().__init__(queue_name)
        self._auth_service_url = settings.auth_service_url.rstrip("/")

    async def handle_event(self, message_body: dict) -> None:
        """Обрабатывает сообщения для изменения роли пользователя."""
        user_id = message_body.get("user_id")
        role = message_body.get("role")

        if not all([user_id, role]):
            raise PermanentWorkerError("Неверная структура сообщения для обработки AuthWorker")

        url = f"{self._auth_service_url}/{user_id}/role/"
        await self.make_post_request(url, payload={"role": role})
