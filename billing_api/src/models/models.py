import uuid
from datetime import datetime

from sqlalchemy import Boolean, ForeignKey, String, Text, func
from sqlalchemy.dialects.postgresql import ENUM, TIMESTAMP
from sqlalchemy.dialects.postgresql import UUID as PgUUID
from sqlalchemy.ext.declarative import declared_attr
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship

from models.enums import SubscriptionStatus


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
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)

    subscriptions: Mapped[list["Subscription"]] = relationship(back_populates="plan")


class Subscription(Base):
    user_id: Mapped[uuid.UUID] = mapped_column(PgUUID)
    plan_id: Mapped[uuid.UUID] = mapped_column(PgUUID, ForeignKey("subscriptionplans.id", ondelete="RESTRICT"))
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
