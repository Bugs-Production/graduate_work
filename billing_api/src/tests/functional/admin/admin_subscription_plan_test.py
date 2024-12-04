import uuid
from http import HTTPStatus

import pytest
from httpx import AsyncClient

from models.models import SubscriptionPlan

SUBSCRIPTION_PLANS_ENDPOINT = "api/v1/admin/subscription_plans/"


@pytest.mark.asyncio(loop_scope="session")
async def test_create_subscription_plan_success(api_client: AsyncClient, admin_auth_header: dict[str, str]):
    plan_data = {
        "title": "New Test Plan",
        "description": "Test description",
        "price": 1000,
        "duration_days": 30,
        "is_archive": False,
    }

    response = await api_client.post(SUBSCRIPTION_PLANS_ENDPOINT, json=plan_data, headers=admin_auth_header)
    assert response.status_code == HTTPStatus.CREATED

    data = response.json()
    assert data["title"] == plan_data["title"]
    assert data["description"] == plan_data["description"]
    assert data["price"] == plan_data["price"]
    assert data["duration_days"] == plan_data["duration_days"]
    assert data["is_archive"] == plan_data["is_archive"]
    assert "id" in data


@pytest.mark.asyncio(loop_scope="session")
async def test_create_subscription_plan_duplicate_title(
    api_client: AsyncClient, random_subscription_plans: list[SubscriptionPlan], admin_auth_header: dict[str, str]
):
    """Тест создания плана с дублирующимся названием"""
    existing_plan = random_subscription_plans[0]
    plan_data = {"title": existing_plan.title, "description": "Test description", "price": 1000, "duration_days": 30}

    response = await api_client.post(SUBSCRIPTION_PLANS_ENDPOINT, json=plan_data, headers=admin_auth_header)
    assert response.status_code == HTTPStatus.BAD_REQUEST


@pytest.mark.asyncio(loop_scope="session")
@pytest.mark.parametrize(
    "invalid_payload",
    [
        {
            "title": "Test",
            "price": 1000,
            "duration_days": 30,
        },
        {
            "title": "Test",
            "description": "Test description",
            "price": -100,
            "duration_days": 30,
        },
        {
            "title": "Test",
            "description": "Test description",
            "price": 1000,
            "duration_days": 0,
        },
    ],
)
async def test_create_subscription_plan_invalid_data(
    api_client: AsyncClient, invalid_payload: dict, admin_auth_header: dict[str, str]
):
    response = await api_client.post(SUBSCRIPTION_PLANS_ENDPOINT, json=invalid_payload, headers=admin_auth_header)
    assert response.status_code == HTTPStatus.UNPROCESSABLE_ENTITY


@pytest.mark.asyncio(loop_scope="session")
async def test_update_subscription_plan_success(
    api_client: AsyncClient, random_subscription_plans: list[SubscriptionPlan], admin_auth_header: dict[str, str]
):
    existing_plan = random_subscription_plans[0]
    update_data = {
        "title": "Updated Plan Title",
        "description": "Updated description",
        "price": 2000,
        "duration_days": 60,
        "is_archive": True,
    }

    response = await api_client.patch(
        f"{SUBSCRIPTION_PLANS_ENDPOINT}{existing_plan.id}", json=update_data, headers=admin_auth_header
    )
    assert response.status_code == HTTPStatus.OK

    data = response.json()
    assert data["id"] == str(existing_plan.id)
    assert data["title"] == update_data["title"]
    assert data["description"] == update_data["description"]
    assert data["price"] == update_data["price"]
    assert data["duration_days"] == update_data["duration_days"]
    assert data["is_archive"] == update_data["is_archive"]


@pytest.mark.asyncio(loop_scope="session")
async def test_update_subscription_plan_partial(
    api_client: AsyncClient, random_subscription_plans: list[SubscriptionPlan], admin_auth_header: dict[str, str]
):
    existing_plan = random_subscription_plans[1]
    update_data = {"price": 1500, "duration_days": 45}

    response = await api_client.patch(
        f"{SUBSCRIPTION_PLANS_ENDPOINT}{existing_plan.id}", json=update_data, headers=admin_auth_header
    )
    assert response.status_code == HTTPStatus.OK

    data = response.json()
    assert data["id"] == str(existing_plan.id)
    assert data["title"] == existing_plan.title
    assert data["description"] == existing_plan.description
    assert data["price"] == update_data["price"]
    assert data["duration_days"] == update_data["duration_days"]
    assert data["is_archive"] == existing_plan.is_archive


@pytest.mark.asyncio(loop_scope="session")
async def test_update_subscription_plan_duplicate_title(
    api_client: AsyncClient, random_subscription_plans: list[SubscriptionPlan], admin_auth_header: dict[str, str]
):
    plan_to_update = random_subscription_plans[2]
    existing_title = random_subscription_plans[3].title

    update_data = {"title": existing_title}

    response = await api_client.patch(
        f"{SUBSCRIPTION_PLANS_ENDPOINT}{plan_to_update.id}", json=update_data, headers=admin_auth_header
    )
    assert response.status_code == HTTPStatus.BAD_REQUEST


@pytest.mark.asyncio(loop_scope="session")
async def test_update_subscription_plan_not_found(api_client: AsyncClient, admin_auth_header: dict[str, str]):
    non_existent_id = uuid.uuid4()
    update_data = {"title": "New Title"}

    response = await api_client.patch(
        f"{SUBSCRIPTION_PLANS_ENDPOINT}{non_existent_id}", json=update_data, headers=admin_auth_header
    )
    assert response.status_code == HTTPStatus.NOT_FOUND


@pytest.mark.asyncio(loop_scope="session")
@pytest.mark.parametrize("invalid_payload", [{"price": -100}, {"duration_days": 0}, {"title": ""}, {"description": ""}])
async def test_update_subscription_plan_invalid_data(
    api_client: AsyncClient,
    random_subscription_plans: list[SubscriptionPlan],
    invalid_payload: dict,
    admin_auth_header: dict[str, str],
):
    existing_plan = random_subscription_plans[0]

    response = await api_client.patch(
        f"{SUBSCRIPTION_PLANS_ENDPOINT}{existing_plan.id}", json=invalid_payload, headers=admin_auth_header
    )
    assert response.status_code == HTTPStatus.UNPROCESSABLE_ENTITY


@pytest.mark.asyncio(loop_scope="session")
async def test_create_subscription_not_allowed_for_regular_user(
    api_client: AsyncClient, access_token_user: dict[str, str]
):
    plan_data = {
        "title": "New Test Plan N",
        "description": "Test description",
        "price": 1000,
        "duration_days": 30,
        "is_archive": False,
    }

    response = await api_client.post(SUBSCRIPTION_PLANS_ENDPOINT, json=plan_data, headers=access_token_user)
    assert response.status_code == HTTPStatus.FORBIDDEN


@pytest.mark.asyncio(loop_scope="session")
async def test_update_subscription_not_allowed_for_regular_user(
    api_client: AsyncClient, random_subscription_plans: list[SubscriptionPlan], access_token_user: dict[str, str]
):
    existing_plan = random_subscription_plans[0]
    update_data = {
        "title": "Updated Plan Title",
        "description": "Updated description",
        "price": 2000,
        "duration_days": 60,
        "is_archive": True,
    }

    response = await api_client.patch(
        f"{SUBSCRIPTION_PLANS_ENDPOINT}{existing_plan.id}", json=update_data, headers=access_token_user
    )
    assert response.status_code == HTTPStatus.FORBIDDEN
