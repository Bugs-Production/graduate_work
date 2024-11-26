from http import HTTPStatus
from uuid import UUID

from fastapi import APIRouter, Depends

from api.utils import generate_error_responses
from schemas.subscription import SubscriptionCreate, SubscriptionResponse
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
