from http import HTTPStatus
from unittest.mock import AsyncMock, patch

import pytest
from sqlalchemy import select

from models.enums import StatusCardsEnum
from models.models import UserCardsStripe


class TestGetUserCards:
    def setup_method(self):
        self.get_cards_path = "/api/v1/billing/all-user-cards/"

    @pytest.mark.asyncio(loop_scope="session")
    async def test_get_success_cards_for_user(self, api_client, access_token_user, user_card) -> None:
        """Успешное получение карт юзера."""
        # создаем активную карту юзера
        card = await user_card(StatusCardsEnum.SUCCESS, True)

        # создаем еще одну, но с неуспешным статусом
        await user_card(StatusCardsEnum.FAIL, False)

        response = await api_client.get(self.get_cards_path, headers=access_token_user)
        assert response.status_code == HTTPStatus.OK
        assert len(response.json()) == 1  # проверяем что действительно получили одну карту юзера
        assert response.json() == [
            {
                "id": str(card.id),
                "last_numbers": "4242",
                "default": True,
            }
        ]

    @pytest.mark.asyncio(loop_scope="session")
    async def test_get_success_user_cards(self, api_client, access_token_user) -> None:
        """Отсутствие карт юзера."""
        response = await api_client.get(self.get_cards_path, headers=access_token_user)

        assert response.status_code == HTTPStatus.NOT_FOUND
        assert response.json() == {"detail": "User cards not found"}

    @pytest.mark.asyncio(loop_scope="session")
    async def test_get_user_card_for_anonymous_user(self, api_client) -> None:
        """Проверка на анонимного юзера."""
        response = await api_client.get(self.get_cards_path)

        assert response.status_code == HTTPStatus.FORBIDDEN
        assert response.json() == {"detail": "Not authenticated"}


@pytest.mark.asyncio(loop_scope="session")
async def test_get_card_form(api_client) -> None:
    """Проверка получения формы привязки карты."""
    form_path = "/api/v1/billing/get-card-form/"

    response = await api_client.get(form_path)
    assert response.status_code == HTTPStatus.OK
    assert response.headers["Content-Type"] == "text/html; charset=utf-8"


@pytest.mark.asyncio(loop_scope="session")
async def test_get_success_card(api_client) -> None:
    """Проверка получения шаблона успеха привязки карты."""
    form_path = "/api/v1/billing/success-card/"

    response = await api_client.get(form_path)
    assert response.status_code == HTTPStatus.OK
    assert response.headers["Content-Type"] == "text/html; charset=utf-8"


class TestInitializePaymentMethod:
    def setup_method(self):
        self.path = "/api/v1/billing/create-checkout-session/"

    @pytest.mark.asyncio(loop_scope="session")
    @patch("services.payment_process.PaymentProcessorStripe.create_card", new_callable=AsyncMock)
    async def test_initialize_payment_method(
        self, mock_create_card, api_client, access_token_user, test_session
    ) -> None:
        """Проверка успешного запроса на создание карты."""
        mock_create_card.return_value = "https://mocked.stripe.url/checkout"

        response = await api_client.post(self.path, headers=access_token_user)

        result = await test_session.execute(select(UserCardsStripe))
        cards = result.scalars().all()

        assert response.status_code == 303
        assert response.headers["location"] == "https://mocked.stripe.url/checkout"
        assert len(cards) == 1

    @pytest.mark.asyncio(loop_scope="session")
    async def test_initialize_payment_method_for_anonymous_user(self, api_client) -> None:
        """Проверка на анонимного юзера."""
        response = await api_client.post(self.path)

        assert response.status_code == HTTPStatus.FORBIDDEN
        assert response.json() == {"detail": "Not authenticated"}


class TestSetDefaultCard:
    def setup_method(self):
        self.path = "/api/v1/billing/set-default-card/?card_id={}"

    @pytest.mark.asyncio(loop_scope="session")
    async def test_success_set_default_card(self, test_session, api_client, access_token_user, user_card) -> None:
        """Успешное проставление дефолтной карты."""
        # создаем карты
        card = await user_card(StatusCardsEnum.SUCCESS, True)
        card_2 = await user_card(StatusCardsEnum.SUCCESS, False)

        response = await api_client.post(self.path.format(card_2.id), headers=access_token_user)

        # проверяем успешность ответа
        assert response.status_code == HTTPStatus.OK
        assert response.json() == {"detail": "success"}

        # обновляем данные
        await test_session.refresh(card)
        await test_session.refresh(card_2)

        # проверяем что другая карта действительно стала дефолтной
        assert not card.is_default
        assert card_2.is_default

    @pytest.mark.asyncio(loop_scope="session")
    async def test_not_success_another_user(self, api_client, access_token_another_user, user_card) -> None:
        """Проверка, что только хозяин может сделать карту дефолтной."""
        # создаем карты
        await user_card(StatusCardsEnum.SUCCESS, True)
        card_2 = await user_card(StatusCardsEnum.SUCCESS, False)

        response = await api_client.post(self.path.format(card_2.id), headers=access_token_another_user)

        assert response.status_code == HTTPStatus.FORBIDDEN
        assert response.json() == {"detail": "Forbidden"}

    @pytest.mark.asyncio(loop_scope="session")
    async def test_set_card_already_default(self, api_client, access_token_user, user_card) -> None:
        """Карта уже является дефолтной."""
        card = await user_card(StatusCardsEnum.SUCCESS, True)

        response = await api_client.post(self.path.format(card.id), headers=access_token_user)

        assert response.status_code == HTTPStatus.BAD_REQUEST
        assert response.json() == {"detail": "Card is already set as default"}

    @pytest.mark.asyncio(loop_scope="session")
    async def test_set_default_card_for_anonymous_user(self, api_client, user_card) -> None:
        """Доступ запрещен для анонимного юзера."""
        card = await user_card(StatusCardsEnum.SUCCESS, True)

        response = await api_client.post(self.path.format(card.id))

        assert response.status_code == HTTPStatus.FORBIDDEN
        assert response.json() == {"detail": "Not authenticated"}

    @pytest.mark.asyncio(loop_scope="session")
    async def test_set_default_not_found_card(self, api_client, access_token_user, user_card) -> None:
        """Карта не найдена."""
        card = await user_card(StatusCardsEnum.FAIL, True)

        response = await api_client.post(self.path.format(card.id), headers=access_token_user)

        assert response.status_code == HTTPStatus.NOT_FOUND
        assert response.json() == {"detail": "User card not found"}
