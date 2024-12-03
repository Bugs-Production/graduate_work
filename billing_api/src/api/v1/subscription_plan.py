from http import HTTPStatus
from uuid import UUID

from fastapi import APIRouter, Depends, Path
from fastapi_pagination import Page, paginate

from api.utils import generate_error_responses
from schemas.subscription_plan import SubscriptionPlanResponse
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
):
    return paginate(await subscription_plan_service.get_many({"is_archive": False}))


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
