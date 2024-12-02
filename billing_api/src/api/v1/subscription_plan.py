from http import HTTPStatus
from uuid import UUID

from fastapi import APIRouter, Depends, Path
from fastapi_pagination import Page, paginate

from api.jwt_access_token import AccessTokenPayload, UserRole, require_admin, security_jwt
from api.utils import generate_error_responses
from schemas.subscription_plan import SubscriptionPlanCreate, SubscriptionPlanResponse, SubscriptionPlanUpdate
from services.subscription_plan import SubscriptionPlanService, get_subscription_plan_service

router = APIRouter()


@router.get(
    "/",
    response_model=Page[SubscriptionPlanResponse],
    summary="Вывести планы подписок",
    description="Вывести все существующие планы подписок с пагинацией",
    status_code=HTTPStatus.OK,
    responses=generate_error_responses(HTTPStatus.INTERNAL_SERVER_ERROR, HTTPStatus.FORBIDDEN, HTTPStatus.UNAUTHORIZED),  # type: ignore[reportArgumentType]
)
async def get_subscription_plans(
    subscription_plan_service: SubscriptionPlanService = Depends(get_subscription_plan_service),
    token: AccessTokenPayload = Depends(security_jwt),
):
    if token.role == UserRole.ADMIN:
        subscription_plans = await subscription_plan_service.get_many()
    else:
        subscription_plans = await subscription_plan_service.get_many({"is_archive": False})
    return paginate(subscription_plans)


@router.post(
    "/",
    response_model=SubscriptionPlanResponse,
    summary="Создать план подписки",
    description="Создание плана подписки",
    status_code=HTTPStatus.CREATED,
    responses=generate_error_responses(HTTPStatus.INTERNAL_SERVER_ERROR, HTTPStatus.FORBIDDEN, HTTPStatus.UNAUTHORIZED),  # type: ignore[reportArgumentType]
    dependencies=[Depends(require_admin)],
)
async def create_subscription_plan(
    subscription_plan_data: SubscriptionPlanCreate,
    subscription_plan_service: SubscriptionPlanService = Depends(get_subscription_plan_service),
):
    return await subscription_plan_service.create_new_subscription_plan(subscription_plan_data)


@router.get(
    "/{subscription_plan_id}",
    response_model=SubscriptionPlanResponse,
    summary="Вывести план подписки",
    description="Вывести план подписки по его id",
    status_code=HTTPStatus.OK,
    responses=generate_error_responses(HTTPStatus.INTERNAL_SERVER_ERROR, HTTPStatus.NOT_FOUND),  # type: ignore[reportArgumentType]
)
async def get_subscription_plan_by_id(
    subscription_plan_id: UUID = Path(..., description="ID плана подписки"),
    subscription_plan_service: SubscriptionPlanService = Depends(get_subscription_plan_service),
):
    return await subscription_plan_service.get(subscription_plan_id)


@router.patch(
    "/{subscription_plan_id}",
    response_model=SubscriptionPlanResponse,
    summary="Обновить план подписки",
    description="Обновление данных выбранного плана подписки",
    status_code=HTTPStatus.OK,
    responses=generate_error_responses(
        HTTPStatus.INTERNAL_SERVER_ERROR, HTTPStatus.NOT_FOUND, HTTPStatus.FORBIDDEN, HTTPStatus.UNAUTHORIZED
    ),  # type: ignore[reportArgumentType]
    dependencies=[Depends(require_admin)],
)
async def update_subscription_plan(
    subscription_plan_data: SubscriptionPlanUpdate,
    subscription_plan_id: UUID = Path(..., description="ID плана подписки"),
    subscription_plan_service: SubscriptionPlanService = Depends(get_subscription_plan_service),
):
    return await subscription_plan_service.update_subscription_plan(subscription_plan_id, subscription_plan_data)
