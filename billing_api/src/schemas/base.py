from uuid import UUID

from pydantic import BaseModel


class IDMixin(BaseModel):
    id: UUID

    class Config:
        from_attributes = True
