from datetime import datetime
from uuid import UUID

from schemas.base import IDMixin


class UserCardBase(IDMixin):
    user_id: UUID
    status: str
    last_numbers_card: str | None
    is_default: bool


class UserCardResponse(UserCardBase):
    stripe_user_id: str
    token_card: str | None
    created_at: datetime
    updated_at: datetime
