from datetime import datetime
from uuid import UUID

from pydantic import BaseModel

from models.enums import SubscriptionStatus


class SubscriptionCreate(BaseModel):
    """Схема для создания новой подписки.

    Используется при получении данных (request) в эндпойнтах.
    """

    plan_id: UUID
    auto_renewal: bool = False


class SubscriptionCreateFull(SubscriptionCreate):
    """Расширенная схема для создания подписки.

    Используется внутри сервиса для создания записи в БД.
    """

    user_id: UUID
    status: SubscriptionStatus = SubscriptionStatus.PENDING
    start_date: datetime
    end_date: datetime


class SubscriptionCreateAdmin(SubscriptionCreate):
    user_id: UUID


class SubscriptionRenew(BaseModel):
    """Схема для обновления подписки.

    Используется при получении данных (request) в эндпойнтах.
    """

    plan_id: UUID


class SubscriptionUpdate(BaseModel):
    """Схема для частичного обновления подписки.

    Используется внутри сервиса для обновления записи в БД.
    """

    status: SubscriptionStatus | None = None
    start_date: datetime | None = None
    end_date: datetime | None = None
    auto_renewal: bool | None = None


class SubscriptionResponse(SubscriptionCreateFull):
    """Схема для использования в качестве response-модели в эндпойнтах."""

    id: UUID

    class Config:
        from_attributes = True
