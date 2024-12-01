from uuid import UUID

from pydantic import BaseModel, Field


class SubscriptionPlanBase(BaseModel):
    title: str = Field(..., min_length=1, max_length=255)
    description: str = Field(..., min_length=1, max_length=1000)
    price: int = Field(..., ge=0)
    duration_days: int = Field(..., gt=0)
    archive: bool | None = None


class SubscriptionPlanCreate(SubscriptionPlanBase):
    pass


class SubscriptionPlanUpdate(BaseModel):
    title: str | None = Field(None, min_length=1, max_length=255)
    description: str | None = Field(None, min_length=1, max_length=1000)
    price: int | None = Field(None, ge=0)
    duration_days: int | None = Field(default=None, gt=0)
    archive: bool | None = None


class SubscriptionPlanResponse(SubscriptionPlanBase):
    id: UUID

    class Config:
        from_attributes = True
