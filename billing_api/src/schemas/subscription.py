from datetime import datetime
from uuid import UUID

from pydantic import BaseModel

from models.enums import SubscriptionStatus


class SubscriptionCreate(BaseModel):
    plan_id: UUID
    auto_renewal: bool = False


class SubscriptionCreateFull(SubscriptionCreate):
    user_id: UUID
    status: SubscriptionStatus = SubscriptionStatus.PENDING
    start_date: datetime
    end_date: datetime


class SubscriptionUpdate(SubscriptionCreate):
    pass  # TODO


class SubscriptionResponse(SubscriptionCreateFull):
    id: UUID

    class Config:
        from_attributes = True
