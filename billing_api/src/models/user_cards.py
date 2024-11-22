import enum

from sqlalchemy import UUID, Column, Enum, String

from models.models import Base


class StatusCardsEnum(enum.Enum):
    INIT = "init"
    SUCCESS = "success"
    FAIL = "fail"


class UserCardsStripe(Base):
    user_id = Column(UUID(as_uuid=True), nullable=False)
    stripe_user_id = Column(String, nullable=False)
    token_card = Column(String, nullable=True)
    status = Column(
        Enum(StatusCardsEnum, name="status_cards_enum", create_type=True),
        nullable=False,
        default=StatusCardsEnum.INIT,
    )
    last_numbers_card = Column(String, nullable=True)
