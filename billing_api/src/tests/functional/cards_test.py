from http import HTTPStatus

import pytest

from models.enums import StatusCardsEnum


class TestGetUserCards:
    def setup_method(self):
        self.get_cards_path = "/api/v1/billing/all-user-cards/"

    @pytest.mark.asyncio(loop_scope="session")
    async def test_get_success_cards_for_user(self, api_client, access_token_user, user_card) -> None:
        """Успешное получение карт юзера."""
        # создаем активную карту юзера
        card = await user_card(StatusCardsEnum.SUCCESS)

        # создаем еще одну, но с неуспешным статусом
        await user_card(StatusCardsEnum.FAIL)

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
