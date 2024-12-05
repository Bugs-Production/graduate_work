from http import HTTPStatus
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Path
from fastapi_pagination import Page, paginate

from api.utils import generate_error_responses, user_card_query_params
from schemas.user_card import UserCardBase, UserCardResponse
from services.cards_manager import CardsManager, get_cards_manager_service

router = APIRouter()


@router.get(
    "/",
    response_model=Page[UserCardBase],
    summary="Вывести карты",
    description="Вывести все карты с пагинацией и фильтрацией по полям",
    status_code=HTTPStatus.OK,
    responses=generate_error_responses(
        HTTPStatus.INTERNAL_SERVER_ERROR, HTTPStatus.NOT_FOUND, HTTPStatus.FORBIDDEN, HTTPStatus.UNAUTHORIZED
    ),  # type: ignore[reportArgumentType]
)
async def get_user_cards(
    query_params: dict[str, str] = Depends(user_card_query_params),
    user_card_service: CardsManager = Depends(get_cards_manager_service),
):
    cards = await user_card_service.get_all_cards(query_params)

    if not cards:
        raise HTTPException(status_code=HTTPStatus.NOT_FOUND, detail="User Cards with such params not found") from None

    return paginate(cards)


@router.get(
    "/{card_id}",
    response_model=UserCardResponse,
    summary="Вывести информацию о карте",
    description="Вывести параметры карты пользователя по id",
    status_code=HTTPStatus.OK,
    responses=generate_error_responses(
        HTTPStatus.INTERNAL_SERVER_ERROR, HTTPStatus.NOT_FOUND, HTTPStatus.FORBIDDEN, HTTPStatus.UNAUTHORIZED
    ),  # type: ignore[reportArgumentType]
)
async def get_subscription_by_id(
    card_id: UUID = Path(..., description="ID подписки"),
    user_card_service: CardsManager = Depends(get_cards_manager_service),
):
    return await user_card_service.get_card_by_id(card_id)
