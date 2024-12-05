import uuid
from http import HTTPStatus

import pytest
import pytest_asyncio
from httpx import AsyncClient

from models.enums import StatusCardsEnum


class TestGetUserCards:
    def setup_method(self):
        self.user_cards_url = "api/v1/admin/user_cards/"

    @pytest_asyncio.fixture(loop_scope="session")
    async def card_id(self, random_user_cards) -> str:
        random_card = random_user_cards[1]
        return str(random_card.id)

    @pytest_asyncio.fixture(loop_scope="session")
    async def card_url(self, card_id) -> str:
        return f"{self.user_cards_url}{card_id}"

    @pytest.mark.asyncio(loop_scope="session")
    async def test_get_user_cards_urls_not_allowed_for_regular_user(
        self, api_client: AsyncClient, access_token_user: dict[str, str], card_url: str
    ):
        response_by_id = await api_client.get(card_url, headers=access_token_user)
        response_all = await api_client.get(self.user_cards_url, headers=access_token_user)
        assert response_by_id.status_code == HTTPStatus.FORBIDDEN
        assert response_all.status_code == HTTPStatus.FORBIDDEN

    @pytest.mark.asyncio(loop_scope="session")
    async def test_get_user_cards_urls_not_allowed_for_anonymous(self, api_client: AsyncClient, card_url: str):
        response_by_id = await api_client.get(card_url)
        response_all = await api_client.get(self.user_cards_url)
        assert response_by_id.status_code == HTTPStatus.FORBIDDEN
        assert response_all.status_code == HTTPStatus.FORBIDDEN

    @pytest.mark.asyncio(loop_scope="session")
    async def test_get_user_card_by_id_not_found(
        self,
        api_client: AsyncClient,
        admin_auth_header: dict[str, str],
    ):
        url = f"{self.user_cards_url}{uuid.uuid4()}"
        response = await api_client.get(url, headers=admin_auth_header)

        assert response.status_code == HTTPStatus.NOT_FOUND

    @pytest.mark.asyncio(loop_scope="session")
    async def test_get_user_card_by_id_allowed_for_admin(
        self, api_client: AsyncClient, admin_auth_header: dict[str, str], card_id: str, card_url: str
    ):
        response = await api_client.get(card_url, headers=admin_auth_header)
        data = response.json()

        assert response.status_code == HTTPStatus.OK
        assert data["id"] == card_id

    @pytest.mark.asyncio(loop_scope="session")
    async def test_get_user_cards_paginated(
        self, api_client: AsyncClient, admin_auth_header: dict[str, str], random_user_cards
    ):
        response = await api_client.get(f"{self.user_cards_url}?page=1&size=1", headers=admin_auth_header)
        data = response.json()

        assert response.status_code == HTTPStatus.OK
        assert data["total"] == len(random_user_cards)
        assert len(data["items"]) == 1
        assert data["page"] == 1
        assert data["size"] == 1

        response = await api_client.get(f"{self.user_cards_url}?page=2&size=1", headers=admin_auth_header)
        data = response.json()

        assert response.status_code == HTTPStatus.OK
        assert data["total"] == len(random_user_cards)
        assert len(data["items"]) == 1
        assert data["page"] == 2
        assert data["size"] == 1

    @pytest.mark.asyncio(loop_scope="session")
    async def test_get_user_cards_with_filter_params(
        self, api_client: AsyncClient, admin_auth_header: dict[str, str], random_user_cards
    ):
        is_default = True
        status = StatusCardsEnum.SUCCESS.value
        filtered_url = f"{self.user_cards_url}?status={status}&is_default={is_default}"
        filtered_cards = [
            card for card in random_user_cards if (card.status == status and card.is_default == is_default)
        ]
        response = await api_client.get(f"{filtered_url}", headers=admin_auth_header)
        data = response.json()

        if len(filtered_cards) == 0:
            assert response.status_code == HTTPStatus.NOT_FOUND
        else:
            assert response.status_code == HTTPStatus.OK
            assert data["total"] == len(filtered_cards)
            assert len(data["items"]) == len(filtered_cards)
