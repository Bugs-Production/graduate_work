from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi_pagination import Page, paginate

from api.v1.utils import transaction_filters_query_params
from schemas.admin import TransactionSchema, TransactionSchemaShort
from services.admin import AdminTransactionService, get_admin_transaction_service
from services.exceptions import ORMBadRequestError, TransactionNotFoundError

router = APIRouter()


@router.get(
    "/{transaction_id}",
    response_model=TransactionSchema,
    summary="Вывести информацию о транзакции",
    description="Вывести подробную информацию о транзакции",
    responses={
        status.HTTP_404_NOT_FOUND: {
            "content": {"application/json": {"example": {"detail": "Internal server error"}}},
        },
    },
)
async def get_transaction(
    transaction_id: UUID,
    admin_service: AdminTransactionService = Depends(get_admin_transaction_service),
) -> Page[TransactionSchema]:
    try:
        return await admin_service.get_transaction_by_id(str(transaction_id))
    except TransactionNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e)) from None


@router.get(
    "/",
    response_model=Page[TransactionSchemaShort],
    summary="Вывести транзакции пользователя",
    description="Вывести транзакции пользователя, возможно отфильтровать по параметрам",
    responses={
        status.HTTP_400_BAD_REQUEST: {
            "content": {"application/json": {"example": {"detail": "Internal server error"}}},
        },
        status.HTTP_404_NOT_FOUND: {
            "content": {"application/json": {"example": {"detail": "Internal server error"}}},
        },
    },
)
async def get_user_transactions(
    user_id: UUID,
    subscription_id: UUID | None = None,
    query_params: dict[str, str] = Depends(transaction_filters_query_params),
    admin_service: AdminTransactionService = Depends(get_admin_transaction_service),
) -> Page[TransactionSchemaShort]:
    try:
        transactions_list = await admin_service.get_user_transactions(user_id, subscription_id, query_params)
    except ORMBadRequestError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)) from None

    if not transactions_list:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Transactions with such params not found"
        ) from None

    return paginate(transactions_list)
