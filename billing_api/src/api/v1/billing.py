import logging
import uuid

import stripe
from fastapi import APIRouter, Depends, Request, status
from fastapi.responses import JSONResponse, RedirectResponse

from api.jwt_access_token import AccessTokenPayload, security_jwt
from core.config import settings
from core.templates import templates
from services.cards_manager import CardsManager, get_cards_manager_service
from services.exceptions import CardNotFoundException, UserNotOwnerOfCardException
from services.subscription_manager import SubscriptionManager, get_subscription_manager

logger = logging.getLogger(__name__)

stripe.api_key = settings.stripe_api_key

router = APIRouter()


@router.get(
    "/get-card-form/",
    summary="Получение формы добавления карты",
    description="Возвращает HTML-форму для добавления новой карты.",
)
async def get_add_card_form(request: Request):
    return templates.TemplateResponse("checkout-session.html", {"request": request})


@router.get(
    "/success-card/",
    summary="Шаблон успешной привязки",
    description="Возвращает HTML-форму после успешной привязки карты.",
)
async def success_card(request: Request):
    return templates.TemplateResponse("success_redirect.html", {"request": request})


@router.post(
    "/create-checkout-session/",
    summary="Создание сессии привязки карты",
    description="Инициализирует процесс добавления новой карты для пользователя.",
)
async def initialize_payment_method(
    manager_service: CardsManager = Depends(get_cards_manager_service),
    token: AccessTokenPayload = Depends(security_jwt),
) -> RedirectResponse:
    url = await manager_service.create_user_card(user_id=token.user_id)
    return RedirectResponse(url, status_code=303)


@router.post(
    "/payment/webhook/",
    summary="Обработка Stripe Webhook",
    description="Обрабатывает события Stripe Webhook, такие как привязка карты или ошибки.",
)
async def stripe_webhook(
    request: Request,
    cards_manager_service: CardsManager = Depends(get_cards_manager_service),
    subscription_manager: SubscriptionManager = Depends(get_subscription_manager),
) -> JSONResponse:
    payload = await request.json()
    event_type = payload.get("type")
    data = payload.get("data")

    webhook_handlers = {
        # обработка в CardsManager
        "payment_method.attached": cards_manager_service.handle_webhook,
        "setup_intent.succeeded": cards_manager_service.handle_webhook,
        "setup_intent.setup_failed": cards_manager_service.handle_webhook,
        # обработка в SubscriptionManager
        "payment_intent.succeeded": subscription_manager.handle_payment_webhook,
        "payment_intent.payment_failed": subscription_manager.handle_payment_webhook,
        "charge.refunded": subscription_manager.handle_payment_webhook,
    }
    handler = webhook_handlers.get(event_type)
    if handler:
        await handler(event_type, data)
    else:
        logger.warning(f"Не найден обработчик для вебхуа типа {event_type}")

    return JSONResponse(content={"detail": "success"})


@router.post(
    "/set-default-card/",
    summary="Делает карту дефолтной",
    description="Ставит выбранную карту юзера дефолтной, "
    "при этом если другая карта была дефолтной, с нее активность снимается",
    responses={
        status.HTTP_200_OK: {
            "description": "Успешный запрос.",
            "content": {"application/json": {"example": {"detail": "success"}}},
        },
        status.HTTP_400_BAD_REQUEST: {
            "description": "Карта уже является дефолтной",
            "content": {"application/json": {"example": {"detail": "Card is already set as default"}}},
        },
        status.HTTP_403_FORBIDDEN: {
            "description": "Доступ запрещен",
            "content": {"application/json": {"example": {"detail": "Forbidden"}}},
        },
        status.HTTP_404_NOT_FOUND: {
            "description": "Карта не найдена",
            "content": {"application/json": {"example": {"detail": "User card not found"}}},
        },
    },
)
async def set_default_card_user(
    card_id: uuid.UUID,
    manager_service: CardsManager = Depends(get_cards_manager_service),
    token: AccessTokenPayload = Depends(security_jwt),
) -> JSONResponse:
    try:
        success = await manager_service.set_default_card(user_id=str(token.user_id), card_id=str(card_id))
        if success:
            return JSONResponse(content={"detail": "success"}, status_code=200)
        return JSONResponse(content={"detail": "Card is already set as default"}, status_code=400)
    except CardNotFoundException as e:
        return JSONResponse(content={"detail": str(e)}, status_code=404)
    except UserNotOwnerOfCardException as e:
        return JSONResponse(content={"detail": str(e)}, status_code=403)


@router.get(
    "/all-user-cards/",
    summary="Список карт юзера.",
    description="Получает список активных карт юзера.",
    responses={
        status.HTTP_200_OK: {
            "description": "Успешный запрос.",
            "content": {
                "application/json": {
                    "example": [
                        {
                            "id": "15153fbb-b2b6-4ad4-b226-6aff38305f2b",
                            "last_numbers": "4242",
                            "default": True,
                        },
                    ]
                }
            },
        },
        status.HTTP_404_NOT_FOUND: {
            "description": "Карты не найдены",
            "content": {"application/json": {"example": {"detail": "User cards not found"}}},
        },
    },
)
async def get_all_user_cards(
    manager_service: CardsManager = Depends(get_cards_manager_service),
    token: AccessTokenPayload = Depends(security_jwt),
) -> JSONResponse:
    manager_response = await manager_service.get_all_user_cards(user_id=str(token.user_id))
    if manager_response:
        return JSONResponse(content=manager_response, status_code=200)
    return JSONResponse(content={"detail": "User cards not found"}, status_code=404)


@router.delete(
    "/delete-card/",
    summary="Удаляет карту у юзера.",
    description="Удаляет карту у юзера, так же дополнительно проверяет нет ли другой, чтоб сделать ее дефолтной.",
    responses={
        status.HTTP_200_OK: {
            "description": "Успешный запрос.",
            "content": {"application/json": {"example": {"detail": "success"}}},
        },
        status.HTTP_400_BAD_REQUEST: {
            "description": "Некорректный запрос",
            "content": {"application/json": {"example": {"detail": "Sorry try again later"}}},
        },
        status.HTTP_403_FORBIDDEN: {
            "description": "Доступ запрещен",
            "content": {"application/json": {"example": {"detail": "Forbidden"}}},
        },
        status.HTTP_404_NOT_FOUND: {
            "description": "Карта не найдена",
            "content": {"application/json": {"example": {"detail": "User card not found"}}},
        },
    },
)
async def delete_card_user(
    card_id: uuid.UUID,
    manager_service: CardsManager = Depends(get_cards_manager_service),
    token: AccessTokenPayload = Depends(security_jwt),
) -> JSONResponse:
    try:
        result_service = await manager_service.remove_card_from_user(card_id=card_id, user_id=str(token.user_id))
        if result_service:
            return JSONResponse(content={"detail": "success"}, status_code=200)
        return JSONResponse(content={"detail": "Sorry try again later"}, status_code=400)
    except CardNotFoundException as e:
        return JSONResponse(content={"detail": str(e)}, status_code=404)
    except UserNotOwnerOfCardException as e:
        return JSONResponse(content={"detail": str(e)}, status_code=403)
