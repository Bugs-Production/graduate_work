from http import HTTPStatus
from uuid import UUID

from fastapi import APIRouter, Depends, Path
from fastapi_pagination import Page, paginate

from api.jwt_access_token import AccessTokenPayload, security_jwt
from api.utils import generate_error_responses, subscription_query_params
from schemas.subscription import SubscriptionCreate, SubscriptionRenew, SubscriptionResponse
from services.subscription_manager import SubscriptionManager, get_subscription_manager

router = APIRouter()


@router.get(
    "/{subscription_id}",
    response_model=SubscriptionResponse,
    summary="Вывести подписку пользователя",
    description="Вывести параметры подписки пользователя по id",
    status_code=HTTPStatus.OK,
    responses=generate_error_responses(
        HTTPStatus.INTERNAL_SERVER_ERROR, HTTPStatus.NOT_FOUND, HTTPStatus.FORBIDDEN, HTTPStatus.UNAUTHORIZED
    ),  # type: ignore[reportArgumentType]
)
async def get_subscription_by_id(
    subscription_id: UUID = Path(..., description="ID подписки"),
    subscription_manager: SubscriptionManager = Depends(get_subscription_manager),
    token: AccessTokenPayload = Depends(security_jwt),
):
    return await subscription_manager.get_user_subscription(token.user_id, subscription_id)


@router.get(
    "/",
    response_model=Page[SubscriptionResponse],
    summary="Вывести все подписки",
    description="Вывести все подписки пользователя с пагинацией и фильтрацией по полям",
    status_code=HTTPStatus.OK,
    responses=generate_error_responses(HTTPStatus.INTERNAL_SERVER_ERROR, HTTPStatus.FORBIDDEN, HTTPStatus.UNAUTHORIZED),  # type: ignore[reportArgumentType]
)
async def get_subscriptions(
    subscription_manager: SubscriptionManager = Depends(get_subscription_manager),
    query_params: dict[str, str | UUID] = Depends(subscription_query_params),
    token: AccessTokenPayload = Depends(security_jwt),
):
    query_params.update({"user_id": token.user_id})
    return paginate(await subscription_manager.get_subscriptions(query_params))


@router.post(
    "/",
    response_model=SubscriptionResponse,
    summary="Создать подписку",
    description="Создаёт подписку для пользователя",
    status_code=HTTPStatus.CREATED,
    responses=generate_error_responses(HTTPStatus.INTERNAL_SERVER_ERROR, HTTPStatus.BAD_REQUEST, HTTPStatus.NOT_FOUND),  # type: ignore[reportArgumentType]
)
async def create_subscription(
    subscription_data: SubscriptionCreate,
    subscription_manager: SubscriptionManager = Depends(get_subscription_manager),
    token: AccessTokenPayload = Depends(security_jwt),
):
    return await subscription_manager.create_subscription(token.user_id, subscription_data)


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
    token: AccessTokenPayload = Depends(security_jwt),
):
    return await subscription_manager.cancel_subscription(user_id=token.user_id, subscription_id=subscription_id)


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
    token: AccessTokenPayload = Depends(security_jwt),
):
    return await subscription_manager.renew_subscription(
        user_id=token.user_id, subscription_id=subscription_id, renew_data=renew_data
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
    token: AccessTokenPayload = Depends(security_jwt),
):
    return await subscription_manager.toggle_subscription_auto_renewal(
        user_id=token.user_id, subscription_id=subscription_id
    )
