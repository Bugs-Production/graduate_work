from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi_pagination import Page, paginate

from api.jwt_access_token import AccessTokenPayload, security_jwt
from api.v1.utils import transaction_filters_query_params
from schemas.admin import TransactionSchemaBaseResponse, TransactionSchemaResponse
from services.exceptions import ORMBadRequestError, TransactionNotFoundError
from services.transaction import TransactionService, get_admin_transaction_service

router = APIRouter()


@router.get(
    "/{transaction_id}",
    response_model=TransactionSchemaResponse,
    summary="Вывести информацию о транзакции",
    description="Вывести подробную информацию о транзакции",
    responses={
        status.HTTP_404_NOT_FOUND: {
            "content": {"application/json": {"example": {"detail": "Error message"}}},
        },
    },
)
async def get_transaction(
    transaction_id: UUID,
    token: AccessTokenPayload = Depends(security_jwt),
    transaction_service: TransactionService = Depends(get_admin_transaction_service),
) -> Page[TransactionSchemaResponse]:
    try:
        return await transaction_service.get_transaction_by_id(transaction_id, token.user_id)
    except TransactionNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e)) from None


@router.get(
    "/",
    response_model=Page[TransactionSchemaBaseResponse],
    summary="Вывести транзакции пользователя",
    description="Вывести транзакции пользователя, возможно отфильтровать по параметрам",
    responses={
        status.HTTP_400_BAD_REQUEST: {
            "content": {"application/json": {"example": {"detail": "Error message"}}},
        },
        status.HTTP_404_NOT_FOUND: {
            "content": {"application/json": {"example": {"detail": "Error message"}}},
        },
    },
)
async def get_user_transactions(
    subscription_id: UUID | None = None,
    query_params: dict[str, str] = Depends(transaction_filters_query_params),
    token: AccessTokenPayload = Depends(security_jwt),
    transaction_service: TransactionService = Depends(get_admin_transaction_service),
) -> Page[TransactionSchemaBaseResponse]:
    try:
        transactions_list = await transaction_service.get_user_transactions(
            token.user_id, subscription_id, query_params
        )
    except ORMBadRequestError as e:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e)) from None

    if not transactions_list:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Transactions with such params not found"
        ) from None

    return paginate(transactions_list)
