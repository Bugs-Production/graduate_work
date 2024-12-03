from http import HTTPStatus
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from fastapi_pagination import Page, paginate

from api.utils import generate_error_responses, transaction_query_params
from schemas.admin import TransactionSchemaBaseResponse, TransactionSchemaResponse
from services.exceptions import TransactionNotFoundError
from services.transaction import TransactionService, get_admin_transaction_service

router = APIRouter()


@router.get(
    "/{transaction_id}",
    response_model=TransactionSchemaResponse,
    summary="Вывести информацию о транзакции",
    description="Вывести подробную информацию о транзакции",
    responses=generate_error_responses(HTTPStatus.INTERNAL_SERVER_ERROR, HTTPStatus.NOT_FOUND, HTTPStatus.UNAUTHORIZED),  # type: ignore[reportArgumentType]
)
async def get_transaction_by_id(
    transaction_id: UUID,
    transaction_service: TransactionService = Depends(get_admin_transaction_service),
) -> Page[TransactionSchemaResponse]:
    try:
        return await transaction_service.get_transaction_by_id(transaction_id)
    except TransactionNotFoundError as e:
        raise HTTPException(status_code=HTTPStatus.NOT_FOUND, detail=str(e)) from None


@router.get(
    "/",
    response_model=Page[TransactionSchemaBaseResponse],
    summary="Вывести транзакции",
    description="Вывести транзакции с пагинацией и фильтрацией по полям",
    responses=generate_error_responses(HTTPStatus.INTERNAL_SERVER_ERROR, HTTPStatus.UNAUTHORIZED),  # type: ignore[reportArgumentType]
)
async def get_transactions(
    query_params: dict = Depends(transaction_query_params),
    transaction_service: TransactionService = Depends(get_admin_transaction_service),
) -> Page[TransactionSchemaBaseResponse]:
    transactions_list = await transaction_service.get_transactions(query_params)

    if not transactions_list:
        raise HTTPException(
            status_code=HTTPStatus.NOT_FOUND, detail="Transactions with such params not found"
        ) from None

    return paginate(transactions_list)
