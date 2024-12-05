import uuid
from http import HTTPStatus

import pytest
import pytest_asyncio
from httpx import AsyncClient

from models.enums import SubscriptionStatus


class TestSubscriptions:
    def setup_method(self):
        self.subscriptions_url = "api/v1/admin/subscriptions/"

    @pytest_asyncio.fixture(loop_scope="session")
    async def subscription_id(self, random_subscriptions) -> str:
        random_subscription = random_subscriptions[1]
        return str(random_subscription.id)

    @pytest_asyncio.fixture(loop_scope="session")
    async def subscription_url(self, subscription_id) -> str:
        return f"{self.subscriptions_url}{subscription_id}"

    @pytest.mark.asyncio(loop_scope="session")
    async def test_get_subscriptions_urls_not_allowed_for_regular_user(
        self, api_client: AsyncClient, access_token_user: dict[str, str], subscription_url: str
    ):
        response_by_id = await api_client.get(subscription_url, headers=access_token_user)
        response_all = await api_client.get(self.subscriptions_url, headers=access_token_user)
        assert response_by_id.status_code == HTTPStatus.FORBIDDEN
        assert response_all.status_code == HTTPStatus.FORBIDDEN

    @pytest.mark.asyncio(loop_scope="session")
    async def test_get_subscriptions_urls_not_allowed_for_anonymous(
        self, api_client: AsyncClient, subscription_url: str
    ):
        response_by_id = await api_client.get(subscription_url)
        response_all = await api_client.get(self.subscriptions_url)
        assert response_by_id.status_code == HTTPStatus.FORBIDDEN
        assert response_all.status_code == HTTPStatus.FORBIDDEN

    @pytest.mark.asyncio(loop_scope="session")
    async def test_get_subscription_by_id_not_found(
        self,
        api_client: AsyncClient,
        admin_auth_header: dict[str, str],
    ):
        url = f"{self.subscriptions_url}{uuid.uuid4()}"
        response = await api_client.get(url, headers=admin_auth_header)

        assert response.status_code == HTTPStatus.NOT_FOUND

    @pytest.mark.asyncio(loop_scope="session")
    async def test_get_subscription_by_id_allowed_for_admin(
        self, api_client: AsyncClient, admin_auth_header: dict[str, str], subscription_id: str, subscription_url: str
    ):
        response = await api_client.get(subscription_url, headers=admin_auth_header)
        data = response.json()

        assert response.status_code == HTTPStatus.OK
        assert data["id"] == subscription_id

    @pytest.mark.asyncio(loop_scope="session")
    async def test_get_subscriptions_paginated(
        self, api_client: AsyncClient, admin_auth_header: dict[str, str], random_subscriptions
    ):
        response = await api_client.get(f"{self.subscriptions_url}?page=1&size=1", headers=admin_auth_header)
        data = response.json()

        assert response.status_code == HTTPStatus.OK
        assert data["total"] == len(random_subscriptions)
        assert len(data["items"]) == 1
        assert data["page"] == 1
        assert data["size"] == 1

        response = await api_client.get(f"{self.subscriptions_url}?page=2&size=1", headers=admin_auth_header)
        data = response.json()

        assert response.status_code == HTTPStatus.OK
        assert data["total"] == len(random_subscriptions)
        assert len(data["items"]) == 1
        assert data["page"] == 2
        assert data["size"] == 1

    @pytest.mark.asyncio(loop_scope="session")
    async def test_get_subscriptions_with_filter_params(
        self, api_client: AsyncClient, admin_auth_header: dict[str, str], random_subscriptions
    ):
        status = SubscriptionStatus.ACTIVE.value
        auto_renewal = False
        filtered_url = f"{self.subscriptions_url}?status={status}&auto_renewal={auto_renewal}"
        filtered_subscriptions = [
            sub for sub in random_subscriptions if (sub.status == status and sub.auto_renewal == auto_renewal)
        ]
        response = await api_client.get(f"{filtered_url}", headers=admin_auth_header)
        data = response.json()

        assert response.status_code == HTTPStatus.OK
        assert data["total"] == len(filtered_subscriptions)
        assert len(data["items"]) == len(filtered_subscriptions)

    @pytest.mark.asyncio(loop_scope="session")
    async def test_create_subscription_success(
        self, api_client: AsyncClient, admin_auth_header: dict[str, str], random_subscription_plans
    ):
        plan = random_subscription_plans[0]
        subs_data = {
            "user_id": str(uuid.uuid4()),
            "plan_id": str(plan.id),
            "auto_renewal": False,
        }

        response = await api_client.post(self.subscriptions_url, json=subs_data, headers=admin_auth_header)
        assert response.status_code == HTTPStatus.CREATED

        data = response.json()
        assert data["user_id"] == subs_data["user_id"]
        assert data["plan_id"] == subs_data["plan_id"]
        assert data["auto_renewal"] == subs_data["auto_renewal"]
        assert "id" in data

    @pytest.mark.asyncio(loop_scope="session")
    @pytest.mark.parametrize(
        "invalid_payload",
        [
            {},
            {
                "user_id": "111",
                "plan_id": "9e83f000-26d5-4258-aa92-d30d17f2fde1",
                "auto_renewal": True,
            },
            {
                "user_id": "9e83f000-26d5-4258-aa92-d30d17f2fde1",
                "plan_id": "111",
                "auto_renewal": True,
            },
            {
                "plan_id": "9e83f000-26d5-4258-aa92-d30d17f2fde1",
                "auto_renewal": False,
            },
        ],
    )
    async def test_create_subscription_invalid_data(
        self, api_client: AsyncClient, invalid_payload: dict, admin_auth_header: dict[str, str]
    ):
        response = await api_client.post(self.subscriptions_url, json=invalid_payload, headers=admin_auth_header)
        assert response.status_code == HTTPStatus.UNPROCESSABLE_ENTITY
