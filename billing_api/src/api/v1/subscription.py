from http import HTTPStatus
from uuid import UUID

from fastapi import APIRouter, Depends, Path

from api.utils import generate_error_responses
from schemas.subscription import SubscriptionCreate, SubscriptionRenew, SubscriptionResponse
from services.subscription_manager import SubscriptionManager, get_subscription_manager

router = APIRouter()


@router.post(
    "/",
    response_model=SubscriptionResponse,
    summary="Создать подписку",
    description="Создаёт подписку для пользователя",
    status_code=HTTPStatus.CREATED,
    responses=generate_error_responses(HTTPStatus.INTERNAL_SERVER_ERROR, HTTPStatus.BAD_REQUEST, HTTPStatus.NOT_FOUND),  # type: ignore[reportArgumentType]
)
async def create_subscription(
    subscription_data: SubscriptionCreate, subscription_manager: SubscriptionManager = Depends(get_subscription_manager)
):
    user_id = UUID("3fa85f64-5717-4562-b3fc-2c963f66afa8")  # TODO: забрать из токена
    return await subscription_manager.create_subscription(user_id, subscription_data)


@router.post(
    "/{subscription_id}/cancel",
    response_model=SubscriptionResponse,
    summary="Отменить подписку",
    description="Отменяет выбранную подписку пользователя",
    status_code=HTTPStatus.OK,
    responses=generate_error_responses(HTTPStatus.INTERNAL_SERVER_ERROR, HTTPStatus.FORBIDDEN, HTTPStatus.NOT_FOUND),  # type: ignore[reportArgumentType]
)
async def cancel_subscription(
    subscription_id: UUID = Path(..., description="ID подписки"),
    subscription_manager: SubscriptionManager = Depends(get_subscription_manager),
):
    user_id = UUID("3fa85f64-5717-4562-b3fc-2c963f66afa8")  # TODO: забрать из токена
    return await subscription_manager.cancel_subscription(user_id=user_id, subscription_id=subscription_id)


@router.post(
    "/{subscription_id}/renew",
    response_model=SubscriptionResponse,
    summary="Обновить подписку",
    description="Обновляет подписку, путем смещения даты завершения подписки",
    status_code=HTTPStatus.OK,
    responses=generate_error_responses(HTTPStatus.INTERNAL_SERVER_ERROR, HTTPStatus.FORBIDDEN, HTTPStatus.NOT_FOUND),  # type: ignore[reportArgumentType]
)
async def renew_subscription(
    renew_data: SubscriptionRenew,
    subscription_id: UUID = Path(..., description="ID подписки"),
    subscription_manager: SubscriptionManager = Depends(get_subscription_manager),
):
    user_id = UUID("3fa85f64-5717-4562-b3fc-2c963f66afa8")  # TODO: забрать из токена
    return await subscription_manager.renew_subscription(
        user_id=user_id, subscription_id=subscription_id, renew_data=renew_data
    )


@router.post(
    "/{subscription_id}/toggle_auto_renewal",
    response_model=SubscriptionResponse,
    summary="Переключить режим автоматического продления подписки",
    description="Включает режим автоматического продления подписки, если он был отключен и наоборот",
    status_code=HTTPStatus.OK,
    responses=generate_error_responses(HTTPStatus.INTERNAL_SERVER_ERROR, HTTPStatus.FORBIDDEN, HTTPStatus.NOT_FOUND),  # type: ignore[reportArgumentType]
)
async def toggle_auto_renewal_subscription(
    subscription_id: UUID = Path(..., description="ID подписки"),
    subscription_manager: SubscriptionManager = Depends(get_subscription_manager),
):
    user_id = UUID("3fa85f64-5717-4562-b3fc-2c963f66afa8")  # TODO: забрать из токена
    return await subscription_manager.toggle_auto_renewal(user_id=user_id, subscription_id=subscription_id)
