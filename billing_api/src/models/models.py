import uuid
from datetime import datetime

from sqlalchemy import BigInteger, Boolean, Column, ForeignKey, String, Text, func
from sqlalchemy.dialects.postgresql import ENUM, TIMESTAMP
from sqlalchemy.dialects.postgresql import UUID as PgUUID
from sqlalchemy.ext.declarative import declared_attr
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship

from models.enums import PaymentType, StatusCardsEnum, SubscriptionStatus, TransactionStatus


class Base(DeclarativeBase):
    @declared_attr.directive
    def __tablename__(cls):
        return f"{cls.__name__.lower()}s"

    id: Mapped[uuid.UUID] = mapped_column(PgUUID, primary_key=True, default=uuid.uuid4)
    created_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True),
        server_default=func.current_timestamp(),
    )
    updated_at: Mapped[datetime] = mapped_column(
        TIMESTAMP(timezone=True),
        server_default=func.current_timestamp(),
        server_onupdate=func.current_timestamp(),
    )


class SubscriptionPlan(Base):
    title: Mapped[str] = mapped_column(String(255))
    description: Mapped[str] = mapped_column(Text)
    price: Mapped[int]
    duration_days: Mapped[int]

    subscriptions: Mapped[list["Subscription"]] = relationship(back_populates="plan")


class Subscription(Base):
    user_id: Mapped[uuid.UUID] = mapped_column(PgUUID)
    plan_id: Mapped[uuid.UUID] = mapped_column(
        PgUUID,
        ForeignKey("subscriptionplans.id", ondelete="RESTRICT"),
    )
    status: Mapped[SubscriptionStatus] = mapped_column(
        ENUM(
            SubscriptionStatus,
            values_callable=lambda obj: [e.value for e in obj],
            name="subscription_status",
        ),
        default=SubscriptionStatus.PENDING.value,
    )
    start_date: Mapped[datetime]
    end_date: Mapped[datetime]
    auto_renewal: Mapped[bool] = mapped_column(Boolean, default=False)

    plan: Mapped["SubscriptionPlan"] = relationship(back_populates="subscriptions")
    transactions: Mapped[list["Transaction"]] = relationship(back_populates="subscription")


class UserCardsStripe(Base):
    user_id = Column(PgUUID(as_uuid=True), nullable=False)
    stripe_user_id = Column(String, nullable=False)
    token_card = Column(String, nullable=True)
    status = Column(
        ENUM(StatusCardsEnum, name="status_cards_enum", create_type=True),
        nullable=False,
        default=StatusCardsEnum.INIT,
    )
    last_numbers_card = Column(String, nullable=True)
    is_default = Column(Boolean, nullable=False, default=False)
    transactions: Mapped[list["Transaction"]] = relationship(back_populates="user_card")


class Transaction(Base):
    subscription_id: Mapped[uuid.UUID] = mapped_column(
        PgUUID,
        ForeignKey("subscriptions.id", ondelete="RESTRICT"),
    )
    user_id: Mapped[uuid.UUID] = mapped_column(PgUUID)
    amount: Mapped[int] = mapped_column(BigInteger)
    payment_type: Mapped[PaymentType] = mapped_column(
        ENUM(
            PaymentType,
            values_callable=lambda obj: [e.value for e in obj],
            name="payment_type",
        ),
        default=PaymentType.STRIPE.value,
        nullable=False,
    )
    status: Mapped[TransactionStatus] = mapped_column(
        ENUM(
            TransactionStatus,
            values_callable=lambda obj: [e.value for e in obj],
            name="transaction_status",
        ),
        default=TransactionStatus.PENDING.value,
        nullable=False,
    )
    user_card_id: Mapped[uuid.UUID] = mapped_column(
        PgUUID,
        ForeignKey("usercardsstripes.id", ondelete="RESTRICT"),
    )
    stripe_payment_intent_id: Mapped[str] = mapped_column(String, nullable=True)

    subscription: Mapped["Subscription"] = relationship(back_populates="transactions")
    user_card: Mapped["UserCardsStripe"] = relationship(back_populates="transactions")
