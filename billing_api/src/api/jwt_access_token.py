import enum
from uuid import UUID

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import jwt
from jose.exceptions import ExpiredSignatureError, JWTError
from pydantic import BaseModel, ValidationError

from core.config import settings


class UserRole(enum.Enum):
    ADMIN = "admin"
    BASIC_USER = "basic_user"
    SUBSCRIBER = "subscriber"

    @classmethod
    def values(cls):
        return [status.value for status in cls]


class AccessTokenPayload(BaseModel):
    user_id: UUID
    role: UserRole
    iat: int
    exp: int


class JWTBearer(HTTPBearer):
    def __init__(self, auto_error: bool = True):
        super().__init__(auto_error=auto_error)

    async def __call__(self, request: Request) -> AccessTokenPayload:
        credentials: HTTPAuthorizationCredentials = await super().__call__(request)
        if not credentials:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Invalid authorization code.",
            )
        if credentials.scheme != "Bearer":
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Only Bearer token might be accepted",
            )

        return await self.decode_and_parse_token(credentials.credentials)

    @staticmethod
    async def decode_and_parse_token(jwt_token: str) -> AccessTokenPayload:
        try:
            decoded_token = jwt.decode(jwt_token, settings.jwt_secret_key, algorithms=[settings.jwt_algorithm])
        except ExpiredSignatureError:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Access token is expired",
            ) from None
        except JWTError:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid format for JWT token",
            ) from None
        try:
            access_token = AccessTokenPayload(**decoded_token)
        except ValidationError as exc:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=f"Access token is invalid: {exc}",
            ) from None
        return access_token


security_jwt = JWTBearer()


async def require_admin(access_token: AccessTokenPayload = Depends(security_jwt)):
    if access_token.role != UserRole.ADMIN:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Operation allowed only for admin users",
        )
