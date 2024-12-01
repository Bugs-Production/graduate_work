import asyncio
import random
import uuid
from datetime import datetime, timedelta

from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine
from sqlalchemy.orm import sessionmaker

from core.config import settings
from models.enums import PaymentType, StatusCardsEnum, SubscriptionStatus, TransactionStatus
from models.models import Subscription, SubscriptionPlan, Transaction, UserCardsStripe

num_plans = 10
num_subscriptions = 50
num_users = 20
num_transactions = 100


async def fill_test_data_to_db():
    engine = create_async_engine(settings.postgres_url, echo=True, future=True)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with async_session() as session:
        # Создание тестовых UserCardsStripe
        user_cards = []
        for _ in range(num_users):
            user_card = UserCardsStripe(
                id=uuid.uuid4(),
                user_id=uuid.uuid4(),
                stripe_user_id=f"stripe_{uuid.uuid4()}",
                token_card=f"tok_{uuid.uuid4()}",
                status=random.choice(list(StatusCardsEnum)),
                last_numbers_card=str(random.randint(1000, 9999)),
                is_default=random.choice([True, False]),
                created_at=datetime.now(),
                updated_at=datetime.now(),
            )
            user_cards.append(user_card)
        session.add_all(user_cards)
        await session.commit()

        # Создание тестовых планов подписки
        subscription_plans = []
        for i in range(num_plans):
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
        session.add_all(subscription_plans)
        await session.commit()

        # Создание тестовых подписок
        subscriptions = []
        for _ in range(num_subscriptions):
            plan = random.choice(subscription_plans)
            start_date = datetime.now()
            end_date = start_date + timedelta(days=plan.duration_days)
            user_card = random.choice(user_cards)

            subscription = Subscription(
                id=uuid.uuid4(),
                user_id=user_card.user_id,
                plan_id=plan.id,
                status=random.choice(list(SubscriptionStatus)),
                start_date=start_date,
                end_date=end_date,
                auto_renewal=random.choice([True, False]),
                created_at=datetime.now(),
                updated_at=datetime.now(),
            )
            subscriptions.append(subscription)
        session.add_all(subscriptions)
        await session.commit()

        # Создание тестовых транзакций
        transactions = []
        for _ in range(num_transactions):
            subscription = random.choice(subscriptions)
            user_card = random.choice(user_cards)

            transaction = Transaction(
                id=uuid.uuid4(),
                subscription_id=subscription.id,
                user_id=user_card.user_id,
                amount=random.randint(5000, 20000),
                payment_type=random.choice(list(PaymentType)),
                status=random.choice(list(TransactionStatus)),
                user_card_id=user_card.id,
                stripe_payment_intent_id=f"pi_{uuid.uuid4()}",
                created_at=datetime.now(),
                updated_at=datetime.now(),
            )
            transactions.append(transaction)
        session.add_all(transactions)
        await session.commit()


if __name__ == "__main__":
    asyncio.run(fill_test_data_to_db())
