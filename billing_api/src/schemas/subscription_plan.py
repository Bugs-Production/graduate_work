from uuid import UUID

from pydantic import BaseModel


class SubscriptionPlanBase(BaseModel):
    title: str
    description: str
    price: int
    duration_days: int


class SubscriptionPlanCreate(SubscriptionPlanBase):
    pass


class SubscriptionPlanUpdate(BaseModel):
    title: str | None
    description: str | None
    price: int | None
    duration_days: int | None


class SubscriptionPlanResponse(SubscriptionPlanBase):
    id: UUID

    class Config:
        from_attributes = True
