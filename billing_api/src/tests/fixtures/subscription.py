import random
import uuid
from datetime import datetime, timedelta

import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession

from models.enums import SubscriptionStatus
from models.models import Subscription, SubscriptionPlan, UserCardsStripe


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
