from functools import lru_cache
from uuid import UUID

from fastapi import Depends
from sqlalchemy.exc import DBAPIError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select

from db.postgres import get_postgres_session
from models.models import Transaction
from services.exceptions import ORMBadRequestError, TransactionNotFoundError


class AdminTransactionService:
    def __init__(self, postgres_session: AsyncSession):
        self.postgres_session = postgres_session

    async def get_transaction_by_id(self, transaction_id: UUID, user_id: UUID) -> Transaction:
        async with self.postgres_session() as session:
            notifications_data = await session.scalars(
                select(Transaction).filter_by(id=str(transaction_id), user_id=str(user_id))
            )
            notification = notifications_data.first()

            if notification is None:
                raise TransactionNotFoundError("Transaction not found")

            return notification

    async def get_user_transactions(
        self, user_id: UUID, subscription_id: UUID | None, query_params: dict[str, str]
    ) -> list[Transaction] | None:
        filter_params = {"user_id": str(user_id)}
        if query_params:
            filter_params.update(query_params)
        if subscription_id:
            filter_params.update({"subscription_id": str(subscription_id)})

        async with self.postgres_session() as session:
            try:
                result = await session.scalars(select(Transaction).filter_by(**filter_params))
            except DBAPIError as e:
                raise ORMBadRequestError(f"Bad request {e}") from None
            return result.all()


@lru_cache
def get_admin_transaction_service(
    postgres_session: AsyncSession = Depends(get_postgres_session),
) -> AdminTransactionService:
    return AdminTransactionService(postgres_session)
