from typing import Annotated

from fastapi import Query

from models.enums import PaymentType, TransactionStatus


def transaction_filters_query_params(
    status: Annotated[TransactionStatus | None, Query()] = None,
    payment_type: Annotated[PaymentType | None, Query()] = None,
) -> dict[str, TransactionStatus | PaymentType]:
    query_params = {"status": status, "payment_type": payment_type}
    return {k: v for k, v in query_params.items() if v is not None}
