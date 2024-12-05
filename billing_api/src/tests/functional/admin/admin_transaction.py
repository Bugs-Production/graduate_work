import uuid
from http import HTTPStatus

import pytest
import pytest_asyncio
from httpx import AsyncClient

from models.enums import PaymentType, TransactionStatus


class TestGetTransactions:
    def setup_method(self):
        self.transactions_url = "api/v1/admin/transactions/"

    @pytest_asyncio.fixture(loop_scope="session")
    async def transaction_id(self, random_transactions) -> str:
        random_transaction = random_transactions[1]
        return str(random_transaction.id)

    @pytest_asyncio.fixture(loop_scope="session")
    async def transaction_url(self, transaction_id) -> str:
        return f"{self.transactions_url}{transaction_id}"

    @pytest.mark.asyncio(loop_scope="session")
    async def test_get_transactions_urls_not_allowed_for_regular_user(
        self, api_client: AsyncClient, access_token_user: dict[str, str], transaction_url: str
    ):
        response_by_id = await api_client.get(transaction_url, headers=access_token_user)
        response_all = await api_client.get(self.transactions_url, headers=access_token_user)
        assert response_by_id.status_code == HTTPStatus.FORBIDDEN
        assert response_all.status_code == HTTPStatus.FORBIDDEN

    @pytest.mark.asyncio(loop_scope="session")
    async def test_get_transactions_urls_not_allowed_for_anonymous(self, api_client: AsyncClient, transaction_url: str):
        response_by_id = await api_client.get(transaction_url)
        response_all = await api_client.get(self.transactions_url)
        assert response_by_id.status_code == HTTPStatus.FORBIDDEN
        assert response_all.status_code == HTTPStatus.FORBIDDEN

    @pytest.mark.asyncio(loop_scope="session")
    async def test_get_transaction_by_id_not_found(
        self,
        api_client: AsyncClient,
        admin_auth_header: dict[str, str],
    ):
        url = f"{self.transactions_url}{uuid.uuid4()}"
        response = await api_client.get(url, headers=admin_auth_header)

        assert response.status_code == HTTPStatus.NOT_FOUND

    @pytest.mark.asyncio(loop_scope="session")
    async def test_get_transaction_by_id_allowed_for_admin(
        self, api_client: AsyncClient, admin_auth_header: dict[str, str], transaction_id: str, transaction_url: str
    ):
        response = await api_client.get(transaction_url, headers=admin_auth_header)
        data = response.json()

        assert response.status_code == HTTPStatus.OK
        assert data["id"] == transaction_id

    @pytest.mark.asyncio(loop_scope="session")
    async def test_get_transactions_paginated(
        self, api_client: AsyncClient, admin_auth_header: dict[str, str], random_transactions
    ):
        response = await api_client.get(f"{self.transactions_url}?page=1&size=1", headers=admin_auth_header)
        data = response.json()

        assert response.status_code == HTTPStatus.OK
        assert data["total"] == len(random_transactions)
        assert len(data["items"]) == 1
        assert data["page"] == 1
        assert data["size"] == 1

        response = await api_client.get(f"{self.transactions_url}?page=2&size=1", headers=admin_auth_header)
        data = response.json()

        assert response.status_code == HTTPStatus.OK
        assert data["total"] == len(random_transactions)
        assert len(data["items"]) == 1
        assert data["page"] == 2
        assert data["size"] == 1

    @pytest.mark.asyncio(loop_scope="session")
    async def test_get_transactions_with_filter_params(
        self, api_client: AsyncClient, admin_auth_header: dict[str, str], random_transactions
    ):
        payment_type = PaymentType.STRIPE.value
        status = TransactionStatus.SUCCESS.value
        filtered_url = f"{self.transactions_url}?status={status}&payment_type={payment_type}"
        filtered_transactions = [
            tr for tr in random_transactions if (tr.status == status and tr.payment_type == payment_type)
        ]
        response = await api_client.get(f"{filtered_url}", headers=admin_auth_header)
        data = response.json()

        assert response.status_code == HTTPStatus.OK
        assert data["total"] == len(filtered_transactions)
        assert len(data["items"]) == len(filtered_transactions)
