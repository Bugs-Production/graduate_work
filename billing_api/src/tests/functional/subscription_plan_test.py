import uuid
from http import HTTPStatus

import pytest
from httpx import AsyncClient

from models.models import SubscriptionPlan

SUBSCRIPTION_PLANS_ENDPOINT = "api/v1/subscription_plans/"


@pytest.mark.asyncio(loop_scope="session")
async def test_get_subscription_plans_empty(api_client: AsyncClient):
    response = await api_client.get(SUBSCRIPTION_PLANS_ENDPOINT)
    assert response.status_code == HTTPStatus.OK

    data = response.json()

    assert "items" in data
    assert len(data["items"]) == 0

    assert "total" in data
    assert data["total"] == 0


@pytest.mark.asyncio(loop_scope="session")
async def test_get_all_subscription_plans_pagination(
    api_client: AsyncClient, random_subscription_plans: list[SubscriptionPlan]
):
    active_subscription_plans = [plan for plan in random_subscription_plans if plan.is_archive == False]  # noqa: E712
    response = await api_client.get(f"{SUBSCRIPTION_PLANS_ENDPOINT}?page=1&size=2")
    assert response.status_code == HTTPStatus.OK

    data = response.json()
    assert data["total"] == len(active_subscription_plans)
    assert len(data["items"]) == 2
    assert data["page"] == 1
    assert data["size"] == 2

    first_item_title = data["items"][0]["title"]

    response = await api_client.get(f"{SUBSCRIPTION_PLANS_ENDPOINT}?page=2&size=2")
    data = response.json()

    assert data["page"] == 2
    assert data["size"] == 2
    assert first_item_title != data["items"][0]["title"]


@pytest.mark.asyncio(loop_scope="session")
async def test_get_subscription_plan_by_id_success(
    api_client: AsyncClient, random_subscription_plans: list[SubscriptionPlan]
):
    existing_plan = random_subscription_plans[0]

    response = await api_client.get(f"{SUBSCRIPTION_PLANS_ENDPOINT}{existing_plan.id}")
    assert response.status_code == HTTPStatus.OK

    data = response.json()
    assert data["id"] == str(existing_plan.id)
    assert data["title"] == existing_plan.title
    assert data["description"] == existing_plan.description
    assert data["price"] == existing_plan.price
    assert data["duration_days"] == existing_plan.duration_days
    assert data["is_archive"] == existing_plan.is_archive


@pytest.mark.asyncio(loop_scope="session")
async def test_get_subscription_plan_by_id_not_found(api_client: AsyncClient):
    non_existent_id = uuid.uuid4()
    response = await api_client.get(f"{SUBSCRIPTION_PLANS_ENDPOINT}{non_existent_id}")
    assert response.status_code == HTTPStatus.NOT_FOUND


@pytest.mark.asyncio(loop_scope="session")
async def test_get_subscription_plan_by_id_invalid_uuid(api_client: AsyncClient):
    response = await api_client.get(f"{SUBSCRIPTION_PLANS_ENDPOINT}invalid-uuid")
    assert response.status_code == HTTPStatus.UNPROCESSABLE_ENTITY
