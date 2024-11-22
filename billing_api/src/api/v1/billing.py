import stripe
from fastapi import APIRouter, Depends, Request
from fastapi.responses import JSONResponse, RedirectResponse

from core.config import settings
from core.templates import templates
from services.subscration_manager import SubscriptionManager, get_manager_service

stripe.api_key = settings.stripe_api_key

router = APIRouter()


@router.get("/get-card-form/")
async def get_add_card_form(request: Request):
    return templates.TemplateResponse("checkout-session.html", {"request": request})


@router.post("/create-checkout-session/")
async def initialize_payment_method(
    manager_service: SubscriptionManager = Depends(get_manager_service),
) -> RedirectResponse:
    user_id = "637987f8-e99d-4b00-b4ca-54e377c042e2"  # TODO: заменить на реальный айди юзера, полученный с токена auth

    url = await manager_service.create_user_card(user_id=user_id)
    return RedirectResponse(url, status_code=303)


@router.post("/payment/webhook/")
async def stripe_webhook(
    request: Request, manager_service: SubscriptionManager = Depends(get_manager_service)
) -> JSONResponse:
    payload = await request.json()
    event_type = payload.get("type")
    data = payload.get("data")

    if data is not None:
        await manager_service.handle_webhook(event_type=event_type, data=data)

    return JSONResponse(content={"detail": "success"})
