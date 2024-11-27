import random
import uuid
from datetime import datetime

import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession

from models.models import SubscriptionPlan


@pytest_asyncio.fixture(loop_scope="session")
async def random_subscription_plans(test_session: AsyncSession):
    subscription_plans = []
    for i in range(10):
        plan = SubscriptionPlan(
            id=uuid.uuid4(),
            title=f"Test Plan {i + 1}",
            description=f"This is a description for test plan {i + 1}",
            price=100 + i * 10,
            duration_days=random.choice([1, 7, 30]),
            created_at=datetime.now(),
            updated_at=datetime.now(),
        )
        subscription_plans.append(plan)
    test_session.add_all(subscription_plans)
    await test_session.commit()
    return subscription_plans
