import random
import uuid
from datetime import datetime, timedelta
from unittest.mock import AsyncMock

import pytest_asyncio
from fastapi import Depends
from jose import jwt
from sqlalchemy.ext.asyncio import AsyncSession

from core.config import settings
from db.postgres import get_session
from models.enums import SubscriptionStatus
from models.models import Subscription, SubscriptionPlan, UserCardsStripe
from services.subscription import SubscriptionService
from services.subscription_manager import SubscriptionManager
from services.subscription_plan import SubscriptionPlanService


@pytest_asyncio.fixture(loop_scope="session")
async def random_subscriptions(
    test_session: AsyncSession,
    random_subscription_plans: list[SubscriptionPlan],
    random_user_cards: list[UserCardsStripe],
) -> list[Subscription]:
    subscriptions = []
    for _ in range(30):
        plan = random.choice(random_subscription_plans)
        start_date = datetime.now()
        end_date = start_date + timedelta(days=plan.duration_days)
        card = random.choice(random_user_cards)

        subscription = Subscription(
            id=uuid.uuid4(),
            user_id=card.user_id,
            plan_id=plan.id,
            status=random.choice(list(SubscriptionStatus)),
            start_date=start_date,
            end_date=end_date,
            auto_renewal=random.choice([True, False]),
            created_at=datetime.now(),
            updated_at=datetime.now(),
        )
        subscriptions.append(subscription)

    test_session.add_all(subscriptions)
    await test_session.commit()

    return subscriptions


@pytest_asyncio.fixture(loop_scope="session")
async def active_user_subscription(
    test_session: AsyncSession,
    access_token_user: dict[str, str],
    random_subscription_plans: list[SubscriptionPlan],
) -> Subscription:
    token = access_token_user["Authorization"].split(" ")[1]
    payload = jwt.decode(token, settings.jwt_secret_key, algorithms=[settings.jwt_algorithm])
    user_id = payload["user_id"]

    subscription = Subscription(
        id=uuid.uuid4(),
        user_id=uuid.UUID(user_id),
        plan_id=random_subscription_plans[0].id,
        status="active",
        auto_renewal=True,
        created_at=datetime.now(),
        start_date=datetime.now(),
        end_date=datetime.now() + timedelta(days=30),
    )
    test_session.add(subscription)
    await test_session.commit()
    await test_session.refresh(subscription)

    return subscription


class MockPaymentManager:
    async def process_payment_with_card(self, *args, **kwargs):
        return AsyncMock(
            id=uuid.uuid4(),
            subscription_id=uuid.uuid4(),
            user_id=uuid.uuid4(),
            amount=1000,
            payment_type="stripe",
            status="pending",
            created_at=datetime.now(),
            updated_at=datetime.now(),
        )

    async def get_user_default_card_id(self, *args, **kwargs):
        return uuid.uuid4()

    async def handle_payment_succeeded(self, *args, **kwargs):
        return AsyncMock(
            id=uuid.uuid4(),
            subscription_id=uuid.uuid4(),
            user_id=uuid.uuid4(),
            status="succeeded",
            amount=1000,
            payment_type="card",
            created_at=datetime.now(),
            updated_at=datetime.now(),
        )

    async def handle_payment_failed(self, *args, **kwargs):
        pass

    async def handle_payment_refunded(self, *args, **kwargs):
        return AsyncMock(
            id=uuid.uuid4(),
            subscription_id=uuid.uuid4(),
            user_id=uuid.uuid4(),
            status="refunded",
            amount=1000,
            created_at=datetime.now(),
            updated_at=datetime.now(),
        )


class MockAuthService:
    async def upgrade_user_to_subscriber(self, *args, **kwargs):
        pass

    async def downgrade_user_to_basic(self, *args, **kwargs):
        pass


class MockNotificationService:
    async def notify_user_subscription_status(self, *args, **kwargs):
        pass


mock_payment_manager = MockPaymentManager()
mock_auth_service = MockAuthService()
mock_notification_service = MockNotificationService()


async def override_get_subscription_manager(
    session: AsyncSession = Depends(get_session),
) -> SubscriptionManager:
    subscription_service = SubscriptionService(session, subscription_plan_service=SubscriptionPlanService(session))

    return SubscriptionManager(
        subscription_service=subscription_service,
        payment_manager=mock_payment_manager,
        auth_service=mock_auth_service,
        notification_service=mock_notification_service,
    )
