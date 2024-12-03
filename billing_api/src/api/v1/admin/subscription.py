from http import HTTPStatus
from uuid import UUID

from fastapi import APIRouter, Depends, Path
from fastapi_pagination import Page, paginate

from api.utils import generate_error_responses, subscription_query_params
from schemas.subscription import SubscriptionCreate, SubscriptionResponse
from services.subscription_manager import SubscriptionManager, get_subscription_manager

router = APIRouter()


@router.get(
    "/{subscription_id}",
    response_model=SubscriptionResponse,
    summary="Вывести подписку",
    description="Вывести параметры подписки по id",
    status_code=HTTPStatus.OK,
    responses=generate_error_responses(
        HTTPStatus.INTERNAL_SERVER_ERROR, HTTPStatus.NOT_FOUND, HTTPStatus.FORBIDDEN, HTTPStatus.UNAUTHORIZED
    ),  # type: ignore[reportArgumentType]
)
async def get_subscription_by_id(
    subscription_id: UUID = Path(..., description="ID подписки"),
    subscription_manager: SubscriptionManager = Depends(get_subscription_manager),
):
    return await subscription_manager.get(subscription_id)


@router.get(
    "/",
    response_model=Page[SubscriptionResponse],
    summary="Вывести все подписки",
    description="Админ может просмотреть все подписки, пользователь только свои.",
    status_code=HTTPStatus.OK,
    responses=generate_error_responses(HTTPStatus.INTERNAL_SERVER_ERROR, HTTPStatus.FORBIDDEN, HTTPStatus.UNAUTHORIZED),
    # type: ignore[reportArgumentType]
)
async def get_subscriptions(
    subscription_manager: SubscriptionManager = Depends(get_subscription_manager),
    query_params: dict[str, str] = Depends(subscription_query_params),
):
    return paginate(await subscription_manager.get_many(query_params))


@router.post(
    "/",
    response_model=SubscriptionResponse,
    summary="Создать подписку для пользователя",
    description="Создаёт подписку для пользователя",
    status_code=HTTPStatus.CREATED,
    responses=generate_error_responses(HTTPStatus.INTERNAL_SERVER_ERROR, HTTPStatus.BAD_REQUEST, HTTPStatus.NOT_FOUND),  # type: ignore[reportArgumentType]
)
async def create_subscription(
    user_id: UUID,
    subscription_data: SubscriptionCreate,
    subscription_manager: SubscriptionManager = Depends(get_subscription_manager),
):
    return await subscription_manager.create_subscription(user_id, subscription_data)


@router.post(
    "/{subscription_id}/cancel",
    response_model=SubscriptionResponse,
    summary="Отменить подписку для пользователя",
    description="Отменяет выбранную подписку для пользователя",
    status_code=HTTPStatus.OK,
    responses=generate_error_responses(HTTPStatus.INTERNAL_SERVER_ERROR, HTTPStatus.FORBIDDEN, HTTPStatus.NOT_FOUND),  # type: ignore[reportArgumentType]
)
async def cancel_subscription(
    user_id: UUID,
    subscription_id: UUID = Path(..., description="ID подписки"),
    subscription_manager: SubscriptionManager = Depends(get_subscription_manager),
):
    return await subscription_manager.cancel_subscription(user_id=user_id, subscription_id=subscription_id)
