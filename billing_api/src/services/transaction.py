from functools import lru_cache
from uuid import UUID

from fastapi import Depends
from sqlalchemy.exc import DBAPIError, IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from db.postgres import get_postgres_session
from models.enums import PaymentType
from models.models import Transaction
from services.exceptions import ObjectNotUpdatedException, ORMBadRequestError, TransactionNotFoundError


class TransactionService:
    def __init__(self, postgres_session: AsyncSession):
        self.postgres_session = postgres_session

    async def get_user_transaction_by_id(self, transaction_id: UUID, user_id: UUID) -> Transaction:
        async with self.postgres_session() as session:
            result = await session.scalars(select(Transaction).filter_by(id=str(transaction_id), user_id=str(user_id)))
            transaction = result.first()

            if transaction is None:
                raise TransactionNotFoundError("Transaction not found")

            return transaction

    async def get_transaction_by_id(self, transaction_id: UUID) -> Transaction:
        async with self.postgres_session() as session:
            result = await session.scalars(select(Transaction).filter_by(id=str(transaction_id)))
            transaction = result.first()

            if transaction is None:
                raise TransactionNotFoundError("Transaction not found")

            return transaction

    async def get_transactions(self, query_params: dict[str, str]) -> list[Transaction] | None:
        async with self.postgres_session() as session:
            try:
                result = await session.scalars(select(Transaction).filter_by(**query_params))
            except DBAPIError as e:
                raise ORMBadRequestError(f"Bad request {e}") from None
            return result.all()

    async def create_transaction(
        self,
        subscription_id: UUID,
        user_id: UUID,
        amount: int,
        payment_type: PaymentType,
        user_card_id: UUID,
        stripe_payment_intent_id: str | None = None,
    ):
        async with self.postgres_session() as session:
            transaction = Transaction(
                subscription_id=subscription_id,
                user_id=user_id,
                amount=amount,
                payment_type=payment_type,
                user_card_id=user_card_id,
                stripe_payment_intent_id=stripe_payment_intent_id,
            )
            session.add(transaction)
            await session.commit()
            return transaction

    async def update_transaction(self, transaction_id: UUID, updated_data: dict) -> Transaction:
        transaction = await self.get_transaction_by_id(transaction_id)

        for key, value in updated_data.items():
            if hasattr(transaction, key):
                setattr(transaction, key, value)

        async with self.postgres_session() as session:
            try:
                await session.merge(transaction)
                await session.commit()
            except IntegrityError as e:
                await session.rollback()
                raise ObjectNotUpdatedException(f"Update error: {e}") from None


@lru_cache
def get_admin_transaction_service(
    postgres_session: AsyncSession = Depends(get_postgres_session),
) -> TransactionService:
    return TransactionService(postgres_session)
