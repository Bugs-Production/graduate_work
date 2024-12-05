import random
import uuid
from datetime import datetime

import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession

from models.enums import PaymentType, TransactionStatus
from models.models import Subscription, SubscriptionPlan, Transaction, UserCardsStripe


@pytest_asyncio.fixture(loop_scope="session")
async def random_transactions(
    test_session: AsyncSession,
    random_user_cards: list[UserCardsStripe],
    random_subscription_plans: list[SubscriptionPlan],
    random_subscriptions: list[Subscription],
) -> list[Transaction]:
    transactions = []
    for _ in range(50):
        subscription = random.choice(random_subscriptions)
        card = random.choice(random_user_cards)

        transaction = Transaction(
            id=uuid.uuid4(),
            subscription_id=subscription.id,
            user_id=card.user_id,
            amount=random.randint(5000, 20000),
            payment_type=random.choice(list(PaymentType)),
            status=random.choice(list(TransactionStatus)),
            user_card_id=card.id,
            stripe_payment_intent_id=f"pi_{uuid.uuid4()}",
            created_at=datetime.now(),
            updated_at=datetime.now(),
        )
        transactions.append(transaction)

    test_session.add_all(transactions)
    await test_session.commit()

    return transactions
