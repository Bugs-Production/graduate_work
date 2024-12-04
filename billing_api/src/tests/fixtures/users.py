from datetime import datetime, timedelta
from uuid import uuid4

import pytest_asyncio
from jose import jwt
from sqlalchemy.ext.asyncio import AsyncSession

from api.jwt_access_token import UserRole
from core.config import settings
from models.enums import StatusCardsEnum
from models.models import UserCardsStripe


def auth_header(user_role: UserRole) -> dict[str, str]:
    valid_till = datetime.now() + timedelta(hours=1)
    payload = {
        "user_id": str(uuid4()),
        "role": user_role.value,
        "iat": int(datetime.now().timestamp()),
        "exp": int(valid_till.timestamp()),
    }
    token = jwt.encode(payload, settings.jwt_secret_key, algorithm=settings.jwt_algorithm)
    return {"Authorization": f"Bearer {token}"}


@pytest_asyncio.fixture(loop_scope="session")
async def access_token_user() -> dict:
    return auth_header(UserRole.BASIC_USER)


@pytest_asyncio.fixture(loop_scope="session")
async def access_token_another_user() -> dict:
    return auth_header(UserRole.BASIC_USER)


@pytest_asyncio.fixture(loop_scope="session")
async def user_card(test_session: AsyncSession, access_token_user: dict) -> UserCardsStripe:
    async def _create_user_card(status: StatusCardsEnum, is_default: bool):
        token = access_token_user["Authorization"].split(" ")[1]
        payload = jwt.decode(token, settings.jwt_secret_key, algorithms=[settings.jwt_algorithm])
        user_id = payload["user_id"]

        new_card = UserCardsStripe(
            user_id=user_id,
            stripe_user_id="some_stripe_id",
            token_card="some_token",  # noqa: S106
            status=status,
            last_numbers_card="4242",
            is_default=is_default,
        )
        test_session.add(new_card)
        await test_session.commit()

        return new_card

    return _create_user_card


@pytest_asyncio.fixture(loop_scope="session")
async def admin_auth_header() -> dict[str, str]:
    return auth_header(UserRole.ADMIN)
