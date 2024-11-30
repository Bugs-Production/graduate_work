import enum
from uuid import UUID

from aio_pika.abc import AbstractExchange

from services.external.base import BaseQueueService


class UserRole(str, enum.Enum):
    BASIC_USER = "basic_user"
    SUBSCRIBER = "subscriber"


class AuthService(BaseQueueService):
    def __init__(self, queue_name: str, exchange: AbstractExchange) -> None:
        super().__init__(queue_name, exchange)

    async def change_user_role(self, user_id: UUID, role: UserRole) -> bool:
        """Изменяет роль пользователя."""
        payload = {"user_id": str(user_id), "role": role.value}
        return await self.send_message_to_queue(payload)

    async def downgrade_user_to_basic(self, user_id: UUID) -> bool:
        """Понижает роль пользователя до базового уровня."""
        return await self.change_user_role(user_id, UserRole.BASIC_USER)

    async def upgrade_user_to_subscriber(self, user_id: UUID) -> bool:
        """Повышает роль пользователя до уровня 'подписчик.'"""
        return await self.change_user_role(user_id, UserRole.SUBSCRIBER)
