from datetime import datetime
from uuid import UUID

from pydantic import BaseModel


class IDMixin(BaseModel):
    id: UUID

    class Config:
        from_attributes = True


class TransactionSchemaBaseResponse(IDMixin):
    subscription_id: UUID
    user_id: UUID
    payment_type: str
    amount: int
    status: str


class TransactionSchemaResponse(TransactionSchemaBaseResponse):
    subscription_id: UUID
    user_id: UUID
    payment_type: str
    amount: int
    status: str
    user_card_id: UUID
    stripe_payment_intent_id: str
    created_at: datetime
    updated_at: datetime
