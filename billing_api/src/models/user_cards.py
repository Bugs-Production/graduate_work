import enum
import uuid
from datetime import datetime

from sqlalchemy import UUID, Column, DateTime, Enum, String

from db.postgres import Base


class StatusCardsEnum(enum.Enum):
    INIT = "init"
    SUCCESS = "success"
    FAIL = "fail"


class UserCardsStripe(Base):
    __tablename__ = "user_cards_stripe"

    id = Column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        unique=True,
        nullable=False,
    )
    created_at = Column(DateTime, default=datetime.now())
    user_id = Column(UUID(as_uuid=True), nullable=False)
    stripe_user_id = Column(String, nullable=False)
    token_card = Column(String, nullable=True)
    status = Column(
        Enum(StatusCardsEnum, name="status_cards_enum", create_type=True),
        nullable=False,
        default=StatusCardsEnum.INIT,
    )
    last_numbers_card = Column(String, nullable=True)
