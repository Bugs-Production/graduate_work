import uuid
from http import HTTPStatus

import pytest
from httpx import AsyncClient

from models.enums import SubscriptionStatus
from models.models import Subscription, SubscriptionPlan

SUBSCRIPTIONS_ENDPOINT = "api/v1/subscriptions/"


@pytest.mark.asyncio(loop_scope="session")
async def test_get_subscriptions_empty(api_client: AsyncClient, access_token_user: dict[str, str]):
    response = await api_client.get(SUBSCRIPTIONS_ENDPOINT, headers=access_token_user)
    assert response.status_code == HTTPStatus.OK

    data = response.json()
    assert "items" in data
    assert len(data["items"]) == 0
    assert "total" in data
    assert data["total"] == 0


@pytest.mark.asyncio(loop_scope="session")
async def test_get_all_subscriptions_pagination(
    api_client: AsyncClient, active_user_subscription: Subscription, access_token_user: dict[str, str]
):
    response = await api_client.get(f"{SUBSCRIPTIONS_ENDPOINT}?page=1&size=2", headers=access_token_user)
    assert response.status_code == HTTPStatus.OK

    data = response.json()
    assert len(data["items"]) == 1
    assert data["page"] == 1
    assert data["size"] == 2


@pytest.mark.asyncio(loop_scope="session")
async def test_get_subscription_by_id_success(
    api_client: AsyncClient, active_user_subscription: Subscription, access_token_user: dict[str, str]
):
    response = await api_client.get(f"{SUBSCRIPTIONS_ENDPOINT}{active_user_subscription.id}", headers=access_token_user)
    assert response.status_code == HTTPStatus.OK

    data = response.json()
    assert data["id"] == str(active_user_subscription.id)
    assert data["user_id"] == str(active_user_subscription.user_id)
    assert data["plan_id"] == str(active_user_subscription.plan_id)
    assert "status" in data


@pytest.mark.asyncio(loop_scope="session")
async def test_get_subscription_by_id_not_found(api_client: AsyncClient, access_token_user: dict[str, str]):
    non_existent_id = uuid.uuid4()
    response = await api_client.get(f"{SUBSCRIPTIONS_ENDPOINT}{non_existent_id}", headers=access_token_user)
    assert response.status_code == HTTPStatus.NOT_FOUND


@pytest.mark.asyncio(loop_scope="session")
async def test_create_subscription_success(
    api_client: AsyncClient, random_subscription_plans: list[SubscriptionPlan], access_token_user: dict[str, str]
):
    subscription_data = {"plan_id": str(random_subscription_plans[0].id), "auto_renewal": True}

    response = await api_client.post(SUBSCRIPTIONS_ENDPOINT, json=subscription_data, headers=access_token_user)
    assert response.status_code == HTTPStatus.CREATED

    data = response.json()
    assert data["plan_id"] == str(subscription_data["plan_id"])
    assert data["auto_renewal"] == subscription_data["auto_renewal"]
    assert data["status"] == SubscriptionStatus.PENDING.value
    assert "id" in data
    assert "start_date" in data
    assert "end_date" in data


@pytest.mark.asyncio(loop_scope="session")
async def test_create_subscription_invalid_plan(api_client: AsyncClient, access_token_user: dict[str, str]):
    subscription_data = {"plan_id": str(uuid.uuid4()), "auto_renewal": True}

    response = await api_client.post(SUBSCRIPTIONS_ENDPOINT, json=subscription_data, headers=access_token_user)
    assert response.status_code == HTTPStatus.NOT_FOUND


@pytest.mark.asyncio(loop_scope="session")
async def test_pay_for_subscription_success(
    api_client: AsyncClient, random_subscriptions: list[Subscription], access_token_user: dict[str, str]
):
    subscription = random_subscriptions[0]
    card_id = uuid.uuid4()

    response = await api_client.post(
        f"{SUBSCRIPTIONS_ENDPOINT}{subscription.id}/pay", params={"card_id": str(card_id)}, headers=access_token_user
    )
    assert response.status_code == HTTPStatus.OK

    data = response.json()
    assert "id" in data
    assert "status" in data
    assert "amount" in data


@pytest.mark.asyncio(loop_scope="session")
async def test_pay_for_subscription_not_found(api_client: AsyncClient, access_token_user: dict[str, str]):
    non_existent_id = uuid.uuid4()
    card_id = uuid.uuid4()

    response = await api_client.post(
        f"{SUBSCRIPTIONS_ENDPOINT}{non_existent_id}/pay", params={"card_id": str(card_id)}, headers=access_token_user
    )
    assert response.status_code == HTTPStatus.NOT_FOUND


@pytest.mark.asyncio(loop_scope="session")
async def test_cancel_subscription_success(
    api_client: AsyncClient, active_user_subscription: Subscription, access_token_user: dict[str, str]
):
    response = await api_client.post(
        f"{SUBSCRIPTIONS_ENDPOINT}{active_user_subscription.id}/cancel", headers=access_token_user
    )
    assert response.status_code == HTTPStatus.OK

    data = response.json()
    assert data["id"] == str(active_user_subscription.id)
    assert data["status"] == SubscriptionStatus.CANCELLED.value


@pytest.mark.asyncio(loop_scope="session")
async def test_renew_subscription_success(
    api_client: AsyncClient,
    active_user_subscription: Subscription,
    access_token_user: dict[str, str],
    random_subscription_plans: list[SubscriptionPlan],
):
    renew_data = {"plan_id": str(random_subscription_plans[0].id)}

    response = await api_client.post(
        f"{SUBSCRIPTIONS_ENDPOINT}{active_user_subscription.id}/renew", json=renew_data, headers=access_token_user
    )
    assert response.status_code == HTTPStatus.OK

    data = response.json()
    assert "id" in data
    assert data["status"] == SubscriptionStatus.PENDING.value
    assert "end_date" in data


@pytest.mark.asyncio(loop_scope="session")
async def test_toggle_auto_renewal_success(
    api_client: AsyncClient, active_user_subscription: Subscription, access_token_user: dict[str, str]
):
    initial_auto_renewal = active_user_subscription.auto_renewal

    response = await api_client.post(
        f"{SUBSCRIPTIONS_ENDPOINT}{active_user_subscription.id}/toggle_auto_renewal", headers=access_token_user
    )
    assert response.status_code == HTTPStatus.OK

    data = response.json()
    assert data["id"] == str(active_user_subscription.id)
    assert data["auto_renewal"] != initial_auto_renewal


@pytest.mark.asyncio(loop_scope="session")
async def test_unauthorized_access(api_client: AsyncClient):
    response = await api_client.get(SUBSCRIPTIONS_ENDPOINT)
    assert response.status_code == HTTPStatus.FORBIDDEN


@pytest.mark.asyncio(loop_scope="session")
async def test_forbidden_access_other_user_subscription(
    api_client: AsyncClient, random_subscriptions: list[Subscription], access_token_user: dict[str, str]
):
    other_user_subscription = random_subscriptions[-1]

    response = await api_client.get(f"{SUBSCRIPTIONS_ENDPOINT}{other_user_subscription.id}", headers=access_token_user)
    assert response.status_code == HTTPStatus.FORBIDDEN
