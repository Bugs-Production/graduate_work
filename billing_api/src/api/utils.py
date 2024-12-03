from http import HTTPStatus
from typing import Annotated, Any
from uuid import UUID

from fastapi import Query
from pydantic import BaseModel

from models.enums import PaymentType, SubscriptionStatus, TransactionStatus


class ErrorResponse(BaseModel):
    detail: str


def generate_error_responses(*error_statuses: HTTPStatus) -> dict[int, dict[str, Any]]:
    """
    Генерирует стандантизированные описания ошибок API,
    используя стандартные HTTP статусы и их описания.
    """
    return {
        int(error_status.value): {"description": error_status.phrase, "model": ErrorResponse}
        for error_status in error_statuses
    }


def transaction_query_params(
    subscription_id: UUID | None = None,
    status: Annotated[TransactionStatus | None, Query()] = None,
    payment_type: Annotated[PaymentType | None, Query()] = None,
) -> dict[str, TransactionStatus | PaymentType]:
    query_params = {"subscription_id": subscription_id, "status": status, "payment_type": payment_type}
    return {k: v for k, v in query_params.items() if v is not None}


def subscription_query_params(
    status: Annotated[SubscriptionStatus | None, Query()] = None,
    plan_id: Annotated[UUID | None, Query()] = None,
    auto_renewal: Annotated[bool | None, Query()] = None,
) -> dict[str, TransactionStatus | PaymentType]:
    query_params = {"status": status, "plan_id": plan_id, "auto_renewal": auto_renewal}
    return {k: v for k, v in query_params.items() if v is not None}
